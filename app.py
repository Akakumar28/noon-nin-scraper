from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import requests
import zipfile
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import shutil

app = Flask(__name__, template_folder="templates", static_folder="static")

# Auto-detect user's Downloads folder
DEFAULT_DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def get_product_details(nin, category_name, region="uae"):
    """Fetch high-resolution product details & images from Noon using Selenium."""
    product_url = f"https://www.noon.com/{region}-en/{nin}/p/?o={nin.lower()}-1"
    print(f"Fetching product details from: {product_url}")

    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("window-size=1920x1080")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--start-maximized")
        options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # ✅ Fix: Check and fallback for chrome binary with debugging
        print("🔍 Checking for Chrome binary...")
        chromium_path = shutil.which("chromium")
        google_chrome_path = shutil.which("google-chrome")
        chromium_browser_path = shutil.which("chromium-browser")
        
        print(f"  - chromium: {chromium_path}")
        print(f"  - google-chrome: {google_chrome_path}")
        print(f"  - chromium-browser: {chromium_browser_path}")
        
        chrome_path = chromium_path or google_chrome_path or chromium_browser_path
        if not chrome_path:
            print("❌ Chrome binary not found in PATH")
            print("Current PATH:", os.environ.get("PATH"))
            print("Checking common locations:")
            common_paths = [
                "/usr/bin/chromium",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chrome",
                "/usr/local/bin/chromium",
                "/usr/local/bin/google-chrome"
            ]
            for path in common_paths:
                if os.path.exists(path):
                    print(f"✅ Found Chrome at: {path}")
                    chrome_path = path
                    break
                else:
                    print(f"❌ Not found: {path}")
            
            if not chrome_path:
                print("⚠️ Chrome binary not found. Trying fallback approach...")
                # Fallback: Try using undetected_chromedriver without specifying binary location
                try:
                    print("Attempting to use undetected_chromedriver without specifying binary location...")
                    driver = uc.Chrome(options=options)
                    driver.get(product_url)
                    wait = WebDriverWait(driver, 10)
                    
                    # Extract Product Name
                    try:
                        product_name = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text.strip()
                    except:
                        product_name = "Unknown"

                    # Extract product image from Noon
                    image_elements = driver.find_elements(By.CSS_SELECTOR, "img")
                    image_url = None

                    for img in image_elements:
                        src = img.get_attribute("src")
                        if src and "nooncdn.com/p/pnsku" in src and "svg" not in src:
                            image_url = src.split("?")[0]  # Remove query parameters for highest resolution
                            break  # Stop at the first valid image

                    if not image_url:
                        print("❌ No valid image found. Using default placeholder.")
                        image_url = f"https://f.nooncdn.com/p/pnsku/{nin}/45/_/1722414094/image.jpg"

                    driver.quit()

                    print(f"✅ Scraped Product: {product_name}")
                    print(f"✅ Image URL: {image_url}")

                    return {
                        "nin": nin,
                        "product_name": product_name,
                        "product_url": product_url,
                        "image_url": image_url,
                        "category_name": category_name
                    }
                except Exception as e:
                    print(f"❌ Fallback approach failed: {str(e)}")
                    raise Exception("❌ Chromium binary not found and fallback approach failed. Cannot proceed.")
        
        print(f"✅ Using Chrome binary: {chrome_path}")
        options.binary_location = chrome_path

        driver = uc.Chrome(options=options)
        driver.get(product_url)
        wait = WebDriverWait(driver, 10)

        # Extract Product Name
        try:
            product_name = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text.strip()
        except:
            product_name = "Unknown"

        # Extract product image from Noon
        image_elements = driver.find_elements(By.CSS_SELECTOR, "img")
        image_url = None

        for img in image_elements:
            src = img.get_attribute("src")
            if src and "nooncdn.com/p/pnsku" in src and "svg" not in src:
                image_url = src.split("?")[0]  # Remove query parameters for highest resolution
                break  # Stop at the first valid image

        if not image_url:
            print("❌ No valid image found. Using default placeholder.")
            image_url = f"https://f.nooncdn.com/p/pnsku/{nin}/45/_/1722414094/image.jpg"

        driver.quit()

        print(f"✅ Scraped Product: {product_name}")
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
    """Fetch high-quality product images from Google Images."""
    search_url = f"https://www.google.com/search?tbm=isch&q={product_name.replace(' ', '+')}+product+photo"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=5)
        image_urls = re.findall(r'"https://[^"]*\.jpg"', response.text)

        # ✅ Filter out stock images, watermarks, and logos
        filtered_images = [
            url.strip('"') for url in image_urls
            if "shutterstock" not in url and "logo" not in url and "stock" not in url
        ]

        return filtered_images[:5] if filtered_images else ["https://via.placeholder.com/150"]

    except Exception as e:
        print(f"❌ Google Images Fetching Failed: {str(e)}")
        return ["https://via.placeholder.com/150"]


@app.route("/fetch", methods=["POST"])
def fetch():
    """Fetch product details from Noon & Google Images when requested."""
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
            product["google_images"] = get_google_images(product["product_name"])
            products.append(product)

    return jsonify(products)


@app.route("/upload", methods=["POST"])
def upload():
    """Process Excel file, extract NINs, fetch product details & allow ZIP download."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        df = pd.read_excel(file)
        nins = df.iloc[:, 0].dropna().astype(str).tolist()
        if not nins:
            return jsonify({"error": "No NINs found in Excel file"}), 400

        products = [get_product_details(nin, "Default_Category") for nin in nins if get_product_details(nin, "Default_Category")]

        return jsonify({"products": products})

    except Exception as e:
        print(f"❌ Error processing Excel file: {str(e)}")
        return jsonify({"error": "Failed to process Excel file"}), 500


@app.route("/download_zip", methods=["POST"])
def download_zip():
    """Download images into a ZIP file."""
    data = request.json
    nins = data.get("nins", [])
    google_images = data.get("google_images", [])
    category_name = data.get("category_name", "Default_Category")

    if not nins and not google_images:
        return jsonify({"error": "No images selected"}), 400

    category_folder = os.path.join(DEFAULT_DOWNLOAD_DIR, category_name)
    os.makedirs(category_folder, exist_ok=True)

    zip_filename = f"{category_name}_images.zip"
    zip_path = os.path.join(DEFAULT_DOWNLOAD_DIR, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # ✅ Download Noon Images
        for nin in nins:
            product = get_product_details(nin, category_name)
            if product:
                image_path = os.path.join(category_folder, f"{nin}.jpg")
                img_data = requests.get(product["image_url"]).content
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
                zipf.write(image_path, os.path.basename(image_path))

        # ✅ Download Google Images
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
