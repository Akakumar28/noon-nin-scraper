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

# Define base download directory
BASE_DOWNLOAD_DIR = r"C:\Users\akash\OneDrive\Desktop\Noon Nins"
if not os.path.exists(BASE_DOWNLOAD_DIR):
    os.makedirs(BASE_DOWNLOAD_DIR)

def get_product_details(nin, category_name, region="uae"):
    """Fetch product details from Noon using Selenium and extract high-resolution images."""

    search_url = f"https://www.noon.com/{region}-en/{nin}/p/?o={nin.lower()}-12"
    print(f"Fetching product data from: {search_url}")

    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(search_url)

        wait = WebDriverWait(driver, 10)

        # Extract Product Name
        try:
            product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            product_name = "Unknown"

        # Extract Product Link
        product_url = search_url

        # Extract High-Resolution Image
        try:
            # Locate all product thumbnails
            thumbnails = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".swiper-slide img")))
            
            if thumbnails:
                # Click on the first thumbnail
                thumbnails[0].click()
                time.sleep(2)

                # Wait for the high-resolution image to load
                active_image = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".swiper-slide-active img")))
                image_url = active_image.get_attribute("src")

                # Remove query parameters for high-resolution image
                image_url = image_url.split("?")[0]

            else:
                print(f"⚠️ No valid image found for {nin}, using placeholder.")
                image_url = f"https://f.nooncdn.com/p/pnsku/{nin}/45/_/1722414094/image.jpg"

        except:
            image_url = f"https://f.nooncdn.com/p/pnsku/{nin}/45/_/1722414094/image.jpg"

        driver.quit()

        print(f"✅ Scraped Product: {product_name} - {product_url}")
        print(f"✅ High-Resolution Image URL: {image_url}")

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

def download_images(nins, category_name, region="uae"):
    """Download all images for given NINs and save in a category-based folder."""
    category_folder = os.path.join(BASE_DOWNLOAD_DIR, category_name)
    os.makedirs(category_folder, exist_ok=True)

    zip_filename = f"{category_name}_images.zip"
    zip_path = os.path.join(BASE_DOWNLOAD_DIR, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for nin in nins:
            product = get_product_details(nin, category_name, region)
            if product:
                image_path = os.path.join(category_folder, f"{nin}.png")
                img_data = requests.get(product["image_url"]).content
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
                zipf.write(image_path, os.path.basename(image_path))

    print(f"✅ ZIP file created: {zip_path}")
    return zip_path

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/fetch", methods=["POST"])
def fetch():
    """Handle product fetching from Noon based on input NINs."""
    data = request.json
    print("Received request:", data)
    nins = data.get("nins", [])
    category_name = data.get("category_name", "Default_Category")  # Default fallback
    region = data.get("region", "uae")

    if not nins:
        return jsonify({"error": "No NINs provided"}), 400

    products = []
    for nin in nins:
        product = get_product_details(nin, category_name, region)
        if product:
            products.append(product)

    print("Returning products:", products)
    return jsonify(products)

@app.route("/upload", methods=["POST"])
def upload():
    """Handle Excel file upload and extract NINs to fetch product details."""
    file = request.files["file"]
    category_name = request.form.get("category_name", "Default_Category")  # Default fallback
    region = request.form.get("region", "uae")

    df = pd.read_excel(file)
    nins = df.iloc[:, 0].dropna().astype(str).tolist()
    
    zip_path = download_images(nins, category_name, region)
    return send_file(zip_path, as_attachment=True)

@app.route("/download_zip/<category_name>", methods=["GET"])
@app.route("/download_zip/<category_name>", methods=["GET"])
def download_zip(category_name):
    """Allow downloading the ZIP file from a category folder."""
    zip_path = os.path.join(BASE_DOWNLOAD_DIR, f"{category_name}_images.zip")

    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True)
    else:
        return jsonify({"error": "ZIP file not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
