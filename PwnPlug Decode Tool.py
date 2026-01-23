#!/usr/bin/env python3
"""
- Detects hex/base64
- Tries decoding
- Tries ROT (ROT13 and ROT-N alpha rotations)
- Tries single-byte XOR brute force
- Scores candidates with entropy + printability heuristics
Standard library only.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import math
import re
import string
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


# -----------------------------
# Scoring / heuristics
# -----------------------------

PRINTABLE_BYTES = set(bytes(string.printable, "ascii"))

COMMON_WORDS = (
    " the ", " and ", " to ", " of ", " in ", " is ", " for ", "http", "https", "www",
    "cmd", "powershell", "select", "from", "user", "admin", "token", "key", "password",
)


def shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits/byte."""
    if not data:
        return 0.0
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    n = len(data)
    ent = 0.0
    for c in freq.values():
        p = c / n
        ent -= p * math.log2(p)
    return ent


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(1 for b in data if b in PRINTABLE_BYTES)
    return printable / len(data)


def ascii_like_score(text: str) -> float:
    """
    Bonus points for:
    - printable ASCII dominance
    - common words/markers
    - reasonable length
    """
    if not text:
        return 0.0

    lower = text.lower()
    word_hits = sum(lower.count(w) for w in COMMON_WORDS)
    # Prefer moderately long outputs (but don’t overdo it)
    length_bonus = min(len(text) / 80.0, 1.0)

    # Penalize lots of replacement chars / control-looking output
    weird = sum(1 for ch in text if ch not in string.printable)
    weird_penalty = weird / max(len(text), 1)

    return (word_hits * 1.5) + (length_bonus * 0.5) - (weird_penalty * 2.0)


def candidate_score(data: bytes) -> float:
    """
    Composite score:
    - High printable ratio is good
    - Entropy: for human text typically ~3.5–5.5 bits/byte
      Penalize extremes (very low or very high)
    """
    pr = printable_ratio(data)
    ent = shannon_entropy(data)

    # Text tends to sit mid-entropy; random/encrypted tends higher
    ent_target = 4.5
    ent_penalty = abs(ent - ent_target)

    # Convert bytes to best-effort string for keyword scoring
    text = data.decode("utf-8", errors="replace")
    kw = ascii_like_score(text)

    # Weighted sum
    return (pr * 6.0) + (kw * 1.0) - (ent_penalty * 1.2)


@dataclass(frozen=True)
class Result:
    method: str
    score: float
    entropy: float
    printable: float
    preview: str
    raw: bytes


def make_result(method: str, raw: bytes) -> Result:
    ent = shannon_entropy(raw)
    pr = printable_ratio(raw)
    score = candidate_score(raw)
    preview = raw.decode("utf-8", errors="replace")
    # keep previews bounded
    if len(preview) > 400:
        preview = preview[:400] + "…"
    return Result(method=method, score=score, entropy=ent, printable=pr, preview=preview, raw=raw)


# -----------------------------
# Decoders
# -----------------------------

def is_hex(s: str) -> bool:
    if len(s) < 2 or (len(s) % 2 != 0):
        return False
    if not HEX_RE.fullmatch(s):
        return False
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False


def try_hex(s: str) -> Optional[bytes]:
    if not is_hex(s):
        return None
    try:
        return bytes.fromhex(s)
    except ValueError:
        return None


def try_base64(s: str) -> Optional[bytes]:
    # add padding if user gives unpadded base64
    ss = s.strip()
    pad = (-len(ss)) % 4
    if pad:
        ss = ss + ("=" * pad)
    try:
        return base64.b64decode(ss, validate=True)
    except (binascii.Error, ValueError):
        return None


def rot_alpha(s: str, n: int) -> str:
    """Rotate letters A-Z / a-z by n (0..25)."""
    out = []
    for ch in s:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + n) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + n) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


def try_rot_candidates(s: str) -> Iterable[Tuple[str, bytes]]:
    # ROT13 is common
    rot13 = rot_alpha(s, 13).encode("utf-8", errors="replace")
    yield ("rot13", rot1
