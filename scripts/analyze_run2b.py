#!/usr/bin/env python
"""Run-2b analysis, implementing PREREG_run2b_analysis.md (sha db2b189ac606c473) exactly.

PRIMARY  : McNemar exact two-sided, prompt-level strict, paired by key, run 1 vs run 2b (unclosed INCLUDED).
SECONDARY: standalone Clopper-Pearson 95% CI on run 2b.
Power rule: <50 completed pairs -> verdict "UNDERPOWERED" (never "no difference").
Sensitivity: same paired test with unclosed-</think> prompts EXCLUDED.
"""
import json, os, subprocess, sys, hashlib
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__)); P = lambda *a: os.path.join(HERE, *a)

for f, pre in [("PREREG_run2.md", "a7b616ee0f881fff"), ("PREREG_run2b.md", "326455ea25c5dd7a"),
               ("PREREG_run2b_analysis.md", "db2b189ac606c473")]:
    h = hashlib.sha256(open(P(f), "rb").read()).hexdigest()
    assert h.startswith(pre), f"{f} CHANGED: {h}"

def clopper_pearson(k, n, alpha=0.05):
    """Exact binomial CI without scipy: invert the beta quantiles by bisection on the binomial tail."""
    if n == 0: return (float("nan"), float("nan"))
    def binom_cdf(p, k, n): return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(0, k+1))
    lo, hi = 0.0, 0.0
    if k > 0:  # P(X>=k) = alpha/2  ->  1-cdf(k-1) = alpha/2
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a+b)/2
            if 1 - binom_cdf(m, k-1, n) < alpha/2: a = m
            else: b = m
        lo = (a+b)/2
    if k < n:  # P(X<=k) = alpha/2
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a+b)/2
            if binom_cdf(m, k, n) > alpha/2: a = m
            else: b = m
        hi = (a+b)/2
    else: hi = 1.0
    return lo, hi

def mcnemar_exact(b, c):
    """Two-sided exact McNemar: binomial(b+c, 0.5) tail, doubled, capped at 1."""
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k+1)) / 2**n
    return min(1.0, 2*p)

def main():
    gens = [json.loads(l) for l in open(P("generations_run2b.jsonl")) if l.strip()]
    n_done = len(gens)
    if n_done == 0: sys.exit("no run-2b generations yet")
    if not os.path.exists(P("scored_run2b", "metrics.json")):
        subprocess.run([sys.executable, P("score_ifeval.py"), "--responses", P("generations_run2b.jsonl"),
                        "--out_dir", P("scored_run2b"), "--restrict"], check=True)
    m2b = json.load(open(P("scored_run2b", "metrics.json")))
    r1 = {json.loads(l)["prompt"]: all(json.loads(l)["follow_instruction_list"])
          for l in open(P("scored", "eval_results_strict.jsonl"))}
    r2 = {json.loads(l)["prompt"]: all(json.loads(l)["follow_instruction_list"])
          for l in open(P("scored_run2b", "eval_results_strict.jsonl"))}
    closed = {g["prompt"]: g["think_closed"] for g in gens}
    out = {}
    for label, keep in [("included", lambda p: True), ("excluded_unclosed", lambda p: closed[p])]:
        ps = [p for p in r2 if keep(p)]
        b = sum(1 for p in ps if r1[p] and not r2[p])   # run1 pass, run2b fail
        c = sum(1 for p in ps if not r1[p] and r2[p])   # run1 fail, run2b pass
        both = sum(1 for p in ps if r1[p] and r2[p]); neither = sum(1 for p in ps if not r1[p] and not r2[p])
        k2 = sum(r2[p] for p in ps); k1 = sum(r1[p] for p in ps)
        lo, hi = clopper_pearson(k2, len(ps))
        out[label] = dict(n_pairs=len(ps), b_run1pass_run2bfail=b, c_run1fail_run2bpass=c,
                          both_pass=both, neither_pass=neither, discordant=b+c,
                          run1_acc_on_these=k1/len(ps) if ps else float("nan"),
                          run2b_acc=k2/len(ps) if ps else float("nan"),
                          run2b_ci95=[lo, hi], mcnemar_exact_p=mcnemar_exact(b, c),
                          underpowered=len(ps) < 50, ci_reaches_94_8=hi*100 >= 94.8)
    res = dict(n_completed=n_done, n_of_planned=80,
               unclosed_think=sum(1 for g in gens if not g["think_closed"]),
               metrics_run2b={k: m2b[k] for k in ["prompt_level_strict_acc", "prompt_level_loose_acc",
                                                  "instruction_level_strict_acc", "instruction_level_loose_acc"]},
               primary_included=out["included"], sensitivity_excluded_unclosed=out["excluded_unclosed"],
               prereg=["PREREG_run2.md a7b616ee", "PREREG_run2b.md 326455ea", "PREREG_run2b_analysis.md db2b189a"])
    v = out["included"]
    res["verdict"] = ("UNDERPOWERED: fewer than 50 completed pairs; no conclusion about the card's 94.8 may be "
                      "drawn from the paired test. This is 'underpowered', NOT 'no difference'."
                      if v["underpowered"] else
                      f"Paired test has adequate n ({v['n_pairs']} pairs). McNemar exact p={v['mcnemar_exact_p']:.4f}. "
                      f"Note this tests run 2b vs run 1 (joint effect of thinking mode AND decoding), not against 94.8; "
                      f"the card's number is reached only if the CI reaches it (CI upper = {100*v['run2b_ci95'][1]:.1f}).")
    json.dump(res, open(P("run2b_analysis.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))

if __name__ == "__main__":
    main()
