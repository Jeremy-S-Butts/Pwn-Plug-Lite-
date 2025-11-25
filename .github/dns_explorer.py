#!/usr/bin/env python3
"""
dns_explorer.py

Simple DNS exploration / subdomain enumeration module.

Implements what you sketched as:
- (a) load subdomain wordlist from subdomains.txt
- (b) subdomainSearch(domain, dictionary, nums)
- (c) DNS request + reverse DNS print
- (d) reverseDNS(ip)

Requires:  pip install dnspython
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import dns.resolver
import dns.exception


# ---------- (d) Reverse DNS helper ---------- #

def reverse_dns(ip: str) -> List[str]:
    """
    Return PTR/hostnames for an IP address.

    Equivalent to your reverseDNS(ip) sketch.
    """
    try:
        name, aliases, _ = socket.gethostbyaddr(ip)
        results = [name]
        results.extend(aliases)
        return results
    except (socket.herror, socket.gaierror, TimeoutError):
        return []


# ---------- (c) Single DNS A lookup ---------- #

def resolve_a(name: str) -> List[str]:
    """
    Resolve A records for a hostname, return list of IP strings.
    """
    try:
        answers = dns.resolver.resolve(name, "A")
        return [rdata.to_text() for rdata in answers]
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
        dns.resolver.LifetimeTimeout,
    ):
        return []


def dns_request(name: str, do_reverse: bool = True) -> List[Tuple[str, List[str]]]:
    """
    Perform DNS request for A records and optional reverse DNS.
    Returns list of (ip, [ptr_names]) tuples.
    """
    ips = resolve_a(name)
    results: List[Tuple[str, List[str]]] = []

    for ip in ips:
        ptrs = reverse_dns(ip) if do_reverse else []
        results.append((ip, ptrs))

    return results


# ---------- Result structure ---------- #

@dataclass
class DNSRecord:
    fqdn: str
    ip: str
    ptrs: List[str]


# ---------- (b) SubdomainSearch() ---------- #

def subdomain_search(
    domain: str,
    wordlist: Iterable[str],
    nums: bool = True,
    do_reverse: bool = True,
) -> List[DNSRecord]:
    """
    Try <word>.<domain> and optionally <word><0-9>.<domain>.

    This is your SubdomainSearch(domain, dictionary, nums).
    Returns a list of DNSRecord objects for everything that resolves.
    """
    records: List[DNSRecord] = []

    for word in wordlist:
        word = word.strip()
        if not word:
            continue

        # base word: word.domain
        fqdn = f"{word}.{domain}"
        for ip, ptrs in dns_request(fqdn, do_reverse=do_reverse):
            records.append(DNSRecord(fqdn=fqdn, ip=ip, ptrs=ptrs))

        # optional numeric variants: word0.domain ... word9.domain
        if nums:
            for i in range(0, 10):
                label = f"{word}{i}"
                fqdn_num = f"{label}.{domain}"
                for ip, ptrs in dns_request(fqdn_num, do_reverse=do_reverse):
                    records.append(DNSRecord(fqdn=fqdn_num, ip=ip, ptrs=ptrs))

    return records


# ---------- (a) Wordlist loader ---------- #

def load_wordlist(path: str) -> List[str]:
    """
    Load subdomains from a file (like your subdomains.txt example).
    Blank lines and comments (#) are ignored.
    """
    words: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.append(line)
    return words


# ---------- Optional: quick CLI entrypoint ---------- #

def main() -> None:
    """
    Simple command-line interface so you can test quickly:

        python3 dns_explorer.py -d google.com -w subdomains.txt
    """
    import argparse
    parser = argparse.ArgumentParser(description="DNS exploration / subdomain enum")
    parser.add_argument("-d", "--domain", required=True, help="Target domain")
    parser.add_argument(
        "-w", "--wordlist", required=True, help="Subdomain wordlist file"
    )
    parser.add_argument(
        "--no-nums",
        action="store_true",
        help="Disable word+digit variants (www0, www1, ...)",
    )
    parser.add_argument(
        "--no-reverse",
        action="store_true",
        help="Disable reverse DNS lookups",
    )
    args = parser.parse_args()

    words = load_wordlist(args.wordlist)
    records = subdomain_search(
        args.domain,
        words,
        nums=not args.no_nums,
        do_reverse=not args.no_reverse,
    )

    for rec in records:
        if rec.ptrs:
            print(f"{rec.fqdn:40} {rec.ip:16} PTR: {', '.join(rec.ptrs)}")
        else:
            print(f"{rec.fqdn:40} {rec.ip:16}")


if __name__ == "__main__":
    main()

