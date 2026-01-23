#!/usr/bin/env python3
"""
True random passphrase generator (cryptographically secure).

- Uses secrets (NOT random) for security.
- Supports a custom wordlist file (one word per line), or a built-in fallback list.
- Optionally adds a separator and/or a digit block (useful for legacy password policies).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
import string
from typing import List, Optional


DEFAULT_WORDS = [
    # Fallback list (small). For real use, provide a wordlist file with thousands of words.
    "ocean", "lamp", "orbit", "violet", "monarch", "cable", "silent", "harbor",
    "raven", "puzzle", "matrix", "cactus", "nebula", "saturn", "ember", "timber",
]


@dataclass(frozen=True)
class PassphraseConfig:
    num_words: int = 4
    separator: str = "-"
    capitalize: bool = False
    add_digits: int = 0  # 0 = no digits; 2..6 often used for convenience
    wordlist_path: Optional[Path] = None
    min_word_length: int = 3
    max_word_length: int = 20


def load_wordlist(path: Path, min_len: int, max_len: int) -> List[str]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Wordlist not found: {path}")

    words: List[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        w = line.strip()
        if not w:
            continue
        # Keep only simple word tokens; you can relax this if your wordlist is clean.
        if any(ch.isspace() for ch in w):
            continue
        if min_len <= len(w) <= max_len:
            words.append(w)

    if len(words) < 1000:
        # Not an error—just a warning sign for security strength.
        # Larger wordlists dramatically increase entropy.
        print(f"Warning: wordlist contains only {len(words)} usable words. "
              f"Consider using a larger list (e.g., 10k+ words).")
    return words


def generate_passphrase(cfg: PassphraseConfig) -> str:
    if cfg.num_words < 3:
        raise ValueError("Use at least 3 words; 4+ is recommended for most users.")
    if cfg.add_digits < 0:
        raise ValueError("add_digits must be >= 0")

    if cfg.wordlist_path:
        words = load_wordlist(cfg.wordlist_path, cfg.min_word_length, cfg.max_word_length)
    else:
        words = DEFAULT_WORDS

    if not words:
        raise ValueError("No usable words available after filtering.")

    chosen = [secrets.choice(words) for _ in range(cfg.num_words)]

    if cfg.capitalize:
        chosen = [w.capitalize() for w in chosen]

    phrase = cfg.separator.join(chosen)

    if cfg.add_digits:
        digits = "".join(secrets.choice(string.digits) for _ in range(cfg.add_digits))
        phrase = f"{phrase}{cfg.separator}{digits}"

    return phrase


def estimate_entropy_bits(wordlist_size: int, num_words: int) -> float:
    """
    Approximate entropy (bits) for 'num_words' independently chosen words
    from a wordlist of size 'wordlist_size':
        entropy = log2(wordlist_size ** num_words) = num_words * log2(wordlist_size)
    """
    if wordlist_size <= 1 or num_words <= 0:
        return 0.0
    # Use Python's integer bit_length trick for roughness? We'll do math via logs safely:
    import math
    return num_words * math.log2(wordlist_size)


def main() -> None:
    # Example configuration:
    cfg = PassphraseConfig(
        num_words=4,
        separator="-",
        capitalize=False,
        add_digits=0,
        # wordlist_path=Path("dictionarywords.txt"),
    )

    phrase = generate_passphrase(cfg)
    print("Passphrase:", phrase)

    # Entropy estimate (meaningful only with a large real wordlist)
    wordlist_size = len(load_wordlist(cfg.wordlist_path, cfg.min_word_length, cfg.max_word_length)) if cfg.wordlist_path else len(DEFAULT_WORDS)
    bits = estimate_entropy_bits(wordlist_size, cfg.num_words)
    print(f"Estimated entropy: ~{bits:.1f} bits (wordlist_size={wordlist_size}, words={cfg.num_words})")


if __name__ == "__main__":
    main()
