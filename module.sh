
#!/bin/bash
# PwnPlug Lite Module Launcher – SAFE MODE

MODULE_DIR="$(dirname "$(realpath "$0")")"
REPORT_DIR="/opt/pwnplug/reports/account_access_removal_safe"

mkdir -p "$REPORT_DIR"

echo "[*] Running Account Access Removal (SAFE MODE)"
python3 "$MODULE_DIR/account_access_removal_safe.py" \
  --output "$REPORT_DIR"

echo "[+] Report saved to $REPORT_DIR"
