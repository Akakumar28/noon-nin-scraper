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

# Debug: List installed packages
echo "Installed packages:"
dpkg -l | grep -E 'chromium|chrome'

# Debug: Check if chromium-browser is installed
echo "Checking chromium-browser installation:"
which chromium-browser || echo "chromium-browser not found in PATH"
ls -la /usr/bin/chromium* || echo "No chromium binaries in /usr/bin"

# Create symlinks so Python can locate Chromium via shutil.which()
echo "Creating symlinks for Chromium..."
ln -sf /usr/bin/chromium-browser /usr/bin/chromium || true
ln -sf /usr/bin/chromium-browser /usr/bin/google-chrome || true
ln -sf /usr/bin/chromium-browser /usr/bin/chrome || true

# Debug: Check if symlinks were created
echo "Checking symlinks:"
ls -la /usr/bin/chromium /usr/bin/google-chrome /usr/bin/chrome || echo "Symlinks not created"

# Verify Chromium installation
echo "Verifying Chromium installation..."
if [ -f "/usr/bin/chromium-browser" ]; then
    echo "✅ Chromium binary found at /usr/bin/chromium-browser"
    # Make sure it's executable
    chmod +x /usr/bin/chromium-browser
else
    echo "❌ Chromium binary not found at /usr/bin/chromium-browser"
    echo "Trying alternative installation method..."
    
    # Try installing chromium directly
    apt-get install -y chromium
    
    # Check again
    if [ -f "/usr/bin/chromium" ]; then
        echo "✅ Chromium binary found at /usr/bin/chromium"
        chmod +x /usr/bin/chromium
        ln -sf /usr/bin/chromium /usr/bin/chromium-browser || true
        ln -sf /usr/bin/chromium /usr/bin/google-chrome || true
        ln -sf /usr/bin/chromium /usr/bin/chrome || true
    else
        echo "❌ Chromium binary still not found after alternative installation"
        echo "Trying one more approach..."
        
        # Try installing google-chrome-stable
        apt-get install -y wget gnupg
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list
        apt-get update
        apt-get install -y google-chrome-stable
        
        # Check if google-chrome-stable is installed
        if [ -f "/usr/bin/google-chrome-stable" ]; then
            echo "✅ Google Chrome binary found at /usr/bin/google-chrome-stable"
            chmod +x /usr/bin/google-chrome-stable
            ln -sf /usr/bin/google-chrome-stable /usr/bin/chromium-browser || true
            ln -sf /usr/bin/google-chrome-stable /usr/bin/chromium || true
            ln -sf /usr/bin/google-chrome-stable /usr/bin/google-chrome || true
            ln -sf /usr/bin/google-chrome-stable /usr/bin/chrome || true
        else
            echo "❌ All installation methods failed"
            exit 1
        fi
    fi
fi

# Set up a virtual display for headless Chrome
echo "Setting up virtual display..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

echo "✅ Chromium installed successfully."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
