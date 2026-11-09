"""Draw docs/figures/design.png: the tracer-convention experiment and the field check."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

NAVY, TEAL, RED, GREY, INK, PAPER, AMBER = "#1B2A3A", "#0F766E", "#C0392B", "#8A99A8", "#22313F", "#F5F8FA", "#B45309"
OUT = Path(__file__).resolve().parents[1] / "docs" / "figures" / "design.png"


def box(ax, x, y, w, h, title, sub, edge, fill="white", tsize=11.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", lw=1.6, ec=edge, fc=fill))
    ax.text(x + w / 2, y + h - 0.32, title, ha="center", va="center", fontsize=tsize, weight="bold", color=INK)
    ax.text(x + w / 2, y + (h - 0.5) / 2, sub, ha="center", va="center", fontsize=8.8, color=INK, linespacing=1.3)


def arrow(ax, a, b, col=GREY):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=14, lw=1.6, color=col))


fig, ax = plt.subplots(figsize=(14, 6.4), dpi=200)
ax.set_xlim(0, 14)
ax.set_ylim(0, 6.4)
ax.axis("off")
fig.patch.set_facecolor(PAPER)
ax.text(0.3, 6.05, "Tracer conventions: does an agent copy a practice, or reinvent it?", fontsize=15, weight="bold", color=NAVY)
ax.text(0.3, 5.7, "An arbitrary marker cannot be rediscovered, only copied. Seed it on a shared wiki and count who reproduces it.",
        fontsize=10, color=INK)

# seeded wiki
box(ax, 0.3, 2.35, 3.6, 3.0, "Shared team wiki (seeded)",
    "prior agents' pages, e.g.\nanswer-Q-5438-Z5L\nanswer-Q-1207-Z5L\n+ body tag  ~vx3~\n+ Answers-Index page\n\nexposure: 0, 1, 2 or 4 prior pages;\ncodes shared or all different", NAVY)
# agent
box(ax, 4.9, 2.35, 3.3, 3.0, "Evaluation agent (LLM)",
    "task: answer one question and\nleave the answer for teammates\n\ntools: list_pages, read_page,\nwrite_page, submit_answer\n\nGemma 4 31B · Qwen3.8 27B ·\nMinistral-3 14B · gpt-oss-120b ·\nDeepSeek-V4 Flash · GLM-5.2 ·\nQwen3.5 397B", TEAL, fill="#E6F7F5")
arrow(ax, (3.9, 3.85), (4.9, 3.85))
# outcome
box(ax, 9.2, 2.35, 4.5, 3.0, "What it writes (exact match)",
    "copies the name structure?  answer-<q>-<slot>\nslot = the seeded code?  (copying)\nslot = its own id?  (structure only)\nbody tag reproduced?\nindex entry added?\n\n12 paired conditions × 48 seeds × 7 models", NAVY)
arrow(ax, (8.2, 3.85), (9.2, 3.85))

# field check strip
ax.add_patch(FancyBboxPatch((0.3, 0.25), 13.4, 1.65, boxstyle="round,pad=0.02,rounding_size=0.12", lw=1.4, ec=AMBER, fc="#FEF4DC"))
ax.text(0.55, 1.6, "Field check: the collusion.wiki swarm (real incident log)", fontsize=11, weight="bold", color=AMBER)
ax.text(0.55, 0.95, "14,591 wiki revisions by 3,099 agent labels · 15 techniques + 8 placebo words · time-shuffle, within-label and\n"
                    "same-page tests · positive control. Question: in a write-only log, can technique spread be told apart from word echo?",
        fontsize=9.3, color=INK, va="center", linespacing=1.35)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor=PAPER)
print(OUT)
