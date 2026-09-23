# Reproducing IFEval on a 4B agent model — and what the generation batch size does to the answer

[![test](https://github.com/GuoCheng24/ifeval-reproduction/actions/workflows/check.yml/badge.svg)](https://github.com/GuoCheng24/ifeval-reproduction/actions/workflows/check.yml)

A first-hand reproduction of the IFEval score published for
[InternScience/Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B), with a
pre-registration chain CI re-hashes on every push.

**The finding: two arms that differ only in how many sequences share a forward pass land on
opposite sides of the model card's number, while being statistically indistinguishable from each
other.**

| arm | generation batch | prompt-level strict, n=80 | 95% CI | against the card's 94.8 |
|---|---|---|---|---|
| **3a** | 16 | **86.25%** (69/80) | [76.73, 92.93] | **excludes it** |
| **3b** | 8 | **90.00%** (72/80) | [81.24, 95.58] | **contains it** |

Paired on the same 80 prompts: discordant b = 4, c = 7, exact two-sided McNemar **p = 0.549**. The
3.75-point difference is well inside sampling noise; the verdict flips anyway, because the
pre-registered threshold is a confidence-interval boundary and the two intervals straddle it. Only
**1 of 80** responses is byte-identical between the arms.

Batch size is not a setting the model card states, the benchmark defines, or a leaderboard reports.
It is chosen from whatever memory is free. **Report it, and report more than one arm when a verdict
rests on an interval boundary.**

Full write-up: [`results/RESULTS_run3.md`](results/RESULTS_run3.md).

### Three controls that make that readable

- **Generation on one machine is bit-exact.** The same 541 prompts, greedy, same batch size and
  seed, on two cards of the same model: **541 of 541 responses byte-identical**, zero discordant.
  So the batch effect is not run-to-run nondeterminism.
- **The scorer moves on a file that never changes.** Ten scorings of one unchanged file span
  **0.370 points** on prompt-level strict; exactly **2 of 541** prompts are unstable, and one of
  them is inside the 80-prompt subsample, where a single flipped prompt is worth **1.25 points**.
  Three scorings had said it was stable.
- **Changing only the accelerator moves the score.** Same weights, checksum, decoding, batch size,
  seed and scorer on two different cards: prompt-level strict **76.89% → 75.42%**, a **−1.48**-point
  difference that is **4.0×** the scorer's own spread. The two instruction-level differences are
  1.3× and 1.5× and do not carry weight.

### The full-set measurement

| metric | measured here | model card |
|---|---|---|
| prompt-level strict | **76.9** (416/541) | **94.8** |
| prompt-level loose | 80.4 (435/541) | variant not stated |
| instruction-level strict | 83.6 (697/834) | |
| instruction-level loose | 86.2 (719/834) | |

Greedy, bf16, thinking off, `max_new_tokens=1280`, plain `transformers` — **not** the card's own
recommendation, which is sampling at T=0.85 with thinking on. That difference is the reason for
every later arm.

**Thinking on versus off, at the pre-registered size:** 86.25% against 81.25% on the same 80
prompts, discordant b = 8, c = 4, exact two-sided McNemar **p = 0.388**. Run 2b had 32 pairs and was
labelled UNDERPOWERED by its own analysis pre-registration, which requires 50; run 3 has 80, so the
test is interpretable and it does not separate the arms.


> **On machine names.** Everything here uses neutral labels in place of local cluster hostnames.
> The pre-registrations were sealed before that decision, so removing the name from them is a
> **redaction**, not a tidy-up, and it is recorded as one:
> [`prereg/REDACTION.md`](prereg/REDACTION.md) gives the hash each was sealed under, the hash now,
> and a byte count showing the change is exactly a same-length substitution of one token.

## Earlier arms, and an analysis that killed my own result

Arm 3 re-ran a random subsample of 80 prompts under the card's sampling settings with a 16384-token
thinking budget. A cost cap stopped it after **32** of those 80, so its **87.5%** is 28 of 32
prompts, not 80 — against arm 1's 76.9% over all 541, an apparent 11-point gain from thinking mode.

It is not a gain. **Arm 1 scores 87.5% on those same 32 prompts.** The subsample was simply easier.
Paired by prompt, McNemar exact: b=2, c=2, p=1.000; excluding the four unclosed responses, b=0, c=2,
p=0.500.

The paired analysis was pre-registered as the primary test *before* any arm-3 score was computed,
precisely because an independent proportion at n≈30 has a confidence interval wide enough to contain
both 76.9 and 94.8 and therefore settles nothing. Comparing the two arms on the same prompts has the
power that comparing two independent estimates does not.

By the pre-registered stopping rule, those 32 completed pairs are under the 50 required, so the
verdict is **underpowered** — not "no difference".

## A finding that is useful on its own

At a **4096-token** budget the model fails to close its reasoning block on **58%** of IFEval prompts.
Raising the budget to **16384** brings closure to **88%**. Median tokens among responses that do
close: 2136 and 4539.

Those two medians are the one class of number here that this repository cannot re-derive: they come
from the generation files, which `.gitignore` keeps out (`generations*.jsonl`, `scored*/`). They are
quoted from `results/RESULTS_run2.md`, which is what the runs wrote, and `scripts/check_readme_numbers.py`
fails if the page and that file ever disagree.

Serving this model with a 4k output budget truncates most answers mid-reasoning. Arm 2's low score
largely measures that truncation rather than instruction-following, which is why it is reported as a
token-budget observation and not as an accuracy estimate.

## What was controlled, and what was not

Scorer controls, each seen failing before the real run was trusted: ten empty responses score 0/10
prompts and 0/16 instructions; ten prompt-echoes score 2/10, with both passes traced to the prompt
text itself satisfying a stated constraint; five hand-written compliant answers score 5/5.

Two things I found while checking the harness rather than the model:

- **The official scorer is not deterministic.** Four runs over identical generations give
  instruction-strict 83.57–83.69. Cause: `langdetect` is unseeded, and one prompt requests the
  letter `#`, which the reference checker replaces with `random.choice(ascii_letters)` on every run.
  Left untouched; the table reports run 1 and the spread is documented.
- **Batched bf16 decoding is not bit-exact.** The same 48 prompts at batch 48 versus batch 24 gave
  byte-identical responses for only 10 of 48. "Reproducible" here means same script, same batch
  size, same GPU class.

Uncontrolled, and stated as such: thinking budget (16384 was still insufficient for 4 of 32
responses), a single sampling seed, batch composition, and the serving stack — every arm used
`transformers.generate()`, not vLLM.

## Pre-registration

Three files, each hash-linked to the previous, each written before the scores it governs existed:
`prereg/`. `scripts/analyze_run2b.py` recomputes all three hashes and refuses to run if any changed.
CI now exercises that in both directions on every push -- unmodified it must clear the hashes, and with
a file tampered with it must abort on the hash -- rather than resting on my having watched it once.

The analysis itself cannot be re-run from a clone: it reads the generations and the scorer output, and
`.gitignore` keeps those out (`generations*.jsonl`, `scored*/`), so the script says so and stops. What
it produced is in `results/RESULTS_run2.md`, and `scripts/check_readme_numbers.py` fails if this page
and that file ever disagree about it.

The second amendment exists because the first design was wrong: at a 4096-token budget most
responses never finished reasoning, so the measurement would have been of the budget rather than of
the model. The third exists because the subsample was too small for an independent estimate to
distinguish anything, which is where the paired test came from.

## Running it

```bash
pip install torch transformers   # see results/env.txt for exact versions
python scripts/gen_ifeval.py --data data/input_data.jsonl --out generations.jsonl
python scripts/make_results.py
```

The scorer under `ifeval_scorer/` is Google Research's `instruction_following_eval`, vendored
unmodified apart from import-path packaging; `nltk` is pinned to 3.8.1 so its punkt pickle loads.
Prompt data is the 541-prompt `input_data.jsonl` from that project.

## Scope

This is one reproduction, on one GPU, by one person, under settings that differ from the card's own
recommendation in ways the card does not specify. It is not an audit and it does not support the
word "inflated". If the maintainers publish their decoding settings and thinking budget, the gap may
close entirely — and this repository is arranged so that re-running it under those settings is a
single command.
