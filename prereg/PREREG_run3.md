# Pre-registration — run 3 (gpu-03 L40, full n=80, batch-composition arm, thinking-OFF pairing)

Written **2026-09-22 23:59 (Asia/Shanghai)**, BEFORE any run-3 generation has been started. The generation
commands in `scripts/run_gen_run3*.sh` are committed in the same commit as this file and had not been
executed when it was committed.

## Why run 3 exists, stated plainly

Run 2b was stopped by its pre-registered 3-hour cost cap at 15:38 with **32 of its 80 pre-registered
prompts** done, and was reported as partial and **UNDERPOWERED** — its own analysis pre-registration
required at least 50 completed pairs. That verdict stands and is not being revised here.

Two things have changed since:

1. **Hardware.** Runs 1, 2 and 2b were done on one contended RTX 4090 (24 GB, shared with other users'
   jobs) under a self-imposed 20 GB memory cap. A second cluster node, `gpu-03`, carries **4 idle NVIDIA
   L40s with 46 GB each**. The memory cap and the time cap that produced the partial arm are artefacts of
   the machine that was available that day, not of the measurement.
2. **The raw generations of runs 1, 2 and 2b were not preserved.** `generations*.jsonl` is in
   `.gitignore` and the scratch working directory is gone. Aggregate metrics survive in
   `results/metrics_run1.json` and `results/metrics_run2b.json`; **per-prompt outcomes do not**. So the
   paired run-1-vs-run-2b comparison reported in `RESULTS_run2.md` cannot be recomputed by anyone,
   including us. Run 3 regenerates both arms and **commits the per-prompt scored table**, which is small.

**Disclosure of order.** Run 3 was decided upon *after* run 2b's partial score (28/32 strict) was seen.
The reason is hardware availability and the missing per-prompt record, not the score. Nothing in the
analysis plan below is chosen with knowledge of that number: the primary comparison, its threshold and
its interpretation are copied unchanged from `PREREG_run2b.md` and `PREREG_run2b_analysis.md`. The one
genuinely new element — the batch-composition arm — is new because it tests a *different* question, and
is pre-registered here with its own threshold before any of it is generated.

## What is held fixed from the earlier pre-registrations

- **Model**: `InternScience/Agents-A1-4B`, snapshot `945c40a4aa6f534d434a353207b8d42ecf7a5293`, bf16, the
  same safetensors sha256 recorded in `results/env.txt`.
- **Data**: `data/input_data.jsonl` = google-research master `instruction_following_eval/data/input_data.jsonl`,
  541 records, md5 `4c2c43252cc2d32969218a4252fc7212` — **the identical bytes used in run 1 and run 2**,
  re-fetched and md5-verified on 2026-09-22.
- **The n=80 subsample**: the same 80 keys, re-derived by `random.Random(0).sample(sorted(keys), 80)` and
  checked to be set-identical to the final list in `PREREG_run2b.md`. Written to
  `data/input_data_run3_n80.jsonl`, md5 `756f0f7a0f80901f0acf423faefcece4`, **123 instructions**.
- **Decoding, thinking-ON arms**: temperature 0.85, top_p 0.95, top_k 20, presence_penalty 1.1
  (vLLM semantics, additive, generated tokens only), `max_new_tokens=16384`, `enable_thinking=True`,
  template-default system message, seed 0. Unchanged from `PREREG_run2b.md`.
- **Decoding, thinking-OFF arm**: greedy, `max_new_tokens=1280`, `enable_thinking=False`, seed 0.
  Unchanged from run 1.
- **Scorer**: the same vendored official scorer under `ifeval_scorer/`, unmodified, run once per arm.
- **Unclosed `</think>`**: a response with no closing tag is scored as-is and counted as "unclosed", as in
  runs 2a and 2b.

## What changes, and it is only the machine

- **Hardware**: `gpu-03`, one NVIDIA L40 (46 GB) per arm, arms on separate GPUs, no other job on those
  GPUs at launch. GPU 3 is deliberately left free for other users of the shared node.
- **No memory cap and no time cap.** Every arm runs until all of its prompts are done. Batch size is set
  from the measured KV cost and recorded, exactly as `PREREG_run2b.md` already allowed ("Batch size is not
  pre-registered (it is a memory/throughput knob)") — with the single exception of arm 3b below, where
  batch size *is* the manipulated variable.

## The three arms

| arm | thinking | prompts | budget | decoding | batch size | GPU |
|---|---|---|---|---|---|---|
| **3a** primary | ON | the 80 pre-registered keys | 16384 | card sampling, seed 0 | **16** | gpu-03:0 |
| **3b** batch-composition | ON | the same 80 keys | 16384 | card sampling, seed 0 | **8** | gpu-03:1 |
| **3c** thinking-OFF pairing | OFF | all 541 | 1280 | greedy | 24 (as run 1) | gpu-03:2 |

If 46 GB cannot hold batch size 16 at a 16384-token budget, **both** 3a and 3b are halved together
(16/8 → 8/4) so that the 2× ratio between them is preserved, and the actual values are recorded. No other
response to an out-of-memory error is permitted.

## Pre-stated analysis

**Primary (arm 3a).** Prompt-level strict accuracy on n=80 with an exact (Clopper-Pearson) 95% CI, and the
other three IFEval metrics alongside. The threshold is copied from `PREREG_run2b.md`: **the subsample can
be compared with the card's 94.8 only if its 95% CI excludes 94.8.** If the CI contains 94.8, the honest
statement is that this arm does not distinguish our measurement from the card. Per-category instruction
accuracy is reported but no category is singled out after the fact.

**Thinking ON vs OFF (3a vs 3c on the same 80 keys).** Exact McNemar on the 80 paired prompt-level strict
outcomes. `PREREG_run2b_analysis.md` requires at least 50 completed pairs for this test to be interpreted;
with all 80 prompts generated in both arms that condition is met by construction, and if it is not met
(crash, truncation of an arm) the exact completed pair count is reported and the UNDERPOWERED label is
applied again. Discordant-pair counts are reported in both directions, not only the p-value.

**Batch composition (3a vs 3b).** The two arms differ in nothing that the model card, the benchmark or the
pre-registration treats as a setting: same model, same prompts, same decoder, same seed, same budget, same
scorer, same GPU model. They differ only in how many sequences share a forward pass. Report:

- prompt-level strict accuracy of each arm with its Clopper-Pearson CI, and the **difference in points**;
- the number of prompts whose strict outcome flips between the arms, with exact McNemar;
- the number of prompts whose generated text is byte-identical between the arms;
- median and maximum new tokens, and the unclosed-`</think>` count, per arm.

**Pre-stated interpretation, and the limit of it.** These arms use sampling (T=0.85), and the two arms do
not share a per-prompt random stream: batch size changes how the sequence-level sampling is consumed. A
score difference is therefore **not** by itself evidence of a numerical batch-invariance defect — sampling
noise alone produces one. Stated in advance:

- The quantity this arm can support is a **magnitude**: how far apart two runs can land when a practitioner
  changes nothing they would think of as a setting. That is the reportable result regardless of outcome.
- The quantity it **cannot** support is attribution to bf16 batch non-invariance. Our companion measurement
  in `batch-logprob-gap` establishes that mechanism at the log-probability level under greedy, paired
  conditions; this arm does not re-establish it and will not be written as if it does.
- Arm **3c is the clean hardware test**: greedy decoding at a fixed batch size is deterministic given the
  kernels, so comparing 3c's four aggregate metrics against `results/metrics_run1.json` (same data, same
  settings, same batch size, RTX 4090 → L40) isolates hardware and kernel differences with no sampling
  noise at all. Any difference there is reported as the headline of this comparison. Per-prompt comparison
  with run 1 is **impossible** because run 1's per-prompt record was not preserved; only the four aggregate
  metrics and the per-category table can be compared, and that limitation is stated wherever the comparison
  appears.

**Stopping rule.** There is no time cap. Each arm runs to completion of its prompt list; the harness is
resume-safe by key. If an arm cannot complete, whatever completed is reported, labelled partial, with the
exact prompt count and the same CI treatment — and, for the paired tests, the UNDERPOWERED rule above.

**No further amendment will be made on the basis of seeing run-3 scores.**

**What gets committed this time.** For every arm: the per-prompt scored table (key, strict outcome, loose
outcome, instruction ids, n_new_tokens, think_closed) as CSV, the run statistics, and the sha256 of the
generations file. The raw generations stay out of git for size, but the per-prompt table is what makes
every number in `RESULTS*.md` recomputable, and its absence is the reason run 2b's comparison cannot be
checked by a reader today.

## The 80 keys (re-derived, set-identical to PREREG_run2b.md)

Derivation is reproduced by `python3 -c "import json,random;ks=[json.loads(l)['key'] for l in open('data/input_data.jsonl')];print(sorted(random.Random(0).sample(sorted(ks),80)))"`.


```
[16, 164, 292, 331, 334, 1094, 1098, 1129, 1139, 1180, 1237, 1246, 1251, 1259, 1281, 1287, 1342, 1466, 1508, 1551, 1561, 1571, 1593, 1619, 1825, 1843, 1857, 1879, 1936, 1939, 2023, 2035, 2070, 2169, 2195, 2215, 2225, 2247, 2292, 2299, 2359, 2362, 2386, 2404, 2422, 2432, 2471, 2482, 2532, 2577, 2583, 2590, 2617, 2653, 2667, 2674, 2787, 2807, 2943, 3001, 3071, 3091, 3198, 3203, 3287, 3329, 3345, 3362, 3484, 3506, 3513, 3565, 3595, 3617, 3680, 3697, 3710, 3750, 3751, 3754]
```
