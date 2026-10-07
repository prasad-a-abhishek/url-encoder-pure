"""Minimal reproducer for cycle_185/adversary/T3 finding.

Surface: S4 (unquote_plus)
Class:   BUGSAFE / AttributeError (Invariant 21 violation — CWE-754)
Trigger: unquote_plus(None)

Background
----------
T3 logged crashes with `in_repr = repr(s)[:200]` where s was the
Python `None` object. So `repr(None)[:200]` is the literal 4-byte
string ``"None"`` — which is exactly what every one of T3's 219
``.in`` files contains (md5uniq == 1, content-uniq == 1 across all 219
artifacts, each 4 bytes long). The .in file is therefore a faithful
*trace* of the triggering input: the actual call site received the
Python None singleton.

The on-disk minimized.bin reproduces the harness's logged payload
(str "None") so a downstream reader can see *what was logged*, while
the repro *itself* calls the SUT with the live trigger value (`None`)
that produced the crash.

Expected output (last line):
    AttributeError: 'NoneType' object has no attribute 'replace'

Exit code: 1 (uncaught exception).

Usage:
    python3 repro.py
"""
from __future__ import annotations

from pathlib import Path
import sys

# Add the repo root to sys.path so we import the *committed* module
# rather than any installed version. The worktree is at
# /root/.worktrees/t_cycle185-adversary-01/ so repo root is the parent.
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from url_encoder_pure import unquote_plus  # noqa: E402

# Verify the on-disk payload matches what we expect (sanity check that
# the fuzzer logged the None repr).
payload = (Path(__file__).parent / "minimized.bin").read_text()
assert payload == "None", f"unexpected payload: {payload!r}"

# Call the SUT with the actual trigger (the Python None singleton).
# The ``type: ignore`` is deliberate: the type signature says ``s: str``,
# but the whole point of this finding is that the function accepts None
# at runtime and crashes with AttributeError — exactly the Invariant 21
# violation F-001 from VULN_AUDIT.md and the same gap fix2 (commit
# 3e5a893) missed on the decode side.
unquote_plus(None)  # type: ignore[arg-type]