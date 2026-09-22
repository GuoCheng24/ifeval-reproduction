#!/usr/bin/env python
"""Run-3 analysis, implementing PREREG_run3.md and its addendum exactly.

Four arms, all on idle 46 GB L40s, no memory cap and no time cap:

  3a  thinking ON,  the 80 pre-registered keys, 16384 budget, batch 16
  3b  thinking ON,  the same 80 keys,           16384 budget, batch  8
  3c  thinking OFF, all 541, greedy, 1280 budget, batch 24   (run 1's settings)
  3d  thinking OFF, identical repeat of 3c on a second L40   (the control)

Comparisons, in the order the pre-registration states them:

  PRIMARY      3a alone, n=80, Clopper-Pearson 95% CI, against the card's 94.8
  PAIRED       3a vs 3c on the same 80 keys, exact McNemar  (thinking ON vs OFF)
  BATCH        3a vs 3b - identical in everything the benchmark calls a setting
  DETERMINISM  3c vs 3d - same machine, same settings, greedy
  HARDWARE     3c vs run 1 - aggregate only; run 1's per-prompt record is gone
"""
import csv, hashlib, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from stats import clopper_pearson, mcnemar_exact  # noqa: E402

P = lambda *a: os.path.join(ROOT, *a)
CARD = 94.8

# The pre-registration was redacted after publication to remove a machine name -
# a six-character in-place substitution, recorded byte for byte in
# prereg/REDACTION.md along with the hash it was originally sealed under. This
# asserts the post-redaction hash; the original is in that file.
for name, prefix in [("PREREG_run3.md", "56a2b22e39b7741d")]:
    with open(P("prereg", name), "rb") as fh:
        h = hashlib.sha256(fh.read()).hexdigest()
    assert h.startswith(prefix), f"{name} CHANGED: {h}"


def load(arm):
    d = P(f"scored_run{arm}")
    if not os.path.exists(os.path.join(d, "metrics.json")):
        return None
    with open(os.path.join(d, "metrics.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    with open(os.path.join(d, "per_prompt.csv"), encoding="utf-8") as fh:
        rows = {r["key"]: r for r in csv.DictReader(fh)}
    return {"metrics": m, "rows": rows}


def texts(path):
    if not os.path.exists(P(path)):
        return {}
    out = {}
    with open(P(path), encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                out[str(r["key"])] = r["response"]
    return out


def pct(x):
    return f"{100 * x:.2f}"


def paired(a, b, label, out):
    keys = sorted(set(a["rows"]) & set(b["rows"]), key=int)
    bb = sum(1 for k in keys if a["rows"][k]["strict"] == "1" and b["rows"][k]["strict"] == "0")
    cc = sum(1 for k in keys if a["rows"][k]["strict"] == "0" and b["rows"][k]["strict"] == "1")
    p = mcnemar_exact(bb, cc)
    ka = sum(1 for k in keys if a["rows"][k]["strict"] == "1")
    kb = sum(1 for k in keys if b["rows"][k]["strict"] == "1")
    lo_a, hi_a = clopper_pearson(ka, len(keys))
    lo_b, hi_b = clopper_pearson(kb, len(keys))
    rec = {
        "n_pairs": len(keys), "b": bb, "c": cc, "mcnemar_exact_p": p,
        "first": {"n_correct": ka, "acc": ka / len(keys), "ci": [lo_a, hi_a]},
        "second": {"n_correct": kb, "acc": kb / len(keys), "ci": [lo_b, hi_b]},
        "points_difference": 100 * (ka - kb) / len(keys),
    }
    out[label] = rec
    print(f"\n── {label}  (n={len(keys)} paired prompts)")
    print(f"   first  {ka}/{len(keys)} = {pct(ka/len(keys))}%  CI [{pct(lo_a)}, {pct(hi_a)}]")
    print(f"   second {kb}/{len(keys)} = {pct(kb/len(keys))}%  CI [{pct(lo_b)}, {pct(hi_b)}]")
    print(f"   discordant b={bb} c={cc}   exact two-sided McNemar p = {p:.4f}")
    print(f"   difference {rec['points_difference']:+.2f} points")
    return keys


def main():
    arms = {a: load(a) for a in ("3a", "3b", "3c", "3d")}
    have = [a for a, v in arms.items() if v]
    print(f"arms scored: {', '.join(have) or 'none'}")
    out = {"arms_scored": have, "card_claim": CARD}

    for a in have:
        m = arms[a]["metrics"]
        n = m["strict"]["n_prompts"]
        k = m["strict"]["n_prompts_correct"]
        lo, hi = clopper_pearson(k, n)
        out[f"run{a}"] = {
            "n_prompts": n, "n_correct": k,
            "prompt_level_strict_acc": m["prompt_level_strict_acc"],
            "prompt_level_loose_acc": m["prompt_level_loose_acc"],
            "instruction_level_strict_acc": m["instruction_level_strict_acc"],
            "instruction_level_loose_acc": m["instruction_level_loose_acc"],
            "ci95_prompt_level_strict": [lo, hi],
            "ci_excludes_card": not (lo * 100 <= CARD <= hi * 100),
        }
        toks = [int(r["n_new_tokens"]) for r in arms[a]["rows"].values()]
        unclosed = sum(1 for r in arms[a]["rows"].values() if r["think_closed"] == "0")
        out[f"run{a}"].update({
            "median_new_tokens": statistics.median(toks),
            "max_new_tokens": max(toks),
            "unclosed_think": unclosed,
        })
        print(f"\n== run {a}: {k}/{n} strict = {pct(k/n)}%  CI [{pct(lo)}, {pct(hi)}]"
              f"  -> CI {'EXCLUDES' if out[f'run{a}']['ci_excludes_card'] else 'contains'} {CARD}")
        print(f"   loose {pct(m['prompt_level_loose_acc'])}%  "
              f"instruction strict {pct(m['instruction_level_strict_acc'])}%  "
              f"median tokens {statistics.median(toks)}  unclosed </think> {unclosed}/{n}")

    if arms["3a"] and arms["3c"]:
        paired(arms["3a"], arms["3c"], "PAIRED thinking ON (3a) vs OFF (3c), same 80 keys", out)
    if arms["3a"] and arms["3b"]:
        keys = paired(arms["3a"], arms["3b"], "BATCH 16 (3a) vs batch 8 (3b), everything else identical", out)
        ta, tb = texts("generations_run3a_n80_bs16.jsonl"), texts("generations_run3b_n80_bs8.jsonl")
        same = sum(1 for k in keys if k in ta and k in tb and ta[k] == tb[k])
        out["BATCH 16 (3a) vs batch 8 (3b), everything else identical"]["byte_identical_responses"] = same
        print(f"   byte-identical responses: {same}/{len(keys)}")
    if arms["3c"] and arms["3d"]:
        keys = paired(arms["3c"], arms["3d"], "DETERMINISM 3c vs 3d, same machine, same settings, greedy", out)
        tc, td = texts("generations_run3c_full541.jsonl"), texts("generations_run3d_full541.jsonl")
        same = sum(1 for k in keys if k in tc and k in td and tc[k] == td[k])
        out["DETERMINISM 3c vs 3d, same machine, same settings, greedy"]["byte_identical_responses"] = same
        print(f"   byte-identical responses: {same}/{len(keys)}")

    # The scorer's own spread, measured by scoring one unchanged file ten times
    # (scripts/scorer_noise.py). Any arm-to-arm difference below this is not a
    # finding about the arms. Two of 541 prompts do not score the same every
    # time, and one of them is inside the 80-key subsample, where a single
    # flipped prompt is worth 1.25 points.
    noise_path = P("results", "scorer_noise.json")
    noise = None
    if os.path.exists(noise_path):
        with open(noise_path, encoding="utf-8") as fh:
            noise = json.load(fh)
        out["scorer_noise"] = noise
        print("\n── SCORER NOISE (one unchanged file scored "
              f"{noise['n_scorings']} times)")
        for m, v in noise["metrics"].items():
            print(f"   {m:<30} spread {v['spread_points']:.3f} points")
        print(f"   {len(noise['prompts_whose_outcome_is_not_stable'])} of "
              f"{noise['n_prompts']} prompts are not stable: "
              f"{', '.join(noise['prompts_whose_outcome_is_not_stable'])}")

    if arms["3c"]:
        with open(P("results", "metrics_run1.json"), encoding="utf-8") as fh:
            r1 = json.load(fh)
        m3 = arms["3c"]["metrics"]
        rows = []
        for field in ("prompt_level_strict_acc", "prompt_level_loose_acc",
                      "instruction_level_strict_acc", "instruction_level_loose_acc"):
            rows.append((field, r1[field], m3[field], 100 * (m3[field] - r1[field])))
        out["HARDWARE run 1 (RTX 4090) vs 3c (L40), aggregate only"] = {
            "note": "run 1's per-prompt record was not preserved; only aggregates can be compared",
            "metrics": {f: {"run1": a, "run3c": b, "points": d} for f, a, b, d in rows},
            "per_category_strict": {
                k: {"run1": r1["strict"]["per_category_instruction_acc"][k],
                    "run3c": m3["strict"]["per_category_instruction_acc"][k],
                    "points": 100 * (m3["strict"]["per_category_instruction_acc"][k]
                                     - r1["strict"]["per_category_instruction_acc"][k])}
                for k in sorted(m3["strict"]["per_category_instruction_acc"])
                if k in r1["strict"]["per_category_instruction_acc"]},
        }
        print("\n── HARDWARE run 1 (RTX 4090, machine-a) vs run 3c (L40, machine-b), aggregate only")
        for field, a, b, d in rows:
            verdict = ""
            if noise:
                sp = noise["metrics"][field]["spread_points"]
                verdict = ("  BELOW the scorer's own spread "
                           f"({sp:.2f}) - not a hardware finding"
                           if abs(d) <= sp else
                           f"  {abs(d)/sp:.1f}x the scorer's spread ({sp:.2f})")
            print(f"   {field:<30} {pct(a)}%  ->  {pct(b)}%   {d:+.2f} points{verdict}")
            if noise:
                out["HARDWARE run 1 (RTX 4090) vs 3c (L40), aggregate only"]["metrics"][field][
                    "scorer_spread_points"] = noise["metrics"][field]["spread_points"]
                out["HARDWARE run 1 (RTX 4090) vs 3c (L40), aggregate only"]["metrics"][field][
                    "exceeds_scorer_noise"] = abs(d) > noise["metrics"][field]["spread_points"]
        print("   run 1's per-prompt record was not preserved, so this is aggregate-only,")
        print("   and run 1's figure is a single scoring, not a median over scorings.")

    with open(P("results", "metrics_run3.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote results/metrics_run3.json")


if __name__ == "__main__":
    main()
