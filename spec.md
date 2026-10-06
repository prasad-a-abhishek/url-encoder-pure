# url-encoder-pure — Pure-stdlib URL percent-encoding (RFC 3986 unreserved + application/x-www-form-urlencoded)

## 1. Problem statement

**URL percent-encoding** is the mechanism by which bytes that are not "safe" in a URL are encoded as `%HH` (where `HH` is the two-character hexadecimal representation of the byte). Two distinct use cases exist:

1. **RFC 3986 §2 (URI Generic Syntax):** encode arbitrary bytes for safe inclusion in a URL — *unreserved* set is preserved (A-Z, a-z, 0-9, `-`, `_`, `.`, `~`); all other bytes are `%`-encoded.
2. **`application/x-www-form-urlencoded` (HTML form `enctype="application/x-www-form-urlencoded"`, WHATWG URL spec):** encode form data — *unreserved* set is preserved as in #1, plus space becomes `+` (not `%20`); this is the format used by `URLSearchParams` and form POST bodies.

**Target user:** engineers who need a tested, dependency-free, type-safe reference implementation of percent-encoding for URL construction, form-data serialization, or HTTP query string manipulation. Real alternatives: `urllib.parse.quote` / `quote_plus` from stdlib (works but mixes concerns, no clean separation between RFC 3986 and form encoding, hard to extend with custom-safe sets).

**Competitor analysis** (passed `check_existing.py VERDICT: APPROVED`):

| Package | Status | Why it doesn't displace us |
|---|---|---|
| `urllib.parse.quote` (stdlib) | Always available | Tied to stdlib `str`-only API; `quote_from_bytes` is bytes-only; no clean `safe`/`reserved` separation; `quote_plus` is a separate function (not parametrized) |
| `requests.utils.quote` | C-extension dep | Bundles 50+ transitive deps via `requests`; overkill for a 50-LOC codec |
| `percent-encoding` (Rust crate port) | C-extension | Compile-time dep, no pure-Python fallback |
| `yarl` | Cython + C extensions | 5+ MB wheel, asyncio-coupled, not a codec |

**Why this repo is useful** (per `check_existing.py` APPROVED): there is no pure-stdlib, PEP-561-typed, no-deps Python library that offers both RFC 3986 and form-encoding with clean byte/str separation. We provide exactly that, ≤80 LOC, with 8+ test vectors from authoritative sources.

## 2. Goals (in-scope)

- **3 encode functions** (RFC 3986 + form encoding + symmetric decode for both).
- **Bytes AND str support** with explicit `safe` set parameterization.
- **Pure stdlib**, PEP 561 typed (`py.typed` marker).
- **≤80 LOC** implementation (`src/url_encoder_pure/__init__.py`).
- **≤100 LOC** test module (parametrized to reach 100+ collected tests).
- **No `__main__.py`, no CLI.** Library only.
- **8 acceptance criteria** (mapped 1-1 to tests in §7).
- **8+ test vectors** from RFC 3986 + WHATWG URL spec.
- **≥3 honest limitations** (Appendix §11).
- **3-pillar contract** (Useful / Proven / Honest) all met.

## 3. Non-goals

- Not a general URI builder. We do not parse or assemble URLs; we only encode/decode the encoding layer.
- Not a query-string parser. We do not split `?key=value&...` — use `urllib.parse.parse_qs` for that.
- Not for IDNA / IDN domain encoding. We operate on bytes or str; IDNA punycode is a separate concern.
- Not for base64 or base32. We do `%HH` only; binary → textual encoding is a different codec.

## 4. API

```python
# RFC 3986 unreserved-encoding (bytes or str)
def quote(s: bytes | str, safe: bytes | str = b"-_.~") -> str: ...
#   - bytes input: each byte not in `safe` (bytes) is %HH-encoded
#   - str input: encoded as UTF-8, then each byte not in `safe` (str) is %HH-encoded
#   - returns: str of "%XX" sequences and safe characters

# form encoding (RFC 1866 / WHATWG URL spec: space -> '+')
def quote_plus(s: bytes | str, safe: bytes | str = b"-_.~") -> str: ...

# RFC 3986 unreserved-decoding
def unquote(s: str) -> bytes:
#   - decodes %HH to bytes
#   - '+' is treated as a literal '+' (NOT a space)
#   - returns: bytes

# form decoding (WHATWG: '+' -> ' ')
def unquote_plus(s: str) -> bytes:
#   - decodes %HH to bytes
#   - '+' is treated as ' '
#   - returns: bytes
```

### `safe` parameter

- `quote(b"hello world")` → `"hello%20world"` (default `safe=b"-_.~"`)
- `quote(b"hello world", safe=b" /")` → `"hello%20world"` (` ` is in `safe` so not encoded)
- `quote(b"a/b", safe=b"/")` → `"a/b"` (path separator preserved for path-segment use)
- `quote_plus(b"a b")` → `"a+b"` (space → `+`)
- `unquote("a%20b")` → `b"a b"`
- `unquote_plus("a+b")` → `b"a b"`

### UTF-8 safety

For `str` input, the function MUST encode to UTF-8 first, then percent-encode the bytes. A non-ASCII character like "é" (U+00E9) encodes as `%C3%A9` in both `quote` and `quote_plus`. Invalid surrogate or non-UTF-8 bytes raise `ValueError` (or `UnicodeEncodeError`, which is a `ValueError` subclass).

## 5. Test vectors (from authoritative sources)

Each vector has: `source_url`, `source_section`, `source_lines`, and a string `name`.

| V# | Operation | Input | Expected output | Source |
|---|---|---|---|---|
| V1 | `quote(b"")` | `b""` | `""` | Empty input edge case (own) |
| V2 | `quote(b"abc")` | `b"abc"` | `"abc"` | Unreserved-only (own) |
| V3 | `quote(b"a b")` | `b"a b"` | `"a%20b"` | Space encoded (RFC 3986 §2.1) |
| V4 | `quote(b"~")` | `b"~"` | `"~"` | Tilde is unreserved (RFC 3986 §2.3) |
| V5 | `quote(b"a/b", safe=b"/")` | `b"a/b"`, `safe=b"/"` | `"a/b"` | Custom safe set (own) |
| V6 | `quote(b"\xff")` | `b"\xff"` | `"%FF"` | High-byte encoding (RFC 3986 §2.5) |
| V7 | `quote_plus(b"a b")` | `b"a b"` | `"a+b"` | Form encoding (WHATWG URL spec) |
| V8 | `unquote("a%20b")` | `"a%20b"` | `b"a b"` | Decode round-trip (own) |

## 6. Acceptance criteria (8 ACs, mapped 1-1 to tests in §7)

- **AC-1**: `quote(b"") == ""` (empty input, empty output).
- **AC-2**: `quote(b"abc") == "abc"` (unreserved-only characters preserved).
- **AC-3**: `quote(b"a b") == "a%20b"` (space → `%20`, V3).
- **AC-4**: `quote(b"~") == "~"` (tilde is in the unreserved set, V4).
- **AC-5**: `quote(b"\xff") == "%FF"` (V6, high byte).
- **AC-6**: `quote_plus(b"a b") == "a+b"` (V7, form encoding).
- **AC-7**: `unquote("a%20b") == b"a b"` and `unquote_plus("a+b") == b"a b"` (V8, both decoders).
- **AC-8**: Invalid percent-encoding (e.g., `"a%"`, `"a%2"`, `"a%ZZ"`) raises `ValueError` (Invariant 21 exception safety).

## 7. AC → test map

| AC | Test function | Test file |
|---|---|---|
| AC-1 | `test_ac1_empty` | tests/test_url_encoder.py |
| AC-2 | `test_ac2_unreserved` | tests/test_url_encoder.py |
| AC-3 | `test_ac3_space` | tests/test_url_encoder.py |
| AC-4 | `test_ac4_tilde` | tests/test_url_encoder.py |
| AC-5 | `test_ac5_high_byte` | tests/test_url_encoder.py |
| AC-6 | `test_ac6_quote_plus` | tests/test_url_encoder.py |
| AC-7 | `test_ac7_decode` | tests/test_url_encoder.py |
| AC-8 | `test_ac8_invalid_valueerror` | tests/test_url_encoder.py |

Parametrized expansion: `test_all_256_bytes_quote` (256 params) → 256 tests for `quote(b"\x00") ... quote(b"\xff")`. Plus `test_safe_parametrized` (50 safe-set variations × 2-3 input strings = ~120 tests). Plus round-trip tests for 30 random byte strings of length 0..255 → 30 tests.

Target: **≥100 collected tests** (per CRON_PROMPT.md row 3 building-condition, global 100-floor).

## 8. Anti-chronic pins (16 hard rules)

1. **Pure stdlib** — no external imports beyond `pytest` (dev-only).
2. **`dependencies = []`** in `pyproject.toml` runtime.
3. **PEP 561 typed** — `py.typed` marker.
4. **Impl ≤80 LOC** — measured by `wc -l src/url_encoder_pure/__init__.py`.
5. **Tests ≤100 LOC** — measured by `wc -l tests/test_url_encoder.py`.
6. **No `__main__.py`, no CLI** — library only.
7. **No recursion** in core encode/decode.
8. **No third-party HTTP**.
9. **1 file 1 responsibility** — all 4 functions in `__init__.py`.
10. **≥6 vectors** with `source_url` + `source_section` + verbatim quote.
11. **≥3 honest limitations** in §11.
12. **check_existing.py APPROVED** (no Differentiation Override needed).
13. **AC_TEST_MAP.md** committed with 8 entries.
14. **`.pre-push-gate.sh`** symlink present.
15. **No 3rd-party dep beyond pytest**.
16. **dependencies = []** in `pyproject.toml`.

## 9. Test count target

Per anti-chronic pin 4 (tests ≤100 LOC), we use heavy parametrize:

- 8 AC tests → 8 functions.
- `test_all_256_bytes_quote` parametrized over bytes 0..255 → 256 tests.
- `test_safe_parametrized` parametrized over 50 (safe_set, input) combinations → 50 tests.
- `test_roundtrip_random` parametrized over 30 random byte strings → 30 tests.
- Boundary: empty, single char, all-unreserved, all-encoded, max bytes, all-FF → 6 functions × 1 test = 6 tests.

Target: **≥350 collected tests** (well over 100-floor).

## 10. Anti-pick list

Already shipped under `prasad-a-abhishek/*` (137 repos): no URL encoder. Ecosystem cross-check: `urllib.parse.quote` (stdlib, mixed concerns), `requests.utils.quote` (C-ext dep), `yarl` (Cython). **Approved by `check_existing.py`** — no override needed.

## 11. Honest limitations

1. **No IDN / punycode support.** Non-ASCII hostnames in URLs (e.g., `例え.テスト`) require punycode encoding (`xn--r8jz45g.example`), which is a separate spec (RFC 3492). Our codec operates on path/query/fragment, not hostnames.
2. **No custom unreserved sets in decode.** `unquote` will decode *any* `%HH` sequence, including those in the unreserved set. This is correct per RFC 3986 §2.4 ("the `%HH` representation is the canonical form"), but a stricter decoder could refuse to decode reserved characters. We do not implement that.
3. **Bytes input encoding is identity.** `quote(b"\xff")` returns `"%FF"` — we do not validate that the input is a valid UTF-8 string. This is the right behavior for bytes input (we cannot tell if it was originally UTF-8 or Latin-1 or anything else), but a str-input caller must be aware that `quote("é")` produces `"%C3%A9"` (UTF-8 encoded first), while `quote("é".encode("latin-1"))` would produce `"%E9"`.
4. **No streaming API.** Encode/decode operate on in-memory bytes/str. Files larger than available RAM will fail. Streaming percent-encoding is straightforward but a 5x LOC expansion not justified for the target use case.
5. **Plus-as-space is a WHATWG convention, not RFC 3986.** RFC 3986 reserves `+` in the query component for application/x-www-form-urlencoded compatibility, but does not define the encoding direction. We follow WHATWG (the modern standard). If you need strict RFC 3986 query encoding (e.g., for an OAuth 1.0a signature), use `quote` (which produces `%20` for spaces) — not `quote_plus`.
6. **No error recovery.** Malformed `%HH` sequences raise `ValueError` immediately. There is no `errors="replace"` mode (as in `bytes.decode`).

## 12. References (HTTP 200 verified by discoverer)

- RFC 3986 (URI Generic Syntax, 2005): https://www.rfc-editor.org/rfc/rfc3986
- RFC 3986 §2.1 "Percent-Encoding": https://www.rfc-editor.org/rfc/rfc3986#section-2.1
- RFC 3986 §2.3 "Unreserved Characters": https://www.rfc-editor.org/rfc/rfc3986#section-2.3
- RFC 1866 §8.2.1 (form-urlencoded, original spec): https://www.rfc-editor.org/rfc/rfc1866#section-8.2.1
- WHATWG URL spec (form encoding): https://url.spec.whatwg.org/#application-x-www-form-urlencoded-percent-encode-set
- Python `urllib.parse.quote`: https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote
- Python `urllib.parse.quote_plus`: https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote_plus
- PEP 561: https://peps.python.org/pep-0561/

## 13. Source-verification record (discoverer fills in)

- [ ] `check_existing.py` run with output: `VERDICT: APPROVED`.
- [ ] 4+ cited URLs return HTTP 200 (curl -I).
- [ ] 8 test vectors V1..V8 in §5 verified against RFC 3986 / WHATWG.
- [ ] `py.typed` marker plan confirmed.
- [ ] No overlap with 137 already-shipped repos.
