"""Generate results/RESULTS.md and results/macros.json from the machine-readable outputs.

Every number quoted in the paper is present in macros.json (flat key -> value),
so a script can turn it into LaTeX macros.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import pandas as pd


def f(x, nd=3):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    if isinstance(x, (int,)) or (isinstance(x, float) and x.is_integer() and abs(x) >= 10):
        return f"{int(x):,}"
    return f"{x:.{nd}f}"


def pv(p):
    if p is None or (isinstance(p, float) and not math.isfinite(p)):
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def macro_key(*parts):
    s = "".join(re.sub(r"[^A-Za-z]", "", p.title()) for p in parts)
    return s


def build(out: Path):
    S = json.load(open(out / "results.json", encoding="utf-8"))
    main = pd.read_csv(out / "main_results.csv")
    cat = pd.read_csv(out / "technique_catalogue.csv")
    rob = pd.read_csv(out / "robustness.csv") if (out / "robustness.csv").exists() else pd.DataFrame()
    from .techniques import catalogue_records
    recs = pd.DataFrame(catalogue_records())
    cat = cat.drop(columns=[c for c in ("function", "function_note") if c in cat]).merge(
        recs[["name", "function", "function_note"]], left_on="token", right_on="name", how="left").drop(columns="name")
    cat.to_csv(out / "technique_catalogue.csv", index=False)
    tj = []
    for _, r in cat.iterrows():
        d = {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.to_dict().items()}
        tj.append(d)
    with open(out / "techniques.json", "w", encoding="utf-8") as fh:
        json.dump({"tokens": tj, "function_definitions": {
            "functional": "solves a task or environment constraint (data access, timing, liveness, egress)",
            "arbitrary": "naming/formatting convention with no functional value in itself; placebos are arbitrary by construction"}},
            fh, indent=1, default=str)
    M: dict = {}
    D = S["dataset"]
    for k, v in D.items():
        if isinstance(v, (int, float)):
            M[macro_key("data", k)] = v
    tech = cat[cat.kind == "technique"]
    plac = cat[cat.kind == "placebo"]
    M["NTechniques"] = len(tech)
    M["NPlacebos"] = len(plac)
    M["ValidatedTotal"] = int(tech["validated_n"].sum())
    M["PrecisionMin"] = float(tech["precision"].min())
    M["PrecisionStrictPrng"] = float(tech.set_index("token").loc["prng_seed", "precision_strict"])
    M["TechAdopterEvents"] = int(tech["adopters"].sum())
    M["PlaceboAdopterEvents"] = int(plac["adopters"].sum())
    M["TechFirstRevShareMedian"] = float(tech["share_adopt_at_first_revision"].median())
    M["PlacFirstRevShareMedian"] = float(plac["share_adopt_at_first_revision"].median())
    M["TechFirstRevShareMin"] = float(tech["share_adopt_at_first_revision"].min())
    M["TechFirstRevShareMax"] = float(tech["share_adopt_at_first_revision"].max())
    for _, row in cat.iterrows():
        k = macro_key(row["token"])
        M[f"{k}Adopters"] = int(row["adopters"])
        M[f"{k}FirstRevShare"] = row["share_adopt_at_first_revision"]
    for _, row in main.iterrows():
        k = macro_key(row["token"])
        for c in ("E_prior_obs", "E_prior_null", "E_prior_excess", "E_prior_p", "E_here_obs", "E_here_null",
                  "E_here_excess", "E_here_p", "E_cross_excess", "E_cross_p", "holm_E_prior",
                  "hz_E_prior_rr", "hz_E_prior_rr_lo", "hz_E_prior_rr_hi", "hz_E_here_rr",
                  "accel_rho_obs", "accel_rho_null", "p_accel_stronger", "holm_accel",
                  "t50_obs_h", "t50_null_h", "firstpos_obs", "firstpos_null", "median_eligible_revs", "lag_obs_h", "lag_null_h", "lag_p_shorter", "holm_lag"):
            if c in row and pd.notna(row[c]):
                M[k + macro_key(c)] = float(row[c])
    for k, v in S["pooled"].items():
        for kk in ("mean_excess", "mean_observed", "mean_null", "p_upper"):
            if kk in v:
                M[macro_key("pooled", k, kk)] = v[kk]
    import numpy as np
    rng = np.random.default_rng(20261109)
    te = main.loc[main.kind == "technique", "E_here_excess"].to_numpy()
    pe = main.loc[main.kind == "placebo", "E_here_excess"].to_numpy()
    bs = [rng.choice(te, len(te)).mean() - rng.choice(pe, len(pe)).mean() for _ in range(5000)]
    S["contrast_E_here"] = {"tech_minus_placebo_excess": float(te.mean() - pe.mean()),
                            "ci": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]}
    for k in ("contrast_E_prior", "contrast_E_cross", "contrast_E_here"):
        M[macro_key(k)] = S[k]["tech_minus_placebo_excess"]
        M[macro_key(k, "lo")], M[macro_key(k, "hi")] = S[k]["ci"]
    for k, v in S.get("choice", {}).items():
        for kk in ("odds_ratio", "n_events", "n_informative", "n_labels", "share_chosen_exposed",
                   "share_alternatives_exposed", "mean_choice_set"):
            M[macro_key("choice", k, kk)] = v.get(kk)
        M[macro_key("choice", k, "lo")], M[macro_key("choice", k, "hi")] = v["or_ci"]
    # technique vs placebo odds-ratio contrast (normal approximation on the log scale,
    # SE recovered from each bootstrap CI; the two bootstraps are independent)
    ch = S.get("choice", {})
    for col in ("E_prior", "E_cross", "E_here"):
        t, p_ = ch.get(f"techniques_{col}"), ch.get(f"placebos_{col}")
        if t and p_:
            se = lambda v: (math.log(v["or_ci"][1]) - math.log(v["or_ci"][0])) / 3.92  # noqa: E731
            d = math.log(t["odds_ratio"]) - math.log(p_["odds_ratio"])
            sd = math.sqrt(se(t) ** 2 + se(p_) ** 2)
            z = d / sd
            M[macro_key("ror", col)] = math.exp(d)
            M[macro_key("ror", col, "lo")] = math.exp(d - 1.96 * sd)
            M[macro_key("ror", col, "hi")] = math.exp(d + 1.96 * sd)
            M[macro_key("ror", col, "p")] = math.erfc(abs(z) / math.sqrt(2))
            S.setdefault("ror", {})[col] = (math.exp(d), math.exp(d - 1.96 * sd), math.exp(d + 1.96 * sd),
                                           math.erfc(abs(z) / math.sqrt(2)))
    for vname, vv in S.get("robustness_choice", {}).items():
        for k, v in vv.items():
            if v:
                M[macro_key("rob", vname, k, "or")] = v["odds_ratio"]
                M[macro_key("rob", vname, k, "lo")], M[macro_key("rob", vname, k, "hi")] = v["or_ci"]
    for vname, info in S.get("robustness_info", {}).items():
        for k, v in info.items():
            if isinstance(v, (int, float)):
                M[macro_key("rob", vname, k)] = v
    for vname, vv in S.get("robustness_pooled", {}).items():
        for kind, v in vv.items():
            if v:
                M[macro_key("rob", vname, kind, "excess")] = v["mean_excess"]
                M[macro_key("rob", vname, kind, "p")] = v["p_upper"]
    # counts of significant per-token tests after Holm
    for c in ("holm_E_prior", "holm_E_cross", "holm_lag", "holm_accel", "holm_t50"):
        if c in main:
            t = main[main.kind == "technique"][c]
            M[macro_key("n sig", c)] = int((t < 0.05).sum())
    tm = main[main.kind == "technique"]
    M["NAccelBelowNullMedian"] = int((tm["accel_rho_obs"] < tm["accel_rho_null"]).sum())
    M["NPageNovelMajority"] = int((tech["page_novel_adoptions"] > tech["adopters"] / 2).sum())
    M = {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in M.items()}
    with open(out / "macros.json", "w", encoding="utf-8") as fh:
        json.dump(M, fh, indent=1, sort_keys=True)

    from .figures import choice_odds
    (out / "figures").mkdir(exist_ok=True)
    choice_odds(S, out / "figures" / "fig_choice_odds.png")

    # ------------------------------------------------------------ RESULTS.md
    L = []
    L.append("# RESULTS: Spread or Rediscovery?\n")
    L.append("All numbers are generated by `python -m sord.report` from `results.json` and the CSVs in "
             "this directory (`macros.json` holds every quoted number as a flat key -> value map).\n")
    L.append("## Dataset and population\n")
    for k, v in D.items():
        L.append(f"- {k}: {v}")
    L.append("")
    L.append("## Technique catalogue and regex precision\n")
    L.append("Precision = share of 10 randomly sampled adoption events per technique (seeded) whose "
             "matched text refers to the technique (hand-read; `annotations/validation_labels.csv`). "
             "Strict precision for `prng_seed` counts only text that describes performing the seed search "
             "(the remaining matches relay RNG-derived predictions).\n")
    L.append("| token | family | function | adopters | founders | page-novel | first appearance | precision (n) | strict | share adopted at label's first revision |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, r in cat.iterrows():
        L.append(f"| {r.token} | {r.family} | {r.function} | {r.adopters} | {r.founders} | {r.page_novel_adoptions} | "
                 f"{str(r.first_appearance)[:16]} | {f(r.precision, 2)} ({r.validated_n}) | {f(r.precision_strict, 2)} | "
                 f"{f(r.share_adopt_at_first_revision, 2)} |")
    L.append("")
    L.append("## Test (b): re-timing permutation test (rediscovery null)\n")
    L.append("Observed = fraction of non-founder adopters exposed before adoption; null = same with each "
             "adoption re-timed to a uniformly drawn revision of the same label saved after the token's "
             "first appearance. Excess = observed - null with 95% bootstrap CI over adopters; p = one-sided "
             "(observed > null); Holm across the 15 techniques (placebos: separate family).\n")
    L.append("| token | kind | tested | E_prior obs | null | excess [95% CI] | p | Holm | E_here obs | null | p | E_cross excess | p |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in main.iterrows():
        L.append(f"| {r.token} | {r.kind} | {r.tested} | {f(r.E_prior_obs)} | {f(r.E_prior_null)} | "
                 f"{f(r.E_prior_excess)} [{f(r.E_prior_excess_lo)}, {f(r.E_prior_excess_hi)}] | {pv(r.E_prior_p)} | "
                 f"{pv(r.get('holm_E_prior'))} | {f(r.E_here_obs)} | {f(r.E_here_null)} | {pv(r.E_here_p)} | "
                 f"{f(r.E_cross_excess)} | {pv(r.E_cross_p)} |")
    L.append("")
    L.append("Pooled (equal weight per token):\n")
    for k, v in S["pooled"].items():
        L.append(f"- {k}: mean excess {f(v.get('mean_excess'))}, observed {f(v.get('mean_observed'))}, "
                 f"null {f(v.get('mean_null'))}, p(upper) {pv(v.get('p_upper'))}")
    for k in ("contrast_E_prior", "contrast_E_cross", "contrast_E_here"):
        L.append(f"- {k} (technique minus placebo mean excess): {f(S[k]['tech_minus_placebo_excess'])} "
                 f"[{f(S[k]['ci'][0])}, {f(S[k]['ci'][1])}]")
    L.append("")
    L.append("Position diagnostic: share of tested adopters whose adoption is their first eligible revision "
             "(observed) vs the re-timing expectation (mean 1/n_eligible):\n")
    L.append("| token | first-position obs | null | median eligible revisions |")
    L.append("|---|---|---|---|")
    for _, r in main.iterrows():
        if "firstpos_obs" in r:
            L.append(f"| {r.token} | {f(r.firstpos_obs)} | {f(r.firstpos_null)} | {f(r.median_eligible_revs, 1)} |")
    tt = main[main.kind == "technique"]
    pp = main[main.kind == "placebo"]
    M["FirstPosTechMean"] = float(tt["firstpos_obs"].mean())
    M["FirstPosTechNullMean"] = float(tt["firstpos_null"].mean())
    M["FirstPosPlacMean"] = float(pp["firstpos_obs"].mean())
    M["FirstPosPlacNullMean"] = float(pp["firstpos_null"].mean())
    with open(out / "macros.json", "w", encoding="utf-8") as fh:
        json.dump(M, fh, indent=1, sort_keys=True)
    L.append("")
    L.append("Exposure-to-adoption lag (median hours, exposed adopters) vs null:\n")
    L.append("| token | lag obs (h) | lag null (h) | p(shorter) | Holm |")
    L.append("|---|---|---|---|---|")
    for _, r in main.iterrows():
        L.append(f"| {r.token} | {f(r.lag_obs_h)} | {f(r.lag_null_h)} | {pv(r.lag_p_shorter)} | {pv(r.get('holm_lag'))} |")
    L.append("")
    L.append("## Within-label choice design (conditional logit)\n")
    L.append("Each adoption is a choice among the tokens (same set) that existed and that the label had not "
             "yet adopted; covariate = the label's exposure to each alternative at that moment; alternative "
             "fixed effects; 95% CI from cluster bootstrap over labels.\n")
    L.append("| set / exposure | events | informative | labels | OR [95% CI] | chosen exposed | alternatives exposed |")
    L.append("|---|---|---|---|---|---|---|")
    for k, v in S.get("choice", {}).items():
        if v:
            L.append(f"| {k} | {v['n_events']} | {v['n_informative']} | {v['n_labels']} | {f(v['odds_ratio'], 2)} "
                     f"[{f(v['or_ci'][0], 2)}, {f(v['or_ci'][1], 2)}] | {f(v['share_chosen_exposed'])} | "
                     f"{f(v['share_alternatives_exposed'])} |")
    L.append("")
    for col, v in S.get("ror", {}).items():
        L.append(f"- Technique/placebo odds-ratio ratio ({col}): {f(v[0], 2)} [{f(v[1], 2)}, {f(v[2], 2)}], "
                 f"two-sided p = {pv(v[3])} (log-scale normal approximation)")
    L.append("")
    L.append("## Test (a): adoption hazard, exposed vs unexposed revision opportunities\n")
    L.append("| token | kind | RR prior [95% CI] | rate exp / unexp | opps exp / unexp | RR same-page [95% CI] |")
    L.append("|---|---|---|---|---|---|")
    for _, r in main.iterrows():
        L.append(f"| {r.token} | {r.kind} | {f(r.hz_E_prior_rr, 2)} [{f(r.hz_E_prior_rr_lo, 2)}, {f(r.hz_E_prior_rr_hi, 2)}] | "
                 f"{f(r.hz_E_prior_rate1, 4)} / {f(r.hz_E_prior_rate0, 4)} | {r.hz_E_prior_opps1} / {r.hz_E_prior_opps0} | "
                 f"{f(r.hz_E_here_rr, 2)} [{f(r.hz_E_here_rr_lo, 2)}, {f(r.hz_E_here_rr_hi, 2)}] |")
    L.append("")
    L.append("## Burst diagnostic\n")
    L.append("Busiest 24-hour window of adoptions per token, compared with the share of all agent labels whose "
             "first revision falls in the same window.\n")
    L.append("| token | window start | adopters in window | share of adopters | adopters there at their first revision | label arrivals in window | share of all labels | share citing the shared data file |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in main.iterrows():
        if "burst_adopters_in_window" in r and pd.notna(r.burst_adopters_in_window):
            L.append(f"| {r.token} | {str(r.burst_window_start)[:16]} | {int(r.burst_adopters_in_window)} | "
                     f"{f(r.burst_share_adopters_in_window, 2)} | {int(r.burst_window_adopters_at_first_revision)} | "
                     f"{int(r.burst_label_arrivals_in_window)} | {f(r.burst_share_all_labels_arriving_in_window, 2)} | "
                     f"{f(r.burst_window_share_targeting_county_file, 2)} |")
            k = macro_key(r.token)
            M[k + "BurstShare"] = float(r.burst_share_adopters_in_window)
            M[k + "BurstN"] = int(r.burst_adopters_in_window)
            M[k + "BurstFirstRev"] = int(r.burst_window_adopters_at_first_revision)
            M[k + "BurstArrivals"] = int(r.burst_label_arrivals_in_window)
            M[k + "BurstArrivalShare"] = float(r.burst_share_all_labels_arriving_in_window)
            M[k + "BurstCountyShare"] = float(r.burst_window_share_targeting_county_file)
    with open(out / "macros.json", "w", encoding="utf-8") as fh:
        json.dump(M, fh, indent=1, sort_keys=True)
    L.append("")
    L.append("## Tests (d, e): diffusion speed and acceleration\n")
    L.append("T50 = hours from first appearance until half of adopting labels had adopted. rho = Spearman "
             "correlation between k and the k-th inter-adoption gap (negative = gaps shrink). p(accel) = "
             "share of null rho <= observed.\n")
    L.append("| token | T50 obs (h) | T50 null (h) | p(faster) | rho obs | rho null | p(accel) | Holm |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in main.iterrows():
        L.append(f"| {r.token} | {f(r.t50_obs_h, 1)} | {f(r.t50_null_h, 1)} | {pv(r.p_t50_faster)} | {f(r.accel_rho_obs)} | "
                 f"{f(r.accel_rho_null)} | {pv(r.p_accel_stronger)} | {pv(r.get('holm_accel'))} |")
    L.append("")
    if len(rob):
        L.append("## Robustness\n")
        for k, v in S.get("robustness_info", {}).items():
            L.append(f"- {k}: {v}")
        L.append("")
        L.append("Pooled E_prior excess per variant:\n")
        for vname, vv in S.get("robustness_pooled", {}).items():
            for kind, v in vv.items():
                if v:
                    L.append(f"- {vname} / {kind}: mean excess {f(v['mean_excess'])}, p(upper) {pv(v['p_upper'])}")
        L.append("")
        L.append("Choice-design odds ratios per variant:\n")
        for vname, vv in S.get("robustness_choice", {}).items():
            for k, v in vv.items():
                if v:
                    L.append(f"- {vname} / {k}: OR {f(v['odds_ratio'], 2)} [{f(v['or_ci'][0], 2)}, {f(v['or_ci'][1], 2)}]"
                             f" (events {v['n_events']}, informative {v['n_informative']})")
        L.append("")
        L.append("Per-token robustness table: `robustness.csv`.\n")
    L.append("## Figures\n")
    for p in sorted((out / "figures").glob("*.png")):
        L.append(f"- `figures/{p.name}`")
    (out / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    a = ap.parse_args(argv)
    build(Path(a.out))


if __name__ == "__main__":
    main()
