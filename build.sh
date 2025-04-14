#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Chromium and its dependencies
echo "Installing Chromium and dependencies..."
apt-get update
apt-get install -y \
    chromium-browser \
    chromium-chromedriver \
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

# Set up a virtual display for headless Chrome
echo "Setting up virtual display..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

echo "Build script completed successfully!" 