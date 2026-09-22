#!/usr/bin/env python
"""The two exact tests this repository uses, in one place.

They were written inline in `analyze_run2b.py` first. Keeping a second copy in
`analyze_run3.py` is how two scripts end up disagreeing about a p-value, so they
live here and both import them.

Run this file to check the functions against the numbers already published in
`results/RESULTS_run2.md`. If the refactor changed anything, the self-test says
so rather than the reader finding out.
"""
from math import comb

__all__ = ["clopper_pearson", "mcnemar_exact"]


def clopper_pearson(k, n, alpha=0.05):
    """Exact binomial CI without scipy: invert the binomial tails by bisection."""
    if n == 0:
        return (float("nan"), float("nan"))

    def binom_cdf(p, k, n):
        return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))

    lo, hi = 0.0, 0.0
    if k > 0:                      # P(X>=k) = alpha/2  ->  1 - cdf(k-1) = alpha/2
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if 1 - binom_cdf(m, k - 1, n) < alpha / 2:
                a = m
            else:
                b = m
        lo = (a + b) / 2
    if k < n:                      # P(X<=k) = alpha/2
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if binom_cdf(m, k, n) > alpha / 2:
                a = m
            else:
                b = m
        hi = (a + b) / 2
    else:
        hi = 1.0
    return lo, hi


def mcnemar_exact(b, c):
    """Two-sided exact McNemar: binomial(b+c, 0.5) tail, doubled, capped at 1."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


if __name__ == "__main__":
    # Targets are the figures printed in results/RESULTS_run2.md, which were
    # produced by the inline copies these functions replace.
    checks = []
    lo, hi = clopper_pearson(28, 32)
    checks.append(("run 2b CI [71.0, 96.5]", (round(lo * 100, 1), round(hi * 100, 1)) == (71.0, 96.5)))
    lo, hi = clopper_pearson(26, 28)
    checks.append(("sensitivity CI [76.5, 99.1]", (round(lo * 100, 1), round(hi * 100, 1)) == (76.5, 99.1)))
    checks.append(("McNemar b=2 c=2 -> 1.000", round(mcnemar_exact(2, 2), 3) == 1.000))
    checks.append(("McNemar b=0 c=2 -> 0.500", round(mcnemar_exact(0, 2), 3) == 0.500))
    # and a deliberately wrong expectation must fail, or the self-test proves nothing
    checks.append(("a wrong target is rejected", round(mcnemar_exact(0, 2), 3) != 1.000))
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("ok   " if ok else "FAIL ") + name)
    raise SystemExit(1 if bad else 0)
