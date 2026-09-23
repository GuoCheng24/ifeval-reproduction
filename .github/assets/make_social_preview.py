"""The 1200x630 card that appears when the link is shared.

The card carries the finding: two arms that differ only in generation batch size
straddle the model card's number, one interval excluding it and one containing
it, while being statistically indistinguishable from each other. Two intervals
and a threshold line is the whole argument, so that is what the card shows.

Every figure is read from results/metrics_run3.json; nothing here is typed.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cardkit import INK, MUTE, SANS, card  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
M = json.loads((ROOT / "results/metrics_run3.json").read_text())
CARD = M["card_claim"]
BATCH = M["BATCH 16 (3a) vs batch 8 (3b), everything else identical"]

ROWS = []
for arm, batch in (("3a", 16), ("3b", 8)):
    a = M[f"run{arm}"]
    lo, hi = (100 * v for v in a["ci95_prompt_level_strict"])
    ROWS.append((f"batch {batch}", 100 * a["prompt_level_strict_acc"], lo, hi,
                 a["ci_excludes_card"]))

WARN, OK = "#b4562a", "#1f6f6b"
LO, HI = 72.0, 99.0


def chart(ax, accent):
    from matplotlib.patches import Rectangle

    x0, x1 = 3.95, 10.30
    def X(v):
        return x0 + (x1 - x0) * (v - LO) / (HI - LO)

    # the threshold the pre-registration made the verdict turn on
    xc = X(CARD)
    ax.plot([xc, xc], [1.48, 3.48], color=MUTE, lw=2.4, ls=(0, (5, 4)), zorder=2)
    ax.text(xc + 0.12, 3.30, f"card {CARD}", fontsize=34, color=MUTE,
            family=SANS, va="center")

    for i, (name, acc, lo, hi, excludes) in enumerate(ROWS):
        y = 2.72 - i * 0.82
        colour = WARN if excludes else OK
        ax.plot([X(lo), X(hi)], [y, y], color=colour, lw=7, solid_capstyle="round", zorder=3)
        ax.add_patch(Rectangle((X(acc) - 0.035, y - 0.21), 0.07, 0.42,
                               fc=INK, ec="none", zorder=4))
        ax.text(0.78, y, name, fontsize=34, color=INK, family=SANS, va="center")
        ax.text(X(hi) + 0.20, y, f"{acc:.1f}", fontsize=34, fontweight="bold",
                color=colour, family=SANS, va="center")

    ax.text(0.78, 1.00,
            f"identical in everything else · McNemar p = {BATCH['mcnemar_exact_p']:.3f}",
            fontsize=34, color=MUTE, family=SANS, va="center")


out = card(
    out=str(pathlib.Path(__file__).parent / "social-preview.png"),
    accent=WARN, badge="I",
    kicker="REPRODUCTION  ·  IFEval, prompt-level strict, n=80",
    headline="The batch size decides the verdict",
    evidence="95% intervals against the number on the model card",
    chart=chart,
    footer="github.com/GuoCheng24/ifeval-reproduction",
    headline_size=46,
)
print(f"written {pathlib.Path(out).name}  "
      + "  ".join(f"{n} {a:.2f} [{lo:.2f},{hi:.2f}] {'excl' if e else 'cont'}"
                  for n, a, lo, hi, e in ROWS))
