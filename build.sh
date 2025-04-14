#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

echo "🔧 Installing Chromium..."

# Install Chromium and dependencies
apt-get update
apt-get install -y \
    chromium-browser \
    chromium-driver \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libfontconfig1 \
    libxcb1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1

# Create symlinks so Python can locate Chromium via shutil.which()
echo "Creating symlinks for Chromium..."
ln -sf /usr/bin/chromium-browser /usr/bin/chromium || true
ln -sf /usr/bin/chromium-browser /usr/bin/google-chrome || true

# Verify Chromium installation
echo "Verifying Chromium installation..."
if [ -f "/usr/bin/chromium-browser" ]; then
    echo "✅ Chromium binary found at /usr/bin/chromium-browser"
else
    echo "❌ Chromium binary not found at /usr/bin/chromium-browser"
    exit 1
fi

# Set up a virtual display for headless Chrome
echo "Setting up virtual display..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

echo "✅ Chromium installed successfully."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
