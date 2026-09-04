# PREREG_run2b.md — explicit AMENDMENT to PREREG_run2.md

Written 2026-09-04 13:01 (Asia/Shanghai), BEFORE any run-2b generation has been started.

## What this amends

This amends `PREREG_run2.md`, sha256 `a7b616ee0f881fff5d39a45cf6920da5c8151826f7feec475adb0fdabc3ad11c`
(that file is unchanged and remains in force for run 2a). It does not revise, reinterpret or replace any
result already obtained; it adds a third arm because the budget fixed in the original pre-registration was
found to be inadequate.

## Reason for the amendment (evidence available at the time of writing)

Measured on the FIRST BATCH ONLY of run 2a (n=12 generations, batch 1 at batch size 12):

- 7/12 responses (58%) never emitted a closing `</think>` within the
  pre-registered 4096-token budget;
- mean new tokens 3339;
- median new tokens among those that DID close their thinking: 2136.

At a 4096-token budget the measurement is therefore dominated by whether the model can finish thinking inside
the budget, rather than by whether it follows the instruction. That is a defect of the budget chosen in
`PREREG_run2.md`, not a property of the model.

**No IFEval scores of any run-2 response had been computed or seen when this amendment was written.** No
`scored_run2/` directory existed at that moment (verified). The only run-2 information used to justify this
amendment is the token-count / `</think>`-closure statistics quoted above. Run 1's scores (prompt-strict 76.9)
were known, but concern a different arm (greedy, thinking off).

## Design of run 2b (fixed here, before generation)

- **Subsample**: n=80 prompts drawn uniformly without replacement from the 541 IFEval prompts using
  Python `random.Random(0).sample(sorted(keys), 80)`. The drawn keys are listed below and are FINAL.
- **Decoding**: identical to `PREREG_run2.md` — temperature 0.85, top_p 0.95, top_k 20,
  presence_penalty 1.1, thinking ON (template default), sampler seed 0.
- **Budget**: `max_new_tokens = 16384` (the amended quantity; 4x the original).
- **Scored text**: everything after the first closing `</think>`; `raw_response` kept; a response with no
  closing tag is scored as-is and counted as "unclosed", as in run 2a.
- **Scorer**: the same vendored official scorer, run once.
- **Hardware**: GPU 1 only, same 20 GB cap. Batch size is not pre-registered (it is a memory/throughput
  knob); it will be set from the measured KV cost so the 20 GB cap holds, and its value recorded.

## Pre-stated analysis and interpretation

- Report prompt-level strict accuracy on the subsample with an exact (Clopper-Pearson) binomial 95% CI, and
  report the other three IFEval metrics alongside.
- **A subsample of n=80 cannot be compared with the card's 94.8 unless its 95% CI excludes 94.8.** If the CI
  contains 94.8, the honest statement is that this arm does not distinguish our measurement from the card.
- The unclosed-`</think>` rate is reported as a first-class result for both run 2a and run 2b, not as a
  footnote: it is a deployment-relevant fact about the token budget this model needs.
- **Stopping rule**: the 3-hour cost cap continues to run from the ORIGINAL run-2 launch at 12:38, i.e. it
  expires at 15:38. If run 2b has not finished all 80 prompts by then, generation stops and whatever
  completed is reported, labelled partial, with the exact prompt count and the same CI treatment.
  At the throughput measured in run 2a, completing all 80 within the cap is NOT expected; a partial arm of
  roughly 30-50 prompts is the realistic outcome and is an accepted result of this design.
- No further amendment will be made on the basis of seeing run-2b scores.

## The 80 drawn keys (final)

```
[16, 164, 292, 331, 334, 1094, 1098, 1129, 1139, 1180, 1237, 1246, 1251, 1259, 1281, 1287, 1342, 1466, 1508, 1551, 1561, 1571, 1593, 1619, 1825, 1843, 1857, 1879, 1936, 1939, 2023, 2035, 2070, 2169, 2195, 2215, 2225, 2247, 2292, 2299, 2359, 2362, 2386, 2404, 2422, 2432, 2471, 2482, 2532, 2577, 2583, 2590, 2617, 2653, 2667, 2674, 2787, 2807, 2943, 3001, 3071, 3091, 3198, 3203, 3287, 3329, 3345, 3362, 3484, 3506, 3513, 3565, 3595, 3617, 3680, 3697, 3710, 3750, 3751, 3754]
```
