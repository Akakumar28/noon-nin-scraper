#!/usr/bin/env bash

# Exit on any failure
set -e

echo "🔧 Installing Chromium dependencies..."

# Update and install Chromium
apt-get update && apt-get install -y \
    chromium chromium-driver fonts-liberation libappindicator3-1 libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    xdg-utils wget unzip

# Create symlink for undetected_chromedriver to find Chromium
ln -sf /usr/bin/chromium /usr/bin/google-chrome
ln -sf /usr/bin/chromium /usr/bin/chromium-browser

echo "✅ Chromium installed and linked."

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
