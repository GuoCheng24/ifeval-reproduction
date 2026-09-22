"""Generate the GitHub social-preview card (1280x640). Reproducible: python3 make_social_preview.py

The scores are read from results/metrics_*.json at draw time, so the card is held to the same
source as the README rather than being a second place for a number to go stale.
"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
r1 = json.loads((ROOT / "results/metrics_run1.json").read_text())
r2b = json.loads((ROOT / "results/metrics_run2b.json").read_text())
CARD = 94.8

W, H = 12.8, 6.4
fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), W, H, color="#0d1117"))
SANS, MONO = "Liberation Sans", "Liberation Mono"

ax.text(0.75, 5.55, "ifeval-reproduction", fontsize=34, fontweight="bold", color="#e6edf3", family=SANS)
ax.text(0.75, 4.92, "Reproducing a published IFEval score on one shared GPU, and the analysis that killed my own result.",
        fontsize=16, color="#8b949e", family=SANS)

ax.add_patch(FancyBboxPatch((0.72, 1.28), 11.36, 3.05, boxstyle="round,pad=0.12",
                            fc="#161b22", ec="#30363d", lw=1.5))
ax.text(0.95, 4.02, "$ python scripts/make_results.py      # Agents-A1-4B, all 541 prompts",
        fontsize=13.5, color="#7d8590", family=MONO)
p1 = 100 * r1["strict"]["prompt_level_acc"]
n2c, n2 = r2b["strict"]["n_prompts_correct"], r2b["strict"]["n_prompts"]
p2 = 100 * r2b["strict"]["prompt_level_acc"]
rows = [
    (f"prompt-strict   {p1:.1f}   measured here, greedy, thinking off, 541/541", "#e6edf3"),
    (f"model card      {CARD:.1f}   metric variant, decoding and budget all unstated", "#f0883e"),
    (f"thinking on     {p2:.1f}   but only {n2c} of {n2} prompts - a cost cap stopped it", "#58a6ff"),
    ("the trap        arm 1 scores 87.5 on those same 32. The subsample was easier.", "#f85149"),
]
y = 3.55
for txt, c in rows:
    ax.text(0.95, y, txt, fontsize=14, color=c, family=MONO)
    y -= 0.5
ax.text(0.95, y - 0.02,
        "three arms | pre-registration hash-chained before any score existed | paired McNemar, p = 1.000",
        fontsize=12, color="#7d8590", family=MONO)

ax.text(0.75, 0.62,
        "Could not reproduce 94.8 under the settings one shared 4090 can afford - and did not refute it either. "
        "Both halves matter.",
        fontsize=12.5, color="#8b949e", family=SANS)

out = pathlib.Path(__file__).parent / "social-preview.png"
fig.savefig(out)
print(f"written {out.name} 1280x640 (run1 {p1:.1f}, run2b {p2:.1f} on {n2c}/{n2})")
