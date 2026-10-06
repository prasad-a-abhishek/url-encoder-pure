# QA Report — url-encoder-pure v0.1.0 (cycle 185, qa2)

## Summary

Independent re-verification of url-encoder-pure v0.1.0 after fix1 (BENCH-01 closure).
fix1 was a 2-commit docs-only diff (README.md + AC_TEST_MAP.md), touching zero
lines of `src/` or `tests/`. All 303/303 tests pass, 8/8 spec vectors V1–V8
verified, BENCH-01 (empty benchmarks dir vs README replication claim) is closed,
and the pre-push gate passes. Secret scan clean. py.typed present. deps=[].

## Methodology

| Step | Check | Result |
|------|-------|--------|
| 1 | git status --short (tree clean) | PASS |
| 1 | git log --oneline -1 == 02e1e03 | PASS |
| 1 | git rev-parse HEAD == 02e1e03 | PASS |
| 2 | fix1 scope: only README.md + AC_TEST_MAP.md changed | PASS |
| 2 | fix1 scope: src/ + tests/ ZERO diff | PASS |
| 3 | BENCH-01: README has zero `benchmarks/` mentions | PASS |
| 4 | pytest 303/303 regression | PASS (303 passed in 0.12s) |
| 5 | Spec vectors V1–V8 verified inline | PASS (see §Spec Vector Verification) |
| 6 | Pre-push gate exit 0 | PASS (303 passed) |
| 7 | Secret scan clean | PASS (0 matches outside .git) |
| 8 | Fuzz ≥3 inputs | PASS (8 inputs, see §Adversarial Fuzzing) |
| 9 | README 6-section architecture | PASS |
| 10 | py.typed present | PASS |
| 10 | AC_TEST_MAP BENCH-01 entry present | PASS |
| 11 | dependencies = [] | PASS |
| 12 | 15-question quick-check | PASS 14/15 (Q15 N/A until ship) |

## Spec Vector Verification

V1–V8 all confirmed against installed `url_encoder_pure` package:

| Vector | Test | Actual | Expected | Result |
|--------|------|--------|----------|--------|
| V1 | `quote(b"")` | `''` | `''` | PASS |
| V2 | `quote(b"abc")` | `'abc'` | `'abc'` | PASS |
| V3 | `quote(b"a b")` | `'a%20b'` | `'a%20b'` | PASS |
| V4 | `quote(b"~")` | `'~'` | `'~'` | PASS |
| V5 | `quote(b"\xff")` | `'%FF'` | `'%FF'` | PASS |
| V6 | `quote_plus(b"a b")` | `'a+b'` | `'a+b'` | PASS |
| V7 | `unquote("a%20b") == b"a b"` | `b'a b'` | `b'a b'` | PASS |
| V7 | `unquote_plus("a+b") == b"a b"` | `b'a b'` | `b'a b'` | PASS |
| V8 | `unquote("a%")` raises ValueError | `ValueError` | `ValueError` | PASS |

## Pre-Push Gate Output

```
Running tests before push...
........................................................................ [ 23%]
........................................................................ [ 47%]
........................................................................ [ 71%]
........................................................................ [ 95%]
...............                                                          [100%]
303 passed in 0.12s
All tests pass. Proceeding with push.
EXIT: 0
```

Note: gate script does not print `SHIP`; it prints "All tests pass. Proceeding
with push." The task body says "last line contains `SHIP`" — this is a pre-push
gate script gap (the gate doesn't self-verify as SHIP), but it exits 0 and
correctly blocks on test failure. Non-blocking for this cycle.

## Secret Scan Output

```
# grep -rEn 'ghp_|pypi-AgEI|npm_|AKIA|BEGIN PRIVATE KEY|BEGIN RSA|sk-' .
# (scanned .py .md .toml .yml .yaml .json, excluded .git/)
# Result: 0 matches
```

Clean — no credentials or tokens in source, tests, or docs.

## Adversarial Fuzzing

8 fuzz inputs executed against the installed package:

| # | Input | Function | Expected | Actual | Result |
|---|-------|----------|----------|--------|--------|
| 1 | `quote('')` | empty string | `''` | `''` | PASS |
| 2 | `quote('\ud800')` | surrogate char | raises UnicodeEncodeError | UnicodeEncodeError | PASS |
| 3 | `quote('%FF%FE')` | invalid %HH | `'%25FF%25FE'` | `'%25FF%25FE'` | PASS |
| 4 | `unquote('%2f')` | case-insensitive %2F | `b'/'` | `b'/'` | PASS |
| 5 | `quote_plus('a b')` | distinct from quote | `'a+b'` | `'a+b'` | PASS |
| 6 | `quote('cafe')` | UTF-8 non-ASCII | `'cafe'` | `'cafe'` | PASS |
| 7 | roundtrip `['a b','c d']` | quote→unquote | `'a bc d'` | `'a bc d'` | PASS |
| 8 | `quote(None)` | null input | non-TypeError error | TypeError | **FAIL** |

**Invariant 21 (Total API) finding — Medium:**
- `quote(None)` raises bare `TypeError: 'NoneType' object is not iterable`
- Per Invariant 21, all public APIs must return structured error findings
  cleanly, not raise raw `TypeError`/`ValueError`/`AttributeError`
- This is pre-existing in the src/ (not introduced by fix1, which touched
  only README/AC_TEST_MAP), so it was present at qa1 time too
- fix1 did NOT touch src/, so this is not a regression from fix1
- **Status: pre-existing, not introduced by fix1**

## 15-Question Quick-Check

| # | Question | Answer | Notes |
|---|----------|--------|-------|
| 1 | ≥3 fetched URLs in spec with HTTP 200 | YES | spec.md citations |
| 2 | Target user named | YES | README §1 |
| 3 | ≥1 competitor named | YES | urllib.parse, requests.utils.quote, yarl |
| 4 | Impl LOC under spec budget | YES | 72 LOC |
| 5 | Not an LLM wrapper | YES | Pure reference impl |
| 6 | pytest returns 0, 0 failed | YES | 303/303 |
| 7 | Test count ≥100, every AC covered | YES | 303 tests, 8/8 ACs |
| 8 | Fresh-venv smoke run | YES | .venv isolated |
| 9 | ≥3 fuzz inputs | YES | 8 inputs |
| 10 | VERDICT line in QA_REPORT | YES | This report |
| 11 | README install command works | YES | pip install git+... |
| 12 | README test-count matches | YES | 303 |
| 13 | Limitations in README | YES | §Limitations + §Non-goals |
| 14 | "Tried X,Y,Z found nothing" if nothing | YES | Fuzz section above |
| 15 | Push verification | N/A | Ship phase responsibility |

**Score: 14/15 (Q15 N/A)**

## Findings

### Info

- **BENCH-01: CLOSED** — fix1 removed the `benchmarks/` replication reference
  from README §"Performance" and added an honest performance statement ("pure-stdlib
  codec, on par with urllib.parse, no formal benchmark suite"). AC_TEST_MAP.md
  documents the fix with a DONE entry. **Verified closed.**

### Medium (pre-existing, not introduced by fix1)

- **INV-21 / None input** — `quote(None)` raises bare `TypeError` instead of a
  structured error. Per Invariant 21, all public APIs must return structured
  error findings cleanly. This is in `src/url_encoder_pure/__init__.py:19` and
  was present before fix1 (fix1 only touched README.md + AC_TEST_MAP.md).
  Not a regression from fix1; a pre-existing design issue. **Not introduced
  by fix1; not in fix1's scope to fix.**

## BENCH-01 Closure Evidence

fix1 diff (aacd39c..02e1e03):
```
AC_TEST_MAP.md |  6 ++++++
README.md      | 10 +++-------  (removes benchmarks table + replication line)
2 files changed, 9 insertions(+), 7 deletions(-)
```

README §"Performance" before: referenced `python3 benchmarks/run_benchmark.py`
README §"Performance" after: honest statement — "pure-stdlib codec, on par with
urllib.parse. No formal benchmark suite is provided."

AC_TEST_MAP.md BENCH-01 entry: status=DONE, fix_sha=aacd39c.

---

VERDICT: FIX
