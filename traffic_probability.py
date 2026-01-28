#!/usr/bin/env python3
"""
traffic_probability.py
Feature-based probabilistic traffic scoring (Naïve Bayes-style) for PCAP or live sniffing.

- Extracts features: ports, client IP, server IP, (client,server) connection tuples
- Uses Laplace smoothing
- Uses log-likelihood to avoid underflow
- Computes Shannon entropy for each feature distribution
- Outputs JSON (default) or text summary

Ethical note: Intended for authorized analysis of your own captures/labs.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Any

try:
    from scapy.all import IP, TCP, UDP, rdpcap, sniff  # type: ignore
except Exception as e:
    print("[-] Scapy not available. Install with: pip install scapy", file=sys.stderr)
    raise


FeatureValue = Any  # int for ports, str for IPs, tuple(str,str) for conn


def shannon_entropy_from_counts(counts: Counter) -> float:
    """Shannon entropy H(X) in bits from a Counter."""
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            h -= p * math.log2(p)
    return h


@dataclass
class ModelStats:
    threshold: int
    alpha: float
    total_samples: int
    feature_counts: Dict[str, Counter]
    feature_totals: Dict[str, int]
    feature_unique: Dict[str, int]
    feature_entropy: Dict[str, float]


class TrafficProbabilityModel:
    """
    A simple, explainable probabilistic scorer:
    score(packet) = sum_over_features log P(feature_value)
    where P uses Laplace smoothing.
    """

    def __init__(self, threshold: int = 50, alpha: float = 1.0):
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        if alpha <= 0:
            raise ValueError("alpha must be > 0")
        self.threshold = threshold
        self.alpha = alpha

        self.counts: Dict[str, Counter] = {
            "port": Counter(),
            "cip": Counter(),
            "sip": Counter(),
            "conn": Counter(),
        }
        self.n_samples = 0  # packets processed (that had IP layer)

    @staticmethod
    def _is_ip_packet(p) -> bool:
        return p.haslayer(IP)

    def _extract_features(self, p, client_mode: str) -> Dict[str, FeatureValue]:
        """
        client_mode:
          - "src": treat IP.src as client, IP.dst as server
          - "dst": treat IP.dst as client, IP.src as server
          - "auto": heuristic: ephemeral port likely client; well-known port likely server
        """
        ip = p[IP]
        src = ip.src
        dst = ip.dst

        # Determine transport and ports (if any)
        sport = dport = None
        if p.haslayer(TCP):
            sport = int(p[TCP].sport)
            dport = int(p[TCP].dport)
        elif p.haslayer(UDP):
            sport = int(p[UDP].sport)
            dport = int(p[UDP].dport)

        # Decide client/server direction
        cip, sip = src, dst

        if client_mode == "src":
            cip, sip = src, dst
        elif client_mode == "dst":
            cip, sip = dst, src
        elif client_mode == "auto":
            # Heuristic: "client" tends to use ephemeral port (>1023) to talk to a server well-known port (<=1023)
            if sport is not None and dport is not None:
                if sport > 1023 and dport <= 1023:
                    cip, sip = src, dst
                elif dport > 1023 and sport <= 1023:
                    cip, sip = dst, src
                else:
                    # fallback: default to src as client
                    cip, sip = src, dst
            else:
                cip, sip = src, dst
        else:
            raise ValueError("client_mode must be one of: src, dst, auto")

        # Choose a single port feature consistent with your original logic:
        # If client is src -> use destination port; else use source port
        port_feature = None
        if sport is not None and dport is not None:
            if cip == src:
                port_feature = dport
            else:
                port_feature = sport

        feats: Dict[str, FeatureValue] = {
            "cip": cip,
            "sip": sip,
            "conn": (cip, sip),
        }
        if port_feature is not None:
            feats["port"] = port_feature

        return feats

    def update(self, feats: Dict[str, FeatureValue]) -> None:
        """Update model counts with extracted features."""
        for k, v in feats.items():
            if k in self.counts:
                self.counts[k][v] += 1
        self.n_samples += 1

    def ready(self) -> bool:
        """Whether we have enough samples to produce non-trivial scoring."""
        return self.n_samples >= self.threshold

    def _log_prob(self, feature_name: str, value: FeatureValue) -> float:
        """
        Laplace-smoothed probability:
          P(v) = (count(v) + alpha) / (N + alpha * |V|)
        """
        c = self.counts[feature_name]
        N = sum(c.values())
        V = max(1, len(c))  # avoid divide-by-zero
        num = c.get(value, 0) + self.alpha
        den = N + self.alpha * V
        return math.log(num / den)

    def score(self, feats: Dict[str, FeatureValue]) -> Dict[str, float]:
        """
        Returns per-feature log-likelihood contributions and the total.
        If not ready, returns zeros (or very mild baseline).
        """
        if not self.ready():
            return {"total_loglik": 0.0, "total_prob_proxy": 1.0}

        total = 0.0
        per: Dict[str, float] = {}
        for k, v in feats.items():
            if k not in self.counts:
                continue
            lp = self._log_prob(k, v)
            per[f"logP_{k}"] = lp
            total += lp

        # Convert to a "probability proxy" only for interpretability (still not a calibrated probability).
        # exp(total) can underflow for very negative totals, so clamp.
        total_clamped = max(-700.0, min(700.0, total))
        prob_proxy = math.exp(total_clamped)

        per["total_loglik"] = total
        per["total_prob_proxy"] = prob_proxy
        return per

    def stats(self) -> ModelStats:
        ent = {k: shannon_entropy_from_counts(v) for k, v in self.counts.items()}
        totals = {k: sum(v.values()) for k, v in self.counts.items()}
        uniq = {k: len(v) for k, v in self.counts.items()}
        return ModelStats(
            threshold=self.threshold,
            alpha=self.alpha,
            total_samples=self.n_samples,
            feature_counts=self.counts,
            feature_totals=totals,
            feature_unique=uniq,
            feature_entropy=ent,
        )


def iter_packets_from_pcap(path: str) -> Iterable:
    pkts = rdpcap(path)
    for p in pkts:
        yield p


def iter_packets_live(iface: str, bpf: Optional[str], count: int, timeout: int) -> Iterable:
    # store=False returns packets as they arrive (generator-like)
    pkts = sniff(iface=iface, filter=bpf, count=count if count > 0 else 0, timeout=timeout if timeout > 0 else None, store=True)
    for p in pkts:
        yield p


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Feature-based probabilistic traffic scoring (ports/IPs/connection tuples) for PCAP or live capture."
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pcap", help="Path to PCAP file to analyze")
    src.add_argument("--live", help="Interface name for live sniffing (e.g., eth0, wlan0)")

    ap.add_argument("--bpf", default=None, help='BPF filter for live sniffing (e.g., "tcp or udp")')
    ap.add_argument("--count", type=int, default=0, help="Packet count for live sniffing (0 = unlimited until timeout)")
    ap.add_argument("--timeout", type=int, default=30, help="Seconds to sniff in live mode (0 = no timeout)")

    ap.add_argument("--threshold", type=int, default=50, help="Minimum samples before scoring becomes active")
    ap.add_argument("--alpha", type=float, default=1.0, help="Laplace smoothing alpha (>0)")

    ap.add_argument("--client-mode", choices=["src", "dst", "auto"], default="auto",
                    help="How to decide client/server direction for CIP/SIP features")
    ap.add_argument("--max-report", type=int, default=200, help="Max packets to include in report output")

    ap.add_argument("--output", default="-", help="Output path (JSON). Use '-' for stdout")
    ap.add_argument("--format", choices=["json", "text"], default="json", help="Output format")

    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    model = TrafficProbabilityModel(threshold=args.threshold, alpha=args.alpha)

    # Choose packet source
    if args.pcap:
        pkt_iter = iter_packets_from_pcap(args.pcap)
        source_meta = {"mode": "pcap", "pcap": args.pcap}
    else:
        pkt_iter = iter_packets_live(args.live, args.bpf, args.count, args.timeout)
        source_meta = {"mode": "live", "iface": args.live, "bpf": args.bpf, "count": args.count, "timeout": args.timeout}

    report_packets: List[Dict[str, Any]] = []
    processed = 0
    skipped = 0

    for p in pkt_iter:
        if not model._is_ip_packet(p):
            skipped += 1
            continue

        try:
            feats = model._extract_features(p, client_mode=args.client_mode)
        except Exception:
            skipped += 1
            continue

        model.update(feats)
        processed += 1

        # score current packet against model-so-far
        scores = model.score(feats)

        if len(report_packets) < args.max_report:
            row = {
                "idx": processed,
                "features": {
                    "port": feats.get("port"),
                    "cip": feats.get("cip"),
                    "sip": feats.get("sip"),
                    "conn": feats.get("conn"),
                },
                "scores": scores,
            }
            report_packets.append(row)

    st = model.stats()

    out_obj = {
        "source": source_meta,
        "config": {
            "threshold": args.threshold,
            "alpha": args.alpha,
            "client_mode": args.client_mode,
        },
        "summary": {
            "processed_ip_packets": processed,
            "skipped_non_ip_or_failed_parse": skipped,
            "model_ready": model.ready(),
            "feature_totals": st.feature_totals,
            "feature_unique_values": st.feature_unique,
            "feature_entropy_bits": st.feature_entropy,
        },
        "samples": report_packets,
        # For reproducibility/debug, include top-N counts (trimmed)
        "top_counts": {
            k: st.feature_counts[k].most_common(20) for k in st.feature_counts
        },
    }

    if args.format == "text":
        lines = []
        lines.append("=== Traffic Probability Report ===")
        lines.append(json.dumps(source_meta, indent=2))
        lines.append(f"Processed IP packets: {processed} | Skipped: {skipped} | Ready: {model.ready()}")
        lines.append("Entropy (bits):")
        for k, v in st.feature_entropy.items():
            lines.append(f"  - {k}: {v:.4f}")
        lines.append("Top counts:")
        for k in st.feature_counts:
            lines.append(f"  {k}: {st.feature_counts[k].most_common(10)}")
        text_out = "\n".join(lines)

        if args.output == "-":
            print(text_out)
        else:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text_out + "\n")
        return 0

    # json output
    blob = json.dumps(out_obj, indent=2, default=str)
    if args.output == "-":
        print(blob)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(blob + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
