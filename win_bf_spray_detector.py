import argparse
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import win32evtlog

SERVER = "localhost"
LOGTYPE = "Security"
FLAGS = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

EVENT_FAILED_LOGON = 4625
SUSPICIOUS_LOGON_TYPES = {3, 8, 10}

IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")


def shannon_entropy(counts: Counter) -> float:
    """Shannon entropy (base-2) over a categorical distribution."""
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    import math
    ent = 0.0
    for c in counts.values():
        p = c / total
        ent -= p * math.log2(p)
    return ent


def open_log(evtx_path: str | None):
    if evtx_path:
        return win32evtlog.OpenBackupEventLog(SERVER, evtx_path)
    return win32evtlog.OpenEventLog(SERVER, LOGTYPE)


def looks_like_ip(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    if IPV4_RE.match(s):
        # very light sanity: each octet 0-255
        parts = s.split(".")
        return all(0 <= int(p) <= 255 for p in parts if p.isdigit())
    # accept IPv6-ish strings (best effort)
    if ":" in s and IPV6_RE.match(s):
        return True
    return False


def extract_4625_fields(evt) -> dict:
    """
    Extract key fields from a 4625 event.
    Note: StringInserts indexing varies by OS/event format.
    We use:
      - username: default index 5 (as in your original script), with fallback search
      - logon_type: default index 8 with fallback numeric scan
      - source_ip: best-effort scan of inserts for something that looks like an IP
    """
    inserts = list(evt.StringInserts or [])
    username = None
    logon_type = None
    source_ip = None

    # Timestamp (pywin32 gives pytime)
    ts = evt.TimeGenerated
    # Convert to Python datetime (pytime is already datetime-like in most pywin32 builds)
    if isinstance(ts, datetime):
        dt = ts
    else:
        # best effort
        dt = datetime.fromtimestamp(int(ts))

    # Username heuristic
    if len(inserts) > 5 and inserts[5]:
        username = inserts[5].strip()
    else:
        # fallback: choose first non-empty token that looks like a user (not an IP, not "-")
        for s in inserts:
            if not s:
                continue
            s2 = s.strip()
            if s2 and s2 not in {"-", "N/A"} and not looks_like_ip(s2) and len(s2) <= 64:
                username = s2
                break

    # Logon type heuristic
    if len(inserts) > 8:
        try:
            logon_type = int(str(inserts[8]).strip())
        except Exception:
            logon_type = None
    if logon_type is None:
        # fallback: scan for a small integer that matches known types
        for s in inserts:
            try:
                v = int(str(s).strip())
                if v in range(2, 12):
                    logon_type = v
                    break
            except Exception:
                continue

    # Source IP heuristic
    for s in inserts:
        if looks_like_ip(str(s)):
            source_ip = str(s).strip()
            break
    if not source_ip:
        source_ip = "UNKNOWN"

    return {
        "time": dt,
        "username": username or "UNKNOWN_USER",
        "logon_type": logon_type,
        "source_ip": source_ip,
        "event_id": evt.EventID,
    }


def read_failed_logons(evtx_path: str | None):
    h = open_log(evtx_path)
    records = []

    while True:
        events = win32evtlog.ReadEventLog(h, FLAGS, 0)
        if not events:
            break

        for evt in events:
            if evt.EventID != EVENT_FAILED_LOGON:
                continue
            rec = extract_4625_fields(evt)
            # Only focus on common remote/suspicious logon types (configurable if desired)
            if rec["logon_type"] in SUSPICIOUS_LOGON_TYPES:
                records.append(rec)

    # Sort by time for windowing
    records.sort(key=lambda r: r["time"])
    return records


def window_bucket_start(dt: datetime, window: timedelta) -> datetime:
    # Bucket by epoch alignment (stable bucketing)
    epoch = datetime(1970, 1, 1)
    seconds = int((dt - epoch).total_seconds())
    w = int(window.total_seconds())
    return epoch + timedelta(seconds=(seconds // w) * w)


def analyze(records, window_minutes: int, brute_user_threshold: int, brute_ip_threshold: int,
            spray_unique_users_threshold: int, spray_max_per_user: int):
    window = timedelta(minutes=window_minutes)

    # Buckets:
    #  - per bucket: counts by user, counts by ip, and mapping ip->users and user->ips
    bucket_user_counts = defaultdict(Counter)   # bucket -> Counter(user->failures)
    bucket_ip_counts = defaultdict(Counter)     # bucket -> Counter(ip->failures)
    bucket_ip_users = defaultdict(lambda: defaultdict(Counter))  # bucket -> ip -> Counter(user->failures)
    bucket_user_ips = defaultdict(lambda: defaultdict(Counter))  # bucket -> user -> Counter(ip->failures)

    for r in records:
        b = window_bucket_start(r["time"], window)
        u = r["username"]
        ip = r["source_ip"]
        bucket_user_counts[b][u] += 1
        bucket_ip_counts[b][ip] += 1
        bucket_ip_users[b][ip][u] += 1
        bucket_user_ips[b][u][ip] += 1

    brute_user_alerts = []
    brute_ip_alerts = []
    spray_alerts = []
    entropy_observations = []

    for b in sorted(bucket_user_counts.keys()):
        # Brute force per user
        for u, c in bucket_user_counts[b].items():
            if c >= brute_user_threshold:
                brute_user_alerts.append((b, u, c))

        # Brute force per IP
        for ip, c in bucket_ip_counts[b].items():
            if c >= brute_ip_threshold:
                brute_ip_alerts.append((b, ip, c))

        # Password spray: per IP in bucket
        for ip, user_ctr in bucket_ip_users[b].items():
            unique_users = len(user_ctr)
            max_per_user = max(user_ctr.values()) if user_ctr else 0
            total = sum(user_ctr.values())

            if unique_users >= spray_unique_users_threshold and max_per_user <= spray_max_per_user:
                # Entropy: user distribution for this IP in this window
                u_ent = shannon_entropy(user_ctr)
                spray_alerts.append((b, ip, total, unique_users, max_per_user, u_ent))

            # Always compute entropy observations for context (top talkers only)
            if total >= max(10, brute_ip_threshold // 2):
                u_ent = shannon_entropy(user_ctr)
                entropy_observations.append((b, "ip->user", ip, total, unique_users, u_ent))

        # Distributed attack against a user (many IPs)
        for u, ip_ctr in bucket_user_ips[b].items():
            unique_ips = len(ip_ctr)
            total = sum(ip_ctr.values())
            if total >= max(10, brute_user_threshold // 2):
                ip_ent = shannon_entropy(ip_ctr)
                entropy_observations.append((b, "user->ip", u, total, unique_ips, ip_ent))

    return {
        "brute_user_alerts": brute_user_alerts,
        "brute_ip_alerts": brute_ip_alerts,
        "spray_alerts": spray_alerts,
        "entropy_observations": entropy_observations,
        "bucket_minutes": window_minutes,
        "total_records": len(records),
    }


def print_report(result, top_entropy=10):
    print(f"\nAnalyzed {result['total_records']} failed-logon (4625) records")
    print(f"Window size: {result['bucket_minutes']} minutes\n")

    # Brute-force by user
    print("== Brute-force alerts (per user) ==")
    if result["brute_user_alerts"]:
        for b, u, c in result["brute_user_alerts"]:
            print(f"[{b}] user={u} failures={c}")
    else:
        print("None")

    print("\n== Brute-force alerts (per source IP) ==")
    if result["brute_ip_alerts"]:
        for b, ip, c in result["brute_ip_alerts"]:
            print(f"[{b}] ip={ip} failures={c}")
    else:
        print("None")

    print("\n== Password spray alerts (per source IP) ==")
    if result["spray_alerts"]:
        for b, ip, total, uniq, max_per_user, ent in result["spray_alerts"]:
            print(f"[{b}] ip={ip} total_failures={total} unique_users={uniq} "
                  f"max_per_user={max_per_user} user_entropy={ent:.3f}")
    else:
        print("None")

    # Entropy context
    print("\n== Entropy observations (top activity windows) ==")
    obs = sorted(result["entropy_observations"], key=lambda x: x[3], reverse=True)[:top_entropy]
    if obs:
        for b, mode, key, total, uniq, ent in obs:
            if mode == "ip->user":
                print(f"[{b}] IP {key}: total={total} unique_users={uniq} user_entropy={ent:.3f}")
            else:
                print(f"[{b}] User {key}: total={total} unique_ips={uniq} ip_entropy={ent:.3f}")
    else:
        print("None")


def main():
    p = argparse.ArgumentParser(description="Windows 4625 detector: time-window brute force + password spray + entropy")
    p.add_argument("-f", "--file", help="Offline EVTX file (optional). If omitted, reads local Security log.")
    p.add_argument("-w", "--window-minutes", type=int, default=10, help="Time window size in minutes (default: 10)")
    p.add_argument("--brute-user-threshold", type=int, default=10, help="Failures per user per window to alert (default: 10)")
    p.add_argument("--brute-ip-threshold", type=int, default=25, help="Failures per IP per window to alert (default: 25)")
    p.add_argument("--spray-unique-users", type=int, default=15, help="Unique users per IP per window to flag spray (default: 15)")
    p.add_argument("--spray-max-per-user", type=int, default=3, help="Max failures per user from an IP per window for spray (default: 3)")
    args = p.parse_args()

    records = read_failed_logons(args.file)
    result = analyze(
        records,
        window_minutes=args.window_minutes,
        brute_user_threshold=args.brute_user_threshold,
        brute_ip_threshold=args.brute_ip_threshold,
        spray_unique_users_threshold=args.spray_unique_users,
        spray_max_per_user=args.spray_max_per_user,
    )
    print_report(result)


if __name__ == "__main__":
    main()
