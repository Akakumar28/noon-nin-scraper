from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import requests
import zipfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

app = Flask(__name__, template_folder="templates", static_folder="static")

# Detect the user's default Downloads folder
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
# Define the download folder
DOWNLOAD_FOLDER = "/Users/akakumar/Desktop/nin-auto-down"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_product_details(nin, category_name, region="uae"):
    """Fetch product details from Noon using Selenium and extract high-resolution images."""
    search_url = f"https://www.noon.com/{region}-en/{nin}/p/?o={nin.lower()}-1"
    print(f"Fetching product data from: {search_url}")

    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(search_url)

        wait = WebDriverWait(driver, 10)

        # Extract Product Name
        try:
            product_name = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text.strip()
        except:
            product_name = "Unknown"

        product_url = search_url

        # Extract High-Resolution Image
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".swiper-slide-active img")))
            
            image_url = driver.execute_script(
                "return document.querySelector('.swiper-slide-active img')?.src || '';"
            )

            if not image_url or "svg" in image_url or "placeholder" in image_url:
                print(f"⚠️ Placeholder image detected. Retrying with a different method...")
                thumbnails = driver.find_elements(By.CSS_SELECTOR, ".swiper-slide img")
                if thumbnails:
                    thumbnails[0].click()
                    time.sleep(2)
                    image_url = driver.execute_script(
                        "return document.querySelector('.swiper-slide-active img')?.src || '';"
                    )

            image_url = image_url.split("?")[0] if image_url else None

        except:
            print("❌ No valid image found. Using default placeholder.")
            image_url = f"https://f.nooncdn.com/p/pnsku/{nin}/45/_/1722414094/image.jpg"

        driver.quit()

        print(f"✅ Scraped Product: {product_name} - {product_url}")
        print(f"✅ Image URL: {image_url}")

        return {
            "nin": nin,
            "product_name": product_name,
            "product_url": product_url,
            "image_url": image_url,
            "category_name": category_name
        }

    except Exception as e:
        print(f"❌ Error in get_product_details: {str(e)}")
        return None
    
    

def get_google_images(product_name):
    """Fetch high-resolution product images from Google Images, filtering out irrelevant ones."""
    search_url = f"https://www.google.com/search?tbm=isch&q={product_name.replace(' ', '+')}+product"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(search_url)

        wait = WebDriverWait(driver, 10)

        # Scroll down to load more images
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Allow images to load

        # Wait for image elements to appear
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img")))

        # Extract image URLs
        image_urls = []
        images = driver.find_elements(By.CSS_SELECTOR, "img")

        for img in images[:10]:  # Fetch first 10 images (filter out non-product ones)
            img_url = img.get_attribute("src")
            if not img_url:
                img_url = img.get_attribute("data-src")

            # Ensure we get only high-quality product images (not logos, UI elements)
            if img_url and "https" in img_url and "google" not in img_url.lower() and "logo" not in img_url.lower():
                image_urls.append(img_url)

        driver.quit()

        # If no product images found, return a placeholder
        return image_urls[:5] if image_urls else ["https://via.placeholder.com/150"]

    except Exception as e:
        print(f"❌ Error fetching Google images: {str(e)}")
        return ["https://via.placeholder.com/150"]  # Default image in case of failure



@app.route("/fetch", methods=["POST"])
def fetch():
    """Fetches product details from Noon and Google Images, ensuring high quality."""
    data = request.json
    print("Received request:", data)
    nins = data.get("nins", [])
    region = data.get("region", "uae")

    if not nins:
        return jsonify({"error": "No NINs provided"}), 400

    products = []
    for nin in nins:
        product = get_product_details(nin, "Default_Category", region)
        if product:
            # Fetch relevant images from Google
            google_images = get_google_images(product["product_name"])
            product["google_images"] = google_images
            products.append(product)

    print("Returning products:", products)
    return jsonify(products)





@app.route("/upload", methods=["POST"])
def upload():
    """Handles Excel file upload, extracts NINs, fetches product details, and creates a ZIP."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    category_name = request.form.get("category_name", "Default_Category")
    region = request.form.get("region", "uae")

    try:
        df = pd.read_excel(file)  
        nins = df.iloc[:, 0].dropna().astype(str).tolist()

        if not nins:
            return jsonify({"error": "No NINs found in the Excel file"}), 400

        print(f"✅ Extracted NINs from Excel: {nins}")

        products = []
        for nin in nins:
            product = get_product_details(nin, category_name, region)
            if product:
                products.append(product)

        return jsonify({"products": products})

    except Exception as e:
        print(f"❌ Error processing Excel file: {str(e)}")
        return jsonify({"error": "Failed to process Excel file"}), 500

@app.route("/download_zip", methods=["POST"])
def download_zip():
    """Download selected Noon & Google images into a ZIP and send to user."""
    data = request.json
    nins = data.get("nins", [])
    google_images = data.get("google_images", [])  # Selected Google images
    category_name = data.get("category_name", "Default_Category")
    region = data.get("region", "uae")

    if not nins and not google_images:
        return jsonify({"error": "No images selected"}), 400

    category_folder = os.path.join(DEFAULT_DOWNLOAD_DIR, category_name)
    os.makedirs(category_folder, exist_ok=True)

    zip_filename = f"{category_name}_images.zip"
    zip_path = os.path.join(DEFAULT_DOWNLOAD_DIR, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Download Noon Images
        for nin in nins:
            product = get_product_details(nin, category_name, region)
            if product:
                image_path = os.path.join(category_folder, f"{nin}.jpg")
                img_data = requests.get(product["image_url"]).content
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
                zipf.write(image_path, os.path.basename(image_path))

        # Download Selected Google Images
        for idx, img_url in enumerate(google_images):
            google_image_path = os.path.join(category_folder, f"google_image_{idx}.jpg")
            img_data = requests.get(img_url).content
            with open(google_image_path, "wb") as img_file:
                img_file.write(img_data)
            zipf.write(google_image_path, os.path.basename(google_image_path))

    print(f"✅ ZIP file created: {zip_path}")
    return send_file(zip_path, as_attachment=True)




@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
