# AC → Test Coverage Map

| AC | Criterion | Test function(s) |
|---|---|---|
| AC-1 | `quote(b"") == ""` | `test_ac1_empty` |
| AC-2 | `quote(b"abc") == "abc"` | `test_ac2_unreserved` |
| AC-3 | `quote(b"a b") == "a%20b"` | `test_ac3_space` |
| AC-4 | `quote(b"~") == "~"` | `test_ac4_tilde` |
| AC-5 | `quote(b"\xff") == "%FF"` | `test_ac5_high_byte` |
| AC-6 | `quote_plus(b"a b") == "a+b"` | `test_ac6_quote_plus` |
| AC-7 | `unquote("a%20b") == b"a b"` and `unquote_plus("a+b") == b"a b"` | `test_ac7_decode` |
| AC-8 | Invalid `%HH` raises `ValueError` | `test_ac8_invalid_valueerror` |

All 8 ACs covered. 8/8.

## QA Findings & Fixes

| Finding | Severity | Source | Remediation | Fix Card | Status |
|---------|----------|--------|-------------|----------|--------|
| BENCH-01 | honest-pillar | qa t_bef08a96 | README §"Performance" + remove benchmarks table+replication line | fix1 aacd39c | DONE |
