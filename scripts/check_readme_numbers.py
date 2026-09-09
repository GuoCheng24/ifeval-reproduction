#!/usr/bin/env python3
"""Every score the README quotes must match results/metrics_*.json.

The README once wrote arm 3's 87.5% next to "a random subsample of 80 prompts"
without saying a cost cap had stopped the run at 32 of them, so the figure read
as 70 of 80 rather than 28 of 32 and looked far more certain than it was. The
detailed results file said "32 / 80 (partial, cap-stopped)"; the file people
actually read did not.

    python scripts/check_readme_numbers.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
r1 = json.loads((ROOT / "results/metrics_run1.json").read_text())
r2b = json.loads((ROOT / "results/metrics_run2b.json").read_text())
readme = (ROOT / "README.md").read_text(encoding="utf-8")

# (description, quoted percent, quoted numerator/denominator or None, measured source)
CHECKS = [
    ("run 1 prompt-level strict", 76.9, (416, 541), r1["strict"]["prompt_level_acc"],
     r1["strict"]["n_prompts_correct"], r1["strict"]["n_prompts"]),
    ("run 1 prompt-level loose", 80.4, (435, 541), r1["loose"]["prompt_level_acc"],
     r1["loose"]["n_prompts_correct"], r1["loose"]["n_prompts"]),
    ("run 1 instruction-level strict", 83.6, None, r1["strict"]["instruction_level_acc"],
     r1["strict"]["n_instructions_correct"], r1["strict"]["n_instructions"]),
    ("run 1 instruction-level loose", 86.2, None, r1["loose"]["instruction_level_acc"],
     r1["loose"]["n_instructions_correct"], r1["loose"]["n_instructions"]),
    ("run 2b prompt-level strict", 87.5, (28, 32), r2b["strict"]["prompt_level_acc"],
     r2b["strict"]["n_prompts_correct"], r2b["strict"]["n_prompts"]),
]

bad = []
for name, quoted_pct, quoted_frac, acc, corr, tot in CHECKS:
    measured = round(acc * 100, 1)
    ok_pct = measured == quoted_pct
    ok_frac = quoted_frac is None or quoted_frac == (corr, tot)
    ok_in_readme = str(quoted_pct) in readme
    print(f"  {name:<34} README {quoted_pct}  measured {measured} ({corr}/{tot})  "
          f"{'ok' if ok_pct and ok_frac and ok_in_readme else 'MISMATCH'}")
    if not ok_pct:
        bad.append(f"{name}: README says {quoted_pct}, data says {measured}")
    if not ok_frac:
        bad.append(f"{name}: README says {quoted_frac[0]}/{quoted_frac[1]}, data says {corr}/{tot}")
    if not ok_in_readme:
        bad.append(f"{name}: {quoted_pct} no longer appears in the README")

# A percentage from a capped run must carry its own numerator and denominator.
# "of 32" alone is not enough: the README says "4 of 32 responses" elsewhere, so
# that substring survives deleting the sentence this is meant to protect.
n2c, n2 = r2b["strict"]["n_prompts_correct"], r2b["strict"]["n_prompts"]
if "87.5" in readme and f"{n2c} of {n2}" not in readme:
    bad.append(f"the run-2b percentage appears without saying it is {n2c} of {n2} prompts")

if bad:
    print("\n" + "\n".join(bad))
    sys.exit(1)
print("every score quoted in the README matches the committed metrics")
