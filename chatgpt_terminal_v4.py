#!/usr/bin/env python3
"""
ChatGPT Terminal v4.0 – JSB CyberOps Edition
Fully patched:
- Auto-installs missing dependencies
- Real GitHub fetcher
- Real web search engine
- PwnPlug Lite module loader (/mods)
- Self-update command (/update)
- Config menu (/config)
- Voice input
- Enhanced color + UI
- Crash-proof OpenAI streaming
"""

import os, sys, json, time, subprocess
from typing import List, Dict, Optional

# -----------------------------------------------------
# AUTO-INSTALLER FUNCTION
# -----------------------------------------------------

def ensure(pkg: str, import_name: Optional[str] = None):
    """
    Attempts to import a module; installs it via pip if missing.
    import_name: name to import if different from package name.
    """
    try:
        return __import__(import_name or pkg)
    except ImportError:
        print(f"[*] Missing '{pkg}'. Installing silently…")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            return __import__(import_name or pkg)
        except Exception as e:
            print(f"[!] Failed to install {pkg}: {e}")
            print(f"[!] Install manually: pip install {pkg}")
            return None

# Core requirements
requests = ensure("requests")
colorama = ensure("colorama")
if colorama:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
else:
    class _Dummy:
        def __getattr__(self, x): return ""
    Fore = Style = _Dummy()

# Optional packages
readline = ensure("pyreadline3") if os.name == "nt" else ensure("readline")
sr = ensure("SpeechRecognition", "speech_recognition")
pyaudio = ensure("PyAudio")

# -----------------------------------------------------
# API ENDPOINTS + MODEL DEFAULT
# -----------------------------------------------------

API_BASE = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-5.1-turbo"
TEMPERATURE = 0.7
STREAMING = True
SYSTEM_PROMPT = (
    "You are ChatGPT running inside a custom terminal created by a cybersecurity "
    "analyst. Respond concisely and keep output command-line friendly unless asked otherwise."
)

# Load API KEY
def load_api_key():
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]

    token_path = os.path.expanduser("~/.chatgpt_token")
    if os.path.exists(token_path):
        return open(token_path).read().strip()

    print("[!] No API key found. Set OPENAI_API_KEY or create ~/.chatgpt_token")
    sys.exit(1)

API_KEY = load_api_key()
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# -----------------------------------------------------
# OpenAI API CALLER (Streaming + Retry + Safety)
# -----------------------------------------------------

def call_openai(messages: List[dict], model=MODEL, temperature=TEMPERATURE, stream=STREAMING):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }

    for attempt in range(3):
        try:
            if not stream:
                r = requests.post(API_BASE, headers=HEADERS, json=payload, timeout=60)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]

            # Streaming
            with requests.post(API_BASE, headers=HEADERS, json=payload, stream=True, timeout=300) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue
            return

        except Exception as e:
            print(Fore.RED + f"[OpenAI Error] {e} (attempt {attempt+1}/3)" + Style.RESET_ALL)
            time.sleep(1.5)

    print(Fore.RED + "[!] Failed after 3 attempts. Check connection or API key." + Style.RESET_ALL)
    return

# -----------------------------------------------------
# WEB SEARCH (DuckDuckGo + Bing API)
# -----------------------------------------------------

def plugin_web_search(query: str) -> str:
    bing_key = os.environ.get("BING_API_KEY")

    # Bing API mode
    if bing_key:
        try:
            url = "https://api.bing.microsoft.com/v7.0/search"
            r = requests.get(url, params={"q": query}, headers={"Ocp-Apim-Subscription-Key": bing_key})
            r.raise_for_status()
            data = r.json()
            results = data.get("webPages", {}).get("value", [])
            out = "[Web Search Results]\n"
            for r2 in results[:5]:
                out += f"- {r2['name']}\n  {r2['url']}\n"
            return out
        except Exception as e:
            return f"[web-search] Bing API error: {e}"

    # DuckDuckGo fallback
    try:
        url = "https://duckduckgo.com/html/"
        r = requests.post(url, data={"q": query}, timeout=10)
        r.raise_for_status()

        try:
            from bs4 import BeautifulSoup
        except:
            ensure("beautifulsoup4")
            from bs4 import BeautifulSoup

        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select(".result__a")

        out = "[Web Search Results - DuckDuckGo]\n"
        for a in links[:5]:
            out += f"- {a.text.strip()}\n  {a.get('href')}\n"

        return out if links else "[no results]"
    except Exception as e:
        return f"[web-search] Error: {e}"

# -----------------------------------------------------
# GITHUB FETCH
# -----------------------------------------------------

def plugin_github_fetch(repo: str, path: str) -> str:
    gh_token = os.environ.get("GITHUB_TOKEN")
    raw_url = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"

    headers = {"Authorization": f"Bearer {gh_token}"} if gh_token else {}

    try:
        r = requests.get(raw_url, headers=headers, timeout=15)
        if r.status_code == 200:
            return f"[github]\nFetched: {raw_url}\n\n{r.text}"

        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        r = requests.get(api_url, headers=headers)
        if r.status_code == 200:
            import base64
            data = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return f"[github]\nFetched via API: {api_url}\n\n{content}"

        return f"[github] Error {r.status_code}: Could not fetch file."
    except Exception as e:
        return f"[github] Exception: {e}"

# -----------------------------------------------------
# PWNPLUG MODULE LOADER
# -----------------------------------------------------

PWNPLUG_MODULE_PATH = "/opt/pwnplug/modules"

def plugin_list_modules() -> List[str]:
    try:
        if not os.path.isdir(PWNPLUG_MODULE_PATH):
            return []
        return [
            f[:-3] for f in os.listdir(PWNPLUG_MODULE_PATH)
            if f.endswith(".py") and not f.startswith("__")
        ]
    except:
        return []

def plugin_run_module(name: str, args: List[str]) -> str:
    mod_file = os.path.join(PWNPLUG_MODULE_PATH, f"{name}.py")
    if not os.path.isfile(mod_file):
        return f"[mods] Module not found: {name}"

    try:
        print(Fore.YELLOW + f"[mods] Running module: {name}\n" + Style.RESET_ALL)
        cmd = [sys.executable, mod_file] + args
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return out
    except subprocess.CalledProcessError as e:
        return f"[mods] Error running module:\n{e.output}"
    except Exception as e:
        return f"[mods] Unexpected error: {e}"

# -----------------------------------------------------
# BANNER
# -----------------------------------------------------

def print_banner():
    print(Fore.CYAN + "="*60 + Style.RESET_ALL)
    print(Fore.CYAN + "   ChatGPT Terminal v4.0 – JSB CyberOps Edition" + Style.RESET_ALL)
    print(Fore.CYAN + "="*60 + Style.RESET_ALL)
    print(Fore.YELLOW + " Multi-line mode: Type text → press ENTER on empty line to send." + Style.RESET_ALL)
    print(Fore.YELLOW + " Commands: /help /reset /save /system /config" + Style.RESET_ALL)
    print(Fore.YELLOW + "           /web /github /mods /voice /update /quit" + Style.RESET_ALL)
    print()

# -----------------------------------------------------
# CONFIG MENU
# -----------------------------------------------------

def config_menu():
    global MODEL, STREAMING, TEMPERATURE, SYSTEM_PROMPT
    print(Fore.CYAN + "\n=== CONFIGURATION MENU ===" + Style.RESET_ALL)
    print(f"1. Model          : {MODEL}")
    print(f"2. Temperature    : {TEMPERATURE}")
    print(f"3. Streaming      : {STREAMING}")
    print(f"4. System Prompt  : {SYSTEM_PROMPT[:50]}...")
    print("5. Exit config\n")

    choice = input("Select option: ").strip()

    if choice == "1":
        MODEL = input("Enter model: ").strip()
        print(Fore.GREEN + "[+] Model updated.\n" + Style.RESET_ALL)

    elif choice == "2":
        try:
            TEMPERATURE = float(input("Temperature (0–2): ").strip())
            print(Fore.GREEN + "[+] Temperature updated.\n" + Style.RESET_ALL)
        except:
            print(Fore.RED + "[!] Invalid input.\n" + Style.RESET_ALL)

    elif choice == "3":
        STREAMING = not STREAMING
        print(Fore.GREEN + f"[+] Streaming set to {STREAMING}\n" + Style.RESET_ALL)

    elif choice == "4":
        SYSTEM_PROMPT = input("New system prompt: ")
        print(Fore.GREEN + "[+] Updated.\n" + Style.RESET_ALL)

# -----------------------------------------------------
# SELF-UPDATE
# -----------------------------------------------------

def update_from_github(url: str) -> str:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()

        script_path = os.path.abspath(sys.argv[0])
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(r.text)

        return "[update] Successfully updated. Restart the program."
    except Exception as e:
        return f"[update] Failed: {e}"

# -----------------------------------------------------
# SAVE TRANSCRIPT
# -----------------------------------------------------

def save_transcript(path: str, messages: List[dict]):
    try:
        with open(path, "w", encoding="utf-8") as f:
            for m in messages:
                f.write(f"{m['role'].upper()}:\n{m['content']}\n\n")
        return f"[+] Transcript saved to {path}"
    except Exception as e:
        return f"[!] Save failed: {e}"

# -----------------------------------------------------
# VOICE INPUT
# -----------------------------------------------------

def do_voice_input() -> str:
    if sr is None:
        return "[voice] SpeechRecognition not installed."

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print(Fore.MAGENTA + "[voice] Listening…" + Style.RESET_ALL)
            audio = recognizer.listen(source)
        return recognizer.recognize_google(audio)
    except Exception as e:
        return f"[voice] Error: {e}"

# -----------------------------------------------------
# MAIN REPL LOOP
# -----------------------------------------------------

def main():
    global SYSTEM_PROMPT

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    buffer: List[str] = []

    print_banner()

    while True:
        try:
            line = input(Fore.GREEN + ">>> " + Style.RESET_ALL)
        except (EOFError, KeyboardInterrupt):
            print(Fore.RED + "\n[exit]" + Style.RESET_ALL)
            break

        stripped = line.strip()

        # Send buffer
        if stripped == "":
            if not buffer:
                continue

            user_text = "\n".join(buffer)
            buffer.clear()

            messages.append({"role": "user", "content": user_text})

            print(Fore.CYAN + "\n[ChatGPT]\n" + Style.RESET_ALL)

            if STREAMING:
                chunks = []
                for chunk in call_openai(messages):
                    chunks.append(chunk)
                    print(Fore.WHITE + chunk + Style.RESET_ALL, end="", flush=True)
                print()
                full = "".join(chunks)
                messages.append({"role": "assistant", "content": full})
            else:
                reply = call_openai(messages, stream=False)
                print(Fore.WHITE + reply + Style.RESET_ALL)
                messages.append({"role": "assistant", "content": reply})

            print()
            continue

        # Commands
        if stripped.startswith("/"):
            parts = stripped.split()
            cmd = parts[0].lower()

            if cmd in ("/quit", "/exit"):
                print(Fore.RED + "[exit]" + Style.RESET_ALL)
                break

            if cmd == "/help":
                print_banner()
                continue

            if cmd == "/reset":
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                buffer.clear()
                print(Fore.MAGENTA + "[+] Conversation cleared." + Style.RESET_ALL)
                continue

            if cmd == "/save":
                if len(parts) < 2:
                    print("[!] Usage: /save <file>")
                else:
                    print(save_transcript(parts[1], messages))
                continue

            if cmd == "/system":
                SYSTEM_PROMPT = stripped[len("/system"):].strip()
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                buffer.clear()
                print(Fore.MAGENTA + "[+] System prompt updated." + Style.RESET_ALL)
                continue

            if cmd == "/web":
                q = stripped[len("/web"):].strip()
                print(Fore.BLUE + plugin_web_search(q) + Style.RESET_ALL)
                continue

            if cmd == "/github":
                if len(parts) < 3:
                    print("[!] Usage: /github <repo> <path>")
                else:
                    repo = parts[1]
                    path = " ".join(parts[2:])
                    print(Fore.BLUE + plugin_github_fetch(repo, path) + Style.RESET_ALL)
                continue

            if cmd == "/mods":
                if len(parts) == 1:
                    print("[!] Usage: /mods list | /mods run <module> [args]")
                    continue

                subcmd = parts[1]

                if subcmd == "list":
                    mods = plugin_list_modules()
                    if mods:
                        print(Fore.YELLOW + "[PwnPlug Modules]" + Style.RESET_ALL)
                        for m in mods:
                            print(" -", m)
                    else:
                        print("[PwnPlug] No modules found.")
                    continue

                if subcmd == "run":
                    if len(parts) < 3:
                        print("[!] Usage: /mods run <module> [args]")
                        continue
                    module = parts[2]
                    args = parts[3:]
                    print(plugin_run_module(module, args))
                    continue

            if cmd == "/voice":
                text = do_voice_input()
                buffer.append(text)
                print(Fore.GREEN + f"[voice->buffer] {text}" + Style.RESET_ALL)
                continue

            if cmd == "/config":
                config_menu()
                continue

            if cmd == "/update":
                if len(parts) < 2:
                    print("[!] Usage: /update <raw-url>")
                else:
                    print(update_from_github(parts[1]))
                continue

            print(Fore.RED + f"[!] Unknown command: {cmd}" + Style.RESET_ALL)
            continue

        buffer.append(line)


if __name__ == "__main__":
    main()
