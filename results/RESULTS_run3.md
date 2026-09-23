# Run 3 — report the generation batch size, because it decides the verdict

Pre-registered in [`prereg/PREREG_run3.md`](../prereg/PREREG_run3.md) and its
[addendum](../prereg/PREREG_run3_addendum_3d.md), both committed before any
generation. Four arms on idle 46 GB accelerators, no memory cap and no time cap
— the constraints that stopped run 2b at 32 of its 80 prompts were properties of
one contended card, not of the measurement.

## The finding

**Two arms that differ only in how many sequences share a forward pass land on
opposite sides of the model card's number, while being statistically
indistinguishable from each other.**

| arm | batch | prompt-level strict | 95% CI (Clopper–Pearson) | against the card's 94.8 |
|---|---|---|---|---|
| **3a** | 16 | 86.25% (69/80) | [76.73, 92.93] | **excludes it** |
| **3b** | 8 | 90.00% (72/80) | [81.24, 95.58] | **contains it** |

Paired on the same 80 prompts: discordant **b = 4, c = 7**, exact two-sided
McNemar **p = 0.549**. The 3.75-point difference is well inside sampling noise —
and the pre-registered verdict against the card flips anyway, because the
threshold is a CI boundary and the two CIs straddle it.

Only **1 of 80** responses is byte-identical between the arms.

Batch size is not a setting the model card states, the benchmark defines, or any
leaderboard reports. It is chosen from available memory. **On this benchmark,
with this model, at this sample size, it decides the published conclusion.**

The recommendation that follows is cheap: **report the generation batch size,
and report more than one arm when a verdict rests on a CI boundary.**

## The three controls that make that readable

### Generation on one machine is bit-exact

| | 3c | 3d |
|---|---|---|
| prompt-level strict | 75.42% (408/541) | 75.42% (408/541) |

Arms 3c and 3d are the same 541 prompts, greedy, same batch size, same seed, on
two cards of the same model. **541 of 541 responses are byte-identical**, zero
discordant prompts, McNemar p = 1.000.

So the batch effect above is not run-to-run nondeterminism. Within a machine
this model's greedy generation is exactly reproducible, which is what the
addendum required before any hardware claim was allowed.

### The scorer moves on a file that never changes

Scoring one unchanged generations file **ten times**:

| metric | spread |
|---|---|
| prompt-level strict | **0.370 points** |
| prompt-level loose | 0.370 points |
| instruction-level strict | 0.360 points |
| instruction-level loose | 0.240 points |

Exactly **2 of 541 prompts** fail to score the same every time — 3130, a
`language:response_language` instruction that goes through a language detector,
and 1129, `keywords:letter_frequency` + `combination:repeat_prompt`, which does
not.

Three scorings had said prompt-level strict was stable. Ten say it is not, and
the wrong number is the one that was nearly used.

**1129 is inside the 80-key subsample**, where one flipped prompt is worth
**1.25 points**. The batch comparison above therefore carries this figure
alongside it: a one-prompt difference between arms 3a and 3b would be within the
scorer's own range.

`results/scorer_noise.json`.

### Changing only the card moves the score

Run 1 and arm 3c are the same 541 prompts, same weights and checksum, same
greedy decoding, same batch size, same seed, same scorer — on two different
accelerator models.

| metric | run 1 | 3c | difference | vs the scorer's spread |
|---|---|---|---|---|
| prompt-level strict | 76.89% | 75.42% | **−1.48** | **4.0×** |
| prompt-level loose | 80.41% | 79.11% | −1.29 | 3.5× |
| instruction-level strict | 83.57% | 83.09% | −0.48 | 1.3× |
| instruction-level loose | 86.21% | 85.85% | −0.36 | 1.5× |

The two prompt-level differences are several times the scorer's own range. The
two instruction-level differences are barely above it and **do not carry
weight**.

Run 1's per-prompt record was never committed, so this comparison is
aggregate-only and run 1's figure is a single scoring rather than a median.
That limitation is why run 3 commits a per-prompt table for every arm.

## Thinking on versus off, at the pre-registered size

| | 3a (thinking on) | 3c (thinking off), same 80 keys |
|---|---|---|
| prompt-level strict | 86.25% (69/80) | 81.25% (65/80) |

Discordant **b = 8, c = 4**, exact two-sided McNemar **p = 0.388**.

`PREREG_run2b_analysis.md` requires at least 50 completed pairs for this test to
be interpreted. Run 2b had 32 and was labelled **UNDERPOWERED**; run 3 has 80,
so the condition is met and the test is interpretable.

It does not resolve a 5-point difference: 12 prompts move, 8 one way and 4 the
other. The honest statement is that **80 pairs do not separate the arms**, which
is different from "thinking mode makes no difference" and different again from
"underpowered".

## The token budget

| arm | budget | unclosed `</think>` | median new tokens |
|---|---|---|---|
| run 2a | 4096 | 7/12 | 2136 |
| run 2b | 16384 | 4/32 | 4539 |
| **3a** | 16384 | **7/80** | 4338 |
| **3b** | 16384 | **5/80** | 4345 |

At 16384 this model closes its reasoning block on 91% of prompts. Serving it
with a 4k output budget silently truncates most answers mid-reasoning, which is
a deployment fact independent of any score.

## What run 3 fixed about run 2

Run 1's and run 2b's per-prompt outcomes were never committed, so the paired
comparison published in `RESULTS_run2.md` cannot be recomputed by a reader —
including by us. Every arm here writes `per_prompt.csv` next to its metrics, and
the input file was re-fetched and md5-verified against the bytes runs 1 and 2
used.

## Reproducing

```bash
python3 scripts/analyze_run3.py          # asserts the pre-registration's hash first
python3 scripts/scorer_noise.py --responses generations_run3c_full541.jsonl --n 10
```
