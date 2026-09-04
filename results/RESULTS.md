# IFEval — InternScience/Agents-A1-4B, measured first-hand on this machine

Snapshot `945c40a4aa6f534d434a353207b8d42ecf7a5293`, plain `transformers` 5.16.1 `generate()`, bf16, 1x NVIDIA GeForce RTX 4090 (CUDA index 1).
Everything in this directory is on disk and re-runnable: `run_gen.sh` (generation, resume-by-id), `score_ifeval.py` (official scorer), `scorer_controls.py`, `make_results.py`.

## Result

| metric | measured (this run) | model card claim |
|---|---|---|
| prompt-level strict acc | **76.9** (416/541) | 94.8 (metric variant not stated) |
| prompt-level loose acc | **80.4** (435/541) | |
| instruction-level strict acc | **83.6** (697/834) | |
| instruction-level loose acc | **86.2** (719/834) | |

Prompts scored: 541 (of 541). Data: `data/input_data.jsonl` = google-research `instruction_following_eval/data/input_data.jsonl` (541 prompts, 834 instructions). Scorer: official `google-research/instruction_following_eval` code, vendored unmodified in `ifeval_scorer/` and invoked through its own `evaluation_main` (report in `scored/official_report.txt`, per-prompt verdicts in `scored/eval_results_{strict,loose}.jsonl`).

Difference vs the card's 94.8: prompt-strict -17.9, prompt-loose -14.4, instr-strict -11.2, instr-loose -8.6 points. **Every one of the four metrics is more than 3 points below the card's number.** Truncation cannot close the gap: 22 of the 43 responses that hit the 1280-token cap fail prompt-level strict; even if all of them had passed, prompt-level strict would be at most 81.0.

## Exact generation settings

| setting | value |
|---|---|
| decoding | greedy (`do_sample=False`), `repetition_penalty=1.0`, no presence penalty |
| max_new_tokens | 1280 |
| dtype / device | bfloat16 / cuda, `flash-linear-attention` 0.5.2 Triton kernels for the gated-delta-net layers, torch fallback for causal-conv1d |
| chat template | the snapshot's own `chat_template.jinja` via `tokenizer.apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)`; no system message supplied, so the template injects its built-in Intern-A1 system prompt (dated 2026-07-14) |
| thinking | **off** (`enable_thinking=False` -> prompt ends with an empty `<think>\n\n</think>` block); a `<think>...</think>` prefix, if any, is stripped before scoring — none occurred at the start of any response |
| seed | `torch.manual_seed(0)` (irrelevant under greedy, set anyway) |
| batching | batch size 24, left padding, prompts sorted by token length |
| responses that hit the 1280-token cap | 43/541 (scored as-is, truncated); of these, 6 are degenerate repetition loops by a simple heuristic (a 20-char window recurring >=4x in the last 400 chars), keys [202, 3326, 1880, 3407, 2912, 2275] |
| spontaneous `<think>` emitted mid-answer despite thinking off | 1 response(s), keys [3130] (greedy continuation re-opened a `assistant\n<think>` turn; scored as-is) |
| generated tokens per response | mean 377, median 243, max 1280 |

## Cost

Wall-clock 45.7 min for 541 prompts (203692 new tokens, 74.2 tok/s aggregate, 0.197 prompt/s), model load excluded; peak `torch.cuda.max_memory_allocated` 11.43 GB on GPU 1 (nvidia-smi showed ~13.3 GB incl. context/cache). Model load ~25 s. Run timestamps in `gen.log`.

## Deviations from the model card — read before comparing numbers

* **The card does not say how its 94.8 was produced.** It gives no decoding settings for IFEval, does not say which of the four IFEval metrics 94.8 is (prompt/instruction x strict/loose), and does not say whether thinking mode was on. Its general recommendation is *sampling* (`temperature=0.85, top_p=0.95, top_k=20, presence_penalty=1.1`, README lines 352-361) served through vLLM/SGLang with a reasoning parser. I ran **greedy**, **thinking off**, **max_new_tokens=1280**, **plain transformers**. So this is *not* a reproduction of their setting; it is an independent measurement under a stated, deterministic setting. Thinking was turned off because with the template's default thinking mode a 1280-token budget would mostly be spent inside `<think>` and truncated answers would score near zero; a thinking-mode run with a much larger budget was not attempted.
* The card's note (README line ~393) says numbers for *other* models are copied from their technical reports and that their own were produced with the `Agents-A1/evaluation` framework; that framework was not used here (GitHub is unreachable from this node except raw file fetches).
* Data: the HF `google/IFEval` copy differs from the google-research copy in exactly one record (key 2785, prompt says "at least one placeholder" vs "at least 3 placeholders"; `kwargs` identical). The google-research copy was used because it is what the vendored scorer ships with (`data/hf_vs_google_diff.txt`).
* Environment shims that do not change the scorer's logic: files placed in a package dir (import path only); `nltk` pinned to 3.8.1 because nltk 3.10 refuses the punkt pickle the official code loads; punkt data pulled from an HF mirror of `nltk_data` (hashes in `env.txt`).

## Scorer controls (run before trusting the table)

**Negative control** (`controls/negative_*`): 20 prompts; 10 given an empty response, 10 given the prompt echoed back verbatim.
Result: prompt-level strict 10.0%, instruction-level strict 12.9% (loose identical). Breakdown:

```
echo-pass (echo_prompt): ['keywords:existence']
  echo-pass (echo_prompt): ['length_constraints:number_paragraphs', 'detectable_content:postscript']
  echo-pass (echo_prompt): ['length_constraints:number_words']
strict: echo_prompt: prompt-level 2/10  instruction-level 4/15
strict: empty: prompt-level 0/10  instruction-level 0/16
loose: echo_prompt: prompt-level 2/10  instruction-level 4/15
loose: empty: prompt-level 0/10  instruction-level 0/16
```
Empty responses score exactly 0. The two echo "passes" are the prompt text itself satisfying a constraint it states (the prompt contains the required keywords / the `P.S.` marker and paragraph breaks / is longer than the required minimum word count) — a property of the benchmark, not a scorer bug.

**Positive control** (`controls/positive_*`): 5 hand-written, obviously compliant answers to single-instruction prompts (`punctuation:no_comma`, `change_case:english_lowercase`, `startend:quotation`, `detectable_format:title`, `startend:end_checker`). Result: prompt-level strict 100.0%, instruction-level strict 100.0% (5/5).

**Batch-invariance check** (free by-product of an aborted first launch at batch size 48, `generations_bs48_partial.jsonl`): the same 48 prompts generated at batch 48 vs the final batch-24 run are byte-identical for 10/48 responses; scored on those 48 prompts: prompt-strict 85.4 (bs48) vs 83.3 (bs24), instr-strict 85.7 vs 83.7 — i.e. 41 vs 40 prompts and 42 vs 41 instructions correct out of 48/49. So bf16 greedy decoding with left-padded batching is **not** bit-exact across batch compositions here (most responses diverge somewhere after the first tokens), and a re-run with a different batch size should be expected to move the headline numbers by on the order of a point. "Deterministic" in this report means: same script, same batch size, same GPU class reproduces `generations.jsonl` — not that the number is invariant to batching.

**Scorer determinism** (`scored/`, `scored_rep1..3/`): the official scorer was run 4 times on the identical `generations.jsonl`. Range across runs — prompt-strict 76.89-76.89, prompt-loose 80.41-80.59, instr-strict 83.57-83.69, instr-loose 86.09-86.21. Instruction types whose verdict flipped between runs: ['keywords:letter_frequency', 'language:response_language']. The official code is not seeded: `langdetect.detect` is called without `DetectorFactory.seed` (instructions.py lines 158/1416/1448), and checkers whose kwargs are missing or invalid draw parameters with `random` — concretely, key 1122 asks for the letter `#`, which is not an ASCII letter, so `LetterFrequencyChecker.build_description` (instructions.py ~line 1337) substitutes `random.choice(string.ascii_letters)` on every run and that verdict is a coin flip. This is a property of the official scorer left untouched here; the table reports the first run (`scored/`), and the spread above is the honest precision of the scorer itself (about +-1 instruction).

## Per-category instruction-level accuracy (strict)

| category | acc |
|---|---|
| change_case | 77.5 |
| combination | 86.2 |
| detectable_content | 88.7 |
| detectable_format | 94.3 |
| keywords | 76.7 |
| language | 96.8 |
| length_constraints | 74.8 |
| punctuation | 78.8 |
| startend | 94.0 |

## Model card claim, verbatim

```
# Verbatim IFEval claim lines from the model card ($HF_HOME/hub/models--InternScience--Agents-A1-4B/snapshots/945c40a4aa6f534d434a353207b8d42ecf7a5293/README.md), captured 2026-09-04

## README.md line 69:
We release the dense model Agents-A1-4B with only 4B parameters, yet it delivers impressive performance across long-horizon search, engineering & research, instruction following, and general/scientific agentic tasks. It significantly outperforms similarly-sized models on BrowseComp (66.8), XBench-DS-2510 (90.0), GAIA (95.1), FrontierScience-Research (33.3), and IFEval (94.8), with some scores approaching or even surpassing larger MoE models like Nex-N2-mini and Qwen3.6. Compared to the flagship 35B Agents-A1, the 4B variant achieves strong competitiveness with a fraction of the parameters, demonstrating the series' excellent balance between efficiency and performance, and continuously narrowing the gap between small models and frontier systems.

## README.md table header (lines 86-93) and IFEval row (lines 213-220):
</tr>

<tr>
<th align="center">Qwen3.5-4B</th>
<th align="center">Agents-A1-4B</th>
<th align="center">Qwen3.5</th>
<th align="center">Qwen3.6</th>
<th align="center">Nex-N2-mini</th>
...
<tr>
<td align="left">IFEval</td>
<td align="center">89.8</td>
<td align="center">🥇 94.8</td>
<td align="center">91.9</td>
<td align="center">91.3</td>
<td align="center">88.4</td>
<td align="center">🥇 94.8</td>

## README.md lines 352-361 (recommended sampling parameters):
### Recommended Sampling Parameters & System Prompt

For the best generation quality and more stable multi-turn behavior, we recommend using the following sampling parameters:

* `temperature`: 0.85
* `top_p`: 0.95
* `top_k`: 20
* `min_p`: 0.0
* `presence_penalty`: 1.1
* `repetition_penalty`: 1.0

## README.md line 393-396 (evaluation protocol note):
For detailed evaluation scripts, task definitions, metrics, and reproduction instructions, please refer to the evaluation codebase.

## Citation
```

## Files

`gen_ifeval.py` / `run_gen.sh` (generation), `generations.jsonl` (one line per prompt: key, prompt, response, raw_response, n_new_tokens, finished, seed, settings), `score_ifeval.py`, `scored/metrics.json`, `scored/official_report.txt`, `scored/eval_results_strict.jsonl`, `scored/eval_results_loose.jsonl`, `scorer_controls.py`, `controls/`, `env.txt` (pip freeze, nvidia-smi, snapshot + file hashes), `gen.log`, `model_card_claim.txt`, `ifeval_scorer/` (vendored official scorer).
