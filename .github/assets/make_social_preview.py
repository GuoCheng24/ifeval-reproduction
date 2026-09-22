"""Generate the GitHub social-preview card (1200x630). Reproducible: python3 make_social_preview.py

The first version put its message in a block of 14 pt monospace. A social card is unfurled at about
360 px wide in Slack, where that is grey noise, so the message is in the headline now and the
terminal panel is texture beside it. Layout in lightcard.py next to this file, which refuses to emit a card whose left column runs under the panel.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lightcard import draw  # noqa: E402

out = draw(
    out=str(pathlib.Path(__file__).parent / "social-preview.png"),
    accent="#db6d28", badge="I", headline_size=40,
    kicker="REPRODUCTION  ·  one shared RTX 4090",
    headline="The gain was the subsample",
    subline="not the model",
    body=["A paired test on my own result:",
          "thinking mode scored 87.5 where the",
          "baseline scored 76.9 - until that",
          "baseline was scored on the same 32."],
    panel=[("$ python scripts/analyze_run2b.py", "dim"),
           ("prompt-strict  76.9   541/541  greedy", "ink"),
           ("model card     94.8   variant unstated", "warn"),
           ("thinking on    87.5   28 of 32 only", "ink"),
           ("arm 1, same 32 87.5   McNemar p=1.000", "red")],
    footer="github.com/GuoCheng24/ifeval-reproduction",
)
print(f"written {pathlib.Path(out).name} 1200x630")
