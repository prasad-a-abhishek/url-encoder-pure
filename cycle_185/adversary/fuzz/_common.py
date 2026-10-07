"""Shared helpers for url-encoder-pure fuzzing harnesses.

Pure-stdlib (random, signal, threading, traceback, json, time). No atheris,
no hypothesis, no external deps.

Surface-agnostic: each harness imports ``run_loop`` and a crash writer.
Harnesses are deterministic w.r.t. the seed (``--seed N``).
"""
from __future__ import annotations

import argparse
import json
import random
import signal
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Per-call hang threshold. 5s is generous; quote on a 100KB byte string
# is ~10ms, so 5s catches genuine infinite loops only.
DEFAULT_TIMEOUT_SECONDS = 5.0

# Default iteration count if the harness caller doesn't override.
DEFAULT_ITERS = 5000

# Repo-relative paths (the harness may be run from anywhere; resolve against
# the project root once at import time).
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent.parent  # cycle_185/adversary/fuzz -> project root
_CRASH_DIR = _HERE / "crashes"
_LOG_DIR = _HERE / "logs"


# ---------------------------------------------------------------------------
# Timeout machinery
# ---------------------------------------------------------------------------
# signal.alarm only works on the main thread; threading.Timer is the
# cross-platform fallback. We pick whichever is available in the current
# thread.
class _TimeoutError(Exception):
    pass


def _alarm_handler(signum, frame):  # noqa: ARG001
    raise _TimeoutError("call exceeded per-call timeout")


def call_with_timeout(fn: Callable[[], Any], timeout_s: float) -> Any:
    """Invoke ``fn`` and return its result. Raise _TimeoutError on hang.

    Uses signal.alarm on the main thread (Unix only); falls back to a
    threading.Timer on worker threads or non-Unix platforms.
    """
    use_signal = (
        sys.platform != "win32"
        and threading.current_thread() is threading.main_thread()
    )
    if use_signal:
        old = signal.signal(signal.SIGALRM, _alarm_handler)
        # setitimer accepts fractional seconds; alarm rounds to int.
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
        try:
            return fn()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
    # Fallback: threading.Timer.
    def _raise_timeout() -> None:
        raise _TimeoutError("call exceeded per-call timeout")
    timer = threading.Timer(timeout_s, _raise_timeout)
    timer.daemon = True
    timer.start()
    try:
        return fn()
    finally:
        timer.cancel()


# ---------------------------------------------------------------------------
# Crash writer
# ---------------------------------------------------------------------------
def _ensure_dirs() -> None:
    _CRASH_DIR.mkdir(parents=True, exist_ok=True)
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_crash(
    surface: str,
    idx: int,
    input_repr: str,
    kind: str,
    tb: str,
    binary: bytes | None = None,
) -> Path:
    """Persist a crash reproduction artifact. Returns the .in path.

    If ``binary`` is provided, also writes a .bin sibling holding the raw
    bytes (useful for byte-input surfaces like S1/S2 quote). The .in file
    always holds a textual repr of the input for human review.
    """
    _ensure_dirs()
    in_path = _CRASH_DIR / f"{surface}_{idx:05d}_{kind}.in"
    stack_path = _CRASH_DIR / f"{surface}_{idx:05d}_{kind}.stack.txt"
    in_path.write_text(input_repr, encoding="utf-8", errors="replace")
    stack_path.write_text(tb, encoding="utf-8", errors="replace")
    if binary is not None:
        bin_path = _CRASH_DIR / f"{surface}_{idx:05d}_{kind}.bin"
        bin_path.write_bytes(binary)
    return in_path


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
class RunLogger:
    """Append-only structured log writer (JSONL). One file per surface per run."""

    def __init__(self, surface: str, seed: int, iters: int) -> None:
        _ensure_dirs()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = _LOG_DIR / f"run_{surface}_{ts}_seed{seed}_n{iters}.log"
        self.fh = self.path.open("w", encoding="utf-8")
        self.surface = surface
        self.start_ts = time.time()
        self.crashes = 0
        self.hangs = 0
        self.unexpected = 0
        self.value_errors = 0
        self.unicode_errors = 0
        self.type_errors = 0
        self.completed = 0
        self.skipped = 0
        self.none_handled = 0

    def record(self, event: str, **fields: Any) -> None:
        rec = {
            "ts": time.time(),
            "surface": self.surface,
            "event": event,
            **fields,
        }
        self.fh.write(json.dumps(rec, default=str) + "\n")
        self.fh.flush()
        if event == "crash":
            self.crashes += 1
        elif event == "hang":
            self.hangs += 1
        elif event == "unexpected":
            self.unexpected += 1
        elif event == "value_error":
            self.value_errors += 1
        elif event == "unicode_error":
            self.unicode_errors += 1
        elif event == "type_error":
            self.type_errors += 1
        elif event == "completed":
            self.completed += 1
        elif event == "skipped":
            self.skipped += 1
        elif event == "none_handled":
            self.none_handled += 1

    def close(self) -> dict:
        elapsed = time.time() - self.start_ts
        summary = {
            "surface": self.surface,
            "elapsed_s": round(elapsed, 3),
            "crashes": self.crashes,
            "hangs": self.hangs,
            "unexpected": self.unexpected,
            "value_errors": self.value_errors,
            "unicode_errors": self.unicode_errors,
            "type_errors": self.type_errors,
            "completed": self.completed,
            "skipped": self.skipped,
            "none_handled": self.none_handled,
            "log_path": str(self.path),
        }
        self.fh.write("\n# SUMMARY\n" + json.dumps(summary) + "\n")
        self.fh.close()
        return summary


# ---------------------------------------------------------------------------
# Random input generators
# ---------------------------------------------------------------------------
# RFC 3986 §2.3 unreserved chars; everything else must be %-encoded.
_UNRESERVED_BYTES = bytes(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    b"abcdefghijklmnopqrstuvwxyz"
    b"0123456789-_.~"
)


def random_bytes(rng: random.Random, min_len: int = 0, max_len: int = 256) -> bytes:
    """Random bytes of length in [min_len, max_len]."""
    n = rng.randint(min_len, max_len)
    return bytes(rng.randint(0, 255) for _ in range(n))


def random_unreserved_bytes(rng: random.Random, max_len: int = 64) -> bytes:
    """Random bytes drawn from the RFC 3986 unreserved set only.

    Encodes to no-op: useful as a baseline that should NEVER crash.
    """
    n = rng.randint(0, max_len)
    return bytes(rng.choice(_UNRESERVED_BYTES) for _ in range(n))


def random_malformed_percent(rng: random.Random, max_len: int = 64) -> str:
    """Random string of '%XX' triplets where X may be invalid hex.

    Targets unquote's malformed-% ValueError path. Mixes valid + invalid
    hex chars, truncated triplets, and bare '%'.
    """
    pool_hex = "0123456789ABCDEFabcdefGHIJKLMNOPQRSTUVWXYZghijklmnopqrstuvwxyz!@#$%"
    pool_other = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~ "
    n = rng.randint(0, max_len)
    out = []
    for _ in range(n):
        roll = rng.random()
        if roll < 0.6:
            out.append("%")
            out.append(rng.choice(pool_hex))
            out.append(rng.choice(pool_hex))
        elif roll < 0.8:
            out.append("%")
            out.append(rng.choice(pool_other))
        else:
            out.append(rng.choice(pool_other))
    return "".join(out)


def random_mixed_string(rng: random.Random, max_len: int = 64) -> str:
    """Random printable ASCII string mixing letters, digits, punctuation,
    whitespace. Useful for fuzzing str-input surfaces.
    """
    import string as _s
    pool = _s.ascii_letters + _s.digits + _s.punctuation + " \t\n"
    n = rng.randint(0, max_len)
    return "".join(rng.choice(pool) for _ in range(n))


def random_surrogate_string(rng: random.Random, max_len: int = 64) -> str:
    """Random str that may contain surrogate halves (U+D800..U+DFFF).

    Targets quote's UnicodeEncodeError path. UTF-8 cannot encode lone
    surrogates — encoding raises UnicodeEncodeError under strict mode.
    """
    n = rng.randint(0, max_len)
    out = []
    for _ in range(n):
        roll = rng.random()
        if roll < 0.3:
            # lone high surrogate
            out.append(chr(rng.randint(0xD800, 0xDBFF)))
        elif roll < 0.5:
            # lone low surrogate
            out.append(chr(rng.randint(0xDC00, 0xDFFF)))
        elif roll < 0.7:
            # BMP codepoint that may include other "interesting" chars
            out.append(chr(rng.randint(0, 0xFFFF)))
        else:
            # ASCII printable
            out.append(chr(rng.randint(0x20, 0x7E)))
    return "".join(out)


# ---------------------------------------------------------------------------
# Common runner
# ---------------------------------------------------------------------------
def parse_common_args(description: str) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--iters", type=int, default=DEFAULT_ITERS,
                   help=f"iterations (default: {DEFAULT_ITERS})")
    p.add_argument("--seed", type=int, default=42,
                   help="PRNG seed (default: 42)")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS,
                   help=f"per-call timeout seconds (default: {DEFAULT_TIMEOUT_SECONDS})")
    return p.parse_args()


def run_loop(
    surface: str,
    iters: int,
    seed: int,
    timeout_s: float,
    runner: Callable[[random.Random, RunLogger], None],
) -> dict:
    """Drive ``runner`` for ``iters`` iterations under a single seed.

    ``runner`` is invoked once per iteration and is expected to call
    ``logger.record`` and ``call_with_timeout`` itself.
    """
    rng = random.Random(seed)
    logger = RunLogger(surface=surface, seed=seed, iters=iters)
    try:
        for i in range(iters):
            try:
                runner(rng, logger)
            except Exception as exc:  # noqa: BLE001
                # Defensive: anything escaping the harness is a bug here.
                tb = traceback.format_exc()
                write_crash(surface, i, "<runner raised>", "runner_error", tb)
                logger.record("crash", iter=i, kind="runner_error", error=repr(exc))
    finally:
        summary = logger.close()
    return summary


# ---------------------------------------------------------------------------
# Path / import helper
# ---------------------------------------------------------------------------
def ensure_src_on_path() -> None:
    """Insert ``src/`` at the front of sys.path so ``import url_encoder_pure`` works."""
    src = str(_PROJECT_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)