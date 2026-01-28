#!/usr/bin/env python3
from scapy.all import sniff, TCP, IP, Raw
from collections import defaultdict
import math
import argparse
import time

sessions = {}
failed_logins = defaultdict(int)

def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    return -sum((n/len(s)) * math.log2(n/len(s)) for n in freq.values())

def analyze_packet(pkt):
    if not pkt.haslayer(TCP) or not pkt.haslayer(Raw):
        return

    try:
        payload = pkt[Raw].load.decode(errors="ignore").strip()
    except Exception:
        return

    if not payload:
        return

    src, dst = pkt[IP].src, pkt[IP].dst
    sport, dport = pkt[TCP].sport, pkt[TCP].dport
    tokens = payload.split()

    if tokens[0] == "USER" and len(tokens) > 1:
        key = (src, dst, sport)
        sessions[key] = {
            "user": tokens[1],
            "time": time.time()
        }

    elif tokens[0] == "PASS":
        key = (src, dst, sport)
        if key in sessions:
            sessions[key]["pass_seen"] = True

    elif tokens[0] == "530":
        key = (dst, src, dport)
        if key in sessions:
            user = sessions[key]["user"]
            failed_logins[user] += 1
            ent = shannon_entropy(user)

            print(
                f"[FTP AUTH FAIL] user={user} "
                f"failures={failed_logins[user]} "
                f"entropy={ent:.2f}"
            )
            del sessions[key]

def main():
    parser = argparse.ArgumentParser(description="FTP Cleartext Auth Analyzer")
    parser.add_argument("-i", "--iface", required=True)
    parser.add_argument("-c", "--count", type=int, default=0)
    args = parser.parse_args()

    sniff(
        iface=args.iface,
        filter="tcp port 21",
        prn=analyze_packet,
        store=False,
        count=args.count
    )

if __name__ == "__main__":
    main()
