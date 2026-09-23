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

# ---------------------------------------------------------------- run 3
# Every run-3 figure on the page is recomputed from results/metrics_run3.json
# rather than compared against a string, because the page's headline is now a
# comparison whose whole point is that two numbers straddle a threshold - and a
# threshold claim that drifts from its interval is the defect this file exists
# for.
m3_path = ROOT / "results/metrics_run3.json"
if m3_path.exists():
    m3 = json.loads(m3_path.read_text(encoding="utf-8"))

    def pct(x):
        return f"{100 * x:.2f}"

    for arm in ("3a", "3b", "3c", "3d"):
        a = m3.get(f"run{arm}")
        if not a:
            continue
        acc = f"{100 * a['prompt_level_strict_acc']:.2f}%"
        lo, hi = (f"{100 * v:.2f}" for v in a["ci95_prompt_level_strict"])
        counts = f"({a['n_correct']}/{a['n_prompts']})"
        if arm in ("3a", "3b"):
            for token, what in ((acc, "accuracy"), (counts, "counts"),
                                (f"[{lo}, {hi}]", "interval")):
                ok = token in readme
                print(f"  run {arm} {what:<28} {'ok' if ok else 'NOT ON PAGE'}")
                if not ok:
                    bad.append(f"run {arm}: the README does not say {token}")
            # the claim the page makes about the card number must follow from the interval
            excludes = a["ci_excludes_card"]
            says_excludes = f"| **{acc}** {counts} | [{lo}, {hi}] | **excludes it**" in readme
            says_contains = f"| **{acc}** {counts} | [{lo}, {hi}] | **contains it**" in readme
            if says_excludes and not excludes:
                bad.append(f"run {arm}: the page says its interval excludes {m3['card_claim']}, "
                           f"but [{lo}, {hi}] contains it")
            if says_contains and excludes:
                bad.append(f"run {arm}: the page says its interval contains {m3['card_claim']}, "
                           f"but [{lo}, {hi}] excludes it")
            if not (says_excludes or says_contains):
                bad.append(f"run {arm}: the page states no verdict against the card number")
            print(f"  run {arm} verdict vs the card        "
                  f"{'ok' if (says_excludes or says_contains) else 'NOT ON PAGE'}")

    batch = m3.get("BATCH 16 (3a) vs batch 8 (3b), everything else identical")
    if batch:
        for token, what in ((f"b = {batch['b']}, c = {batch['c']}", "discordant counts"),
                            (f"p = {batch['mcnemar_exact_p']:.3f}", "exact p"),
                            (f"{abs(batch['points_difference']):.2f}-point", "difference"),
                            (f"{batch['byte_identical_responses']} of {batch['n_pairs']}",
                             "byte-identical responses")):
            ok = token in readme
            print(f"  batch arm {what:<28} {'ok' if ok else 'NOT ON PAGE'}")
            if not ok:
                bad.append(f"batch arm: the README does not say {token!r}")

    det = m3.get("DETERMINISM 3c vs 3d, same machine, same settings, greedy")
    if det:
        token = f"{det['byte_identical_responses']} of {det['n_pairs']} responses byte-identical"
        ok = token in readme
        print(f"  determinism control                      {'ok' if ok else 'NOT ON PAGE'}")
        if not ok:
            bad.append(f"the determinism control's result {token!r} is not on the page")

    noise = m3.get("scorer_noise")
    if noise:
        sp = noise["metrics"]["prompt_level_strict_acc"]["spread_points"]
        n_unstable = len(noise["prompts_whose_outcome_is_not_stable"])
        for token, what in ((f"{sp:.3f} points", "scorer spread"),
                            (f"{n_unstable} of {noise['n_prompts']}", "unstable prompts")):
            ok = token in readme
            print(f"  {what:<40} {'ok' if ok else 'NOT ON PAGE'}")
            if not ok:
                bad.append(f"scorer noise: the README does not say {token!r}")

    hw = m3.get("HARDWARE run 1 (RTX 4090) vs 3c (L40), aggregate only")
    if hw:
        d = hw["metrics"]["prompt_level_strict_acc"]
        token = f"{d['points']:.2f}"
        ok = token in readme or token.lstrip("-") in readme
        print(f"  hardware difference                      {'ok' if ok else 'NOT ON PAGE'}")
        if not ok:
            bad.append(f"the hardware difference {token} is not on the page")

# 4140 was the wrong median for two weeks. Make sure it cannot come back.
for stale in ("4140",):
    if stale in readme or stale in results2:
        bad.append(f"{stale} is a figure that was found to have no source; it is back on the page")

if bad:
    print("\n" + "\n".join(bad))
    sys.exit(1)
print("every number quoted in the README matches its source")
