"""Fuzz harness S1: quote(s, safe='').

Covers:
  - ``quote(None)`` → must return None (Invariant 21; safe path)
  - ``quote(bytes)`` → must accept bytes input (spec contract)
  - ``quote(str)`` → must accept str input
  - str input with surrogate halves → ``UnicodeEncodeError`` is RFC-correct
    but flagged in T1 audit F-002 (Medium). The harness DOES NOT call this
    a crash — it records ``unicode_error`` and moves on. Triage T4 will
    reclassify against audit F-002 if needed.
  - ``quote([])`` empty list → '' per F-004 (accidental, not robust) —
    the harness treats non-str/bytes/None as ``unexpected`` (BUGSAFE).
  - long inputs up to 100 KB to exercise the linear O(n) hot path

What we look for:
  - any exception other than ``TypeError`` (caught for non-{None,str,bytes})
    and ``UnicodeError`` (caught for surrogate halves) — those are bugs.
  - non-str/None return value (bug).
  - hang (5s per call).
"""
from __future__ import annotations

import sys
import traceback

from _common import (
    call_with_timeout,
    ensure_src_on_path,
    parse_common_args,
    random_bytes,
    random_mixed_string,
    random_surrogate_string,
    random_unreserved_bytes,
    run_loop,
    write_crash,
)

ensure_src_on_path()
from url_encoder_pure import quote  # noqa: E402


# Explicit canonical inputs the audit called out.
# These exercise known edge cases the PRNG might miss.
CANONICAL_INPUTS = [
    None,           # Invariant 21: must return None, no raise
    b"",            # empty bytes -> ''
    "",             # empty str   -> ''
    b"abc",         # unreserved only -> 'abc'
    "abc",          # unreserved only -> 'abc'
    b"/",           # safe default is '/'? Actually default safe=b'' so '/' encodes
    "/",            # same
    b"hello world", # space encodes to %20
    "hello world",  # same
    b"a" * 10_000,  # 10k same byte
    "a" * 10_000,   # 10k same char
    b"\x00",        # NUL byte -> %00
    "\x00",         # same as str (single NUL char)
    b"\xff" * 100,  # high bytes
    b"\xc3\xa9",    # valid UTF-8 é
    "é",            # str with é
    b"%20",         # literal %20 input — does NOT self-decode (encode is one-way)
]


def _run_quote(s, safe):
    """Single quote() invocation with 5s timeout."""
    return call_with_timeout(lambda: quote(s, safe=safe), timeout_s=5.0)


def runner(rng, logger):
    # Pick input kind: 5% None, rest split across bytes/str shapes.
    kind_roll = rng.random()
    if kind_roll < 0.05:
        s = None
    elif kind_roll < 0.10:
        s = rng.choice([b"", "", b"abc", "abc"])
    else:
        # 60% bytes, 40% str
        if rng.random() < 0.6:
            sub_roll = rng.random()
            if sub_roll < 0.4:
                s = random_bytes(rng, 0, 64)
            elif sub_roll < 0.7:
                s = random_bytes(rng, 100, 1000)
            elif sub_roll < 0.85:
                s = random_bytes(rng, 1000, 10_000)
            else:
                s = random_bytes(rng, 10_000, 100_000)  # hot path
        else:
            sub_roll = rng.random()
            if sub_roll < 0.5:
                s = random_surrogate_string(rng, 64)  # F-002 territory
            elif sub_roll < 0.8:
                s = random_mixed_string(rng, 64)
            else:
                s = random_unreserved_bytes(rng, 64).decode("ascii")

    # Occasionally inject a canonical edge case (~2% of the time)
    if rng.random() < 0.02:
        s = rng.choice(CANONICAL_INPUTS)

    # Pick safe arg: 70% default b'', 30% random bytes
    if rng.random() < 0.7:
        safe = b""
    else:
        safe = bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 8)))

    # Snapshot the raw bytes (for crash artifacts) — str inputs don't have one.
    raw_bytes = s if isinstance(s, bytes) else None
    in_repr = repr(s)[:200]

    result = None
    try:
        result = _run_quote(s, safe)
    except TimeoutError as exc:
        write_crash("quote", logger.completed, in_repr, "hang", str(exc), binary=raw_bytes)
        logger.record("hang", iter=logger.completed, input=in_repr)
        return
    except UnicodeError as exc:
        # Surrogate halves raise UnicodeEncodeError. RFC-correct (strict
        # encoding of lone surrogates is impossible) but flagged F-002 Medium.
        # NOT a crash; record as unicode_error so triage T4 sees the count.
        logger.record(
            "unicode_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except TypeError as exc:
        # quote() only accepts (None, bytes, str). Everything else (list,
        # int, dict, ...) raises TypeError — that IS the contract.
        # F-004 noted quote([]) accidentally returns '' (empty iterable),
        # which we will not flag here; the audit is the source of truth.
        logger.record(
            "type_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        write_crash("quote", logger.completed, in_repr, "unexpected", tb, binary=raw_bytes)
        logger.record(
            "unexpected", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return

    # Postconditions
    if s is None:
        # Invariant 21 path: must return None.
        if result is not None:
            write_crash("quote", logger.completed, in_repr, "postcondition",
                        f"quote(None) returned {result!r}, expected None",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="quote(None) returned non-None")
            return
        logger.record("none_handled", iter=logger.completed, input=in_repr)
        return

    if not isinstance(result, str):
        write_crash("quote", logger.completed, in_repr, "postcondition",
                    f"non-str return: {type(result).__name__}={result!r}",
                    binary=raw_bytes)
        logger.record("crash", iter=logger.completed, input=in_repr,
                      reason="non-str return")
        return

    # Sanity: result length should be >= input length (everything is at
    # least 1 char when encoded). Upper bound = 3x the UTF-8 byte length
    # (each byte becomes %HH = 3 chars). For str inputs use the encoded
    # byte length because non-BMP chars expand 3 bytes per char in UTF-8.
    # Note: stray surrogate halves raise UnicodeError before this point
    # (handled in the except block above), so the only str inputs that
    # reach here have well-formed UTF-8.
    if isinstance(s, (bytes, str)):
        if isinstance(s, str):
            byte_len = len(s.encode("utf-8"))
        else:
            byte_len = len(s)
        char_len = len(s)
        if len(result) < char_len:
            write_crash("quote", logger.completed, in_repr, "postcondition",
                        f"result shorter than input: in_chars={char_len} out={len(result)}",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="output shorter than input (chars)")
            return
        if len(result) > 3 * byte_len + 16:
            write_crash("quote", logger.completed, in_repr, "postcondition",
                        f"output suspiciously long: in_bytes={byte_len} out={len(result)}",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="output length explosion")
            return

    logger.record("completed", iter=logger.completed, length=len(s) if s else 0,
                  out_len=len(result))


def main() -> int:
    args = parse_common_args("Fuzz harness S1: quote")
    summary = run_loop("quote", iters=args.iters, seed=args.seed,
                       timeout_s=args.timeout, runner=runner)
    print(f"quote: {summary}")
    return 0 if summary["crashes"] == 0 and summary["hangs"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())