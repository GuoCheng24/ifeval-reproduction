# Reproducing IFEval on a 4B agent model, on one shared GPU

[![test](https://github.com/GuoCheng24/ifeval-reproduction/actions/workflows/check.yml/badge.svg)](https://github.com/GuoCheng24/ifeval-reproduction/actions/workflows/check.yml)

A first-hand reproduction of the IFEval score published for
[InternScience/Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B), run on a single
RTX 4090 shared with other users. Three arms, a pre-registration written before any score existed,
and a paired analysis that killed one of my own conclusions.

**The short version: I could not reproduce the published figure under the settings I could afford,
and I did not refute it either.** Both halves of that sentence matter, and the evidence for each is
in this repository.

| metric | measured here | model card |
|---|---|---|
| prompt-level strict | **76.9** (416/541) | **94.8** |
| prompt-level loose | 80.4 (435/541) | variant not stated |
| instruction-level strict | 83.6 (697/834) | |
| instruction-level loose | 86.2 (719/834) | |

Complete run: all 541 prompts, 45.7 min, 74.2 tok/s, peak 11.4 GB. Greedy, bf16, thinking off,
`max_new_tokens=1280`, plain `transformers` — **not** the card's own recommendation, which is
sampling at T=0.85 with thinking on. That difference is the whole reason for arms two and three.

## The part worth reading: an analysis that killed my own result

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
close: 2136 and 4140.

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
`prereg/`. The analysis script recomputes all three hashes and refuses to run if any changed; I
verified that guard by tampering with a file and watching it abort.

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
