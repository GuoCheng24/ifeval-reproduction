#!/usr/bin/env python
"""Assemble RESULTS_run2.md: three arms side by side, from on-disk artifacts only."""
import json, os, re, statistics, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, *a)
for f, pre in [("PREREG_run2.md","a7b616ee0f881fff"),("PREREG_run2b.md","326455ea25c5dd7a"),
               ("PREREG_run2b_analysis.md","db2b189ac606c473")]:
    h=hashlib.sha256(open(P(f),"rb").read()).hexdigest(); assert h.startswith(pre), f"{f} CHANGED {h}"

m1=json.load(open(P("scored","metrics.json")))
m2a=json.load(open(P("scored_run2","metrics.json")))
m2b=json.load(open(P("scored_run2b","metrics.json")))
an=json.load(open(P("run2b_analysis.json")))
g2a=[json.loads(l) for l in open(P("generations_run2.jsonl"))]
g2b=[json.loads(l) for l in open(P("generations_run2b.jsonl"))]
def stats(g,budget):
    cl=[x for x in g if x["think_closed"]]
    return dict(n=len(g),closed=len(cl),rate=len(cl)/len(g),
                mean_tok=statistics.mean(x["n_new_tokens"] for x in g),
                med_closed=statistics.median([x["n_new_tokens"] for x in cl]) if cl else float("nan"),
                cap=sum(1 for x in g if x["n_new_tokens"]>=budget))
s2a=stats(g2a,4096); s2b=stats(g2b,16384)
runs2b=[json.loads(x) for x in re.findall(r"\{.*?\n\}", open(P("generations_run2b.jsonl.runstats.json")).read(), flags=re.S)] if os.path.exists(P("generations_run2b.jsonl.runstats.json")) else []
pc=lambda x:f"{100*x:.1f}"
pri=an["primary_included"]; sen=an["sensitivity_excluded_unclosed"]
ci=lambda d:f"[{100*d['run2b_ci95'][0]:.1f}, {100*d['run2b_ci95'][1]:.1f}]"
md=f"""# IFEval — Agents-A1-4B: three arms measured on this machine

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
| prompt-level strict | **{pc(m1['prompt_level_strict_acc'])}** | {pc(m2a['prompt_level_strict_acc'])} | {pc(m2b['prompt_level_strict_acc'])} {ci(pri)} |
| prompt-level loose | {pc(m1['prompt_level_loose_acc'])} | {pc(m2a['prompt_level_loose_acc'])} | {pc(m2b['prompt_level_loose_acc'])} |
| instruction-level strict | {pc(m1['instruction_level_strict_acc'])} | {pc(m2a['instruction_level_strict_acc'])} | {pc(m2b['instruction_level_strict_acc'])} |
| instruction-level loose | {pc(m1['instruction_level_loose_acc'])} | {pc(m2a['instruction_level_loose_acc'])} | {pc(m2b['instruction_level_loose_acc'])} |
| **model card claim** | 94.8 (metric variant, decoding and thinking budget all unstated) |||

Only **run 1 is a complete measurement of the benchmark.** Runs 2a and 2b are partial by cost cap; their
percentages are computed on 12 and 32 prompts respectively and carry the uncertainty shown.

## The comparison that matters, and the trap in it

Run 2b scores {pc(m2b['prompt_level_strict_acc'])} and run 1 scores {pc(m1['prompt_level_strict_acc'])} overall, which invites "thinking mode gains ~11 points".
**That reading is wrong.** Run 1 scores **{pc(pri['run1_acc_on_these'])} on the very same {pri['n_pairs']} prompts** — the run-2b subsample is
easier than the full 541, not the arm better. The pre-registered paired test (McNemar exact, two-sided,
paired by prompt key) on those {pri['n_pairs']} pairs:

- discordant pairs: b (run 1 pass, run 2b fail) = **{pri['b_run1pass_run2bfail']}**, c (run 1 fail, run 2b pass) = **{pri['c_run1fail_run2bpass']}**; concordant {pri['both_pass']} both pass, {pri['neither_pass']} neither
- **exact two-sided p = {pri['mcnemar_exact_p']:.3f}**
- sensitivity, unclosed-`</think>` prompts excluded (n={sen['n_pairs']}): b={sen['b_run1pass_run2bfail']}, c={sen['c_run1fail_run2bpass']}, p={sen['mcnemar_exact_p']:.3f}, run 2b {pc(sen['run2b_acc'])} {ci(sen)} vs run 1 {pc(sen['run1_acc_on_these'])} on the same prompts

### Verdict, as pre-registered

**{an['verdict']}**

With {pri['n_pairs']} completed pairs (< 50), the paired test is **underpowered**. It has **not** shown that thinking mode
makes no difference; it has shown that this many pairs cannot resolve a difference of the size at issue.
Separately, and also pre-registered: McNemar compares run 2b with run 1 — it is **not** a test against 94.8.
Run 2b's 95% CI is {ci(pri)}, which **contains 94.8**, so by the pre-stated rule this arm does not
distinguish our measurement from the card's number in either direction.

## First-class finding: the model needs far more than a 4k thinking budget

| arm | budget | closed `</think>` | median tokens (closed responses) | hit the cap |
|---|---|---|---|---|
| run 2a | 4096 | **{s2a['closed']}/{s2a['n']} ({100*s2a['rate']:.0f}%)** | {s2a['med_closed']:.0f} | {s2a['cap']}/{s2a['n']} |
| run 2b | 16384 | **{s2b['closed']}/{s2b['n']} ({100*s2b['rate']:.0f}%)** | {s2b['med_closed']:.0f} | {s2b['cap']}/{s2b['n']} |

At a 4096-token budget this model fails to close its reasoning on **{100*(1-s2a['rate']):.0f}%** of IFEval prompts, and run 2a's
score ({pc(m2a['prompt_level_strict_acc'])}) largely measures that truncation rather than instruction-following. Raising the budget to
16384 lifts closure to {100*s2b['rate']:.0f}%. This is a deployment-relevant fact in its own right: serving this model with a
4k output budget silently truncates most of its answers mid-reasoning. It is also why `PREREG_run2b.md` was
written — the 4096 budget in the original pre-registration was my coordinator's design defect, identified
from batch-1 token counts before any run-2 score existed.

## Cost and what stopped the runs

Run 2b: {sum(r['new_tokens'] for r in runs2b) if runs2b else 'n/a'} new tokens at ~{statistics.mean([r['tok_per_s'] for r in runs2b]) if runs2b else float('nan'):.1f} tok/s, peak torch memory {max([r['peak_mem_GB'] for r in runs2b]) if runs2b else float('nan'):.2f} GB
(max observed `nvidia-smi` 18257 MiB, under the 20 GB cap), 4 batches of 8 in ~2h35m on one RTX 4090 (GPU 1 only).
The pre-registered 3-hour cap from the original 12:38 launch expired at **15:38 and stopped generation by PID**
with 32 of 80 prompts done; completed rows were preserved. Decoding 16384 tokens is sequential, so a larger
batch was the only speed-up available and it would have breached the memory cap.

## What all of this can and cannot settle

**Can**: run 1 is a complete, reproducible IFEval measurement of this snapshot under a fully stated
deterministic setting — prompt-strict {pc(m1['prompt_level_strict_acc'])}, prompt-loose {pc(m1['prompt_level_loose_acc'])}, instruction-strict {pc(m1['instruction_level_strict_acc'])}, instruction-loose {pc(m1['instruction_level_loose_acc'])}
on all 541 prompts, with the official scorer and controls that were seen failing (empty responses 0/10,
prompt echo 2/10 with each pass traced, hand-written compliant answers 5/5). The token-budget finding above
is solid in both arms.

**Cannot**: none of the three arms establishes the card's 94.8, and none refutes it. Run 2b's CI contains
94.8; run 2a is far too small; run 1 differs from the card's own recommended setting. The honest sentence is
that **we could not reproduce 94.8 under the settings we could afford on one shared 4090**. The factors we
did not control are: thinking budget (the card states none; 16384 was still not enough for {s2b['n']-s2b['closed']}/{s2b['n']} responses),
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
"""
open(P("RESULTS_run2.md"),"w").write(md); print(md[:1500])
