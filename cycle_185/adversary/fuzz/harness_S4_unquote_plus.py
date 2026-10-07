"""Fuzz harness S4: unquote_plus(s).

Surface: same as S3 (unquote) but with ``+`` -> space pre-transform
(``unquote_plus`` is implemented as ``unquote(s.replace('+', ' '))``).

Coverage is identical to S3 with extra ``+``-bearing inputs.

What we look for:
  - any exception other than ``ValueError`` (malformed) and ``TypeError``
    (None / bytes per F-001/F-003) — those are bugs.
  - non-bytes return value.
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
    random_malformed_percent,
    random_mixed_string,
    run_loop,
    write_crash,
)

ensure_src_on_path()
from url_encoder_pure import unquote_plus  # noqa: E402


# Same canonical inputs as S3 plus '+' cases.
CANONICAL_INPUTS = [
    "",
    "+",
    "+++",
    "%20",
    "a+b+c",    # 'a b c' after +->space
    "%2B",      # well-formed '+' (literal)
    "+%20",     # '+' becomes space, %20 becomes space too
    "%XX",
    "%2",
    "%",
    "abc%41",
    "a" * 10_000,
]


def _run_unquote_plus(s):
    return call_with_timeout(lambda: unquote_plus(s), timeout_s=5.0)


def runner(rng, logger):
    kind_roll = rng.random()
    if kind_roll < 0.05:
        s = None
    elif kind_roll < 0.10:
        s = rng.choice([b"", b"abc", b"+", b"%20"])
    else:
        sub = rng.random()
        if sub < 0.35:
            # 35% malformed % — ValueError path
            s = random_malformed_percent(rng, 64)
        elif sub < 0.55:
            # 20% '+'-heavy random strings
            base = random_mixed_string(rng, 32)
            # Inject 1-5 '+' characters
            n_plus = rng.randint(1, 5)
            positions = sorted(rng.sample(range(len(base) + n_plus), k=n_plus))
            chars = list(base)
            for pos in reversed(positions):
                chars.insert(pos, "+")
            s = "".join(chars)
        elif sub < 0.70:
            # 15% pure random ASCII
            s = random_mixed_string(rng, 64)
        elif sub < 0.80:
            # 10% pure random bytes
            s = random_bytes(rng, 0, 64)
        elif sub < 0.90:
            # 10% long random ASCII
            s = random_mixed_string(rng, 5_000)
        else:
            # 10% huge well-formed % triplets
            n = rng.randint(1000, 5000)
            s = "%" + "".join(f"{rng.randint(0, 255):02X}" for _ in range(n))

    if rng.random() < 0.02:
        s = rng.choice(CANONICAL_INPUTS)

    raw_bytes = s if isinstance(s, bytes) else None
    in_repr = repr(s)[:200]

    result = None
    try:
        result = _run_unquote_plus(s)
    except TimeoutError as exc:
        write_crash("unquote_plus", logger.completed, in_repr, "hang", str(exc), binary=raw_bytes)
        logger.record("hang", iter=logger.completed, input=in_repr)
        return
    except ValueError as exc:
        logger.record(
            "value_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except TypeError as exc:
        # F-001 (None) / F-003 (bytes) audit-driven BUGSAFE.
        logger.record(
            "type_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        write_crash("unquote_plus", logger.completed, in_repr, "unexpected", tb, binary=raw_bytes)
        logger.record(
            "unexpected", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return

    if not isinstance(result, bytes):
        write_crash("unquote_plus", logger.completed, in_repr, "postcondition",
                    f"non-bytes return: {type(result).__name__}={result!r}",
                    binary=raw_bytes)
        logger.record("crash", iter=logger.completed, input=in_repr,
                      reason="non-bytes return")
        return

    if isinstance(s, str):
        if len(result) > len(s):
            write_crash("unquote_plus", logger.completed, in_repr, "postcondition",
                        f"result longer than input: in={len(s)} out={len(result)}",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="output longer than input (impossible for unquote)")
            return

    logger.record("completed", iter=logger.completed, length=len(s) if s else 0,
                  out_len=len(result))


def main() -> int:
    args = parse_common_args("Fuzz harness S4: unquote_plus")
    summary = run_loop("unquote_plus", iters=args.iters, seed=args.seed,
                       timeout_s=args.timeout, runner=runner)
    print(f"unquote_plus: {summary}")
    return 0 if summary["crashes"] == 0 and summary["hangs"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())