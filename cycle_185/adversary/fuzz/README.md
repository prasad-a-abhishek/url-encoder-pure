# Fuzzing harnesses — cycle_185/adversary/T2

Pure-stdlib fuzzing harnesses for **url-encoder-pure**. No atheris, no
hypothesis, no native fuzzers — stdlib `random` + per-call 5-second
timeout (signal.alarm on main thread, threading.Timer fallback).

## Surfaces

| ID | Surface | Function | Input shape | Notes |
|----|---------|----------|-------------|-------|
| S1 | core encode   | `quote(s, safe='')`           | `bytes` \| `str` \| `None` | Invariant 21 path; surrogate halves raise `UnicodeEncodeError` (F-002 Medium, audit-flagged). |
| S2 | form encode   | `quote_plus(s, safe='')`      | `bytes` \| `str` \| `None` | Identical to S1 plus space→`+` transform. |
| S3 | inverse       | `unquote(s)`                  | `str` only                 | `None`/`bytes` → `TypeError` (F-001/F-003 Medium, audit-flagged). Malformed `%HH` → `ValueError` (EXPECTED). |
| S4 | form inverse  | `unquote_plus(s)`             | `str` only                 | Same as S3 plus `+`→space pre-transform. |

## Running

Each harness accepts `--iters`, `--seed`, `--timeout`:

```bash
cd cycle_185/adversary/fuzz
python3 harness_S1_quote.py        --iters 5000 --seed 42 --timeout 5.0
python3 harness_S2_quote_plus.py   --iters 5000 --seed 42 --timeout 5.0
python3 harness_S3_unquote.py      --iters 5000 --seed 42 --timeout 5.0
python3 harness_S4_unquote_plus.py --iters 5000 --seed 42 --timeout 5.0
```

## What gets written

Each run produces `logs/run_<surface>_<UTC>_seed<N>_n<ITERS>.log`
(JSONL — one record per iteration + a trailing `# SUMMARY` JSON).

Crash / hang / unexpected artifacts land in `crashes/<surface>_<idx>_<kind>.{in,stack.txt,bin}`.
The `.in` file holds a textual repr; `.bin` (when present) holds the
raw bytes for byte-input surfaces.

`corpus/` is reserved for T3 to write a seeded corpus if the random
generator doesn't hit the audit-flagged edge cases within 5000 iters.
For cycle_185 it's empty — the canonical inputs lists in each harness
already pin the audit edge cases.

## Exit codes

Harness exits 0 if `crashes == 0 AND hangs == 0`. Any non-zero exit is a
bug to be triaged by T4.

## Classification scheme

| Event recorded | Meaning |
|----------------|---------|
| `completed`        | Normal successful call (postcondition check passed). |
| `none_handled`     | `quote(None)`/`quote_plus(None)` returned `None` (Invariant 21 path). |
| `unicode_error`    | `UnicodeEncodeError` / `UnicodeDecodeError` raised — RFC-correct (surrogates, malformed UTF-8) but F-002 audit says it's a real bug. NOT a crash. |
| `type_error`       | `TypeError` raised on non-{None,bytes,str} input (or non-str for unquote). F-001/F-003 audit-driven — counted but not crashed. |
| `value_error`      | `ValueError` on malformed `%HH` — RFC-correct. NOT a crash. |
| `hang`             | Per-call timeout (5s default). CRASH. |
| `unexpected`       | Any other exception class. CRASH. |
| `crash`            | Postcondition violation (e.g. `quote(None)` returned non-`None`, output longer than 3×input). CRASH. |

## Anti-patterns

- ❌ Importing atheris / hypothesis / libfuzzer-ctypes — pure stdlib only.
- ❌ Skipping the per-input 5s hang watchdog.
- ❌ Skipping the EXPECTED vs BUGSAFE classification (triage T4 needs it).
- ❌ Touching `src/`, `tests/`, `pyproject.toml`, `README.md`, etc. — T2 only writes under `cycle_185/adversary/fuzz/`.
- ❌ Skipping smoke-test (100 iters). T3 will hydrate from these harnesses; a broken harness means a broken T3.