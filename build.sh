#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

echo "🔧 Installing Chromium..."

# Install Chromium
apt-get update
apt-get install -y chromium-browser chromium-driver

# Create symlink so Python can locate Chromium via shutil.which("chromium")
ln -s /usr/bin/chromium-browser /usr/bin/chromium || true

echo "✅ Chromium installed successfully."

# Install Python dependencies
pip install -r requirements.txt 