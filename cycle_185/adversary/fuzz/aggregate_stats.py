"""Aggregate fuzz run stats into cycle_185/adversary/fuzz/stats.json.

Parses the per-surface JSONL summary lines (the ``# SUMMARY`` block at
the end of each log file) and counts the .stack.txt artifacts written
under crashes/ for unexpected / postcondition / hang findings.

Idempotent: overwrites stats.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "logs"
CRASH_DIR = HERE / "crashes"

# run_<surface>_<TS>_seed42_n5000.log
# TS is %Y%m%dT%H%M%SZ = 16 chars.
LOG_RE = re.compile(
    r"^run_(?P<surface>.+?)_(?P<ts>\d{8}T\d{6}Z)_seed42_n5000$"
)


def main() -> int:
    stats: dict = {}
    for log in sorted(LOG_DIR.glob("run_*_seed42_n5000.log")):
        m = LOG_RE.match(log.stem)
        if not m:
            print(f"WARN: filename does not match pattern: {log.name}",
                  file=sys.stderr)
            continue
        surface = m.group("surface")
        with log.open() as f:
            text = f.read()
        summary_lines = [
            l for l in text.splitlines()
            if '"surface"' in l and '"crashes"' in l
        ]
        if not summary_lines:
            print(f"WARN: no summary in {log}", file=sys.stderr)
            continue
        s = json.loads(summary_lines[-1])
        counts = {
            k: v for k, v in s.items()
            if k not in ("surface", "elapsed_s", "log_path")
        }
        # Match crash files exactly: prefix is "<surface>_" AND the next
        # char must be a digit (the iter index). This prevents "unquote"
        # from matching "unquote_plus_*" (since `+` is not a digit).
        def _matching(suffix: str) -> list[Path]:
            out = []
            for p in CRASH_DIR.glob(f"{surface}_*.stack.txt"):
                if suffix not in p.name:
                    continue
                # After the surface prefix, the next chunk is the iter index.
                tail = p.name[len(f"{surface}_"):]
                if tail[:5].isdigit():
                    out.append(p)
            return sorted(out)

        unexpected = _matching("_unexpected.stack.txt")
        postcond = _matching("_postcondition.stack.txt")
        hangs = _matching("_hang.stack.txt")
        stats[surface] = {
            "iters": 5000,
            "seed": 42,
            "elapsed_s": s["elapsed_s"],
            "counts": counts,
            "crash_files": {
                "unexpected": len(unexpected),
                "postcondition": len(postcond),
                "hang": len(hangs),
                "total": len(unexpected) + len(postcond) + len(hangs),
            },
            "log_path": str(log.relative_to(HERE.parent.parent.parent)),
        }
    (HERE / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())