#!/usr/bin/env python3
"""
ChatGPT Terminal v3.0 - JSB Edition

Features:
- Uses OpenAI Chat Completions API (gpt-5.1-turbo by default)
- Conversation history with system prompt
- Streaming output in the terminal
- Multiline input (empty line sends the prompt)
- Colored output (falls back gracefully if colorama missing)
- Commands:
    /help
    /reset
    /system <text>
    /save <file>
    /voice          (optional, needs SpeechRecognition + PyAudio)
    /web <query>    (placeholder plugin)
    /github <repo> <path>  (placeholder plugin)
    /quit or /exit
"""

import os
import sys
import json
from typing import List

import requests

# readline for history / basic editing on *nix; on Windows pyreadline3 provides similar behavior
try:
    import readline  # noqa: F401
except ImportError:
    pass

# Color handling
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
except ImportError:
    class _Dummy:
        def __getattr__(self, name):
            return ""
    Fore = Style = _Dummy()

# Optional voice input
try:
    import speech_recognition as sr  # type: ignore
    HAVE_VOICE = True
except ImportError:
    HAVE_VOICE = False

API_BASE = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-5.1-turbo"


# ----------------------------
# API key loading
# ----------------------------

def load_api_key() -> str:
    # 1) Env var
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]

    # 2) Token file in home dir
    token_path = os.path.expanduser("~/.chatgpt_token")
    if os.path.exists(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    print("[!] No API key found.")
    print("    Set OPENAI_API_KEY env var, or put your key in ~/.chatgpt_token")
    sys.exit(1)


API_KEY = load_api_key()
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# ----------------------------
# Banner / help
# ----------------------------

def print_banner() -> None:
    print(Fore.CYAN + "-" * 50 + Style.RESET_ALL)
    print(Fore.CYAN + " ChatGPT Terminal v3.0 - JSB Edition" + Style.RESET_ALL)
    print(Fore.CYAN + "-" * 50 + Style.RESET_ALL)
    print(Fore.YELLOW + " Empty line = send multi-line prompt." + Style.RESET_ALL)
    print(Fore.YELLOW + " Commands:" + Style.RESET_ALL)
    print("   /help")
    print("   /reset")
    print("   /system <text>")
    print("   /save <file>")
    print("   /voice")
    print("   /web <query>")
    print("   /github <user/repo> <path>")
    print("   /quit or /exit\n")


# ----------------------------
# OpenAI API call (streaming)
# ----------------------------

def call_openai(messages: List[dict], stream: bool = True):
    """
    If stream=True: yields chunks of text
    If stream=False: returns full string
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": stream,
    }

    if not stream:
        resp = requests.post(API_BASE, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    # Streaming branch
    with requests.post(API_BASE, headers=HEADERS, json=payload, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith("data: "):
                continue
            data_str = line[len("data: "):].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                delta = data["choices"][0]["delta"].get("content")
                if delta:
                    yield delta
            except Exception:
                # swallow malformed chunks
                continue


# ----------------------------
# Plugins (simple placeholders)
# ----------------------------

def plugin_web_search(query: str) -> str:
    """
    Placeholder: you can later wire this into a real search API.
    """
    return f"[web-plugin] Would search the web for: '{query}'.\nConfigure this function with your preferred search API."


def plugin_github_fetch(repo: str, path: str) -> str:
    """
    Placeholder: shows the URL that could be fetched from GitHub.
    """
    url = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"
    return f"[github-plugin] Would fetch: {url}\nAdd requests.get(url) + auth if you want real content."


# ----------------------------
# Voice input (optional)
# ----------------------------

def do_voice_input() -> str:
    if not HAVE_VOICE:
        return "[voice] SpeechRecognition / PyAudio not installed. Run: pip install SpeechRecognition PyAudio"

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print(Fore.MAGENTA + "[voice] Listening… speak now." + Style.RESET_ALL)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print(Fore.MAGENTA + f"[voice] You said: {text}" + Style.RESET_ALL)
        return text
    except Exception as e:
        return f"[voice] Error: {e}"


# ----------------------------
# Transcript saving
# ----------------------------

def save_transcript(path: str, messages: List[dict]) -> str:
    with open(path, "w", encoding="utf-8") as f:
        for m in messages:
            role = m["role"].upper()
            content = m["content"]
            f.write(f"{role}:\n{content}\n\n")
    return path


# ----------------------------
# Main REPL
# ----------------------------

def main() -> None:
    system_prompt = (
        "You are ChatGPT running in a terminal for a power-user cybersecurity analyst. "
        "Be concise but not terse, and keep answers command-line friendly."
    )

    messages: List[dict] = [{"role": "system", "content": system_prompt}]
    buffer: List[str] = []

    print_banner()

    while True:
        try:
            line = input(Fore.GREEN + ">>> " + Style.RESET_ALL)
        except (EOFError, KeyboardInterrupt):
            print(Fore.RED + "\n[exit]" + Style.RESET_ALL)
            break

        stripped = line.strip()

        # Send buffer when you hit an empty line
        if stripped == "":
            if not buffer:
                continue

            user_text = "\n".join(buffer)
            buffer = []

            messages.append({"role": "user", "content": user_text})

            print(Fore.CYAN + "\n[ChatGPT]\n" + Style.RESET_ALL)

            try:
                chunks = []
                for chunk in call_openai(messages, stream=True):
                    chunks.append(chunk)
                    print(Fore.WHITE + chunk + Style.RESET_ALL, end="", flush=True)
                print()
                full_reply = "".join(chunks)
                messages.append({"role": "assistant", "content": full_reply})
            except Exception as e:
                print(Fore.RED + f"\n[ERROR] {e}" + Style.RESET_ALL)

            print()
            continue

        # Commands start with /
        if stripped.startswith("/"):
            parts = stripped.split()
            cmd = parts[0].lower()

            if cmd in ("/quit", "/exit"):
                print(Fore.RED + "[exit]" + Style.RESET_ALL)
                break

            if cmd == "/help":
                print(Fore.YELLOW + "Commands:" + Style.RESET_ALL)
                print("  /help")
                print("  /reset")
                print("  /system <text>")
                print("  /save <file>")
                print("  /voice")
                print("  /web <query>")
                print("  /github <user/repo> <path>")
                print("  /quit or /exit\n")
                continue

            if cmd == "/reset":
                messages = [{"role": "system", "content": system_prompt}]
                buffer = []
                print(Fore.MAGENTA + "[+] Conversation cleared.\n" + Style.RESET_ALL)
                continue

            if cmd == "/system":
                if len(parts) == 1:
                    print(Fore.MAGENTA + f"[current system] {system_prompt}\n" + Style.RESET_ALL)
                else:
                    system_prompt = stripped[len("/system"):].strip()
                    messages = [{"role": "system", "content": system_prompt}]
                    buffer = []
                    print(Fore.MAGENTA + "[+] System prompt updated and history cleared.\n" + Style.RESET_ALL)
                continue

            if cmd == "/save":
                if len(parts) < 2:
                    print(Fore.RED + "[!] Usage: /save transcript.txt\n" + Style.RESET_ALL)
                else:
                    out_path = parts[1]
                    try:
                        save_transcript(out_path, messages)
                        print(Fore.MAGENTA + f"[+] Saved transcript to {out_path}\n" + Style.RESET_ALL)
                    except Exception as e:
                        print(Fore.RED + f"[!] Save failed: {e}\n" + Style.RESET_ALL)
                continue

            if cmd == "/voice":
                text = do_voice_input()
                print(Fore.GREEN + f"[voice->buffer] {text}\n" + Style.RESET_ALL)
                buffer.append(text)
                continue

            if cmd == "/web":
                if len(parts) < 2:
                    print(Fore.RED + "[!] Usage: /web <query>\n" + Style.RESET_ALL)
                else:
                    q = stripped[len("/web"):].strip()
                    out = plugin_web_search(q)
                    print(Fore.BLUE + out + "\n" + Style.RESET_ALL)
                continue

            if cmd == "/github":
                if len(parts) < 3:
                    print(Fore.RED + "[!] Usage: /github <user/repo> <path>\n" + Style.RESET_ALL)
                else:
                    repo = parts[1]
                    path = " ".join(parts[2:])
                    out = plugin_github_fetch(repo, path)
                    print(Fore.BLUE + out + "\n" + Style.RESET_ALL)
                continue

            print(Fore.RED + f"[!] Unknown command: {cmd}. Try /help\n" + Style.RESET_ALL)
            continue

        # Normal text goes to buffer
        buffer.append(line)


if __name__ == "__main__":
    main()
