"""System architecture figure (paper Figure 1 and README): the tracer-convention harness and the field-check pipeline.
    python scripts/build_architecture.py   -> docs/figures/architecture.svg (+ .png)

Every label names a real component; counts are read from paper/numbers.tex and the code, never typed.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from _svgkit import Svg  # noqa: E402
from sord_exp.env import CONDITIONS, MAX_TURNS, INDEX_PAGE  # noqa: E402

NUM = dict(re.findall(r"\\csname sr@([^\\]+)\\endcsname\{(.*)\}\s*$",
                      open(os.path.join(ROOT, "paper", "numbers.tex"), encoding="utf-8").read(), flags=re.M))
REV, LAB = NUM["s1/DataRevisions"], NUM["s1/DataAgentLabels"]
NTECH, NPLAC = NUM["s1/NTechniques"], NUM["s1/NPlacebos"]
NTRIALS = NUM["s2/n/trials"]
GROUPS = [("Baseline", ["isolated", "neutral4", "neutral4_shown"]),
          ("Dose, agent must look", ["dose1", "dose2", "dose4"]),
          ("Components", ["dose4_arbitrary_only", "dose4_functional_only"]),
          ("Page list shown", ["dose1_shown", "dose2_shown", "dose4_shown"]),
          ("Disagreement", ["dose4_shown_mixed"]),
          ("Framing ablation", ["dose4_shown_nocue"])]
assert sorted(c for _, cs in GROUPS for c in cs) == sorted(CONDITIONS), "figure conditions out of sync with env.CONDITIONS"
NCOND = len(CONDITIONS)

INK, INK2, MUTED, FAINT = "#1E293B", "#334155", "#64748B", "#94A3B8"
TEAL, TEAL_BG, AMBER, AMBER_BG = "#0F766E", "#CCFBF1", "#B45309", "#FEF3C7"
NAVY, BLUE, PANEL, LINEC, ROSE = "#1B2A3A", "#2563EB", "#F1F5F9", "#CBD5E1", "#E11D48"

W, H = 1400, 940
s = Svg(W, H, bg="#FFFFFF")
s.add(f'''<defs>
<linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{NAVY}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>
<linearGradient id="hda" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#92400E"/><stop offset="1" stop-color="{AMBER}"/></linearGradient>
<filter id="sh" x="-10%" y="-10%" width="130%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#0F172A" flood-opacity="0.10"/></filter>
<marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1,1 L9,5 L1,9" fill="none" stroke="{INK2}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>
<marker id="aht" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1,1 L9,5 L1,9" fill="none" stroke="{TEAL}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>
<marker id="aha" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1,1 L9,5 L1,9" fill="none" stroke="{AMBER}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>
<style>.lt{{font-family:Inter,'Segoe UI',Helvetica,Arial,sans-serif}}
.ti{{font-size:20px;font-weight:600;fill:#FFFFFF}}.tk{{font-size:19px;font-weight:600;fill:{INK}}}
.su{{font-size:15.5px;fill:{INK2}}}.mu{{font-size:15px;fill:{MUTED}}}.lay{{font-size:16px;font-weight:700;fill:{FAINT};letter-spacing:.4px}}
.mo{{font-family:Consolas,'Cascadia Mono',monospace;font-size:15px;fill:{INK}}}.mot{{font-family:Consolas,'Cascadia Mono',monospace;font-size:15px;font-weight:700;fill:{TEAL}}}
.ch{{font-size:14.5px;font-weight:500;fill:{INK2}}}.gh{{font-size:14px;font-weight:700;fill:{TEAL};letter-spacing:.3px}}
.ah{{font-size:14px;font-weight:700;fill:{AMBER};letter-spacing:.3px}}.wb{{font-size:15px;font-weight:600;fill:#FFFFFF}}.cap{{font-size:15px;font-style:italic;fill:{MUTED}}}</style></defs>''')


def T(x, y, txt, cls, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    s.add(f'<text x="{x}" y="{y}" class="lt {cls}"{a}>{Svg.esc(txt)}</text>')


def rect(x, y, w, h, fill, stroke="none", sw=1.5, rx=14, extra=""):
    s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def line(d, col=INK2, w=1.8, dash=None, marker="ah"):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round"{da} marker-end="url(#{marker})"/>')


def card(x, y, w, h, title, grad="hdr"):
    """White card with a coloured header strip; returns the y where body text starts."""
    rect(x, y, w, h, "#FFFFFF", LINEC, sw=1.2, rx=14, extra='filter="url(#sh)"')
    s.add(f'<path d="M{x} {y + 14} a14 14 0 0 1 14 -14 h{w - 28} a14 14 0 0 1 14 14 v24 h{-w} z" fill="url(#{grad})"/>')
    T(x + 16, y + 26, title, "ti")
    return y + 64


def chip(x, y, label, fill=PANEL, stroke=LINEC, cls="ch", pad=11):
    w = len(label) * 7.9 + 2 * pad
    rect(x, y, w, 26, fill, stroke, sw=1, rx=13)
    T(x + w / 2, y + 18, label, cls, "middle")
    return x + w + 6


# ---- layer labels --------------------------------------------------------------------------------------------------
LX = 22
for (y0, y1, lab, col) in ((20, 610, f"Tracer experiment  ·  {NTRIALS} trials", TEAL), (640, 920, "Field check  ·  real incident log", AMBER)):
    rect(LX, y0, 5, y1 - y0, col, rx=2.5)
    s.add(f'<text transform="translate({LX + 24},{(y0 + y1) / 2}) rotate(-90)" class="lt lay" text-anchor="middle">{Svg.esc(lab.upper())}</text>')

# ==== layer A, row 1: scenario -> seeded wiki -> agent loop -> log + grader ==========================================
R1, R1H = 22, 300
X1, W1 = 62, 250
y = card(X1, R1, W1, R1H, "Scenario (seed s)")
for i, (a, b) in enumerate([("question", "1 of 12 templates"), ("agent id", "A33"), ("page code", "Z5L"), ("body tag", "~vx3~")]):
    T(X1 + 16, y + i * 44, a, "mu")
    T(X1 + 16, y + 21 + i * 44, b, "mot" if a in ("page code", "body tag") else "mo")
T(X1 + 16, y + 196, "same seed, same scenario", "cap")
T(X1 + 16, y + 216, "in every condition", "cap")

X2, W2 = 346, 300
y = card(X2, R1, W2, R1H, "Seeded shared wiki")
T(X2 + 16, y, "prior agents' answer pages:", "mu")
for i, (pre, code) in enumerate([("answer-Q-1207-", "Z5L"), ("answer-Q-3361-", "Z5L"), ("answer-Q-8840-", "Z5L")]):
    rect(X2 + 16, y + 14 + i * 36, W2 - 32, 28, TEAL_BG if i == 0 else "#F0FDFA", rx=7)
    T(X2 + 28, y + 34 + i * 36, pre, "mo")
    T(X2 + 28 + len(pre) * 8.25, y + 34 + i * 36, code, "mot")
rect(X2 + 16, y + 126, W2 - 32, 28, PANEL, rx=7)
T(X2 + 28, y + 146, INDEX_PAGE, "mo")
T(X2 + W2 - 26, y + 146, "functional", "mu", "end")
T(X2 + 16, y + 186, "body: ~vx3~ Q-1207: … Answer: …", "mo")
T(X2 + 16, y + 216, "0, 1, 2 or 4 marked pages", "cap")

X3, W3 = 680, 300
y = card(X3, R1, W3, R1H, "Agent loop (LLM)")
T(X3 + 16, y, "system prompt + one question", "su")
T(X3 + 16, y + 22, "(+ page list in shown conditions)", "mu")
cx, cy = X3 + 16, y + 40
for t_ in ("list_pages", "read_page", "write_page"):
    cx = chip(cx, cy, t_, TEAL_BG, "#99F6E4")
cx = chip(X3 + 16, cy + 34, "submit_answer", TEAL_BG, "#99F6E4")
chip(cx, cy + 34, "finish", TEAL_BG, "#99F6E4")
T(X3 + 16, y + 132, f"one JSON tool call per turn", "su")
T(X3 + 16, y + 154, f"at most {MAX_TURNS} turns", "su")
T(X3 + 16, y + 186, "invalid reply: re-prompted,", "cap")
T(X3 + 16, y + 206, "counted as a protocol error", "cap")

X4, W4 = 1014, 364
y = card(X4, R1, W4, R1H, "Trial log + exact-match grader")
T(X4 + 16, y, "trials.jsonl + transcripts", "mo")
T(X4 + 16, y + 21, "appended per trial; reruns resume", "mu")
checks = ["code slot in the page name?", "seeded code, or own id in it?", "body tag reproduced?",
          "own line in the index?", "listed / read before writing?"]
for i, c_ in enumerate(checks):
    s.add(f'<g transform="translate({X4 + 16},{y + 40 + i * 30})" fill="none" stroke="{TEAL}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
          f'<rect x="0" y="0" width="16" height="16" rx="4"/><path d="M4 8.5l3 3 5-6"/></g>')
    T(X4 + 42, y + 53 + i * 30, c_, "su")

for xa, xb in ((X1 + W1, X2), (X2 + W2, X3), (X3 + W3, X4)):
    line(f"M{xa + 3} {R1 + R1H / 2} H{xb - 5}")

# ==== layer A, row 2: conditions -> wiki ; backends <-> agent ; grader -> statistics ================================
R2, R2H = 352, 258
XC, WC = 62, 584
rect(XC, R2, WC, R2H, "#F8FAFC", LINEC, sw=1.2, rx=14)
T(XC + 16, R2 + 30, f"{NCOND} paired conditions on the same seeds", "tk")
gy = R2 + 54
for gi, (g, cs) in enumerate(GROUPS):
    col_x = XC + 16 + (gi % 2) * 312
    row_y = gy + (gi // 2) * 66
    T(col_x, row_y + 14, g.upper(), "gh")
    cx = col_x
    lab = {"dose4_arbitrary_only": "marker only", "dose4_functional_only": "index only",
           "dose4_shown_mixed": "4 different codes", "dose4_shown_nocue": "no team framing (2 models)"}
    for c in cs:
        cx = chip(cx, row_y + 22, lab.get(c, c.replace("_shown", " shown") if c == "neutral4_shown" else c.replace("_shown", "")), pad=8)
line(f"M{X2 + W2 / 2} {R2 - 2} V{R1 + R1H + 6}", col=TEAL, marker="aht")

XB, WB = 680, 300
y = card(XB, R2, WB, R2H, "Model backends")
T(XB + 16, y, "vLLM on Modal (H100), seeded:", "mu")
for i, m in enumerate(["Gemma 4 31B · Qwen3.8 27B", "Ministral 3 14B · gpt-oss-120b"]):
    T(XB + 16, y + 22 + i * 21, m, "su")
T(XB + 16, y + 82, "Adaption Responses API:", "mu")
for i, m in enumerate(["DeepSeek-V4 Flash · GLM-5.2", "Qwen3.5 397B"]):
    T(XB + 16, y + 104 + i * 21, m, "su")
T(XB + 16, y + 168, "temperature 0.7 for all models", "cap")
line(f"M{X3 + W3 / 2 - 30} {R1 + R1H + 4} V{R2 - 6}")
line(f"M{X3 + W3 / 2 + 30} {R2 - 4} V{R1 + R1H + 6}")

XS, WS = 1014, 364
y = card(XS, R2, WS, R2H, "Statistics")
for i, t_ in enumerate(["exact McNemar on paired seeds, per model", "logistic dose slope, seed-clustered SE",
                        "Wilson 95% intervals", "qualitative read of page names and notes"]):
    T(XS + 16, y + i * 30, "·  " + t_, "su")
rect(XS + 16, y + 128, WS - 32, 46, NAVY, rx=10)
T(XS + WS / 2, y + 156, "make_numbers.py → all numbers in the paper", "wb", "middle")
line(f"M{X4 + W4 / 2} {R1 + R1H + 4} V{R2 - 6}")

# ==== layer B: field-check pipeline =================================================================================
FB = 662
nodes = [("Public export", [f"{REV} revisions", f"{LAB} agent labels"]),
         ("Diff revisions", ["new lines per revision,", "attributed to a label"]),
         ("Token catalogue", [f"{NTECH} techniques (regex)", f"{NPLAC} placebo words"]),
         ("Adoption events", ["first new matching", "line per label, token"]),
         ("Exposure", ["from writes: prior,", "other page, same page"]),
         ("Tests", ["re-timing permutation", "within-label choice", "placebo contrast"])]
NW, GAP = 196, 20
x0 = 62
for i, (t_, ls) in enumerate(nodes):
    x = x0 + i * (NW + GAP)
    y = card(x, FB, NW, 150, t_, grad="hda")
    for j, l_ in enumerate(ls):
        T(x + 14, y + j * 21, l_, "su")
    if i:
        line(f"M{x - GAP + 2} {FB + 75} H{x - 4}", col=AMBER, marker="aha")
# positive control loop
PCX, PCY, PCW = x0 + 3 * (NW + GAP), FB + 186, 2 * NW + GAP
rect(PCX, PCY, PCW + NW + GAP, 70, AMBER_BG, AMBER, sw=1.5, rx=12, extra='stroke-dasharray="7 5"')
T(PCX + 16, PCY + 29, "Positive control: plant a synthetic token in the real timeline,", "su")
T(PCX + 16, PCY + 52, "copy it at a known rate, and measure each test's power", "su")
line(f"M{PCX + 40} {PCY - 2} V{FB + 154}", col=AMBER, marker="aha")
lx = x0 + 5 * (NW + GAP) + NW / 2
line(f"M{lx} {FB + 152} V{PCY - 4}", col=AMBER, dash="5 4", marker="aha")
T(x0, FB + 216, "Reads are not in the export, so exposure", "cap")
T(x0, FB + 238, "is measured from what a label wrote.", "cap")

s.save(os.path.join(ROOT, "docs", "figures", "architecture.svg"), scale=3)
