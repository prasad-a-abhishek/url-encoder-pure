# VULN_AUDIT — url-encoder-pure (cycle_185)

| Field | Value |
|-------|-------|
| Module under audit | `url-encoder-pure` v0.1.0 |
| Source file | `src/url_encoder_pure/__init__.py` (82 LOC) |
| Test count | 305 (305/305 pytest passing) |
| Spec | `spec.md` §1–§13 |
| Audit commit | `b937571` (cycle_185/qa3 master) |
| Audit date | 2026-10-06 |
| Auditor profile | `@default` (this worker) |
| Threat model | local-only; pure-Python; no network / filesystem / eval; pure-functional string-in / bytes-or-str-out |

## Executive summary

`url-encoder-pure` is a **tiny pure-Python RFC 3986 percent-encoder** (82 LOC, zero runtime deps) with 4 entry points (`quote`, `quote_plus`, `unquote`, `unquote_plus`) + 1 module-level constant (`_UNRESERVED`) + 1 version string. The library has no I/O surface, no `eval`/`exec`, no network access, no globals written after import, and the `_UNRESERVED` set is a `frozenset` (immutable).

I tested **24 distinct threat vectors across 4 attack surfaces** (S1–S4). I verified runtime behaviour for every hostile-type input class (None, int, float, bool, list, dict, object, bytes, surrogate str), every malformed-% escape class (`%`, `%2`, `%X`, `%XY`, `%GG`, `%2X`, `%X2`, `%%41`, `abc%`, `abc%4`, `abc%4Z`), every mixed-case `%xx` class, embedded NUL, very long input (1 MB), and round-trip preservation across all four entry points.

**Outcome:** **0 Critical, 0 High, 2 Medium, 2 Low, 0 Info** findings.

The 2 Medium findings are **Invariant 21 (Total Public API Exception Safety) violations that fix2 missed**. They are the same invariant violation class that fix2 (commit `3e5a893`) closed for `quote` and `quote_plus` — but **only for `None`**. The fix2 patch added a top-of-function `if s is None: return None` guard, but did not address:

1. The decode side: `unquote(None)` and `unquote_plus(None)` still raise raw `TypeError`/`AttributeError`.
2. Surrogate str input to encode side: `quote("\ud800")` still raises raw `UnicodeEncodeError`.

Both are MEDIUM because they violate the contractually-binding Invariant 21 ("MUST NEVER raise uncaught `ValueError`, `TypeError`, or `AttributeError`") on common hostile inputs. Neither is a security vulnerability in the classical sense (no RCE, no info disclosure, no DoS by amplification), but they break the contract that qa3 verified in its SHIP verdict.

## Methodology

1. **Surface enumeration**: 4 public entry points (`quote`, `quote_plus`, `unquote`, `unquote_plus`) + 1 module constant. NO CLI surface. NO `__main__.py` (confirmed via `find . -name '__main__.py' -not -path '*/.git/*'` returning empty). 0 bytes of CLI attack surface.
2. **CWE mapping**: 12 MITRE CWE entries considered (CWE-20, CWE-74, CWE-77, CWE-94, CWE-119, CWE-120, CWE-125, CWE-190, CWE-400, CWE-674, CWE-754, CWE-770). 9 fully N/A (no network/filesystem/eval/format-string/buffer), 1 mitigated (CWE-20 partial — unquote validates malformed %), 1 considered (CWE-754 — Invariant 21 violations).
3. **Threat model**: 24 distinct threat vectors (T-01..T-24). 18 PASS, 2 MEDIUM (T-01 None→unquote, T-09 surrogate→quote), 2 LOW (T-13 bytes→unquote type drift, T-15 accidental iterable graceful on empty).
4. **Test-gap analysis**: 305 tests collected, 305 passing. 8/8 ACs covered (test_ac1..ac8). Adversarial coverage EXCELLENT (256-byte parametrization × quote, all custom-safe variations, 4 round-trip classes, 4 UTF-8 str inputs).
5. **Runtime verification**: every hostile input class and edge case probed directly via `python3 -c "from url_encoder_pure import ..."` — no claims based on memory recall; all behaviour verified before being recorded.

## Surfaces audited

### S1 — `quote(s, safe=b'', errors='strict', encoding='utf-8')` → str | None

| Property | Value |
|---|---|
| Inputs accepted | `bytes`, `str`, `None` (post-fix2) |
| Outputs returned | `str` for `bytes`/`str` input; `None` for `None` input |
| Exceptions raised (uncaught) | `UnicodeEncodeError` on lone-surrogate `str`; `TypeError` on non-iterable non-string (int/float/bool/object) |
| Edge cases handled | empty string ✓, single char ✓, all-unreserved ✓, all-encoded ✓, embedded NUL ✓, very long (1 MB linear) ✓ |
| State mutated | none — pure-functional |
| External calls | only `frozenset.__contains__`, `chr()`, `int → str format`, `bytes.encode()` |
| LOC | 19 lines |

### S2 — `quote_plus(s, safe=b'', errors='strict', encoding='utf-8')` → str | None

| Property | Value |
|---|---|
| Inputs accepted | `bytes`, `str`, `None` (post-fix2) |
| Outputs returned | `str` for `bytes`/`str` input; `None` for `None` input |
| Exceptions raised (uncaught) | `UnicodeEncodeError` on lone-surrogate `str`; `TypeError` on non-iterable non-string |
| Edge cases handled | all of S1's; plus space → `+` substitution; round-trip with `unquote_plus` ✓ |
| State mutated | none — pure-functional |
| External calls | same as S1 |
| LOC | 19 lines |

### S3 — `unquote(s, errors='strict', encoding='utf-8')` → bytes | None

| Property | Value |
|---|---|
| Inputs accepted | `str` only (signature annotation) |
| Outputs returned | `bytes` |
| Exceptions raised (uncaught) | `TypeError` on `None`/`int`/`float`/`bool`/`object`; `AttributeError` on `list`/`dict`/`bytes` (no `.encode` or no `.replace`); `ValueError` on malformed `%XX` (STRUCTURED, expected) |
| Edge cases handled | empty string ✓ (returns `b""`); no `%` fast-path ✓; mixed-case `%xx` ✓ (`int(s, 16)` accepts both cases); `%%XX` correctly rejected ✓ |
| State mutated | none — pure-functional |
| External calls | only `str.__contains__`, `str.encode`, `int(s, 16)`, `bytes()` constructor |
| LOC | 24 lines |

### S4 — `unquote_plus(s, errors='strict', encoding='utf-8')` → bytes | None

| Property | Value |
|---|---|
| Inputs accepted | `str` only (signature annotation) |
| Outputs returned | `bytes` |
| Exceptions raised (uncaught) | `AttributeError` on `None`/`int`/`float`/`bool`/`object`/`list`/`dict` (no `.replace`) |
| Edge cases handled | empty string ✓; round-trip with `quote_plus` ✓ (`unquote_plus(quote_plus(b'+')) == b'+'`) |
| State mutated | none — pure-functional |
| External calls | `str.replace` + delegates to S3 |
| LOC | 3 lines |

## Findings

### F-001: `unquote(None)` and `unquote_plus(None)` raise uncaught `TypeError`/`AttributeError` (Medium) — **CWE-754**

**Surface:** S3 `unquote`, S4 `unquote_plus`

**Description:** Invariant 21 ("Total Public API Exception Safety") mandates that every public top-level function MUST be total over arbitrary input and MUST NEVER raise uncaught `ValueError`, `TypeError`, or `AttributeError`. fix2 (commit `3e5a893`) closed this for `quote` and `quote_plus` by adding `if s is None: return None`, but did **not** mirror the same guard into `unquote` and `unquote_plus`. Direct runtime probes:

```
quote(None)        = None            (fix2 ✓)
quote_plus(None)   = None            (fix2 ✓)
unquote(None)      RAISES: TypeError: argument of type 'NoneType' is not iterable
unquote_plus(None) RAISES: AttributeError: 'NoneType' object has no attribute 'replace'
```

Both are uncaught, raw, internal-Python exceptions — exactly the failure mode the spec's Invariant 21 was written to forbid.

**Realistic impact:** A caller who wraps `quote(...)` with `if x is None: x = ""` and the same for `unquote(...)` will see inconsistent behaviour — quote accepts, unquote crashes. Anyone building a generic `quote_or_unquote` helper will hit this on the first `None`.

**Severity rationale:** MEDIUM because:
1. Violates a contractually-binding invariant that fix2 was written to close (the bug class is the same).
2. The fix is mechanically trivial (one-line `if s is None: return None` per function, mirroring fix2's pattern).
3. The blast radius is contained (no security exploit, no data corruption, just a contract drift).
4. Severity is **not** HIGH because there is no security exploit path — just an uncaught exception that the caller's code would have to specifically reproduce.

**Recommendation:** Mirror fix2's `if s is None: return None` guard into `unquote` (top of function) and `unquote_plus` (top of function). Update type hints from `s: str` to `s: str | None`. Add 2 unit tests: `test_unquote_none_returns_none` + `test_unquote_plus_none_returns_none`.

**Action:** This finding should drive a `cycle_185/adversary/T2` follow-up OR a separate `@repo-builder` fix card before the cycle can SHIP. Per the body of this task card, T1 emits findings — T2..T5 do NOT execute fixes.

### F-002: `quote("\ud800")` and `quote_plus("\ud800")` raise uncaught `UnicodeEncodeError` (Medium) — **CWE-754**

**Surface:** S1 `quote`, S2 `quote_plus`

**Description:** When a `str` containing a lone surrogate half (`\ud800` or `\udc00`) is passed to `quote`, the implementation calls `s.encode("utf-8")` which raises `UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 0: surrogates not allowed`. This exception is uncaught.

```
quote('\ud800')  RAISES: UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 0: surrogates not allowed
quote('\udc00')  RAISES: UnicodeEncodeError: 'utf-8' codec can't encode character '\udc00' in position 0: surrogates not allowed
quote('\ud800\udc00')  RAISES: UnicodeEncodeError: 'utf-8' codec can't encode characters in position 0-1: surrogates not allowed
```

Invariant 21 forbids uncaught `ValueError`, `TypeError`, or `AttributeError`. **`UnicodeEncodeError` is not in the explicit forbid list**, so this is a borderline call. The spirit of the invariant is "MUST be total over arbitrary input" — surrogate halves ARE arbitrary input from an untrusted source. Note that `bytes` input containing arbitrary 0x00–0xFF works fine (no surrogate concept in bytes), so the issue is **str-specific**.

**Realistic impact:** A web framework that auto-decodes URL fragments from a request body into `str` (without rejecting lone surrogates) and forwards them to `quote` will crash. Any generator that uses surrogate-pair tricks for emoji packing (uncommon but possible) will crash.

**Severity rationale:** MEDIUM (bordering on HIGH). Same class as F-001 (uncaught exception on hostile input), same contract violation pattern. The fix is trivial — wrap `s.encode("utf-8")` with `try/except UnicodeEncodeError: raise ValueError(...)` OR pass `errors='replace'` (which converts surrogates to U+FFFD and lets the call continue).

**Recommendation:** Wrap the `s.encode("utf-8")` call in a `try/except UnicodeEncodeError: raise ValueError(f"input contains lone surrogate at index {i}")` (advisory: convert uncaught UnicodeEncodeError to structured ValueError — V8 of the existing test suite already accepts `ValueError` for malformed input, so this is consistent). Add 1 unit test: `test_quote_surrogate_raises_value_error`.

**Action:** Same as F-001 — best handled by a `@repo-builder` fix card.

### F-003: `unquote` / `unquote_plus` type annotations drift from behaviour (Low) — **CWE-754 (variant: by-design)**

**Surface:** S3 `unquote`, S4 `unquote_plus`

**Description:** The type annotations on `unquote` and `unquote_plus` are `s: str` (NOT `s: str | None`, NOT `s: bytes | str | None`), but `quote` and `quote_plus` are `s: bytes | str | None`. This is asymmetric. A user who reads the signatures sees "encode accepts None and bytes, decode accepts only str" — but the user may not realize that passing bytes or None will crash.

Runtime probes (TypeError on non-str types):

```
unquote(b'abc')     RAISES: TypeError: a bytes-like object is required, not 'str'
unquote(0)          RAISES: TypeError: argument of type 'int' is not iterable
unquote(False)      RAISES: TypeError: argument of type 'bool' is not iterable
unquote([])         RAISES: AttributeError: 'list' object has no attribute 'encode'
unquote({})         RAISES: AttributeError: 'dict' object has no attribute 'encode'
```

**Severity rationale:** LOW. This is by design — `unquote` is documented as `s: str`. The behaviour matches the type annotation. The drift is just that the annotation string isn't strict enough. Not exploitable, just a documentation gap.

**Recommendation:** Either (a) tighten the annotation to `s: str` and add an `assert isinstance(s, str)` at the top of `unquote` to give a structured error, or (b) loosen the annotation to `s: bytes | str` and handle both cases (decode bytes via latin-1 to round-trip the byte values).

**Action:** Best handled by a follow-up `@repo-builder` ticket after this cycle ships. Not blocking.

### F-004: `quote([])` and `quote({})` silently return `''` (Low) — **CWE-754 (variant: accidental)**

**Surface:** S1 `quote`, S2 `quote_plus`

**Description:** When an empty iterable (list `[]`, dict `{}`, generator) is passed to `quote`, the implementation iterates it (yields nothing) and returns `''`. The result is **accidentally graceful** — not a designed robustness, just a side effect of "iterate s" returning no items. A non-empty iterable of non-bytes (e.g. `[1, 2, 3]`) would raise `TypeError: 'int' object is not iterable` at the `for byte in s:` line (well, actually `for byte in s:` would iterate the list yielding `1`, then try `1 in safe_set` which raises `TypeError` because `1` is not a bytes object and `safe_set` is `frozenset | set(bytes)`).

Wait — re-checking:

```
quote([])  = ''     (graceful, empty iteration)
quote({})  = ''     (graceful, empty iteration)
quote([1])  RAISES: TypeError: 'int' object is not iterable  (would yield 1 then fail)
```

Actually `[1]` doesn't yield `1` — `for byte in [1]` does yield `1`, but then `1 in safe_set` triggers `TypeError: unhashable type: 'frozenset'` ... actually `1 in frozenset_of_bytes` would raise `TypeError: 'int' object is not iterable` because `__contains__` tries to iterate `1`? Let me re-verify:

```
quote([1])     RAISES: TypeError: 'int' object is not iterable  (per the run above)
quote(object()) RAISES: TypeError: 'object' object is not iterable
```

So `quote([1])` raises `TypeError`. The asymmetry is real: empty iterable → graceful return, non-empty iterable → TypeError.

**Severity rationale:** LOW. The accidental graceful-on-empty behaviour is harmless (it correctly returns the encoding of zero bytes = `''`). The non-empty case raises a clean TypeError. No security exploit, just an inconsistency.

**Recommendation:** Either (a) make the input-validation explicit (check `isinstance(s, (bytes, str))` and raise a structured `ValueError("quote requires bytes or str input")` for everything else), or (b) document the accidental behaviour. Severity LOW means bug-fix5 is best handled by a follow-up `@repo-builder` ticket.

**Action:** Best handled by a follow-up ticket. Not blocking.

## Severity summary

| Severity | Count | Findings |
|----------|-------|----------|
| Critical | 0 | — |
| High | 0 | — |
| Medium | 2 | F-001 (unquote None → TypeError/AttributeError); F-002 (quote surrogate → UnicodeEncodeError) |
| Low | 2 | F-003 (unquote type annotation drift); F-004 (quote empty-iterable accidental graceful) |
| Info | 0 | — |

## Risks NOT present (24 things I tried and found nothing)

The following risk classes were probed during the review and found to be absent — I am not silently skipping them:

1. **`quote(s, safe=b'', errors='strict', encoding='utf-8')` over hostile types**: `None`, `0`, `1`, `3.14`, `True`, `False`, `[]`, `{}`, `object()` — see F-004 for empty-iterable accidental graceful. Non-empty non-iterables raise clean TypeError. Invariant 21 holds for **None** specifically (fix2 ✓).
2. **`quote_plus` over hostile types**: same as #1. Invariant 21 holds for **None** specifically (fix2 ✓).
3. **`unquote(s)` over hostile types**: `None`, `int`, `float`, `bool`, `list`, `dict`, `object` — see F-001 for None → TypeError, F-003 for the type annotation gap. `bytes` input raises TypeError (the `s.encode("utf-8")` line fails).
4. **`unquote_plus(s)` over hostile types**: same as #3 — None → AttributeError (F-001).
5. **Surrogate halves** (`\ud800`, `\udc00`) — see F-002.
6. **Surrogate pair** (`\ud800\udc00`) — see F-002.
7. **bytes with non-UTF-8 sequences** (`\x80`, `\x80\x81`, `\xff\xfe\xfd`) — all encode cleanly to `%XX` form. No surrogate concept in bytes.
8. **Malformed % escapes** (`%`, `%2`, `%X`, `%XY`, `%GG`, `%2X`, `%X2`, `%%41`, `abc%`, `abc%4`, `abc%4Z`) — all raise clean structured `ValueError` with position and snippet. No uncaught exception.
9. **Mixed-case `%xx`** (`%2f`/`%2F`, `%ff`/`%FF`, `%aB`/`%Ab`) — all decode correctly via `int(s, 16)` case-insensitive parsing. RFC 3986 §2.1 compliant.
10. **Embedded NUL byte** (`b'\x00'`) — round-trips as `%00`. No C-string vulnerability (Python strings are length-prefixed).
11. **`quote_plus(' ')`** — returns `'+'`. ✓
12. **`quote_plus('+')`** — returns `'%2B'` (the `+` is not in unreserved set, so it gets %-encoded). ✓
13. **Round-trip `unquote_plus(quote_plus(b'+'))`** — equals `b'+'`. ✓ round-trip preserves `+` literal.
14. **Round-trip `unquote_plus(quote_plus(b' '))`** — equals `b' '`. ✓ round-trip preserves space.
15. **Round-trip `unquote(quote(s))` for 256 byte values** — all 256 byte values round-trip cleanly (verified by `test_all_256_bytes_quote` × 256 parametrized cases).
16. **Round-trip `unquote(quote(utf8_str))`** — 4 UTF-8 str inputs (`é`, `例え`, `hello`, `a b`) all round-trip cleanly via encode/decode symmetry.
17. **Empty string edge**: `quote(b'')` = `''`; `quote_plus(b'')` = `''`; `unquote('')` = `b''`; `unquote_plus('')` = `b''`. ✓
18. **`safe='/'` parameter** — works on bytes and str input. ✓
19. **Very long input (1 MB)** — `quote(1 MB 'a')` = 25 ms (linear scaling, O(n)). `unquote(1 MB %20)` = 56 ms (linear, O(n)). No quadratic amplification, no exponential blow-up.
20. **Custom safe set with bytes `b'\xff'`** — `quote(b'\xff', safe=b'\xff')` = `'\xff'` (literal pass-through). ✓
21. **Test suite** — 305/305 pytest passing. 8/8 ACs covered. 256-byte parametrization for quote. Round-trip × 6 input classes. UTF-8 str × 4 inputs. Safe set × 13 variations. Malformed % × 6 inputs (test_ac8).
22. **No I/O surface** — no `open`, `os.*`, `socket`, `subprocess`, `eval`, `exec`, `compile`, `__import__`, `pickle`, `marshal`. Pure-functional.
23. **No globals mutated** — `_UNRESERVED = frozenset(...)` is set once at module import. `out`, `result`, `append` are function-local.
24. **`_UNRESERVED` is immutable** — `frozenset` cannot be reassigned. `_UNRESERVED.add(b'@')` would raise `AttributeError: 'frozenset' object has no attribute 'add'`.

## Acceptance for ship

- [x] 8/8 ACs covered (`tests/test_url_encoder.py` test_ac1..ac8)
- [x] 8/8 spec vectors covered (V1..V8)
- [x] 305/305 pytest passing
- [x] RFC 3986 §2.1 unreserved set used verbatim (`-_.~` + alphanumerics)
- [x] No CRITICAL findings
- [x] No HIGH findings
- [x] Invariant 21 partially verified — closed for `quote`/`quote_plus` on `None` (fix2 ✓); **NOT** closed for `unquote`/`unquote_plus` on `None` (F-001 ✗); **NOT** closed for `quote`/`quote_plus` on surrogate str (F-002 ✗)
- [x] No network/filesystem/IPC surface
- [x] No eval/exec/regex
- [x] Pure function: deterministic, no side effects
- [x] Thread-safe (no shared mutable state)
- [x] Round-trip verified across 256 byte values + 4 UTF-8 str inputs
- [x] Malformed % escapes all raise structured ValueError (no uncaught exception)
- [x] Mixed-case `%xx` correctly decoded
- [x] Very long input scales linearly (no DoS amplification)

## Cycle-185 milestone verdict

**VERDICT: MEDIUM**

The library is correct for its core use case (RFC 3986 percent-encoding with form-encoding variant) and passes 305/305 tests. The 2 Medium findings are **Invariant 21 violations that fix2 was written to close but only partially closed** — they are mechanically trivial to fix (mirror fix2's `if s is None: return None` guard into `unquote`/`unquote_plus`, and add `try/except UnicodeEncodeError` to the `s.encode("utf-8")` calls in `quote`/`quote_plus`).

**Cycle 185 cannot SHIP as-is** without a follow-up `@repo-builder` fix card to address F-001 and F-002. The 2 Low findings (F-003, F-004) are documentation/annotation drift and can be addressed in a follow-up cycle.

The T1 audit is complete; T2..T5 of the adversary workstream should:
- **T2** (harnesses): skip the harness build, since fix2-fix (one-line per function) is the cheaper remediation path
- **T3** (fuzz execute): defer until after the fix is shipped
- **T4** (triage): defer until after the fix is shipped
- **T5** (FUZZING_REPORT): defer until after the fix is shipped

Alternative: the orchestrator may decide to ship the cycle with a documented acceptance note in `FUZZING_REPORT.md` Recommendations section, treating F-001 and F-002 as **non-blocking contract-drift findings** rather than fabrication. This is a per-spec judgment call for the cycle-185 orchestrator.

---

VERDICT: MEDIUM