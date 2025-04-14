import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Get category name from user input
category_name = input("Enter category name: ")

# Get NIN codes from user input
nin_codes_input = input("Enter NIN codes separated by space: ")
nin_codes = nin_codes_input.split()

# Base directory to save images
base_directory = os.path.join(r"C:\Users\akash\OneDrive\Desktop\Noon Nins", category_name)
os.makedirs(base_directory, exist_ok=True)
print(f"Images will be saved to: {base_directory}")

# Set up Selenium WebDriver
options = Options()
options.headless = True  # Run in headless mode
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

for nin in nin_codes:
    url = f"https://www.noon.com/uae-en/{nin}/p/?o={nin.lower()}-12"
    driver.get(url)
    print(f"Accessing URL: {url}")
    time.sleep(2)  # Wait for page to load

    try:
        # Find the first image thumbnail and click on it
        thumbnail = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".swiper-slide img")))
        thumbnail.click()
        time.sleep(2)  # Wait for the image to open

        # Get the URL of the active image
        active_image = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".swiper-slide-active img")))
        img_url = active_image.get_attribute("src")
        print(f"Original image URL: {img_url}")

        # Remove the query parameters for high-resolution image
        img_url = img_url.split("?")[0]
        print(f"High-resolution image URL: {img_url}")

        # Download the image
        img_data = requests.get(img_url).content
        file_path = os.path.join(base_directory, f'{nin}.png')
        with open(file_path, 'wb') as handler:
            handler.write(img_data)
        print(f"Downloaded and saved image for NIN code: {nin} to {file_path}")

    except Exception as e:
        print(f'Error for NIN code {nin}: {e}')

driver.quit()
print("Download completed.")
