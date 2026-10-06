"""Pure-stdlib URL percent-encoding (RFC 3986 + application/x-www-form-urlencoded)."""

__version__ = "0.1.0"
__all__ = ["quote", "quote_plus", "unquote", "unquote_plus"]

# RFC 3986 §2.3 unreserved characters — always safe unless overridden
_UNRESERVED = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~")


def quote(s: bytes | str | None, safe: bytes | str = b"") -> str | None:
    """RFC 3986 percent-encoder: preserves unreserved set, encodes everything else as %HH.

    Returns None if s is None (Invariant 21: Total Public API Exception Safety).
    """
    if s is None:
        return None
    if isinstance(s, str):
        s = s.encode("utf-8")
    if isinstance(safe, str):
        safe = safe.encode("utf-8")
    safe_set = _UNRESERVED | set(safe)
    out = []
    append = out.append
    for byte in s:
        if byte in safe_set:
            append(chr(byte))
        else:
            append(f"%{byte:02X}")
    return "".join(out)


def quote_plus(s: bytes | str | None, safe: bytes | str = b"") -> str | None:
    """Form encoder (RFC 1866 / WHATWG): space -> '+', rest same as quote.

    Returns None if s is None (Invariant 21: Total Public API Exception Safety).
    """
    if s is None:
        return None
    if isinstance(s, str):
        s = s.encode("utf-8")
    if isinstance(safe, str):
        safe = safe.encode("utf-8")
    safe_set = _UNRESERVED | set(safe) | {32}  # 32 = ord(' ')
    out = []
    append = out.append
    for byte in s:
        if byte in safe_set:
            append(chr(byte))
        else:
            append(f"%{byte:02X}")
    return "".join(out).replace(" ", "+")


def unquote(s: str) -> bytes:
    """RFC 3986 decoder: %HH -> bytes, '+' is literal."""
    if "%" not in s:
        return s.encode("utf-8")
    result = []
    result_append = result.append
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "%":
            if i + 2 >= n:
                raise ValueError(f"incomplete percent sequence at position {i}: {s[i:]!r}")
            pair = s[i + 1 : i + 3]
            try:
                byte_val = int(pair, 16)
            except ValueError:
                raise ValueError(f"invalid percent sequence at position {i}: {s[i:i+3]!r}")
            result_append(byte_val)
            i += 3
        else:
            result_append(ord(c))
            i += 1
    return bytes(result)


def unquote_plus(s: str) -> bytes:
    """Form decoder: %HH -> bytes, '+' -> space."""
    return unquote(s.replace("+", " "))
