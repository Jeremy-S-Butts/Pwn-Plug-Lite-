Python 2.7 (r27:82525, Jul  4 2010, 09:01:59) [MSC v.1500 32 bit (Intel)] on win32
Type "copyright", "credits" or "license()" for more information.
>>> #!/usr/bin/env python3
"""
Logon Script Persistence Detector (Windows)

- Checks HKCU\Environment\UserInitMprLogonScript
- Reports status and basic file info
- (Optional) can clear the value if run with --fix

Intended for defensive use and lab/testing.
"""

import os
import sys
import json
from datetime import datetime

try:
    import winreg
except ImportError:
    print("[!] This script must be run on Windows (winreg module not available).")
    sys.exit(1)

REG_HIVE = winreg.HKEY_CURRENT_USER
REG_PATH = r"Environment"
REG_VALUE_NAME = "UserInitMprLogonScript"


def query_logon_script():
    """Return the configured logon script path or None if not set."""
    try:
        reg = winreg.ConnectRegistry(None, REG_HIVE)
        key = winreg.OpenKey(reg, REG_PATH, 0, winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        reg.close()
        value = value.strip()
        return value if value else None
    except FileNotFoundError:
        # key or value does not exist
        return None
    except OSError as e:
        print(f"[!] Registry access error: {e}")
        return None


def get_file_metadata(path):
    """Return basic metadata for a file path, or None if it doesn't exist."""
    if not path or not os.path.isfile(path):
        return None

    stat = os.stat(path)
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def clear_logon_script():
    """Remove the UserInitMprLogonScript registry value."""
    try:
        reg = winreg.ConnectRegistry(None, REG_HIVE)
        key = winreg.OpenKey(reg, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        reg.close()
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        print(f"[!] Failed to clear registry value: {e}")
        return False


def main():
    fix = "--fix" in sys.argv
    json_out = "--json" in sys.argv

    result = {
        "registry_hive": "HKEY_CURRENT_USER",
        "registry_path": REG_PATH,
        "value_name": REG_VALUE_NAME,
        "configured": False,
        "script_path": None,
        "file_info": None,
        "action_taken": None,
    }

    script_path = query_logon_script()
    if script_path is None:
        result["configured"] = False
        if not json_out:
            print("[+] UserInitMprLogonScript is NOT configured for the current user.")
    else:
        result["configured"] = True
        result["script_path"] = script_path
        result["file_info"] = get_file_metadata(script_path)

        if not json_out:
            print("[!] Logon script persistence detected!")
            print(f"    Registry: HKCU\\{REG_PATH}\\{REG_VALUE_NAME}")
            print(f"    Script path: {script_path}")

            if result["file_info"]:
                info = result["file_info"]
                print("    File exists: YES")
                print(f"    Size       : {info['size_bytes']} bytes")
                print(f"    Created    : {info['created']}")
                print(f"    Modified   : {info['modified']}")
            else:
                print("    File exists: NO (or not a regular file)")

    # Optional remediation
    if fix and result["configured"]:
        if not json_out:
            confirm = input("\nDo you want to CLEAR this registry value? [y/N]: ").strip().lower()
            if confirm != "y":
                print("[*] No changes made.")
            else:
                if clear_logon_script():
                    print("[+] Registry value cleared.")
                    result["action_taken"] = "cleared"
                else:
                    result["action_taken"] = "clear_failed"
        else:
            # JSON mode: just attempt
            result["action_taken"] = "cleared" if clear_logon_script() else "clear_failed"

    if json_out:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
