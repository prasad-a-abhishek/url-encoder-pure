# FUZZ_STATS — url-encoder-pure, cycle_185

**Repo:** `url-encoder-pure` v0.1.0
**Commit audited:** `b937571` (cycle_185/qa3 master)
**Branch:** `wt/cycle185-adversary-01`
**Seed:** 42
**Iterations per surface:** 5000
**Total iterations:** 20000 (4 surfaces × 5000)
**Date:** 2026-10-07 UTC
**Operator:** `@default` (default profile)

| Surface | Iters | Runtime (s) | Crashes | Hangs | OOM | Completed | UnicodeError | TypeError | ValueError | Unexpected | Skipped |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 `quote` | 5000 | 6.736 | 0 | 0 | 0 | 3898 | 851 | 0 | 0 | 0 | 0 |
| S2 `quote_plus` | 5000 | 6.915 | 0 | 0 | 0 | 3928 | 814 | 0 | 0 | 0 | 0 |
| S3 `unquote` | 5000 | 0.447 | 0 | 0 | 0 | 1483 | 0 | 1139 | 2378 | 0 | 0 |
| S4 `unquote_plus` | 5000 | 0.725 | 0 | 0 | 0 | 1833 | 0 | 694 | 2225 | **248** | 0 |

**Total: 20000 iters across 4 surfaces, 0 crashes, 0 hangs, 0 OOM, 248 unexpected (all F1: `unquote_plus(None) → AttributeError`, REGRESSED — see FUZZING_REPORT.md §5).**

**Environment:** Python 3.11.15, Linux 6.12.67-linuxkit, no ASan (pure Python), seed=42, `random.Random(seed=42)` only.

## Findings

1 distinct finding class across 20000 iters:

- **F1 — Medium, REGRESSED** — `unquote_plus(None) → AttributeError: 'NoneType' object has no attribute 'replace'` at `src/url_encoder_pure/__init__.py:82`. **248 event occurrences** / **219 dedup'd crash artifacts** / 1 distinct root cause / 1 distinct stack site. REGRESSED (was VULN_AUDIT F-001 — fix2 partial closure missed decode side; same gap pattern as the encode-side closure). See FUZZING_REPORT.md §5.

The **851 + 814 UnicodeError** events on S1/S2 are EXPECTED — the fuzzer feeds lone-surrogate `str` inputs and the API correctly raises `UnicodeEncodeError` per RFC 3986 strict mode (VULN_AUDIT F-002).

The **1139 + 694 TypeError** events on S3/S4 are EXPECTED (audit-driven BUGSAFE classification) — the fuzzer feeds `None`/`bytes`/`int` and the API raises `TypeError`/`AttributeError`. S3's `unquote(None)` raises `TypeError: argument of type 'NoneType' is not iterable` (classified `type_error`). S4's `unquote_plus(None)` raises `AttributeError` (classified `unexpected` → F1).

The **2378 + 2225 ValueError** events on S3/S4 are EXPECTED — the fuzzer feeds malformed `%HH` sequences and the API correctly raises structured `ValueError` per RFC 3986 contract.

## Notes

- Harness design uses `signal.setitimer` (main thread, Unix) with `threading.Timer` fallback (non-Unix) for 5.0 s per-call timeout. No iteration exceeded timeout — all completed in well under 100 ms.
- Per-iteration JSONL event logs are written to `cycle_185/adversary/fuzz/logs/run_<surface>_<ts>_seed42_n5000.log` (gitignored) for T4 triage if needed.
- Initial seed corpus committed at `cycle_185/adversary/fuzz/corpus/S{1,2,3,4}/seed_NNN.bin` (136 seeds total — 26/31/37/42). The `corpus/` directory is `.gitignore`-excluded; regenerated locally via `python3 cycle_185/adversary/fuzz/build_seed_corpus.py`.
- Deterministic: identical seed (42) → identical SUMMARY counters across all 4 surfaces on re-run.
- Per-finding folder: `cycle_185/adversary/fuzz/findings/S4_BUGSAFE_AttributeError_None/{minimized.bin, repro.py, stacktrace.txt}` — see TRIAGE_REPORT.md §3.
- Findings JSONL: `cycle_185/adversary/fuzz/findings.jsonl` (1 entry).
- Cross-references: VULN_AUDIT.md (T1, F-001), RUN_REPORT.md (T3, S4 §2.4), TRIAGE_REPORT.md (T4, §3), FUZZING_REPORT.md (T5, §5).