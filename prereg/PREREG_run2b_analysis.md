# PREREG_run2b_analysis.md — SECOND AMENDMENT: analysis plan for run 2b

Written 2026-09-04 13:06 (Asia/Shanghai), BEFORE any run-2b response has been scored.

## What this amends

Amends `PREREG_run2b.md`, sha256
`326455ea25c5dd7aa4495beb4e3e9bb046decf005e70656a1ed678fcbc706a27` (unchanged and still in force),
which in turn amended `PREREG_run2.md`, sha256
`a7b616ee0f881fff5d39a45cf6920da5c8151826f7feec475adb0fdabc3ad11c` (unchanged and still governs run 2a).
This amendment changes only the ANALYSIS of run 2b. It changes no generation setting: the subsample keys,
decoding (T=0.85 / top_p=0.95 / top_k=20 / presence_penalty=1.1), thinking ON, `max_new_tokens=16384`,
seed 0, scorer and the 15:38 stopping rule all stand exactly as written.

**No run-2b response has been scored at the time of writing.** Verified immediately before writing:
`scored_run2b/` does not exist, `scored_run2/` does not exist, and `generations_run2b.jsonl` contained
0 completed rows (the first batch was still generating). The motivation for this amendment is a power
calculation done on the DESIGN (n and the size of the gap being tested), not on any observed run-2b score.

## Reason

The standalone analysis pre-registered in `PREREG_run2b.md` is underpowered for the question actually at
hand. The question is whether the truth on these prompts is near run 1's 76.9 or near the card's 94.8 — an
18-point gap. Power for the two analyses:

- Independent Clopper-Pearson CI half-width: n=30 gives about +-10.6 to +-14 points, n=50 about +-7.6 to
  +-12 (depending on the observed rate). Such an interval can contain 94.8 and would settle nothing.
- Paired McNemar exact, same prompts, run 1 vs run 2b: n=30 (~5:1 discordant) p=0.219; n=40 (~7:1) p=0.070;
  n=50 (~9:1) p=0.022; n=80 (~14:1) p=0.001.

Run 1 scored all 541 prompts, so every run-2b prompt already has a paired thinking-off baseline on the
identical prompt. Pairing costs no additional GPU time.

## Analysis plan (fixed here)

(a) **PRIMARY — McNemar exact, two-sided**, on prompt-level strict, paired by prompt key: run 1
    (greedy, thinking off, 1280 tokens) vs run 2b (sampling, thinking on, 16384 tokens), restricted to the
    keys run 2b actually completed. Report the discordant counts b (run-1 pass / run-2b fail) and
    c (run-1 fail / run-2b pass), the exact two-sided p-value (binomial on b+c), and the concordant counts.

(b) **SECONDARY — the standalone Clopper-Pearson 95% CI** on run-2b prompt-level strict, exactly as
    pre-registered in `PREREG_run2b.md`, together with the other three IFEval metrics.

(c) **Power rule, pre-stated**: if fewer than **50 completed pairs** are available, the paired test is
    declared **UNDERPOWERED** and no conclusion about the card's 94.8 may be drawn from it. The reported
    wording in that case is "underpowered" — explicitly NOT "no difference" and NOT "no effect".

(d) **Direction rule, pre-stated**: McNemar tests whether the run-2b arm differs from the run-1 arm. That is
    NOT a test against 94.8. A statistically significant paired improvement does **not** establish the
    card's number; the card's number is only reached if the run-2b point estimate's confidence interval
    reaches it. Both statements must appear together in the results.

## Cautions to carry into the write-up

- **The two arms differ in decoding as well as thinking mode** (greedy vs sampling at T=0.85 with top_p /
  top_k / presence_penalty, and 1280 vs 16384 tokens). Any paired effect is the JOINT effect of all of
  these, not the effect of thinking alone. No sentence may attribute it to thinking mode by itself.
- **Unclosed `</think>` prompts must be reported both ways** — included (scored as-is, per
  `PREREG_run2b.md`) and excluded — because excluding them conditions on an outcome of the generation and
  can bias the paired comparison. The primary analysis is the INCLUDED version; the excluded version is
  reported alongside as a sensitivity analysis, with its own n.
- Batch composition differs between the arms (run 1 batch 24; run 2b batch 8) and batched bf16 decoding was
  measured in run 1 to be non-bit-exact across batch compositions; this is a further uncontrolled factor.

## Stopping rule (unchanged)

Generation stops at 15:38 (3 h from the original 12:38 run-2 launch). Whatever completed is reported with
its exact count. If that leaves fewer than 50 pairs, the underpowered verdict in (c) applies.
