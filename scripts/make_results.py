#!/usr/bin/env python
"""Assemble RESULTS.md from on-disk artifacts (metrics.json, generations.jsonl, runstats, controls, model card lines)."""
import json, os, re, statistics, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)

m = json.load(open(P("scored", "metrics.json")))
gens = [json.loads(l) for l in open(P("generations.jsonl")) if l.strip()]
keys = {g["key"] for g in gens}
assert len(keys) == len(gens), "duplicate keys in generations.jsonl"
n = len(gens); n_fin = sum(g["finished"] for g in gens); ntoks = [g["n_new_tokens"] for g in gens]
settings = gens[0]["settings"]
def is_loop(t, win=20, reps=4):
    """degenerate repetition: some 20-char window recurs >=4 times in the last 400 chars"""
    tail = t[-400:]
    return any(tail.count(tail[i:i + win]) >= reps for i in range(0, max(1, len(tail) - win), 5))
capped = [g for g in gens if not g["finished"]]
loops = [g["key"] for g in capped if is_loop(g["response"])]
spont_think = [g["key"] for g in gens if "<think>" in g["raw_response"]]
# run stats: last JSON object appended to generations.jsonl.runstats.json (one per (re)start); log timestamps give wall-clock
runstats_txt = open(P("generations.jsonl.runstats.json")).read()
runs = [json.loads(s) for s in re.findall(r"\{.*?\n\}", runstats_txt, flags=re.S)]
log = open(P("gen.log")).read()
ts = re.findall(r"^(\d\d:\d\d:\d\d) (?:model loaded|DONE)", log, flags=re.M)
gpu_name = runs[-1]["gpu_name"] if runs else "?"
wall = sum(r["wall_s"] for r in runs); tok_per_s = sum(r["new_tokens"] for r in runs) / wall
peak = max(r["peak_mem_GB"] for r in runs)
gpu_idx = ",".join(sorted({str(r["gpu"]) for r in runs}))

neg = json.load(open(P("controls", "negative_scored", "metrics.json")))
pos = json.load(open(P("controls", "positive_scored", "metrics.json")))
negbd = open(P("controls", "negative_breakdown.txt")).read().strip()

# batch-invariance check: 48 prompts generated at batch 48 (aborted first launch) vs the final batch-24 run
bs48 = {json.loads(l)["key"]: json.loads(l)["response"] for l in open(P("generations_bs48_partial.jsonl"))}
final = {g["key"]: g["response"] for g in gens}
shared = [k for k in bs48 if k in final]
ident = sum(bs48[k] == final[k] for k in shared)
s48 = json.load(open(P("scored_bs48_partial", "metrics.json")))
# score the same 48 keys from the final run
sub = P("controls", "final_subset_bs48keys.jsonl")
with open(sub, "w") as f:
    for g in gens:
        if g["key"] in bs48: f.write(json.dumps(dict(key=g["key"], prompt=g["prompt"], response=g["response"])) + "\n")
subprocess.run(["python", P("score_ifeval.py"), "--responses", sub, "--out_dir", P("controls", "final_subset_bs48keys_scored"), "--restrict"],
               check=True, stdout=subprocess.DEVNULL)
s24 = json.load(open(P("controls", "final_subset_bs48keys_scored", "metrics.json")))

claim = open(P("model_card_claim.txt")).read()
# scorer determinism: the official scorer was run 4x on the identical generations.jsonl (scored, scored_rep1..3)
rep_dirs = [d for d in ["scored", "scored_rep1", "scored_rep2", "scored_rep3"] if os.path.exists(P(d, "metrics.json"))]
rep_ms = [json.load(open(P(d, "metrics.json"))) for d in rep_dirs]
spread = {k: (min(100*x[k] for x in rep_ms), max(100*x[k] for x in rep_ms)) for k in
          ["prompt_level_strict_acc", "prompt_level_loose_acc", "instruction_level_strict_acc", "instruction_level_loose_acc"]}
flipped = set()
for mode in ["strict", "loose"]:
    per = [{json.loads(l)["prompt"]: tuple(json.loads(l)["follow_instruction_list"]) for l in open(P(d, f"eval_results_{mode}.jsonl"))} for d in rep_dirs]
    ids = {json.loads(l)["prompt"]: json.loads(l)["instruction_id_list"] for l in open(P(rep_dirs[0], f"eval_results_{mode}.jsonl"))}
    for p in per[0]:
        vs = [x[p] for x in per]
        if len(set(vs)) > 1:
            for j in range(len(vs[0])):
                if len({v[j] for v in vs}) > 1: flipped.add(ids[p][j])
det_md = (f"**Scorer determinism** (`scored/`, `scored_rep1..3/`): the official scorer was run {len(rep_dirs)} times on the identical `generations.jsonl`. "
          f"Range across runs — prompt-strict {spread['prompt_level_strict_acc'][0]:.2f}-{spread['prompt_level_strict_acc'][1]:.2f}, "
          f"prompt-loose {spread['prompt_level_loose_acc'][0]:.2f}-{spread['prompt_level_loose_acc'][1]:.2f}, "
          f"instr-strict {spread['instruction_level_strict_acc'][0]:.2f}-{spread['instruction_level_strict_acc'][1]:.2f}, "
          f"instr-loose {spread['instruction_level_loose_acc'][0]:.2f}-{spread['instruction_level_loose_acc'][1]:.2f}. "
          f"Instruction types whose verdict flipped between runs: {sorted(flipped)}. The official code is not seeded: `langdetect.detect` is called without "
          f"`DetectorFactory.seed` (instructions.py lines 158/1416/1448), and checkers whose kwargs are missing or invalid draw parameters with `random` — concretely, key 1122 asks for the letter `#`, which is not an ASCII letter, so `LetterFrequencyChecker.build_description` (instructions.py ~line 1337) substitutes `random.choice(string.ascii_letters)` on every run and that verdict is a coin flip. "
          f"This is a property of the official scorer left untouched here; the table reports the first run (`scored/`), and the spread above is the honest precision of the scorer itself (about +-1 instruction).")
# truncation ceiling: how much could the 1280-token cap explain at most?
strict_by_prompt = {json.loads(l)["prompt"]: all(json.loads(l)["follow_instruction_list"]) for l in open(P("scored", "eval_results_strict.jsonl"))}
capped_fail = sum(not strict_by_prompt[g["prompt"]] for g in capped)
ceiling = (m["strict"]["n_prompts_correct"] + capped_fail) / m["strict"]["n_prompts"]
pct = lambda x: f"{100*x:.1f}"
card = 94.8
partial = "" if n == 541 else f" **PARTIAL: {n}/541 prompts**"
md = f"""# IFEval — InternScience/Agents-A1-4B, measured first-hand on this machine{partial}

Snapshot `945c40a4aa6f534d434a353207b8d42ecf7a5293`, plain `transformers` 5.16.1 `generate()`, bf16, 1x {gpu_name} (CUDA index {gpu_idx}).
Everything in this directory is on disk and re-runnable: `run_gen.sh` (generation, resume-by-id), `score_ifeval.py` (official scorer), `scorer_controls.py`, `make_results.py`.

## Result

| metric | measured (this run) | model card claim |
|---|---|---|
| prompt-level strict acc | **{pct(m['prompt_level_strict_acc'])}** ({m['strict']['n_prompts_correct']}/{m['strict']['n_prompts']}) | 94.8 (metric variant not stated) |
| prompt-level loose acc | **{pct(m['prompt_level_loose_acc'])}** ({m['loose']['n_prompts_correct']}/{m['loose']['n_prompts']}) | |
| instruction-level strict acc | **{pct(m['instruction_level_strict_acc'])}** ({m['strict']['n_instructions_correct']}/{m['strict']['n_instructions']}) | |
| instruction-level loose acc | **{pct(m['instruction_level_loose_acc'])}** ({m['loose']['n_instructions_correct']}/{m['loose']['n_instructions']}) | |

Prompts scored: {m['n_prompts_scored']} (of 541). Data: `data/input_data.jsonl` = google-research `instruction_following_eval/data/input_data.jsonl` (541 prompts, 834 instructions). Scorer: official `google-research/instruction_following_eval` code, vendored unmodified in `ifeval_scorer/` and invoked through its own `evaluation_main` (report in `scored/official_report.txt`, per-prompt verdicts in `scored/eval_results_{{strict,loose}}.jsonl`).

Difference vs the card's 94.8: prompt-strict {100*m['prompt_level_strict_acc']-card:+.1f}, prompt-loose {100*m['prompt_level_loose_acc']-card:+.1f}, instr-strict {100*m['instruction_level_strict_acc']-card:+.1f}, instr-loose {100*m['instruction_level_loose_acc']-card:+.1f} points. **Every one of the four metrics is more than 3 points below the card's number.** Truncation cannot close the gap: {capped_fail} of the {len(capped)} responses that hit the {settings['max_new_tokens']}-token cap fail prompt-level strict; even if all of them had passed, prompt-level strict would be at most {pct(ceiling)}.

## Exact generation settings

| setting | value |
|---|---|
| decoding | greedy (`do_sample=False`), `repetition_penalty=1.0`, no presence penalty |
| max_new_tokens | {settings['max_new_tokens']} |
| dtype / device | bfloat16 / cuda, `flash-linear-attention` 0.5.2 Triton kernels for the gated-delta-net layers, torch fallback for causal-conv1d |
| chat template | the snapshot's own `chat_template.jinja` via `tokenizer.apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)`; no system message supplied, so the template injects its built-in Intern-A1 system prompt (dated 2026-07-14) |
| thinking | **off** (`enable_thinking=False` -> prompt ends with an empty `<think>\\n\\n</think>` block); a `<think>...</think>` prefix, if any, is stripped before scoring — none occurred at the start of any response |
| seed | `torch.manual_seed({settings['seed']})` (irrelevant under greedy, set anyway) |
| batching | batch size {settings['batch_size']}, left padding, prompts sorted by token length |
| responses that hit the {settings['max_new_tokens']}-token cap | {n - n_fin}/{n} (scored as-is, truncated); of these, {len(loops)} are degenerate repetition loops by a simple heuristic (a 20-char window recurring >=4x in the last 400 chars), keys {loops[:12]}{'...' if len(loops) > 12 else ''} |
| spontaneous `<think>` emitted mid-answer despite thinking off | {len(spont_think)} response(s), keys {spont_think} (greedy continuation re-opened a `assistant\\n<think>` turn; scored as-is) |
| generated tokens per response | mean {statistics.mean(ntoks):.0f}, median {statistics.median(ntoks):.0f}, max {max(ntoks)} |

## Cost

Wall-clock {wall/60:.1f} min for {n} prompts ({sum(r['new_tokens'] for r in runs)} new tokens, {tok_per_s:.1f} tok/s aggregate, {n/wall:.3f} prompt/s), model load excluded; peak `torch.cuda.max_memory_allocated` {peak:.2f} GB on GPU {gpu_idx} (nvidia-smi showed ~13.3 GB incl. context/cache). Model load ~25 s. Run timestamps in `gen.log`.

## Deviations from the model card — read before comparing numbers

* **The card does not say how its 94.8 was produced.** It gives no decoding settings for IFEval, does not say which of the four IFEval metrics 94.8 is (prompt/instruction x strict/loose), and does not say whether thinking mode was on. Its general recommendation is *sampling* (`temperature=0.85, top_p=0.95, top_k=20, presence_penalty=1.1`, README lines 352-361) served through vLLM/SGLang with a reasoning parser. I ran **greedy**, **thinking off**, **max_new_tokens={settings['max_new_tokens']}**, **plain transformers**. So this is *not* a reproduction of their setting; it is an independent measurement under a stated, deterministic setting. Thinking was turned off because with the template's default thinking mode a {settings['max_new_tokens']}-token budget would mostly be spent inside `<think>` and truncated answers would score near zero; a thinking-mode run with a much larger budget was not attempted.
* The card's note (README line ~393) says numbers for *other* models are copied from their technical reports and that their own were produced with the `Agents-A1/evaluation` framework; that framework was not used here (GitHub is unreachable from this node except raw file fetches).
* Data: the HF `google/IFEval` copy differs from the google-research copy in exactly one record (key 2785, prompt says "at least one placeholder" vs "at least 3 placeholders"; `kwargs` identical). The google-research copy was used because it is what the vendored scorer ships with (`data/hf_vs_google_diff.txt`).
* Environment shims that do not change the scorer's logic: files placed in a package dir (import path only); `nltk` pinned to 3.8.1 because nltk 3.10 refuses the punkt pickle the official code loads; punkt data pulled from an HF mirror of `nltk_data` (hashes in `env.txt`).

## Scorer controls (run before trusting the table)

**Negative control** (`controls/negative_*`): 20 prompts; 10 given an empty response, 10 given the prompt echoed back verbatim.
Result: prompt-level strict {pct(neg['prompt_level_strict_acc'])}%, instruction-level strict {pct(neg['instruction_level_strict_acc'])}% (loose identical). Breakdown:

```
{negbd}
```
Empty responses score exactly 0. The two echo "passes" are the prompt text itself satisfying a constraint it states (the prompt contains the required keywords / the `P.S.` marker and paragraph breaks / is longer than the required minimum word count) — a property of the benchmark, not a scorer bug.

**Positive control** (`controls/positive_*`): 5 hand-written, obviously compliant answers to single-instruction prompts (`punctuation:no_comma`, `change_case:english_lowercase`, `startend:quotation`, `detectable_format:title`, `startend:end_checker`). Result: prompt-level strict {pct(pos['prompt_level_strict_acc'])}%, instruction-level strict {pct(pos['instruction_level_strict_acc'])}% (5/5).

**Batch-invariance check** (free by-product of an aborted first launch at batch size 48, `generations_bs48_partial.jsonl`): the same {len(shared)} prompts generated at batch 48 vs the final batch-{settings['batch_size']} run are byte-identical for {ident}/{len(shared)} responses; scored on those {len(shared)} prompts: prompt-strict {pct(s48['prompt_level_strict_acc'])} (bs48) vs {pct(s24['prompt_level_strict_acc'])} (bs{settings['batch_size']}), instr-strict {pct(s48['instruction_level_strict_acc'])} vs {pct(s24['instruction_level_strict_acc'])} — i.e. {s48['strict']['n_prompts_correct']} vs {s24['strict']['n_prompts_correct']} prompts and {s48['strict']['n_instructions_correct']} vs {s24['strict']['n_instructions_correct']} instructions correct out of {s48['strict']['n_prompts']}/{s48['strict']['n_instructions']}. So bf16 greedy decoding with left-padded batching is **not** bit-exact across batch compositions here (most responses diverge somewhere after the first tokens), and a re-run with a different batch size should be expected to move the headline numbers by on the order of a point. "Deterministic" in this report means: same script, same batch size, same GPU class reproduces `generations.jsonl` — not that the number is invariant to batching.

{det_md}

## Per-category instruction-level accuracy (strict)

| category | acc |
|---|---|
""" + "\n".join(f"| {k} | {pct(v)} |" for k, v in m["strict"]["per_category_instruction_acc"].items()) + f"""

## Model card claim, verbatim

```
{claim.strip()}
```

## Files

`gen_ifeval.py` / `run_gen.sh` (generation), `generations.jsonl` (one line per prompt: key, prompt, response, raw_response, n_new_tokens, finished, seed, settings), `score_ifeval.py`, `scored/metrics.json`, `scored/official_report.txt`, `scored/eval_results_strict.jsonl`, `scored/eval_results_loose.jsonl`, `scorer_controls.py`, `controls/`, `env.txt` (pip freeze, nvidia-smi, snapshot + file hashes), `gen.log`, `model_card_claim.txt`, `ifeval_scorer/` (vendored official scorer).
"""
open(P("RESULTS.md"), "w").write(md)
print(md[:2500])
