"""Generate the GitHub social-preview card (1200x630). Reproducible: python3 make_social_preview.py

The card carries the finding: arm 3 looked like an eleven-point gain until arm 1 was scored on
the same 32 prompts and got the same number. Two bars of equal length is the whole argument, so
two bars of equal length is what the card shows.

The two complete scores are read from results/metrics_*.json. Arm 1 restricted to those 32
prompts cannot be recomputed here - the generations are gitignored - so it is parsed out of
results/RESULTS_run2.md, the file scripts/check_readme_numbers.py already holds the README to.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cardkit import SANS, card  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
run1 = 100 * json.loads((ROOT / "results/metrics_run1.json").read_text())["strict"]["prompt_level_acc"]
run2b = 100 * json.loads((ROOT / "results/metrics_run2b.json").read_text())["strict"]["prompt_level_acc"]
results = (ROOT / "results/RESULTS_run2.md").read_text()
m = re.search(r"Run 1 scores \*\*([\d.]+) on the very same 32 prompts\*\*", results)
if not m:
    raise SystemExit("results/RESULTS_run2.md no longer states arm 1's score on the same 32")
paired = float(m.group(1))

BARS = [("arm 1, all 541", run1, False),
        ("arm 3, its 32", run2b, True),
        ("arm 1, same 32", paired, True)]


def chart(ax, accent):
    x0, span, top, step = 4.60, 3.55, 3.28, 0.95
    top_v = max(v for _, v, _ in BARS)
    for i, (name, value, hero) in enumerate(BARS):
        y = top - i * step
        ax.barh(y, span * value / top_v, height=0.52, left=x0,
                color=accent if hero else "#c7c3bc", zorder=3)
        ax.text(x0 - 0.20, y, name, fontsize=34, color="#17181a" if hero else "#55585c",
                family=SANS, ha="right", va="center")
        ax.text(x0 + span * value / top_v + 0.18, y, f"{value:.1f}",
                fontsize=36, fontweight="bold",
                color="#17181a" if hero else "#55585c", family=SANS, va="center")
    # the two equal bars, bracketed, are the argument
    xb = x0 + span + 1.22
    ax.plot([xb, xb], [top - step, top - 2 * step], color=accent, lw=3, zorder=3)
    ax.text(xb + 0.16, top - 1.5 * step, "identical", fontsize=34, fontweight="bold",
            color=accent, family=SANS, va="center")


out = card(
    out=str(pathlib.Path(__file__).parent / "social-preview.png"),
    accent="#d1670a", badge="I",
    kicker="REPRODUCTION  ·  one shared RTX 4090",
    headline="The gain was the subsample",
    evidence="IFEval prompt-level strict, Agents-A1-4B",
    chart=chart,
    footer="github.com/GuoCheng24/ifeval-reproduction",
    headline_size=46,
)
print(f"written {pathlib.Path(out).name} (run1 {run1:.1f}, run2b {run2b:.1f}, paired {paired:.1f})")
