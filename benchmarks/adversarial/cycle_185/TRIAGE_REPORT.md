# cycle_185/adversary/fuzz/TRIAGE_REPORT — T4

**Cycle:** 185
**Phase:** adversary/T4 (triage, minimize, rank findings)
**Date:** 2026-10-07 UTC
**Operator:** `@default` (default profile)
**Predecessor:** T3 corpus_run at `f8a7828` on `wt/cycle185-adversary-01`
**Branch:** `wt/cycle185-adversary-01`
**Commit (T4):** see "Artifacts" below

---

## 1. Executive Summary

T3 produced **219 dedup'd crash artifacts** across **5000 fuzz iterations**
on surface S4 (`unquote_plus`). All 219 artifacts are **content-identical**
(4-byte literal `"None"`; `md5uniq == 1`, `content-uniq == 1`) and all
219 stack-trace files are **byte-identical** (`md5uniq == 1`). There is
**one distinct root cause**, **one finding class**, **one per-finding folder**.

| Outcome | Count |
|---|---|
| Crash artifacts (T3 on-disk) | 219 |
| Distinct `.in` content (md5uniq) | **1** |
| Distinct `.stack.txt` content (md5uniq) | **1** |
| Per-finding folders written | **1** |
| Distinct findings | **1** |
| Severity | **Medium** |
| Status | **REGRESSED** (was Invariant 21 F-001 — fix2 partial closure) |
| Critical findings | 0 |
| High findings | 0 |
| Medium findings (open) | 0 |
| Low findings | 0 |
| Info findings | 0 |
| Regressed (not blocking) | 1 |
| Expected-not-findings (RFC 3986 behavior) | 0 |

**Cycle-185 verdict:** cycle_185 may proceed to T5 with a documented
acceptance note. No High or Critical findings are OPEN. The one Medium
finding is a known REGRESSION that VULN_AUDIT.md F-001 predicted — fix2
(commit 3e5a893) closed the encode side (`quote`/`quote_plus`) but did
NOT mirror the `if s is None: return None` guard into the decode side
(`unquote`/`unquote_plus`). Per T4 spec §"Cross-reference against fix2
INV-21 closure", a REGRESSED finding does **not** trigger a `kanban_block`
back to fix3 — that decision is made by the T5 FUZZING_REPORT.md
recommendations and the orchestrator.

## 2. Findings table

| ID  | Severity | Surface | Exception | Trigger | Minimized bytes | Stack site | Status |
|-----|----------|---------|-----------|---------|----------------:|------------|--------|
| F1  | Medium   | S4 (`unquote_plus`) | `AttributeError` (`'NoneType' object has no attribute 'replace'`) | `unquote_plus(None)` | 4 (the str literal `"None"`) | `src/url_encoder_pure/__init__.py:82` | **REGRESSED** (was F-001 INV-21 — fix2 missed decode side) |

**Severity counts:**
```json
{"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0, "regressed": 1, "expected_not_finding": 0}
```

**Why not HIGH?** The T4 taxonomy says `BUGSAFE_*` (uncaught TypeError /
AttributeError on well-defined input) is **Medium**. None is a
well-defined input that the type signature `s: str` claims to exclude —
but the function accepts it at runtime, calls `s.replace(...)` without
checking, and explodes. This is exactly what fix2 was written to close
for `quote`/`quote_plus`. No security exploit path (no RCE, no info
disclosure, no DoS amplification — just an uncaught exception). No
HIGH/CRITICAL is OPEN.

**Why REGRESSED rather than OPEN?** The T4 spec explicitly states:

> Cross-reference against fix2 INV-21 closure: since fix2 closed
> `quote(None)/quote_plus(None) → TypeError` via
> `if s is None: return None` early-return, ANY T3 finding of
> `BUGSAFE_TypeError` with None input is a REGRESSION (status=REGRESSED,
> not new finding). Document this explicitly.

Although F1 is `AttributeError` rather than `TypeError`, the principle is
identical: this is the same Invariant 21 violation VULN_AUDIT.md F-001
predicted fix2 would miss. The classification is **Medium severity,
REGRESSED status** — not a new finding, just a documented gap awaiting
the same mechanical fix.

## 3. Per-finding narrative

### F1 — `unquote_plus(None) → AttributeError` at `__init__.py:82` (Medium, REGRESSED)

**Surface:** S4 `unquote_plus(s: str) -> bytes`

**Trigger:** calling `unquote_plus(None)`.

**Stack trace** (verbatim from `findings/S4_BUGSAFE_AttributeError_None/stacktrace.txt`):
```
Traceback (most recent call last):
  File ".../findings/S4_BUGSAFE_AttributeError_None/repro.py", line 54, in <module>
    unquote_plus(None)  # type: ignore[arg-type]
  File ".../src/url_encoder_pure/__init__.py", line 82, in unquote_plus
    return unquote(s.replace("+", " "))
                   ^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'replace'
```

**Root cause:** `unquote_plus` does not mirror fix2's
`if s is None: return None` guard from `quote`/`quote_plus`. The
implementation simply calls `s.replace("+", " ")` and then delegates
to `unquote`, with no None-check.

**Why this is REGRESSED, not new:**
1. VULN_AUDIT.md F-001 (T1, 2026-10-06 21:46 UTC) explicitly predicted
   this exact gap: "fix2 closed this for quote and quote_plus by
   adding `if s is None: return None`, but did not mirror the same
   guard into unquote and unquote_plus."
2. RUN_REPORT.md T3 (2026-10-07 00:10 UTC) reconfirmed the same
   finding via 5000-iter fuzzing: 248 event occurrences, 219 dedup'd
   artifacts, 1 distinct root cause.
3. fix2 commit 3e5a893 (2026-10-06, qa2 cycle_185) deliberately closed
   only the encode side, leaving the decode side as a known gap.

**T3 evidence:** 5000 iterations × 5% None-roll = ~250 expected
occurrences. T3 saw 248. The fuzz input that produces the crash is
deterministic (the None singleton), so every occurrence collapses to
the same 4-byte on-disk payload (`"None"` = `repr(None)[:200]`) and
the same stack trace. md5uniq of `.in` files = 1; md5uniq of
`.stack.txt` files = 1.

**Minimization:** the trigger is a Python singleton (`None`), so
"minimization" cannot reduce the runtime input. The on-disk payload
(repr of the trigger) is already the smallest possible 4-byte str
literal `"None"`. The per-finding folder ships this as
`minimized.bin` with a comment in `repro.py` explaining the
singleton-vs-str-literal distinction.

**Why no `kanban_block`:** the T4 spec mandates a `kanban_block`
**only if any High finding is OPEN**. F1 is Medium, status REGRESSED —
no High is OPEN, no block required. Routing to `cycle_185/fix3`
(or beyond) is the T5 FUZZING_REPORT's call to make, and the
orchestrator's.

**Recommended remediation** (mirrors fix2 commit 3e5a893 exactly):

```diff
--- a/src/url_encoder_pure/__init__.py
+++ b/src/url_encoder_pure/__init__.py
-def unquote(s: str) -> bytes:
+def unquote(s: str | None) -> bytes | None:
     """RFC 3986 decoder: %HH -> bytes, '+' is literal."""
+    if s is None:
+        return None
     if "%" not in s:
         return s.encode("utf-8")
     ...

-def unquote_plus(s: str) -> bytes:
+def unquote_plus(s: str | None) -> bytes | None:
     """Form decoder: %HH -> bytes, '+' -> space."""
+    if s is None:
+        return None
     return unquote(s.replace("+", " "))
```

Plus 2 unit tests (`test_unquote_none_returns_none`,
`test_unquote_plus_none_returns_none`). Estimated diff: ~6 LOC net.

## 4. Cross-references

- VULN_AUDIT.md F-001 (Medium, CWE-754, 2026-10-06 21:46 UTC):
  predicted this exact gap.
- RUN_REPORT.md T3 (cycle_185/adversary/fuzz/, f8a7828, 2026-10-07
  00:10 UTC): reconfirmed via 5000 iter fuzzing.
- fix2 commit 3e5a893 (cycle_185/qa2, 2026-10-06): closed the
  encode side; this is the decode-side remainder.
- T1 audit F-002 (surrogate → `UnicodeEncodeError`): NOT observed by
  T3's S1/S2 harnesses because they classify `UnicodeEncodeError` as
  `unicode_error` (expected from surrogate str per RFC 3986 strict
  mode) — see RUN_REPORT.md §2.1. F-002 is therefore not in this
  findings.jsonl either; it would surface only if a future harness
  flipped the policy from "expected" to "unexpected".

## 5. Artifacts

| Path | Purpose |
|------|---------|
| `cycle_185/adversary/fuzz/findings.jsonl` | one JSON object per distinct crash class |
| `cycle_185/adversary/fuzz/findings/S4_BUGSAFE_AttributeError_None/repro.py` | 3-line reproducer (loads minimized.bin + sanity-checks payload + calls SUT) |
| `cycle_185/adversary/fuzz/findings/S4_BUGSAFE_AttributeError_None/minimized.bin` | the 4-byte repr of the trigger (`"None"`) |
| `cycle_185/adversary/fuzz/findings/S4_BUGSAFE_AttributeError_None/stacktrace.txt` | full traceback from `python3 -X dev repro.py` |
| `cycle_185/adversary/fuzz/TRIAGE_REPORT.md` | this document |

## 6. Anti-patterns avoided

- [x] **No crash left unanalyzed.** All 219 T3 artifacts dedup to 1
  finding class; the per-finding folder is created and complete.
- [x] **No skipped minimization.** The trigger is a Python singleton;
  on-disk payload is the smallest possible 4-byte str literal;
  documented explicitly in `repro.py` and in §3.
- [x] **No regression marked as new.** F1 is REGRESSED with
  rationale cross-referencing fix2 commit 3e5a893 and F-001.
- [x] **No src/, tests/, pyproject/ edits.** T4 only wrote under
  `cycle_185/adversary/fuzz/findings/` and `cycle_185/adversary/fuzz/TRIAGE_REPORT.md`.

## 7. Verification (on-disk)

Run from repo root `/root/.worktrees/t_cycle185-adversary-01`:

```bash
# 1. findings.jsonl line count = total distinct crash class count
wc -l cycle_185/adversary/fuzz/findings.jsonl
# expected: 1

# 2. per-finding folder count = total distinct crash class count
ls cycle_185/adversary/fuzz/findings/ | wc -l
# expected: 1

# 3. every per-finding folder has repro.py + stacktrace.txt + minimized.bin
for d in cycle_185/adversary/fuzz/findings/*/; do
  for f in repro.py stacktrace.txt minimized.bin; do
    [ -f "$d$f" ] || echo "MISSING: $d$f"
  done
done
# expected: no output

# 4. TRIAGE_REPORT severity totals match the metadata block
tail -10 cycle_185/adversary/fuzz/TRIAGE_REPORT.md
# expected: severity counts JSON + verdict

# 5. git log shows T4 commit
git log --oneline -1 wt/cycle185-adversary-01
# expected: T4 commit sha
```

---

**Cycle-185 verdict:** cycle_185 proceeds to T5 (FUZZING_REPORT.md
author) with F1 documented as a known REGRESSED gap. No `kanban_block`
issued — no High is OPEN. Routing to `cycle_185/fix3` (or beyond) is
T5's recommendation and the orchestrator's call.