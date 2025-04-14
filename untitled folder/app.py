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
# Define the download folder at the top
DOWNLOAD_FOLDER = "/Users/akakumar/Desktop/nin-auto-down"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_product_details(nin, category_name, region="uae"):
    """Fetch product details from Noon using Selenium and extract high-resolution images."""
    search_url = f"https://www.noon.com/{region}-en/{nin}/p/?o={nin.lower()}-1"
    print(f"Fetching product data from: {search_url}")

    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode
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

        # Extract High-Resolution Image using JavaScript
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".swiper-slide-active img")))
            
            image_url = driver.execute_script(
                "return document.querySelector('.swiper-slide-active img')?.src || '';"
            )

            # If image is missing, look for the main product image
            if not image_url or "svg" in image_url or "placeholder" in image_url:
                print(f"⚠️ Placeholder image detected. Retrying with a different method...")
                
                # Try fetching image from first available thumbnail
                thumbnails = driver.find_elements(By.CSS_SELECTOR, ".swiper-slide img")
                if thumbnails:
                    thumbnails[0].click()
                    time.sleep(2)
                    image_url = driver.execute_script(
                        "return document.querySelector('.swiper-slide-active img')?.src || '';"
                    )

            # Remove unnecessary URL parameters
            image_url = image_url.split("?")[0] if image_url else None

        except Exception as e:
            print(f"❌ No valid image found. Using default placeholder. Error: {e}")
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



@app.route("/fetch", methods=["POST"])
def fetch():
    """Fetches product details WITHOUT downloading images."""
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
            products.append(product)

    print("Returning products:", products)
    return jsonify(products)

@app.route("/download_zip", methods=["POST"])
def download_zip():
    """Download images only when ZIP button is clicked, then return ZIP."""
    data = request.json
    nins = data.get("nins", [])
    category_name = data.get("category_name", "Default_Category")
    region = data.get("region", "uae")

    if not nins:
        return jsonify({"error": "No NINs provided"}), 400

    category_folder = os.path.join(DEFAULT_DOWNLOAD_DIR, category_name)
    os.makedirs(category_folder, exist_ok=True)

    zip_filename = f"{category_name}_images.zip"
    zip_path = os.path.join(DEFAULT_DOWNLOAD_DIR, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for nin in nins:
            product = get_product_details(nin, category_name, region)
            if product:
                image_path = os.path.join(category_folder, f"{nin}.jpg")
                img_data = requests.get(product["image_url"]).content
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
                zipf.write(image_path, os.path.basename(image_path))

    print(f"✅ ZIP file created: {zip_path}")
    return send_file(zip_path, as_attachment=True)

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
