"""Fuzz harness S2: quote_plus(s, safe='').

Covers the form encoder (RFC 1866 / WHATWG): space -> '+', rest same as quote.

Surface is identical to S1 except for the space->'+' transform, so the
fuzz distribution is the same and we reuse the same postconditions. We
specifically add space-heavy inputs to exercise the .replace(" ", ".",.

What we look for:
  - any exception other than ``UnicodeError`` (surrogates) and
    ``TypeError`` (non-{None,bytes,str}) — those are bugs.
  - ``quote_plus`` returning something other than str or None.
  - space surviving in the output (it MUST become '+').
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
from url_encoder_pure import quote_plus  # noqa: E402


# Explicit canonical inputs — same shape as S1 plus space-heavy cases.
CANONICAL_INPUTS = [
    None,
    b"",
    "",
    b"abc",
    "abc",
    b" ",
    " ",
    b"  ",        # multiple spaces
    "hello world",
    b"a b c d",   # spaces between
    b"   spaces   at   edges   ",
    b"a" * 10_000,
    b"\x00",
    b"%20",       # literal '%20' — encode keeps literal, does NOT decode
]


def _run_quote_plus(s, safe):
    return call_with_timeout(lambda: quote_plus(s, safe=safe), timeout_s=5.0)


def runner(rng, logger):
    # Bias toward space-containing inputs (10% extra).
    space_roll = rng.random()
    if space_roll < 0.10:
        # Inject 1-10 spaces somewhere in the input.
        n_spaces = rng.randint(1, 10)
        base = random_mixed_string(rng, 32)
        s = (" " * n_spaces) + base + (" " * n_spaces)
    elif space_roll < 0.15:
        s = None
    else:
        kind_roll = rng.random()
        if kind_roll < 0.6:
            sub = rng.random()
            if sub < 0.4:
                s = random_bytes(rng, 0, 64)
            elif sub < 0.7:
                s = random_bytes(rng, 100, 1000)
            elif sub < 0.85:
                s = random_bytes(rng, 1000, 10_000)
            else:
                s = random_bytes(rng, 10_000, 100_000)
        else:
            sub = rng.random()
            if sub < 0.5:
                s = random_surrogate_string(rng, 64)
            elif sub < 0.8:
                s = random_mixed_string(rng, 64)
            else:
                s = random_unreserved_bytes(rng, 64).decode("ascii")

    if rng.random() < 0.02:
        s = rng.choice(CANONICAL_INPUTS)

    if rng.random() < 0.7:
        safe = b""
    else:
        safe = bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 8)))

    raw_bytes = s if isinstance(s, bytes) else None
    in_repr = repr(s)[:200]

    result = None
    try:
        result = _run_quote_plus(s, safe)
    except TimeoutError as exc:
        write_crash("quote_plus", logger.completed, in_repr, "hang", str(exc), binary=raw_bytes)
        logger.record("hang", iter=logger.completed, input=in_repr)
        return
    except UnicodeError as exc:
        logger.record(
            "unicode_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except TypeError as exc:
        logger.record(
            "type_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        write_crash("quote_plus", logger.completed, in_repr, "unexpected", tb, binary=raw_bytes)
        logger.record(
            "unexpected", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return

    # Postconditions
    if s is None:
        if result is not None:
            write_crash("quote_plus", logger.completed, in_repr, "postcondition",
                        f"quote_plus(None) returned {result!r}, expected None",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="quote_plus(None) returned non-None")
            return
        logger.record("none_handled", iter=logger.completed, input=in_repr)
        return

    if not isinstance(result, str):
        write_crash("quote_plus", logger.completed, in_repr, "postcondition",
                    f"non-str return: {type(result).__name__}={result!r}",
                    binary=raw_bytes)
        logger.record("crash", iter=logger.completed, input=in_repr,
                      reason="non-str return")
        return

    # Invariant 22 (form encoder): no literal spaces in output, ever.
    if " " in result:
        write_crash("quote_plus", logger.completed, in_repr, "postcondition",
                    f"literal space in output: {result[:80]!r}",
                    binary=raw_bytes)
        logger.record("crash", iter=logger.completed, input=in_repr,
                      reason="space in output (should be '+')")
        return

    # Length sanity (same bounds as S1).
    if isinstance(s, (bytes, str)):
        s_len = len(s)
        if len(result) < s_len:
            write_crash("quote_plus", logger.completed, in_repr, "postcondition",
                        f"result shorter than input: in={s_len} out={len(result)}",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="output shorter than input")
            return
        if len(result) > 3 * s_len + 16:
            write_crash("quote_plus", logger.completed, in_repr, "postcondition",
                        f"output suspiciously long: in={s_len} out={len(result)}",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="output length explosion")
            return

    logger.record("completed", iter=logger.completed, length=len(s) if s else 0,
                  out_len=len(result))


def main() -> int:
    args = parse_common_args("Fuzz harness S2: quote_plus")
    summary = run_loop("quote_plus", iters=args.iters, seed=args.seed,
                       timeout_s=args.timeout, runner=runner)
    print(f"quote_plus: {summary}")
    return 0 if summary["crashes"] == 0 and summary["hangs"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())