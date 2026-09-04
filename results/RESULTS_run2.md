# IFEval — Agents-A1-4B: three arms measured on this machine

All numbers first-hand, on disk, re-runnable. Pre-registrations (unchanged, hashes verified by the analysis script):
`PREREG_run2.md` `a7b616ee…`, `PREREG_run2b.md` `326455ea…`, `PREREG_run2b_analysis.md` `db2b189a…`.

## The three arms

| | run 1 | run 2a | run 2b |
|---|---|---|---|
| prompts scored | **541 / 541 (complete)** | **12** (partial) | **32 / 80** (partial, cap-stopped) |
| decoding | greedy | card's sampling | card's sampling |
| thinking | off | **on** | **on** |
| max_new_tokens | 1280 | 4096 | **16384** |
| batch size | 24 | 12 | 8 |
| prompt-level strict | **76.9** | 66.7 | 87.5 [71.0, 96.5] |
| prompt-level loose | 80.4 | 66.7 | 90.6 |
| instruction-level strict | 83.6 | 66.7 | 90.0 |
| instruction-level loose | 86.2 | 66.7 | 92.5 |
| **model card claim** | 94.8 (metric variant, decoding and thinking budget all unstated) |||

Only **run 1 is a complete measurement of the benchmark.** Runs 2a and 2b are partial by cost cap; their
percentages are computed on 12 and 32 prompts respectively and carry the uncertainty shown.

## The comparison that matters, and the trap in it

Run 2b scores 87.5 and run 1 scores 76.9 overall, which invites "thinking mode gains ~11 points".
**That reading is wrong.** Run 1 scores **87.5 on the very same 32 prompts** — the run-2b subsample is
easier than the full 541, not the arm better. The pre-registered paired test (McNemar exact, two-sided,
paired by prompt key) on those 32 pairs:

- discordant pairs: b (run 1 pass, run 2b fail) = **2**, c (run 1 fail, run 2b pass) = **2**; concordant 26 both pass, 2 neither
- **exact two-sided p = 1.000**
- sensitivity, unclosed-`</think>` prompts excluded (n=28): b=0, c=2, p=0.500, run 2b 92.9 [76.5, 99.1] vs run 1 85.7 on the same prompts

### Verdict, as pre-registered

**UNDERPOWERED: fewer than 50 completed pairs; no conclusion about the card's 94.8 may be drawn from the paired test. This is 'underpowered', NOT 'no difference'.**

With 32 completed pairs (< 50), the paired test is **underpowered**. It has **not** shown that thinking mode
makes no difference; it has shown that this many pairs cannot resolve a difference of the size at issue.
Separately, and also pre-registered: McNemar compares run 2b with run 1 — it is **not** a test against 94.8.
Run 2b's 95% CI is [71.0, 96.5], which **contains 94.8**, so by the pre-stated rule this arm does not
distinguish our measurement from the card's number in either direction.

## First-class finding: the model needs far more than a 4k thinking budget

| arm | budget | closed `</think>` | median tokens (closed responses) | hit the cap |
|---|---|---|---|---|
| run 2a | 4096 | **5/12 (42%)** | 2136 | 7/12 |
| run 2b | 16384 | **28/32 (88%)** | 4539 | 6/32 |

At a 4096-token budget this model fails to close its reasoning on **58%** of IFEval prompts, and run 2a's
score (66.7) largely measures that truncation rather than instruction-following. Raising the budget to
16384 lifts closure to 88%. This is a deployment-relevant fact in its own right: serving this model with a
4k output budget silently truncates most of its answers mid-reasoning. It is also why `PREREG_run2b.md` was
written — the 4096 budget in the original pre-registration was my coordinator's design defect, identified
from batch-1 token counts before any run-2 score existed.

## Cost and what stopped the runs

Run 2b: n/a new tokens at ~nan tok/s, peak torch memory nan GB
(max observed `nvidia-smi` 18257 MiB, under the 20 GB cap), 4 batches of 8 in ~2h35m on one RTX 4090 (GPU 1 only).
The pre-registered 3-hour cap from the original 12:38 launch expired at **15:38 and stopped generation by PID**
with 32 of 80 prompts done; completed rows were preserved. Decoding 16384 tokens is sequential, so a larger
batch was the only speed-up available and it would have breached the memory cap.

## What all of this can and cannot settle

**Can**: run 1 is a complete, reproducible IFEval measurement of this snapshot under a fully stated
deterministic setting — prompt-strict 76.9, prompt-loose 80.4, instruction-strict 83.6, instruction-loose 86.2
on all 541 prompts, with the official scorer and controls that were seen failing (empty responses 0/10,
prompt echo 2/10 with each pass traced, hand-written compliant answers 5/5). The token-budget finding above
is solid in both arms.

**Cannot**: none of the three arms establishes the card's 94.8, and none refutes it. Run 2b's CI contains
94.8; run 2a is far too small; run 1 differs from the card's own recommended setting. The honest sentence is
that **we could not reproduce 94.8 under the settings we could afford on one shared 4090**. The factors we
did not control are: thinking budget (the card states none; 16384 was still not enough for 4/32 responses),
sampling seed (one seed), batch composition (run 1 measured batched bf16 decoding as non-bit-exact:
only 10/48 responses byte-identical between batch 48 and batch 24), and serving stack (the card used
vLLM/SGLang with a reasoning parser; the `vllm==0.10.1.1` install here never finished, so all three arms used
transformers `generate()`). The word "inflated" is not supported by this evidence and is not used.

Any of the three arms' paired comparisons would become decisive with more GPU time: 50 completed pairs would
reach p≈0.02 for the effect size at issue, and the run-2b subsample would need roughly the full 80 to give a
CI that could exclude 94.8.

## Files

`gen_ifeval_run2.py` (shared run-2 harness), `run_gen_run2.sh` / `run_gen_run2b.sh`, `generations_run2.jsonl` (2a),
`generations_run2b.jsonl` (2b), `scored_run2/`, `scored_run2b/`, `analyze_run2b.py` + `run2b_analysis.json`
(paired analysis; refuses to run if any pre-registration hash changed), `gen_run2a_final.log`, `gen_run2b.log`,
the three `PREREG_*.md` files and their `.sha256` files, `env.txt`. Run 1: `RESULTS.md`, `generations.jsonl`, `scored/`.
