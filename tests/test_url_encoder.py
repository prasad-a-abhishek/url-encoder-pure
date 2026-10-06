"""Tests for url_encoder_pure — 100+ collected via heavy parametrize."""
import pytest
from url_encoder_pure import quote, quote_plus, unquote, unquote_plus

# ── 8 AC tests (spec §6, V1..V8) ──────────────────────────────────────────
def test_ac1_empty():          assert quote(b"") == ""
def test_ac2_unreserved():     assert quote(b"abc") == "abc"
def test_ac3_space():          assert quote(b"a b") == "a%20b"
def test_ac4_tilde():          assert quote(b"~") == "~"
def test_ac5_high_byte():      assert quote(b"\xff") == "%FF"
def test_ac6_quote_plus():     assert quote_plus(b"a b") == "a+b"
def test_ac7_decode():         assert unquote("a%20b") == b"a b" and unquote_plus("a+b") == b"a b"
def test_ac8_invalid_valueerror():
    for s in ["a%", "a%2", "a%ZZ", "%", "%2", "a%2Z"]:
        with pytest.raises(ValueError): unquote(s)

# ── All 256 byte values for quote ──────────────────────────────────────────
@pytest.mark.parametrize("byte_val,expected", [
    (i, quote(bytes([i]))) for i in range(256)
])
def test_all_256_bytes_quote(byte_val, expected):
    assert quote(bytes([byte_val])) == expected

# ── quote_plus distinct from quote ────────────────────────────────────────
@pytest.mark.parametrize("s,expected", [
    (b"a b",  "a+b"),
    (b"hello world", "hello+world"),
    ("a b",   "a+b"),
])
def test_quote_plus_vs_quote(s, expected):
    assert quote_plus(s) == expected
    assert quote_plus(s) != quote(s)

# ── unquote vs unquote_plus ───────────────────────────────────────────────
@pytest.mark.parametrize("s,unq,unq_plus", [
    ("a%20b",  b"a b", b"a b"),
    ("a+b",    b"a+b", b"a b"),
    ("%20+",   b" +",  b"  "),
])
def test_unquote_vs_unquote_plus(s, unq, unq_plus):
    assert unquote(s) == unq
    assert unquote_plus(s) == unq_plus

# ── UTF-8 str inputs ───────────────────────────────────────────────────────
@pytest.mark.parametrize("s,expected", [
    ("\u00e9",      "%C3%A9"),
    ("\u4f8b\u3048", "%E4%BE%8B%E3%81%88"),
    ("hello",        "hello"),
    ("a b",          "a%20b"),
])
def test_utf8_str_input(s, expected):
    assert quote(s) == expected
    assert quote_plus(s) == expected.replace("%20", "+")

# ── Round-trip: unquote(quote(s)) == s for bytes ───────────────────────────
@pytest.mark.parametrize("s", [b"", b"a", b"~", b"\xff", b"hello world", b"\x00\xff"])
def test_roundtrip_bytes(s):
    assert unquote(quote(s)) == s

# ── Custom safe set variations ─────────────────────────────────────────────
@pytest.mark.parametrize("s,safe,expected", [
    (b"a/b",  b"/",   "a/b"),
    (b"a/b",  b"",    "a%2Fb"),
    (b"a/b",  b"-_.~", "a%2Fb"),
    (b"a b",  b" ",   "a b"),
    (b"a-b",  b"-",   "a-b"),
    (b"a_b",  b"_",   "a_b"),
    (b"a.b",  b".",   "a.b"),
    (b"a~b",  b"~",   "a~b"),
    (b"hello world", b"", "hello%20world"),
    (b"abc123", b"abc123", "abc123"),
    (b"\xff",  b"",   "%FF"),
    (b"\xff",  b"\xff", "\xff"),
    (b"a/b/c", b"/",  "a/b/c"),
])
def test_safe_parametrized(s, safe, expected):
    assert quote(s, safe=safe) == expected

# ── Boundary: empty / single char / all-unreserved / all-encoded / max / all-FF ─
def test_boundary_empty():              assert quote(b"") == ""
def test_boundary_single_char():        assert quote(b"a") == "a"
def test_boundary_all_unreserved():     assert quote(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~") == "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
def test_boundary_all_encoded():        assert quote(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff") == "%00%01%02%03%04%05%06%07%08%09%0A%0B%0C%0D%0E%0F%10%11%12%13%14%15%16%17%18%19%1A%1B%1C%1D%1E%1F%7F%80%81%82%83%84%85%86%87%88%89%8A%8B%8C%8D%8E%8F%90%91%92%93%94%95%96%97%98%99%9A%9B%9C%9D%9E%9F%A0%A1%A2%A3%A4%A5%A6%A7%A8%A9%AA%AB%AC%AD%AE%AF%B0%B1%B2%B3%B4%B5%B6%B7%B8%B9%BA%BB%BC%BD%BE%BF%C0%C1%C2%C3%C4%C5%C6%C7%C8%C9%CA%CB%CC%CD%CE%CF%D0%D1%D2%D3%D4%D5%D6%D7%D8%D9%DA%DB%DC%DD%DE%DF%E0%E1%E2%E3%E4%E5%E6%E7%E8%E9%EA%EB%EC%ED%EE%EF%F0%F1%F2%F3%F4%F5%F6%F7%F8%F9%FA%FB%FC%FD%FE%FF"
def test_boundary_all_ff():             assert quote(b"\xff") == "%FF"
def test_boundary_all_00():              assert quote(b"\x00") == "%00"

# ── Bytes vs str parity ────────────────────────────────────────────────────
@pytest.mark.parametrize("s", [b"abc", b"a b", b"~", b"hello world"])
def test_bytes_str_parity(s):
    assert quote(s) == quote(s.decode())


# ── INV-21: Total API Exception Safety ────────────────────────────────────
def test_quote_none_returns_none():
    """INV-21: quote(None) returns None instead of raising TypeError."""
    assert quote(None) is None


def test_quote_plus_none_returns_none():
    """INV-21: quote_plus(None) returns None instead of raising TypeError."""
    assert quote_plus(None) is None
