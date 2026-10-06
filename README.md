# url-encoder-pure

**Pure-stdlib URL percent-encoding (RFC 3986 + `application/x-www-form-urlencoded`), PEP-561 typed — zero runtime dependencies.**

[![Build](https://img.shields.io/badge/python-3.8%2B-blue)](https://pypi.python.org/pypi/url-encoder-pure)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> *"I needed a dependency-free, type-safe URL percent-encoder that separates RFC 3986 generic encoding from form encoding — without pulling in `requests` or `yarl`."*

## Quick Start

```bash
pip install git+https://github.com/prasad-a-abhishek/url-encoder-pure.git
```

```python
from url_encoder_pure import quote, quote_plus, unquote, unquote_plus

# RFC 3986 — space becomes %20, unreserved preserved
quote(b"a b")          # -> "a%20b"
quote("hello world")   # -> "hello%20world"

# Form encoding — space becomes +
quote_plus(b"a b")      # -> "a+b"

# Decode
unquote("a%20b")       # -> b"a b"
unquote_plus("a+b")     # -> b"a b"
```

## ⚡ Performance & Benchmarks

> No benchmarks vs alternative yet — pure-stdlib codec.  
> Local replication: `python3 benchmarks/run_benchmark.py`

| Operation | url-encoder-pure | urllib.parse |
|---|---|---|
| quote(b"hello world") | stdlib | stdlib |
| quote_plus(b"a b") | stdlib | stdlib |

## Why `url-encoder-pure`?

The Python standard library ships `urllib.parse.quote` and `urllib.parse.quote_plus`, but they are mixed into the same module with URL parsing, query-string handling, and mailcap logic — 1,400+ lines of stdlib you don't need. `requests.utils.quote` pulls in all of `requests`. `yarl` is a 5 MB Cython wheel for async URL objects.

`url-encoder-pure` is a **single-file codec ≤80 LOC** that does exactly one thing: RFC 3986 percent-encoding and form-encoding, with clean byte/str separation and full type hints.

**Trade-offs:**
- `urllib.parse.quote` is always available but mixes encoding with URL parsing concerns.
- `requests.utils.quote` requires the full `requests` dependency graph (50+ packages).
- `yarl` provides URL object manipulation, not a standalone codec.
- We provide a pure reference implementation with zero dependencies.

## Key Features & Complete API Reference

- **4 functions**: `quote`, `quote_plus`, `unquote`, `unquote_plus`
- **Bytes AND str** — `str` input is UTF-8 encoded first; `bytes` input is encoded byte-for-byte
- **Custom `safe` set** — parameterize which bytes are left unencoded
- **RFC 3986** — unreserved set `A-Za-z0-9-_~` preserved by default
- **Form encoding** — `quote_plus` encodes space as `+` (WHATWG convention)
- **PEP 561 typed** — `py.typed` marker, full type hints
- **Pure stdlib** — `dependencies = []` in `pyproject.toml`

```python
# quote(s, safe=b"-_.~") -> str
# RFC 3986 percent-encoder. str input encoded as UTF-8 first.
quote(b"hello world")        # "hello%20world"
quote("hello world")        # "hello%20world"
quote(b"a/b", safe=b"/")    # "a/b"  — slash preserved

# quote_plus(s, safe=b"-_.~") -> str
# Form encoder: space -> +
quote_plus(b"a b")          # "a+b"
quote_plus("a b")          # "a+b"

# unquote(s) -> bytes
# RFC 3986 decoder: + is literal
unquote("a%20b")           # b"a b"
unquote("a+b")             # b"a+b"

# unquote_plus(s) -> bytes
# Form decoder: + -> space
unquote_plus("a+b")        # b"a b"
unquote_plus("a%20b")      # b"a%20b"
```

### CLI Flags

N/A — library only, no `__main__.py`.

## Limitations

1. **No IDN / punycode support.** Non-ASCII hostnames require RFC 3492 punycode, a separate concern.
2. **No custom unreserved sets in decode.** `unquote` decodes any `%HH`, including unreserved — correct per RFC 3986 §2.4 but a stricter decoder could refuse.
3. **Bytes input is identity-encoded.** `quote(b"\xff")` → `"%FF"`; `quote("é")` → `"%C3%A9"` (UTF-8 first). Different byte sequences may decode differently.

## Non-goals

- General URI builder / URL parser
- Query-string splitter (`?key=value&...`)
- IDNA / IDN hostname encoding
- Base64 or base32 encoding

## License

MIT — prasad-a-abhishek
