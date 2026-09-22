#!/usr/bin/env python
"""How much does the official IFEval scorer move when nothing moves?

Arms 3c and 3d produced byte-identical generations for all 541 prompts, and
their instruction-level scores still differed. That cannot come from the model,
so it comes from the scorer: `instructions.py` calls `langdetect`, which seeds
itself from a global random state, and a few instructions are decided by it.

This scores one unchanged file N times and reports the spread per metric. Any
difference between two arms that is smaller than the spread here is not a
finding about those arms.
"""
import argparse, collections, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS = ["prompt_level_strict_acc", "prompt_level_loose_acc",
           "instruction_level_strict_acc", "instruction_level_loose_acc"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "scorer_noise.json"))
    args = ap.parse_args()

    runs, per_prompt = [], collections.defaultdict(list)
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(args.n):
            d = os.path.join(tmp, f"s{i}")
            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "score_ifeval.py"),
                 "--responses", args.responses, "--out-dir", d],
                capture_output=True, text=True)
            if proc.returncode != 0:
                sys.exit(f"scoring pass {i} failed:\n{proc.stdout[-1500:]}\n{proc.stderr[-1500:]}")
            with open(os.path.join(d, "metrics.json"), encoding="utf-8") as fh:
                runs.append(json.load(fh))
            import csv
            with open(os.path.join(d, "per_prompt.csv"), encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    per_prompt[r["key"]].append((r["strict"], r["loose"]))

    out = {"responses": os.path.basename(args.responses), "n_scorings": args.n, "metrics": {}}
    print(f"{os.path.basename(args.responses)}, scored {args.n} times\n")
    for m in METRICS:
        vals = [100 * r[m] for r in runs]
        out["metrics"][m] = {"min": min(vals), "max": max(vals),
                             "spread_points": max(vals) - min(vals),
                             "distinct_values": sorted(set(round(v, 4) for v in vals))}
        print(f"  {m:<30} {min(vals):7.3f} .. {max(vals):7.3f}   "
              f"spread {max(vals)-min(vals):.3f} points   "
              f"{len(set(round(v,4) for v in vals))} distinct value(s)")

    unstable = {k: v for k, v in per_prompt.items() if len(set(v)) > 1}
    out["prompts_whose_outcome_is_not_stable"] = sorted(unstable, key=int)
    out["n_prompts"] = len(per_prompt)
    print(f"\n  {len(unstable)} of {len(per_prompt)} prompts do not score the same every time: "
          f"{', '.join(sorted(unstable, key=int)[:12]) or 'none'}")
    print("\n  Any difference between two arms smaller than the spread above is not a\n"
          "  finding about those arms. The prompt-level strict column is the one this\n"
          "  repository's primary comparison uses.")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {os.path.relpath(args.out, ROOT)}")


if __name__ == "__main__":
    main()
