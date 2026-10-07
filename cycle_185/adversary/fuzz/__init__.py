"""Cycle 185 adversary fuzz package — makes `fuzz/` importable.

Harnesses are run as scripts (python3 harness_S1_quote.py …) rather than
imported, but the package marker lets tools like pytest collect anything
that does end up exercised under tests/.
"""