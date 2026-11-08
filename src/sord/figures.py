"""Figures (PNG, 200 dpi). Techniques blue, placebos orange, null gray."""
from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

TECH = "#2a78d6"
PLAC = "#eb6834"
NULL = "#8c8b86"
INK = "#0b0b0b"
INK2 = "#52514e"
DPI = 200
REF = pd.Timestamp("2026-01-01", tz="UTC")

plt.rcParams.update({
    "font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "figure.facecolor": "white",
})


def _grid(n, ncol=5, w=2.2, h=1.7):
    nrow = math.ceil(n / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(w * ncol, h * nrow), squeeze=False)
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    return fig, axes.flat


def diffusion_curves(results, tech, path):
    fig, axes = _grid(len(tech))
    for ax, n in zip(axes, tech):
        c = results[n].get("curve")
        if not c:
            ax.set_title(n, fontsize=8)
            continue
        obs = (REF + pd.to_timedelta(c["_obs_times"], unit="s")).tz_localize(None)
        nt = c["_null_times"]
        k = np.arange(1, nt.shape[1] + 1)
        q = np.quantile(nt, [0.025, 0.5, 0.975], axis=0)
        to_dt = lambda a: (REF + pd.to_timedelta(a, unit="s")).tz_localize(None)  # noqa: E731
        ax.fill_betweenx(k, to_dt(q[0]), to_dt(q[2]), color=NULL, alpha=0.3, lw=0, label="re-timing null (95%)")
        ax.step(obs, np.arange(1, len(obs) + 1), where="post", color=TECH, lw=1.5, label="observed")
        ax.set_title(f"{n} (n={len(obs)})", fontsize=8)
        ax.tick_params(axis="x", labelrotation=45, labelsize=6)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m-%d"))
    axes[0].legend(fontsize=6, loc="upper left")
    fig.supylabel("cumulative adopting labels")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def permutation_nulls(results, names, path, col="E_prior"):
    fig, axes = _grid(len(names))
    for ax, n in zip(axes, names):
        s = results[n].get("shuffle", {})
        if col not in s:
            ax.set_title(n, fontsize=8)
            continue
        ax.hist(s[col]["null_samples"], bins=30, color=NULL, alpha=0.8)
        color = TECH if results[n]["kind"] == "technique" else PLAC
        ax.axvline(s[col]["observed"], color=color, lw=2)
        ax.set_title(f"{n}\np(upper)={s[col]['p_upper']:.3f}", fontsize=7)
        ax.set_yticks([])
    fig.supxlabel(f"fraction of adopters with prior exposure ({col}); gray = re-timing null, line = observed")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def hazard_forest(main_df, path):
    cols = [("hz_E_prior", "prior exposure (other writes)"), ("hz_E_here", "token on the page being edited")]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 5.2), sharey=True)
    d = main_df.reset_index(drop=True)
    y = np.arange(len(d))[::-1]
    for ax, (c, title) in zip(axes, cols):
        for yi, (_, row) in zip(y, d.iterrows()):
            rr, lo, hi = row[f"{c}_rr"], row[f"{c}_rr_lo"], row[f"{c}_rr_hi"]
            color = TECH if row["kind"] == "technique" else PLAC
            if not (rr == rr) or rr <= 0:
                ax.plot([], [])
                ax.text(0.12, yi, "no exposed events", fontsize=6, color=INK2, va="center")
                continue
            if lo == lo and hi == hi:
                ax.plot([lo, hi], [yi, yi], color=color, lw=1.2)
            ax.plot(rr, yi, "o", color=color, ms=4)
        ax.axvline(1, color=INK2, lw=0.8, ls="--")
        ax.set_xscale("log")
        ax.set_xlim(0.1, 300)
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("adoption hazard ratio, exposed / unexposed (log)")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(d["token"], fontsize=7)
    axes[0].plot([], [], "o", color=TECH, label="technique")
    axes[0].plot([], [], "o", color=PLAC, label="placebo")
    axes[0].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def placebo_comparison(main_df, path):
    cols = [("E_prior", "prior exposure (other writes)"), ("E_here", "token on the page being edited")]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 5.2), sharey=True)
    d = main_df.reset_index(drop=True)
    y = np.arange(len(d))[::-1]
    for ax, (c, title) in zip(axes, cols):
        for yi, (_, row) in zip(y, d.iterrows()):
            if f"{c}_excess" not in row or not (row[f"{c}_excess"] == row[f"{c}_excess"]):
                continue
            color = TECH if row["kind"] == "technique" else PLAC
            ax.plot([row[f"{c}_excess_lo"], row[f"{c}_excess_hi"]], [yi, yi], color=color, lw=1.2)
            ax.plot(row[f"{c}_excess"], yi, "o", color=color, ms=4)
        ax.axvline(0, color=INK2, lw=0.8, ls="--")
        ax.set_title(title, fontsize=8)
        ax.set_xlabel("observed - null exposed fraction (95% CI)")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(d["token"], fontsize=7)
    axes[0].plot([], [], "o", color=TECH, label="technique")
    axes[0].plot([], [], "o", color=PLAC, label="placebo")
    axes[0].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def choice_odds(summary, path):
    ch = summary.get("choice", {})
    rows = [("E_prior", "prior exposure"), ("E_cross", "prior exposure, other page"), ("E_here", "on page being edited")]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    yt, yl = [], []
    for i, (c, lab) in enumerate(rows):
        kinds = (("techniques", TECH, "all techniques"), ("fetchproxy", "#1baf7a", "fetch-proxy only"),
                 ("envcoord", "#6250d6", "environment+coordination"), ("placebos", PLAC, "placebos"))
        for j, (kind, color, kname) in enumerate(kinds):
            r = ch.get(f"{kind}_{c}")
            if not r:
                continue
            y = -(i * 5 + j)
            ax.plot(r["or_ci"], [y, y], color=color, lw=1.4)
            ax.plot(r["odds_ratio"], y, "o", color=color, ms=5)
            yt.append(y)
            yl.append(f"{lab}: {kname}")
    ax.axvline(1, color=INK2, lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_yticks(yt)
    ax.set_yticklabels(yl, fontsize=7)
    ax.set_xlabel("odds ratio for choosing an exposed alternative\n(conditional logit, 95% cluster-bootstrap CI)")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def acceleration(main_df, results, tech, path):
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    y = np.arange(len(tech))[::-1]
    for yi, n in zip(y, tech):
        c = results[n].get("curve", {})
        if "accel_rho_obs" not in c:
            continue
        lo, hi = c["accel_rho_null_ci"]
        ax.plot([lo, hi], [yi, yi], color=NULL, lw=4, alpha=0.6, solid_capstyle="butt")
        ax.plot(c["accel_rho_obs"], yi, "o", color=TECH, ms=5)
    ax.axvline(0, color=INK2, lw=0.8, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(tech, fontsize=7)
    ax.set_xlabel("Spearman rho(k, k-th inter-adoption gap); <0 = acceleration\n"
                  "dot = observed, bar = 95% re-timing null")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def make_all(results, designs, adopts, main_df, rob_df, outdir, tech, plac, summary=None):
    diffusion_curves(results, tech, outdir / "fig_diffusion_curves.png")
    permutation_nulls(results, tech, outdir / "fig_permutation_null_techniques.png")
    permutation_nulls(results, plac, outdir / "fig_permutation_null_placebos.png")
    hazard_forest(main_df, outdir / "fig_exposed_vs_unexposed_hazard.png")
    placebo_comparison(main_df, outdir / "fig_placebo_comparison.png")
    acceleration(main_df, results, tech, outdir / "fig_acceleration.png")
    if summary is not None:
        choice_odds(summary, outdir / "fig_choice_odds.png")
