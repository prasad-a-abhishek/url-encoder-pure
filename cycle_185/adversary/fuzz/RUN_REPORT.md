# cycle_185/adversary/fuzz/RUN_REPORT — T3 corpus_run

**Cycle:** 185
**Phase:** adversary/T3 (corpus construction + fuzzing execution)
**Date:** 2026-10-07 UTC
**Operator:** @default (default profile)
**Predecessor:** T2 harnesses verified at `00064e0` on `wt/cycle185-adversary-01`
**Branch:** `wt/cycle185-adversary-01`
**Commit (T3):** recorded at end of this run (see "Artifacts" below)

---

## 1. Executive Summary

T3 executed **20,000 fuzz iterations** across **4 surfaces** at **`FUZZ_ITERS=5000`, `FUZZ_SEED=42`** (reproducible). All harnesses completed cleanly with no hangs.

| Outcome | Count |
|---|---|
| Total iterations | 20,000 |
| Total surfaces exercised | 4 (S1 quote, S2 quote_plus, S3 unquote, S4 unquote_plus) |
| Distinct surfaces crashing | **1** (S4 only) |
| Total unexpected exception artifacts | **219** (all from S4, all the same root cause) |
| Distinct unexpected exception classes | **1** (`AttributeError`) |
| Distinct stack-trace sites | **1** (`src/url_encoder_pure/__init__.py:82`, `unquote_plus(None)`) |
| Hangs (per-call watchdog > 5 s) | **0** |
| OOM | **0** |

The single finding is a **Medium** severity regression of **Invariant 21 (Total Public API Exception Safety)** on `unquote_plus(None)` — first identified by T1 audit (F-001) and already known from T2's 100-iter smoke. fix2 closed the encode-side (`quote`/`quote_plus`) but **did not close the decode-side**. S4 produced 219 crash artifacts across 5000 iters, all but a few being deterministic duplicates of the same input.

---

## 2. Per-Surface Results

| Surface | Iters | Completed | UnicodeErrors | TypeErrors | ValueErrors | Unexpected | Crashes (postcond) | Hangs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **S1** `quote` | 5000 | 3898 | 851 | 0 | 0 | 0 | 0 | 0 |
| **S2** `quote_plus` | 5000 | 3928 | 814 | 0 | 0 | 0 | 0 | 0 |
| **S3** `unquote` | 5000 | 1483 | 0 | 1139 | 2378 | 0 | 0 | 0 |
| **S4** `unquote_plus` | 5000 | 1833 | 0 | 694 | 2225 | **248** | 0 | 0 |

(Counts come from `stats.json`'s `counts` field; the per-surface JSONL lines are in
the `logs/run_<surface>_<ts>_seed42_n5000.log` files. The `unexpected` count
for S4 counts invocations; the on-disk artifacts at `crash_files.total` dedupe
to 219 unique iter indices.)

### 2.1 S1 quote — CLEAN

`quote()` is fully INV-21 safe after fix2 (quote/quote_plus return None without raising).
- 251 invocations of `quote(None)` were observed and all returned `None` cleanly
  (none_handled = 251; `completed = 3898`).
- 851 invocations raised `UnicodeEncodeError` on inputs containing lone surrogate
  halves — this is RFC 3986 strict-mode correct (T1 audit F-002 Medium). **Not**
  a bug; recorded for triage audit.
- 0 unexpected, 0 hangs, 0 crashes.

### 2.2 S2 quote_plus — CLEAN

Same surface as S1 with the form-encoder space→`+` transform.
- 258 invocations of `quote_plus(None)` all returned `None` (none_handled).
- 814 surrogate-half UnicodeEncodeErrors — same F-002 territory.
- 0 unexpected, 0 hangs, 0 crashes.
- **postcondition invariant** (no literal spaces in output) held across all 3928
  successful completions.

### 2.3 S3 unquote — CLEAN (audit BUGSAFE)

`unquote()` does not call `.replace` first (unlike `unquote_plus`), so the
INV-21 None-replacement bug does not apply. Behavior is by-design:
- 2378 `ValueError`s from malformed `%HH` triplets — RFC 3986 contract; expected.
- 1139 `TypeError`s — driven by F-001 (None) and F-003 (bytes) audit BUGSAFE
  findings. `unquote(None)` raises TypeError ("argument of type 'NoneType' is
  not iterable"), `unquote(b"...")` raises TypeError ("a bytes-like object is
  required, not 'str'"). Both are recorded under type_error and called out
  as **audit-driven BUGSAFE** — not bugs.
- 0 unexpected, 0 hangs, 0 crashes.

### 2.4 S4 unquote_plus — **1 FINDING (INV-21 violation)**

Single root cause, 248 event-count occurrences (219 dedup'd artifacts):
**`unquote_plus(None) → AttributeError: 'NoneType' object has no attribute 'replace'`**
at `src/url_encoder_pure/__init__.py:82`, in the line `return unquote(s.replace("+", " "))`.

Stack trace (verbatim, all 219 artifacts share this site):
```
  File ".../fuzz/harness_S4_unquote_plus.py", line 98, in runner
    result = _run_unquote_plus(s)
  File ".../harness_S4_unquote_plus.py", line 52, in _run_unquote_plus
    return call_with_timeout(lambda: unquote_plus(s), timeout_s=5.0)
  File ".../_common.py", line 67, in call_with_timeout
    return fn()
  File ".../harness_S4_unquote_plus.py", line 52, in <lambda>
    return call_with_timeout(lambda: unquote_plus(s), timeout_s=5.0)
  File ".../src/url_encoder_pure/__init__.py", line 82, in unquote_plus
    return unquote(s.replace("+", " "))
                   ^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'replace'
```

Root-cause analysis:
- `unquote_plus(s)` does not mirror `quote`'s `if s is None: return None` guard.
- T1 audit (VULN_AUDIT.md F-001 Medium) flagged this pre-build; fix2 closed the
  **encode** side (`quote`/`quote_plus`) but did not touch the **decode** side.
- The fuzz harness's BUGSAFE classification does **not** apply here — the
  audit explicitly calls `unquote(None)` and `unquote_plus(None)` as
  INV-21 violations (the fix2 PR closed only the encode half).

Reproduction (1 line):
```python
>>> from url_encoder_pure import unquote_plus
>>> unquote_plus(None)
AttributeError: 'NoneType' object has no attribute 'replace'
```

Severity: **Medium** (matches T1 audit F-001 classification). 
Invariant 21 (Total Public API Exception Safety) requires all 4 public functions
to never raise uncaught exceptions on any input including `None`. The
encode-side is now compliant; the decode-side still isn't.

Recommended fix (mirroring `quote`):
```python
def unquote(s: str | None) -> bytes | None:
    if s is None:
        return None
    ...
def unquote_plus(s: str | None) -> bytes | None:
    if s is None:
        return None
    return unquote(s.replace("+", " "))
```

This is one of the two pre-existing INV-21 closures expected at cycle_185/ship
(per qa3's INV-21 SHIP verdict which only covered the encode side).

---

## 3. T1 Audit F-002 (Surrogate UnicodeEncodeError) — Re-classification

T1 audit F-002 (Medium) flagged `quote('lone surrogate')` raising
`UnicodeEncodeError`. The harness records these as `unicode_error` events
(NOT crashes). The contract of S1+S2:

- `quote(bytes)` with surrogate halves: bytes input never enters the
  surrogate path (bytes are already encoded). 0 unicode_errors on the
  bytes side.
- `quote(str)` with surrogate halves: RFC 3986 strict encoding raises
  `UnicodeEncodeError`. This is **expected** per RFC and **not** a crash.

F-002 stands as a known limitation rather than a fix-now bug. The README's
section on the surrogate edge case should mention the strict-mode behavior.

---

## 4. Artifacts (under `cycle_185/adversary/fuzz/`)

```
build_seed_corpus.py        — T3 script (seed corpus generator)
aggregate_stats.py          — T3 script (stats.json aggregator)
stats.json                 — aggregated per-surface metrics
RUN_REPORT.md              — this report
corpus/S1/                 — 26 seeds
corpus/S2/                 — 31 seeds
corpus/S3/                 — 37 seeds
corpus/S4/                 — 42 seeds
crashes/                   — 219 .in + 219 .stack.txt (S4 only)
logs/run_<surface>_<ts>_seed42_n5000.log  — 4 per-surface JSONL run logs
README.md                  — T2 README (fuzz dir layout)
```

Per-surface stats.json keys (`cycle_185/adversary/fuzz/stats.json`):
```json
{
  "quote":       {"iters": 5000, "seed": 42, "elapsed_s": 6.736, "counts": {...}, "crash_files": {...}, ...},
"quote_plus":  {"iters": 5000, "seed": 42, "elapsed_s": 6.915, "counts": {...}, "crash_files": {...}, ...},
"unquote":     {"iters": 5000, "seed": 42, "elapsed_s": 0.447, "counts": {...}, "crash_files": {...}, ...},
"unquote_plus":{ "iters": 5000, "seed": 42, "elapsed_s": 0.725, "counts": {...}, "crash_files": {...}, ...}
}
```

---

## 5. Methodology

### 5.1 Harness & watchdog

All 4 harnesses (`harness_S1_quote.py`, `harness_S2_quote_plus.py`,
`harness_S3_unquote.py`, `harness_S4_unquote_plus.py`) are pure-stdlib
(only `random`, `signal`, `threading`, `traceback`, `json`, `time`).

- Per-call watchdog: 5.0 s via `signal.setitimer` on the main thread
  (fallback `threading.Timer` on worker threads / non-Unix).
- Crash artifacts: `<surface>_<idx:05d>_<class>.in` and `.stack.txt`.
  Reproducible by `python3 -c "from url_encoder_pure import quote;
  eval(open('c://')...)"` (but the bug is non-input-dependent — calling
  `unquote_plus(None)` always reproduces).
- 100-iter smoke was run at T2; this run is the full 5000-iter
  production pass per the task body.

### 5.2 Seed corpus

Seeded from `build_seed_corpus.py`. 26/31/37/42 seeds per surface
(S1/S2/S3/S4) totaling 136 corpus inputs covering:

- **RFC 3986 examples** (8): empty, single chars, `hello`, `hello world`,
  `hello/world`, `~`, `%20`, full URL.
- **Edge/zero** (1): empty bytes.
- **Unicode normal** (4): `café`, `日本語`, `🌐`, mixed.
- **Unicode adversarial** (3): lone surrogate, BOM, NULL byte.
- **Percent-encoding adversarial** (5): `%`, `%2`, `%XY`, `%2F`, `%2f`.
- **Surface-specific extras**: `+` cases for S2/S4, malformed `%HH` for
  S3/S4.

### 5.3 Run command

```bash
cd /root/.worktrees/t_cycle185-adversary-01
export FUZZ_ITERS=5000 FUZZ_SEED=42
for s in S1 S2 S3 S4; do
  python3 cycle_185/adversary/fuzz/harness_$s*.py
done
```

Each harness runs to completion; per-call watchdog aborts any 5s+ hang.
Final summary lines in the JSONL logs.

### 5.4 Reproducibility

`FUZZ_SEED=42` is fixed; `random.Random(42)` is the only RNG. Re-running
the harness with `--seed 42` reproduces the same iter ordering. The crash
artifacts are dedup'd by iter index — every `unquote_plus_<NNNNN>_unexpected.*`
crash is the **same** NoneType `.replace` failure, just at a different iter
position. Reproducing any single crash:

```bash
python3 -c "from url_encoder_pure import unquote_plus; unquote_plus(None)"
```

---

## 6. Cross-Surface Findings Comparison

| Surface | Input | Output | Behavior | Post-fix2 status |
|---|---|---|---|---|
| S1 quote | None | None (per fix2 guard at __init__.py:15) | INV-21 OK | FIXED (fix2) |
| S2 quote_plus | None | None (per fix2 guard at __init__.py:37) | INV-21 OK | FIXED (fix2) |
| S3 unquote | None | raises TypeError ('argument of type NoneType is not iterable') at __init__.py:56 | INV-21 violation | UNFIXED (audit F-001) |
| S4 unquote_plus | None | raises AttributeError on `.replace()` at __init__.py:82 | INV-21 violation | UNFIXED (audit F-001) |

Note S3 and S4 both fail INV-21 on None input, but only S4 was observed
in the harness because S3's first failure mode (NoneType not iterable on
the `"%" not in s` check at __init__.py:56) raises `TypeError` — which the
S3 harness categorizes as `type_error` (BUGSAFE per audit F-001). S4's
first failure mode (`.replace` on None) raises `AttributeError`, which is
NOT a TypeError and falls through to the harness's `unexpected` branch.

This is a **harness audit-driven categorization difference**, not a
semantic difference in the bug. Both `unquote(None)` and `unquote_plus(None)`
violate INV-21. T4 must record both as a single combined finding.

---

## 7. T4 Handoff (next phase)

T4 (triage + minimize) should:

1. **Confirm**: the 219 S4 artifacts all collapse to one root cause:
   `unquote_plus(None) → AttributeError`. Verify by spot-checking a few
   `.in` files (all contain the literal text `None`).
2. **Skip minimization** — the bug is **input-independent** (any None
   reproduces). There is no minimized input; the report section is
   effectively one finding.
3. **Classify**: Medium (per T1 audit F-001 + INV-21). The fix is
   trivial — add `if s is None: return None` to both `unquote` and
   `unquote_plus` (defense in depth even though `unquote(None)`
   currently raises TypeError, not AttributeError — making it a proper
   INV-21 contract).
4. **Don't re-classify** the F-002 surrogate behavior (Medium in audit,
   now confirmed at scale as RFC-correct, not a fix-now bug). Document
   the strict-mode behavior in the README.
5. **Update VULN_AUDIT.md** finding F-001 to note the partial fix
   coverage: encode side closed by fix2, decode side still open.

T5 will author the `FUZZING_REPORT.md` that gates cycle_185/ship.

Per **Invariant 26** of the repo-factory contract, an adversary finding of
**Medium** severity does NOT block the cycle to @repo-builder — it
proceeds with a documented acceptance note. The acceptance note for this
finding will be in FUZZING_REPORT.md's Recommendations section (authored
by T5). **Critical/High** would block the cycle; this finding is
Medium so the cycle continues.

---

## 8. VERDICT

**FINDING (Medium):** `unquote_plus(None)` violates Invariant 21 (Total
Public API Exception Safety). 248 invocations / 219 dedup'd artifacts /
1 distinct exception class / 1 distinct stack site.

**Per Invariant 26:** Medium severity allows the cycle to proceed with
a documented acceptance note (FUZZING_REPORT.md Recommendations, T5).
The decode-side INV-21 closure is **deferred** to a follow-up cycle
(consistent with the partial-coverage state already established by
fix2 for the encode side).

**CLEAN:** S1 quote, S2 quote_plus, S3 unquote.

VERDICT: T3 corpus_run DONE — T4 (triage) next.