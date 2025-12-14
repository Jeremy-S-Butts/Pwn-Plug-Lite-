#!/usr/bin/env python3
"""
Simple GUI wrapper for Logon Script Persistence Detector.
"""

import tkinter as tk
from tkinter import messagebox
import os
import sys
from datetime import datetime

try:
    import winreg
except ImportError:
    messagebox.showerror("Error", "Must be run on Windows (winreg not available).")
    sys.exit(1)

REG_HIVE = winreg.HKEY_CURRENT_USER
REG_PATH = r"Environment"
REG_VALUE_NAME = "UserInitMprLogonScript"


def query_logon_script():
    try:
        reg = winreg.ConnectRegistry(None, REG_HIVE)
        key = winreg.OpenKey(reg, REG_PATH, 0, winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        reg.close()
        value = value.strip()
        return value if value else None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def get_file_metadata(path):
    if not path or not os.path.isfile(path):
        return None
    s = os.stat(path)
    return {
        "size": s.st_size,
        "created": datetime.fromtimestamp(s.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.fromtimestamp(s.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


def clear_logon_script():
    try:
        reg = winreg.ConnectRegistry(None, REG_HIVE)
        key = winreg.OpenKey(reg, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        reg.close()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def run_scan():
    txt.delete("1.0", tk.END)
    path = query_logon_script()
    if path is None:
        txt.insert(tk.END, "[+] UserInitMprLogonScript is NOT configured.\n")
        status_var.set("No persistence detected")
        return

    txt.insert(tk.END, "[!] Logon script persistence detected!\n\n")
    txt.insert(tk.END, f"Registry: HKCU\\{REG_PATH}\\{REG_VALUE_NAME}\n")
    txt.insert(tk.END, f"Script path: {path}\n\n")

    info = get_file_metadata(path)
    if info:
        txt.insert(tk.END, "File info:\n")
        txt.insert(tk.END, f"  Exists : YES\n")
        txt.insert(tk.END, f"  Size   : {info['size']} bytes\n")
        txt.insert(tk.END, f"  Created: {info['created']}\n")
        txt.insert(tk.END, f"  Modified: {info['modified']}\n")
    else:
        txt.insert(tk.END, "File info:\n  Exists : NO or not a regular file\n")

    status_var.set("Persistence detected")


def on_clear():
    path = query_logon_script()
    if path is None:
        messagebox.showinfo("Info", "No UserInitMprLogonScript value is set.")
        return

    if not messagebox.askyesno(
        "Confirm",
        "This will clear HKCU\\Environment\\UserInitMprLogonScript.\n\n"
        "Are you sure you want to continue?",
    ):
        return

    if clear_logon_script():
        messagebox.showinfo("Success", "Registry value cleared.")
        run_scan()
    else:
        messagebox.showerror("Error", "Failed to clear registry value.")


# --- GUI Setup ---

root = tk.Tk()
root.title("Logon Script Persistence Detector")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(fill="both", expand=True)

btn_scan = tk.Button(frame, text="Scan", width=12, command=run_scan)
btn_scan.grid(row=0, column=0, padx=5, pady=5, sticky="w")

btn_clear = tk.Button(frame, text="Clear Value", width=12, command=on_clear)
btn_clear.grid(row=0, column=1, padx=5, pady=5, sticky="w")

status_var = tk.StringVar(value="Idle")
lbl_status = tk.Label(frame, textvariable=status_var, fg="blue")
lbl_status.grid(row=0, column=2, padx=5, pady=5, sticky="w")

txt = tk.Text(frame, width=80, height=20)
txt.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

root.mainloop()
