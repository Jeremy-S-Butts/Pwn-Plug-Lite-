# Entropy.py
# Purpose: compute Shannon entropy for packet field values

from __future__ import annotations

import math
from collections import Counter
from typing import Any


def _to_bytes(value: Any) -> bytes:
    """
    Best-effort conversion of common Scapy field values to bytes.
    """
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8", errors="ignore")
    if isinstance(value, int):
        # Minimal bytes to represent int (avoid huge fixed widths)
        if value == 0:
            return b"\x00"
        length = (value.bit_length() + 7) // 8
        return value.to_bytes(length, byteorder="big", signed=False)
    # Fallback: string representation
    return str(value).encode("utf-8", errors="ignore")


def fieldEntropy(value: Any) -> float:
    """
    Shannon entropy (bits/byte) of the input value.
    Returns 0.0 for empty input.
    """
    data = _to_bytes(value)
    if not data:
        return 0.0

    counts = Counter(data)
    n = len(data)

    ent = 0.0
    for c in counts.values():
        p = c / n
        ent -= p * math.log2(p)

    return ent
