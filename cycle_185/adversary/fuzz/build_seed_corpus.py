"""Build the seed corpus for cycle_185 adversary fuzzing (T3).

One run, four surface dirs. Per the task body the corpus must cover:
RFC 3986 examples, empty/edge, normal Unicode, adversarial Unicode,
adversarial percent-encoding, plus the 8 README test vectors.

The script is idempotent (overwrites on each invocation) and writes
under cycle_185/adversary/fuzz/corpus/S<N>/seed_NNN.bin. Plaintext inputs
are UTF-8 encoded before writing.
"""
from __future__ import annotations

from pathlib import Path

WORKTREE = Path("/root/.worktrees/t_cycle185-adversary-01")
CORPUS_ROOT = WORKTREE / "cycle_185" / "adversary" / "fuzz" / "corpus"


def _to_bytes(s: str | bytes) -> bytes:
    return s.encode("utf-8") if isinstance(s, str) else s


# Common base seeds — used by all surfaces.
_BASE = [
    # RFC 3986 examples + empty/edge (8 entries)
    b"", b"a", b"hello", b"hello world", b"hello/world", b"~", b"%20",
    b"a/b/c?x=1&y=2#frag",
    # ASCII alphanum
    b"key=val&key2=val2",
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~",
    # Unicode normal (4 entries)
    "café".encode("utf-8"),
    "日本語".encode("utf-8"),
    "🌐".encode("utf-8"),
    "café-日本語-🌐".encode("utf-8"),
    # Unicode adversarial (3 entries)
    b"\xed\xa0\x80",              # lone high surrogate UTF-8
    b"\xef\xbb\xbf",              # BOM
    b"\x00",                       # NUL byte
    # Percent-encoding adversarial (5 entries)
    b"%", b"%2", b"%XY", b"%2F", b"%2f",
    # Percent-encoded pairs
    b"%41", b"%42", b"%00", b"%ff",
]

# S1 / S2 specific (quote surfaces) — same base.
S1_SEEDS = _BASE
S2_SEEDS = _BASE + [b"hello+world", b"a+b+c", b"+", b" ", b"  "]

# S3 / S4 specific (unquote surfaces) — add malformed percent sequences
# so the ValueError path is exercised on the first iter.
_S3_EXTRA = [
    b"%XX", b"%", b"%2", b"%41", b"abc%41", b"%%20", b"%" + b"FF" * 50,
    b"%C3%A9",        # decoded é (valid UTF-8)
    b"%E6%97%A5%E6%9C%AC%E8%AA%9E",  # decoded 日本語
    b"a" * 10_000,
    b"%41" * 100,
]
S3_SEEDS = _BASE + _S3_EXTRA
S4_SEEDS = _BASE + _S3_EXTRA + [b"+", b"++", b"a+b+c", b"%2B", b"+%20"]


def write_corpus(surface: str, seeds: list[bytes]) -> None:
    d = CORPUS_ROOT / surface
    d.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(seeds):
        (d / f"seed_{i:03d}.bin").write_bytes(s)
    print(f"{surface}: wrote {len(seeds)} seeds to {d}")


def main() -> int:
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    write_corpus("S1", S1_SEEDS)
    write_corpus("S2", S2_SEEDS)
    write_corpus("S3", S3_SEEDS)
    write_corpus("S4", S4_SEEDS)
    total = sum(len(s) for s in [S1_SEEDS, S2_SEEDS, S3_SEEDS, S4_SEEDS])
    print(f"total seeds: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())