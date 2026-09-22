#!/usr/bin/env python
"""Score generations with the vendored official IFEval scorer, unmodified.

The official scorer keys on the prompt string and scores every record in its
input_data file, so scoring a subsample means handing it a subsample input file
rather than filtering afterwards - filtering afterwards would divide by 541.

Writes metrics.json in the same shape as results/metrics_run1.json, plus a
per-prompt table, which is the thing whose absence made the run-1 and run-2b
comparisons impossible to recompute.
"""
import argparse, collections, csv, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True, help="generations jsonl (key, prompt, response)")
    ap.add_argument("--input-data", default=os.path.join(ROOT, "data", "input_data.jsonl"))
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--restrict", action="store_true",
                    help="score only the keys present in --responses")
    args = ap.parse_args()

    # The scorer subprocess runs with cwd set to the vendored package, so every
    # path handed to it has to be absolute or it resolves against the wrong root.
    args.out_dir = os.path.abspath(args.out_dir)
    os.makedirs(args.out_dir, exist_ok=True)
    gens = [json.loads(l) for l in open(args.responses, encoding="utf-8") if l.strip()]
    keys = [g["key"] for g in gens]
    if len(set(keys)) != len(keys):
        sys.exit(f"duplicate keys in {args.responses}")
    have = set(keys)

    rows = [json.loads(l) for l in open(args.input_data, encoding="utf-8") if l.strip()]
    if args.restrict:
        rows = [r for r in rows if r["key"] in have]
    if len(rows) != len(gens):
        sys.exit(f"{len(rows)} input records but {len(gens)} responses - "
                 f"pass --restrict, or the generation is incomplete")

    inp = os.path.join(args.out_dir, "input_data_scored.jsonl")
    resp = os.path.join(args.out_dir, "responses.jsonl")
    with open(inp, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(resp, "w", encoding="utf-8") as fh:
        for g in gens:
            fh.write(json.dumps({"prompt": g["prompt"], "response": g["response"]},
                                ensure_ascii=False) + "\n")

    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "ifeval_scorer"))
    proc = subprocess.run(
        [sys.executable, "-m", "instruction_following_eval.evaluation_main",
         f"--input_data={inp}", f"--input_response_data={resp}",
         f"--output_dir={args.out_dir}"],
        cwd=os.path.join(ROOT, "ifeval_scorer"), env=env,
        capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"scorer failed ({proc.returncode}):\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")

    metrics = {"n_prompts_scored": len(gens), "n_prompts_in_input_data": len(rows)}
    per_prompt = {}
    for mode in ("strict", "loose"):
        outs = [json.loads(l) for l in
                open(os.path.join(args.out_dir, f"eval_results_{mode}.jsonl"), encoding="utf-8")
                if l.strip()]
        n_prompts_correct = sum(o["follow_all_instructions"] for o in outs)
        flat = [(i, ok) for o in outs for i, ok in
                zip(o["instruction_id_list"], o["follow_instruction_list"])]
        by_cat = collections.defaultdict(list)
        for iid, ok in flat:
            by_cat[iid.split(":")[0]].append(ok)
        metrics[mode] = {
            "prompt_level_acc": n_prompts_correct / len(outs),
            "instruction_level_acc": sum(ok for _i, ok in flat) / len(flat),
            "n_prompts": len(outs),
            "n_prompts_correct": n_prompts_correct,
            "n_instructions": len(flat),
            "n_instructions_correct": sum(ok for _i, ok in flat),
            "per_category_instruction_acc": {k: sum(v) / len(v) for k, v in sorted(by_cat.items())},
        }
        metrics[f"prompt_level_{mode}_acc"] = metrics[mode]["prompt_level_acc"]
        metrics[f"instruction_level_{mode}_acc"] = metrics[mode]["instruction_level_acc"]
        prompt_to_key = {g["prompt"]: g["key"] for g in gens}
        for o in outs:
            k = prompt_to_key[o["prompt"]]
            per_prompt.setdefault(k, {"key": k})[mode] = int(o["follow_all_instructions"])

    for g in gens:
        row = per_prompt[g["key"]]
        row["n_new_tokens"] = g["n_new_tokens"]
        row["finished"] = int(g["finished"])
        row["think_closed"] = int(g.get("think_closed", 1))
        row["instruction_ids"] = "|".join(g["instruction_id_list"])

    table = os.path.join(args.out_dir, "per_prompt.csv")
    cols = ["key", "strict", "loose", "n_new_tokens", "finished", "think_closed", "instruction_ids"]
    with open(table, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for k in sorted(per_prompt, key=lambda x: int(x)):
            w.writerow({c: per_prompt[k][c] for c in cols})

    with open(os.path.join(args.out_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=1)
    print(f"{len(gens)} prompts  strict {metrics['prompt_level_strict_acc']*100:.2f}%  "
          f"loose {metrics['prompt_level_loose_acc']*100:.2f}%  -> {args.out_dir}")
    print(f"per-prompt table: {table}")


if __name__ == "__main__":
    main()
