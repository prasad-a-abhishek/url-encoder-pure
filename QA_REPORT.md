# QA Report — url-encoder-pure v0.1.0 (cycle 185)

## Summary

Independent adversarial QA of url-encoder-pure v0.1.0. All 303 tests pass, 8/8 spec vectors verified, 9 adversarial fuzz inputs clean, secret scan clean, py.typed present, deps=[]. One honest-pillar finding: the benchmarks directory is empty — `benchmarks/run_benchmark.py` and `benchmarks/BENCHMARK.md` are both absent, contradicting the README's "Local replication: `python3 benchmarks/run_benchmark.py`" claim. Pre-push gate does not enforce Invariant 22/23 (benchmark completeness), so it passed.

## Methodology

- `pytest -q` — 303/303 collected and passed
- `pytest --collect-only` — confirmed 303 tests
- Manual spec vector script — V1..V8 all confirmed
- Adversarial fuzz script — 9 inputs (empty, None, surrogate, 4× invalid %HH, case-insensitive, roundtrip 100×, quote_plus distinctness, 1MB perf, safe param)
- `git grep` secret scan — 0 hits
- Pre-push gate — PASS
- README architecture check — 7 sections (6 required + Non-goals) all present
- py.typed + pyproject.toml check — present and correct
- AC_TEST_MAP.md — 8/8 ACs with ≥1 test each

## Environment

- Python 3.11.15
- OS: Linux (6.12.67-linuxkit)
- Isolated `.venv` at `/root/projects/url-encoder-pure/.venv`
- Working tree: clean, HEAD=d9cb109 (feat commit)
- 3 commits: d69f6f5 (spec) → 4814fd7 (discover) → d9cb109 (feat)

## Test Suite Results

```
303 passed in 0.06s
```

- Tests collected: 303
- Tests passed: 303
- Tests failed: 0
- LOC (impl): 72 (≤80 budget, soft guideline)
- LOC (tests): 90 (≤100 budget, soft guideline)

## Spec Vector Verification

V1–V8 all confirmed via inline script:

| Vector | Test | Result |
|--------|------|--------|
| V1 | `quote(b"") == ""` | OK |
| V2 | `quote(b"abc") == "abc"` (unreserved) | OK |
| V3 | `quote(b"a b") == "a%20b"` | OK |
| V4 | `quote(b"~") == "~"` (RFC 3986 unreserved) | OK |
| V5 | `quote(b"\xff") == "%FF"` | OK |
| V6 | `quote_plus(b"a b") == "a+b"` | OK |
| V7 | `unquote("a%20b") == b"a b"` + `unquote_plus("a+b") == b"a b"` | OK |
| V8 | `unquote("a%")` raises `ValueError` | OK |

## Adversarial Fuzzing

9 fuzz inputs tried (≥3 required by contract Quick-check #9):

1. **Empty string** — `quote(b"") == ""`, `quote_plus(b"") == ""` — OK
2. **None input** — `quote(None)` raises `TypeError` (total, per Invariant 21) — OK
3. **Invalid UTF-8 surrogate** — `quote('\udcff')` raises `UnicodeEncodeError` — OK
4. **Invalid %HH: `a%`** — `unquote('a%')` raises `ValueError` — OK
5. **Invalid %HH: `a%2`** — `unquote('a%2')` raises `ValueError` — OK
6. **Invalid %HH: `a%ZZ`** — `unquote('a%ZZ')` raises `ValueError` — OK
7. **Invalid %HH: `a%2G`** — `unquote('a%2G')` raises `ValueError` — OK
8. **Case-insensitive %HH** — `unquote('%2F') == b'/'` and `unquote('%2f') == b'/'` — OK
9. **Roundtrip identity (100 random, seed=42)** — `quote → unquote` 100/100 OK
10. **quote_plus distinct from quote** — `quote(b' ') == '%20'`, `quote_plus(b' ') == '+'` — OK
11. **1MB perf smoke** — 1MB encode in 20.8ms — OK (not a crash)
12. **safe parameter** — `quote(b'hello world', safe=b'/') == 'hello%20world'` — OK

I tried empty, None, surrogate, 4 invalid %HH variants, case-insensitive decoding, 100-roundtrip, quote_plus distinctness, 1MB perf, and safe param — found nothing.

## Pre-Push Gate

```
Running tests before push...
303 passed in 0.06s
All tests pass. Proceeding with push.
```

Gate passed. Note: the gate does not check `benchmarks/BENCHMARK.md` existence (Invariant 22/23), so the empty benchmarks directory is not flagged by the gate.

## Honesty Check

| Claim | README says | Reality | Status |
|-------|-------------|---------|--------|
| Install command | `pip install git+https://github.com/prasad-a-abhishek/url-encoder-pure.git` | Matches | PASS |
| Test count | "303 tests" implied by builder metadata | 303 collected | PASS |
| LOC budget | "single-file codec ≤80 LOC" | 72 LOC impl | PASS |
| deps=[] | "zero runtime dependencies" | `dependencies = []` in pyproject.toml | PASS |
| py.typed | "PEP 561 typed" | `py.typed` present + `package_data` in pyproject.toml | PASS |
| benchmarks | "Local replication: `python3 benchmarks/run_benchmark.py`" | File does not exist | **FAIL** |

## 15-Question Quick-Check (Contract Grading Rubric)

| # | Question | Answer | Notes |
|---|----------|--------|-------|
| 1 | ≥3 fetched URLs in spec with HTTP 200 | YES | See spec.md citations |
| 2 | Target user named | YES | README §1: "I needed a dependency-free, type-safe URL percent-encoder" |
| 3 | ≥1 competitor named | YES | urllib.parse, requests.utils.quote, yarl |
| 4 | Impl LOC under spec budget | YES | 72 LOC ≤ 80 budget |
| 5 | Not an LLM wrapper | YES | Pure reference impl |
| 6 | pytest returns 0 exit, 0 failed | YES | 303/303 |
| 7 | Test count ≥100, every AC covered | YES | 303 tests, 8/8 ACs |
| 8 | Fresh-venv smoke run | YES | `.venv` isolated, 303/303 |
| 9 | ≥3 fuzz inputs | YES | 9 inputs tried |
| 10 | VERDICT line in QA_REPORT | YES | This report |
| 11 | README install command works | YES | `pip install git+...` (not on PyPI, honest) |
| 12 | README test-count matches | YES | 303 |
| 13 | Limitations in README | YES | §Limitations + §Non-goals |
| 14 | "I tried X,Y,Z found nothing" if nothing | YES | Section above |
| 15 | Push verification | N-A | Ship phase responsibility |

**Score: 14/15 (Q15 N-A until ship phase)**

## Findings

### Medium (should fix before ship)

- **BENCH-01: Empty benchmarks directory** — `benchmarks/run_benchmark.py` and `benchmarks/BENCHMARK.md` are both absent. README §"⚡ Performance & Benchmarks" references `python3 benchmarks/run_benchmark.py` as the replication command, but the file does not exist. The pre-push gate (`.pre-push-gate.sh`) does not enforce Invariants 22/23 (it checks README/LICENSE/QA_REPORT/AC_TEST_MAP/py.typed existence and pytest, but not `benchmarks/BENCHMARK.md`). This is a gate gap, not a builder omission. Per Invariant 13/14, if the package makes performance claims, there must be a complete competitive benchmark table. The README benchmark table shows "stdlib" for both rows (no actual comparison), which is honest about the absence of competitors but still references a non-existent script. **Fix**: Either remove the "Local replication: `python3 benchmarks/run_benchmark.py`" line from the README, or add the actual `benchmarks/run_benchmark.py` + `benchmarks/BENCHMARK.md`. Given this is a zero-dependency codec where performance is likely on par with stdlib, the honest fix is to remove the replication line and the placeholder table.

## Verdict

The package is functionally correct: 303/303 tests pass, 8/8 spec vectors verified, 9 adversarial fuzz inputs clean, secret scan clean, py.typed present, deps=[], README install instructions honest. The only finding is the empty benchmarks directory contradicting the README's replication claim. This is a Medium severity honest-pillar issue — the README's "Local replication" claim doesn't match the on-disk state. Per the contract, Medium findings allow the cycle to proceed with a documented acceptance note, but the shipper should fix the README claim before pushing.

---

VERDICT: FIX
