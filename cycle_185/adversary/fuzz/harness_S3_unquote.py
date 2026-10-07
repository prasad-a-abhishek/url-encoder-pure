"""Fuzz harness S3: unquote(s).

Surface: ``unquote`` ONLY accepts ``str``. Calling with ``None`` or
``bytes`` raises ``TypeError`` — F-001 (None) and F-003 (bytes) audit
findings (VERDICT: MEDIUM).

Coverage:
  - random strings of printable ASCII
  - malformed ``%HH`` triplets (truncated, invalid hex, bare '%')
    → ``ValueError`` is the contract (EXPECTED, NOT a crash)
  - well-formed ``%HH`` triplets → bytes output
  - ``None`` input → ``TypeError`` (BUGSAFE — F-001)
  - ``bytes`` input → ``TypeError`` (F-003 — by-design but annotation drift)
  - mixed well-formed + malformed → some bytes returned + then ValueError
  - 10k-char input to exercise the linear O(n) hot path

What we look for:
  - any exception other than ``ValueError`` (malformed) — that IS a bug
    when on str input. ``TypeError`` is BUGSAFE per F-001/F-003 and is
    recorded under type_error so triage T4 sees the audit-driven count.
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
from url_encoder_pure import unquote  # noqa: E402


# Explicit canonical inputs the audit called out.
CANONICAL_INPUTS = [
    "",                 # empty -> empty bytes
    "%20",              # well-formed -> space byte
    "%20%21",           # multiple -> " !"
    "%XX",              # invalid hex -> ValueError
    "%2",               # truncated -> ValueError
    "%",                # bare %    -> ValueError
    "%%20",             # mixed: % at end, ValueError (truncated next)
    "abc%41",           # 'abcA'
    "abc%",             # truncated % at end
    "%" + "FF" * 50,    # long valid hex
    "a" * 10_000,       # no % at all (fast path)
    "%41" * 5000,       # 5k valid triplets
]


def _run_unquote(s):
    return call_with_timeout(lambda: unquote(s), timeout_s=5.0)


def runner(rng, logger):
    # Distribute input kinds: None (F-001), bytes (F-003), and various str shapes.
    kind_roll = rng.random()
    if kind_roll < 0.05:
        s = None
    elif kind_roll < 0.10:
        s = rng.choice([b"", b"abc", b"%20", b"%XX"])
    else:
        sub = rng.random()
        if sub < 0.4:
            # 40% malformed % — exercises ValueError path
            s = random_malformed_percent(rng, 64)
        elif sub < 0.6:
            # 20% pure random ASCII
            s = random_mixed_string(rng, 64)
        elif sub < 0.75:
            # 15% pure random bytes
            s = random_bytes(rng, 0, 64)
        elif sub < 0.85:
            # 10% long random ASCII (fast-path hot)
            s = random_mixed_string(rng, 5_000)
        elif sub < 0.95:
            # 10% well-formed % triplets
            n = rng.randint(1, 100)
            s = "%" + "".join(
                f"{rng.randint(0, 255):02X}" for _ in range(n)
            )
        else:
            # 5% huge well-formed
            n = rng.randint(1000, 5000)
            s = "%" + "".join(f"{rng.randint(0, 255):02X}" for _ in range(n))

    if rng.random() < 0.02:
        s = rng.choice(CANONICAL_INPUTS)

    raw_bytes = s if isinstance(s, bytes) else None
    in_repr = repr(s)[:200]

    result = None
    try:
        result = _run_unquote(s)
    except TimeoutError as exc:
        write_crash("unquote", logger.completed, in_repr, "hang", str(exc), binary=raw_bytes)
        logger.record("hang", iter=logger.completed, input=in_repr)
        return
    except ValueError as exc:
        # Malformed %HH — contract says ValueError. NOT a crash.
        logger.record(
            "value_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except TypeError as exc:
        # None (F-001) or bytes (F-003) input. BUGSAFE per audit, recorded
        # so triage T4 can see how often it surfaces.
        logger.record(
            "type_error", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        write_crash("unquote", logger.completed, in_repr, "unexpected", tb, binary=raw_bytes)
        logger.record(
            "unexpected", iter=logger.completed, input=in_repr,
            exc_type=type(exc).__name__, exc_msg=str(exc)[:80],
        )
        return

    # Postcondition: result must be bytes.
    if not isinstance(result, bytes):
        write_crash("unquote", logger.completed, in_repr, "postcondition",
                    f"non-bytes return: {type(result).__name__}={result!r}",
                    binary=raw_bytes)
        logger.record("crash", iter=logger.completed, input=in_repr,
                      reason="non-bytes return")
        return

    # Length sanity: result len should be <= input len (each %HH -> 1 byte).
    if isinstance(s, str):
        if len(result) > len(s):
            write_crash("unquote", logger.completed, in_repr, "postcondition",
                        f"result longer than input: in={len(s)} out={len(result)}",
                        binary=raw_bytes)
            logger.record("crash", iter=logger.completed, input=in_repr,
                          reason="output longer than input (impossible for unquote)")
            return

    logger.record("completed", iter=logger.completed, length=len(s) if s else 0,
                  out_len=len(result))


def main() -> int:
    args = parse_common_args("Fuzz harness S3: unquote")
    summary = run_loop("unquote", iters=args.iters, seed=args.seed,
                       timeout_s=args.timeout, runner=runner)
    print(f"unquote: {summary}")
    return 0 if summary["crashes"] == 0 and summary["hangs"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())