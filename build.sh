#!/bin/bash

# ================================
#  PwnPlug Threaded Build Script
# ================================

SCRIPT_PATH="/home/kali/Downloads/file_discovery_threaded.py"
OUTPUT_NAME="pwnplug-threaded"
DESTINATION="/usr/bin/${OUTPUT_NAME}"

echo "[*] Checking script exists..."
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "[ERROR] Script not found at: $SCRIPT_PATH"
    echo "Fix the path and rerun this script."
    exit 1
fi

echo "[*] Cleaning old build artifacts..."
rm -rf build/ dist/ __pycache__/ 2>/dev/null

echo "[*] Running PyInstaller build..."
pyinstaller --onefile --noconsole --clean \
    --name "$OUTPUT_NAME" \
    "$SCRIPT_PATH"

if [ ! -f "dist/${OUTPUT_NAME}" ]; then
    echo "[ERROR] Build failed — no output binary found."
    exit 1
fi

echo "[*] Moving binary to /usr/bin..."
sudo mv "dist/${OUTPUT_NAME}" "$DESTINATION"

echo "[*] Setting permissions..."
sudo chmod +x "$DESTINATION"

echo "[*] Reloading systemd (just in case)..."
sudo systemctl daemon-reload

echo ""
echo "======================================"
echo "  BUILD COMPLETE"
echo "======================================"
echo "Binary installed at: $DESTINATION"
echo "Run it with:"
echo ""
echo "    $OUTPUT_NAME"
echo ""
echo "If used as a systemd service, ensure:"
echo ""
echo "    ExecStart=${DESTINATION}"
echo ""
echo "======================================"
