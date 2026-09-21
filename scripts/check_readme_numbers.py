#!/usr/bin/env python3
"""Every number the README quotes must match the file it came from.

The README once wrote arm 3's 87.5% next to "a random subsample of 80 prompts"
without saying a cost cap had stopped the run at 32 of them, so the figure read
as 70 of 80 rather than 28 of 32 and looked far more certain than it was. The
detailed results file said "32 / 80 (partial, cap-stopped)"; the file people
actually read did not.

Two kinds of number, checked two ways, because they are not the same kind of
claim:

RE-DERIVED  the five scores, recomputed from results/metrics_*.json.

AGREEING    the closure rates, the median token counts and the paired-test
            figures. The generations they come from are deliberately not in
            this repository (.gitignore: generations*.jsonl, scored*/), so
            nothing here can recompute them. What can be enforced is that the
            page and results/RESULTS_run2.md -- the file the runs wrote -- do
            not disagree. They did: the page said the closed-response median
            at a 16384-token budget was 4140 while the results file said 4539,
            and 4140 came from nowhere at all.

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
results2 = (ROOT / "results/RESULTS_run2.md").read_text(encoding="utf-8")

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

# Numbers this repository cannot recompute, which must at least appear in both
# the page and the results file the runs wrote.
AGREEING = [
    ("closure at a 4096-token budget", "58%", "5/12 (42%)"),
    ("closure at a 16384-token budget", "88%", "28/32 (88%)"),
    ("median closed-response tokens, 4096", "2136", "2136"),
    ("median closed-response tokens, 16384", "4539", "4539"),
    ("paired discordant pairs, unclosed included", "b=2, c=2", "= **2**"),
    ("paired exact p, unclosed included", "p=1.000", "p = 1.000"),
    ("paired, unclosed excluded", "b=0, c=2,\np=0.500", "b=0, c=2, p=0.500"),
    ("arm 1 on the same 32 prompts", "87.5% on those same 32 prompts",
     "87.5 on the very same 32 prompts"),
]
for name, in_readme, in_results in AGREEING:
    ok_r, ok_s = in_readme in readme, in_results in results2
    state = "ok" if ok_r and ok_s else ("NOT ON PAGE" if ok_s else "NOT IN RESULTS")
    print(f"  {name:<40} {state}")
    if not ok_r:
        bad.append(f"{name}: the README no longer says {in_readme!r}")
    if not ok_s:
        bad.append(f"{name}: results/RESULTS_run2.md no longer says {in_results!r}")

# 4140 was the wrong median for two weeks. Make sure it cannot come back.
for stale in ("4140",):
    if stale in readme or stale in results2:
        bad.append(f"{stale} is a figure that was found to have no source; it is back on the page")

if bad:
    print("\n" + "\n".join(bad))
    sys.exit(1)
print("every number quoted in the README matches its source")
