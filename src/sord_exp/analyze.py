"""Analysis for Study 2: rates with Wilson CIs, paired exact McNemar tests, dose-response and acceleration.

Writes <exp>/RESULTS.md, <exp>/results/summary.json and <exp>/figures/dose_response.{png,pdf}.
If <exp>/summary.md exists it is included verbatim at the top of RESULTS.md (hand-written interpretation).
"""
from __future__ import annotations

import argparse
import warnings
import json
import math
import random
from pathlib import Path

DOSE = {"isolated": 0, "dose1": 1, "dose2": 2, "dose4": 4}
COND_ORDER = ["isolated", "neutral4", "dose1", "dose2", "dose4", "dose4_arbitrary_only", "dose4_functional_only",
              "neutral4_shown", "dose1_shown", "dose2_shown", "dose4_shown", "dose4_shown_mixed"]
# outcome -> label. index_like is defined identically in every condition (wrote any index/registry-like page,
# including Answers-Index), so it is the comparable "functional convention present" outcome.
OUTCOMES = {
    "adopt_suffix": "suffix code copied (arbitrary)",
    "adopt_any_prior_code": "any prior page's code copied",
    "slot_filled_with_prior_code": "slot filled with a prior code",
    "suffix_slot_self_id": "slot filled with own agent id",
    "adopt_tag": "body tag copied (arbitrary)",
    "adopt_any_prior_tag": "any prior page's tag copied",
    "adopt_suffix_slot": "name has a trailing code slot",
    "index_like": "wrote an index-like page (functional)",
    "adopt_index": "own line in Answers-Index, exact format",
}
EXTRA = ["wrote_page", "read_before_write", "read_prior_page", "read_index", "answer_correct", "answer_on_wiki",
         "adopt_index_loose", "suffix_slot_self_id", "adopt_name_pattern"]


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def trend_test(groups: list[tuple[float, list[int]]]):
    """Cochran-Armitage test for trend; groups = [(score, [0/1 outcomes])]. Returns (z, two-sided p)."""
    N = sum(len(y) for _, y in groups)
    R = sum(sum(y) for _, y in groups)
    if N == 0 or R in (0, N):
        return float("nan"), 1.0
    pbar = R / N
    T = sum(s * (sum(y) - len(y) * pbar) for s, y in groups)
    sbar = sum(s * len(y) for s, y in groups) / N
    V = pbar * (1 - pbar) * sum(len(y) * (s - sbar) ** 2 for s, y in groups)
    if V <= 0:
        return float("nan"), 1.0
    z = T / math.sqrt(V)
    return z, 2 * (1 - norm_cdf(abs(z)))


def logit_slope(xs, ys, strata=None):
    """Logistic regression slope of y on x (optionally with stratum fixed effects). Returns (beta, se, p) or None."""
    try:
        import numpy as np
        import statsmodels.api as sm
        cols = [np.array(xs, dtype=float)]
        if strata is not None:
            cols += [np.array([1.0 if s == lv else 0.0 for s in strata]) for lv in sorted(set(strata))[1:]]
        X = sm.add_constant(np.column_stack(cols), has_constant="add")
        y = np.array(ys, dtype=float)
        if y.min() == y.max():
            return None
        r = sm.Logit(y, X).fit(disp=0, maxiter=200)
        b, se = float(r.params[1]), float(r.bse[1])
        if not math.isfinite(se) or se > 50:
            return None
        return b, se, float(r.pvalues[1])
    except Exception:
        return None


def regrade(r: dict, tdir: Path) -> dict:
    """Recompute grade fields from the saved transcript (read-only; trials.jsonl is never rewritten)."""
    from .env import Cond
    from .grade import grade
    from .scenarios import make_scenario
    tid = f"{r['model'].replace('/', '_').replace(':', '-')}__{r['condition']}__{r['seed']}"
    t = json.loads((tdir / f"{tid}.json").read_text(encoding="utf-8"))
    ex = dict(actions=t["actions"], initial_wiki=t["initial_wiki"], final_wiki=t["final_wiki"], invalid=r["invalid"],
              finished=r["finished"], transcript=t["transcript"])
    return {**r, **grade(make_scenario(r["seed"]), Cond.get(r["condition"]), ex)}


def load(exp: Path) -> dict:
    data = {}
    for f in sorted((exp / "results").glob("*/trials.jsonl")):
        rows = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if "adopt_any_prior_code" not in r:  # trial graded before these metrics existed: regrade from its transcript
                    r = regrade(r, f.parent / "transcripts")
                rows[(r["condition"], r["seed"])] = r
        if rows:
            data[f.parent.name] = rows
    return data


def fmt_rate(k, n):
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} ({100*p:.0f}%, {100*lo:.0f}-{100*hi:.0f})" if n else "-"


def fmt_p(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def paired(rows, a, b, key):
    seeds = sorted({s for c, s in rows if c == a} & {s for c, s in rows if c == b})
    xa = [bool(rows[(a, s)][key]) for s in seeds]
    xb = [bool(rows[(b, s)][key]) for s in seeds]
    b01 = sum(1 for u, v in zip(xa, xb) if not u and v)  # adopted only under b
    b10 = sum(1 for u, v in zip(xa, xb) if u and not v)
    return len(seeds), sum(xa), sum(xb), b01, b10


def boot_accel(rows, key, n_boot=4000, rng=None):
    """Paired bootstrap over seeds of (r4 - r2) - (r2 - r1); positive = adoption accelerates per doubling."""
    rng = rng or random.Random(0)
    seeds = sorted({s for c, s in rows if c == "dose1"} & {s for c, s in rows if c == "dose2"} & {s for c, s in rows if c == "dose4"})
    if not seeds:
        return None
    y = {c: [float(bool(rows[(c, s)][key])) for s in seeds] for c in ("dose1", "dose2", "dose4")}
    def stat(idx):
        m = {c: sum(y[c][i] for i in idx) / len(idx) for c in y}
        return (m["dose4"] - m["dose2"]) - (m["dose2"] - m["dose1"])
    est = stat(range(len(seeds)))
    bs = sorted(stat([rng.randrange(len(seeds)) for _ in seeds]) for _ in range(n_boot))
    return est, bs[int(0.025 * n_boot)], bs[int(0.975 * n_boot) - 1]


def analyze(exp: Path) -> dict:
    warnings.filterwarnings("ignore")
    data = load(exp)
    out = {"models": {}, "pooled": {}}
    md = []
    if (exp / "summary.md").exists():
        md += [(exp / "summary.md").read_text(encoding="utf-8").strip(), ""]
    md += ["# Study 2 results: seeded convention diffusion", "",
           "Generated by `python -m sord_exp.analyze`. Rates are k/n (percent, 95% Wilson CI). Conditions are paired by seed "
           "(same question, same marker codes); tests are exact McNemar on the discordant seed pairs. "
           "`index_like` = the agent wrote any index/registry-like page (Answers-Index or an invented one); in `isolated` and "
           "`neutral4` it is the rate at which the functional convention is invented without a model to copy.", ""]

    # --- 1. trial counts, cost
    md += ["## 1. Trials, cost and time", "", "| model | trials | errors | LLM calls | prompt tok | completion tok | mean turns | mean s/trial |",
           "|---|---|---|---|---|---|---|---|"]
    for m, rows in data.items():
        R = list(rows.values())
        errs = exp / "results" / m / "errors.jsonl"
        ne = len(errs.read_text(encoding="utf-8").splitlines()) if errs.exists() else 0
        calls = sum(r["usage"]["calls"] for r in R)
        pt = sum(r["usage"]["prompt_tokens"] for r in R)
        ct = sum(r["usage"]["completion_tokens"] for r in R)
        md.append(f"| {m} | {len(R)} | {ne} | {calls} | {pt} | {ct} | {sum(r['turns'] for r in R)/len(R):.1f} | "
                  f"{sum(r['secs'] for r in R)/len(R):.1f} |")
        out["models"][m] = {"n_trials": len(R), "errors_logged": ne, "calls": calls, "prompt_tokens": pt, "completion_tokens": ct}
    md.append("")

    # --- 2. rates per model x condition
    md += ["## 2. Rates per model and condition", ""]
    for m, rows in data.items():
        conds = [c for c in COND_ORDER if any(cc == c for cc, _ in rows)]
        keys = list(OUTCOMES) + ["wrote_page", "listed_before_write", "read_before_write", "read_prior_page", "answer_correct",
                                 "index_clobbered"]
        md += [f"### {m}", "", "| outcome | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]
        rates = {}
        for k in keys:
            cells = []
            for c in conds:
                R = [r for (cc, _), r in rows.items() if cc == c]
                if k == "index_clobbered":
                    R = [r for r in R if r["adopt_index_loose"] or "Answers-Index" in r["written_pages"]]
                kk = sum(1 for r in R if r.get(k))
                rates.setdefault(k, {})[c] = [kk, len(R)]
                cells.append(fmt_rate(kk, len(R)))
            label = OUTCOMES.get(k, k) + (" (among index writers)" if k == "index_clobbered" else "")
            md.append(f"| {label} | " + " | ".join(cells) + " |")
        out["models"][m]["rates"] = rates
        md.append("")

    # --- 3. paired tests
    contrasts = [("isolated", "dose1"), ("isolated", "dose2"), ("isolated", "dose4"), ("neutral4", "dose4"),
                 ("neutral4", "dose4_arbitrary_only"), ("neutral4", "dose4_functional_only"),
                 ("dose4_arbitrary_only", "dose4"), ("dose4_functional_only", "dose4"),
                 ("neutral4_shown", "dose1_shown"), ("neutral4_shown", "dose4_shown"), ("dose1_shown", "dose4_shown"),
                 ("dose1", "dose1_shown"), ("dose4", "dose4_shown"),
                 ("dose1_shown", "dose2_shown"), ("dose2_shown", "dose4_shown"), ("dose4_shown_mixed", "dose4_shown"),
                 ("dose1_shown", "dose4_shown_mixed"), ("neutral4_shown", "dose4_shown_mixed")]
    md += ["## 3. Paired exact McNemar tests", "",
           "b = seeds adopting only under the second condition, c = only under the first. Pooled = all models' pairs together.", ""]
    for key in ["adopt_suffix", "adopt_any_prior_code", "adopt_tag", "adopt_any_prior_tag", "adopt_suffix_slot",
                "suffix_slot_self_id", "index_like"]:
        md += [f"### {OUTCOMES[key]} (`{key}`)", "", "| contrast | " + " | ".join(list(data) + ["pooled"]) + " |",
               "|---|" + "---|" * (len(data) + 1)]
        for a, b in contrasts:
            cells, B, C, NA, NB, N = [], 0, 0, 0, 0, 0
            for m, rows in data.items():
                n, ka, kb, b01, b10 = paired(rows, a, b, key)
                if n == 0:
                    cells.append("-")
                    continue
                p = mcnemar_exact(b01, b10)
                cells.append(f"{ka}->{kb} /{n}, b={b01} c={b10}, p={fmt_p(p)}")
                out["models"][m].setdefault("mcnemar", {}).setdefault(key, {})[f"{a}_vs_{b}"] = dict(n=n, k_a=ka, k_b=kb, b=b01, c=b10, p=p)
                B += b01; C += b10; NA += ka; NB += kb; N += n
            if N == 0:
                continue
            pp = mcnemar_exact(B, C)
            out["pooled"].setdefault("mcnemar", {}).setdefault(key, {})[f"{a}_vs_{b}"] = dict(n=N, k_a=NA, k_b=NB, b=B, c=C, p=pp)
            cells.append(f"{NA}->{NB} /{N}, b={B} c={C}, p={fmt_p(pp)}")
            md.append(f"| {a} vs {b} | " + " | ".join(cells) + " |")
        md.append("")

    # --- 4. dose-response
    md += ["## 4. Dose-response over dose1, dose2, dose4", "",
           "Logistic regression of adoption on log2(dose) (dose 1, 2, 4 -> 0, 1, 2; pooled model adds model fixed effects); "
           "Cochran-Armitage trend test with the same scores. `-` = slope not estimable (no variation or separation). "
           "Acceleration = (r4 - r2) - (r2 - r1), the change in the per-doubling increment, with a 95% paired bootstrap CI over seeds "
           "(positive = adoption accelerates with more prior adopters). Per added agent the increments are r2 - r1 (1 agent) and (r4 - r2)/2 (2 agents).", "",
           "| outcome | model | r1 | r2 | r4 | logit slope per doubling (SE, p) | trend z (p) | acceleration [95% CI] |",
           "|---|---|---|---|---|---|---|---|"]
    for key in ["adopt_suffix", "adopt_tag", "adopt_suffix_slot", "index_like", "adopt_index"]:
        allx, ally, alls = [], [], []
        for m, rows in list(data.items()) + [("pooled", None)]:
            if m == "pooled":
                xs, ys, st = allx, ally, alls
                rr = {c: [y for x, y in zip(xs, ys) if x == math.log2(DOSE[c])] for c in ("dose1", "dose2", "dose4")}
                acc = None
            else:
                xs, ys = [], []
                rr = {}
                for c in ("dose1", "dose2", "dose4"):
                    v = [int(bool(r[key])) for (cc, _), r in rows.items() if cc == c]
                    rr[c] = v
                    xs += [math.log2(DOSE[c])] * len(v)
                    ys += v
                allx += xs; ally += ys; alls += [m] * len(xs)
                st = None
                acc = boot_accel(rows, key)
            if not ys:
                continue
            lr = logit_slope(xs, ys, st)
            z, p = trend_test([(math.log2(DOSE[c]), rr[c]) for c in rr])
            rates = [sum(rr[c]) / len(rr[c]) if rr[c] else float("nan") for c in ("dose1", "dose2", "dose4")]
            lrs = f"{lr[0]:+.2f} ({lr[1]:.2f}, p={fmt_p(lr[2])})" if lr else "-"
            accs = f"{acc[0]:+.2f} [{acc[1]:+.2f}, {acc[2]:+.2f}]" if acc else "-"
            zs = f"{z:+.2f} ({fmt_p(p)})" if math.isfinite(z) else "-"
            md.append(f"| {key} | {m} | {rates[0]:.2f} | {rates[1]:.2f} | {rates[2]:.2f} | {lrs} | {zs} | {accs} |")
            tgt = out["pooled"] if m == "pooled" else out["models"][m]
            tgt.setdefault("dose_response", {})[key] = dict(r1=rates[0], r2=rates[1], r4=rates[2], logit=lr, trend_z=z, trend_p=p,
                                                           acceleration=acc)
    md.append("")

    # --- 5. exposure-conditional adoption
    md += ["## 5. Exposure: adoption among agents that listed the wiki / read a seeded page before writing", "",
           "Page names are visible from `list_pages`; the body tag and the index lines are visible only by reading a page.", "",
           "| model | condition | listed pages before writing | suffix copied, listers | slot used, listers | read a prior page | suffix copied, readers | tag copied, readers | tag copied, non-readers | index_like, readers |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for m, rows in data.items():
        for c in ["dose1", "dose2", "dose4", "dose4_arbitrary_only", "dose4_functional_only", "dose1_shown", "dose2_shown", "dose4_shown", "dose4_shown_mixed"]:
            R = [r for (cc, _), r in rows.items() if cc == c]
            if not R:
                continue
            rd = [r for r in R if r["read_prior_page"]]
            nrd = [r for r in R if not r["read_prior_page"]]
            ls_ = [r for r in R if r["listed_before_write"]]
            md.append(f"| {m} | {c} | {fmt_rate(len(ls_), len(R))} | {fmt_rate(sum(r['adopt_suffix'] for r in ls_), len(ls_))} | "
                      f"{fmt_rate(sum(r['adopt_suffix_slot'] for r in ls_), len(ls_))} | {fmt_rate(len(rd), len(R))} | {fmt_rate(sum(r['adopt_suffix'] for r in rd), len(rd))} | "
                      f"{fmt_rate(sum(r['adopt_tag'] for r in rd), len(rd))} | {fmt_rate(sum(r['adopt_tag'] for r in nrd), len(nrd))} | "
                      f"{fmt_rate(sum(r['index_like'] for r in rd), len(rd))} |")
    md.append("")

    # --- 6. examples of written page names
    md += ["## 6. Most frequent written page-name shapes (qid -> Q-####, suffix code -> <SUF>, own id -> <SELF>)", ""]
    for m, rows in data.items():
        from collections import Counter
        cnt = Counter()
        for (c, _), r in rows.items():
            for n in r["written_pages"]:
                shape = n.replace(r["qid"], "Q-####").replace(r["suffix"], "<SUF>").replace(r["agent"], "<SELF>")
                cnt[(c, shape)] += 1
        md += [f"**{m}**: " + "; ".join(f"{c}: `{s}` x{k}" for (c, s), k in cnt.most_common(12)), ""]

    exp.joinpath("RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (exp / "results").mkdir(exist_ok=True)
    (exp / "results" / "summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    plot(data, exp / "figures")
    return out


def plot(data: dict, figdir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figdir.mkdir(parents=True, exist_ok=True)
    series = [("adopt_suffix", "suffix code (arbitrary)", "#1f77b4", "o"), ("adopt_tag", "body tag (arbitrary)", "#ff7f0e", "s"),
              ("index_like", "index page (functional)", "#2ca02c", "^"), ("adopt_suffix_slot", "trailing code slot (any code)", "#9467bd", "D")]
    xpos = {"isolated": 0, "dose1": 1, "dose2": 2, "dose4": 3}
    n = len(data)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n, 3.4), sharey=True, squeeze=False)
    for ax, (m, rows) in zip(axes[0], data.items()):
        for key, label, col, mk in series:
            xs, ps, lo, hi = [], [], [], []
            for c, x in xpos.items():
                R = [r for (cc, _), r in rows.items() if cc == c]
                if not R:
                    continue
                p, l, h = wilson(sum(bool(r[key]) for r in R), len(R))
                xs.append(x); ps.append(p); lo.append(p - l); hi.append(h - p)
            ax.errorbar(xs, ps, yerr=[lo, hi], color=col, marker=mk, ms=5, capsize=2, lw=1.4, label=label)
            sx, sp = [], []
            for c, x in (("dose1_shown", 1), ("dose2_shown", 2), ("dose4_shown", 3)):
                R = [r for (cc, _), r in rows.items() if cc == c]
                if R:
                    sx.append(x); sp.append(sum(bool(r[key]) for r in R) / len(R))
            if sx:
                ax.plot(sx, sp, color=col, marker=mk, ms=4, ls="--", lw=1, mfc="white", alpha=0.9)
            R = [r for (cc, _), r in rows.items() if cc == "dose4_shown_mixed"]
            if R:
                k2 = "adopt_any_prior_code" if key == "adopt_suffix" else "adopt_any_prior_tag" if key == "adopt_tag" else key
                ax.scatter([3.12], [sum(bool(r[k2]) for r in R) / len(R)], color=col, marker="x", s=36, zorder=4)
            R = [r for (cc, _), r in rows.items() if cc == "neutral4"]
            if R:
                ax.scatter([3.25], [sum(bool(r[key]) for r in R) / len(R)], facecolors="none", edgecolors=col, marker=mk, s=40, zorder=3)
        ax.set_xticks(list(xpos.values()) + [3.25])
        ax.set_xticklabels(["isolated", "1", "2", "4", "n4"], fontsize=8)
        ax.set_title(m, fontsize=10)
        ax.set_xlabel("prior adopters (dose)", fontsize=9)
        ax.set_ylim(-0.03, 1.03)
        ax.grid(alpha=0.3)
    axes[0][0].set_ylabel("share of trials")
    axes[0][-1].legend(fontsize=7, loc="upper left")
    fig.suptitle("Seeded convention diffusion: adoption vs number of prior adopters (solid = agent must list the wiki itself; dashed = listing shown; x = dose4_shown_mixed, any prior code; hollow at n4 = neutral4)", fontsize=10)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(figdir / f"dose_response.{ext}", dpi=200)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="experiments/convention_diffusion")
    a = ap.parse_args(argv)
    analyze(Path(a.exp))
    print(f"wrote {Path(a.exp) / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
