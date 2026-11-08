"""Reproduce every number, table and figure.

    python -m sord.run_all --data <collusion-wiki dir> --out results/
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import figures
from .adoption import adoption_table, first_appearance, token_flags
from .exposure import eligible_rows, exposure_table
from .load import agent_population, load_dataset, merge_labels_by_signoff
from .stats import (EXPO_COLS, ShuffleDesign, build_choice_data, conditional_logit_exposure,
                    curve_and_acceleration, hazard_table, holm, shuffle_test, wilson_ci)
from .techniques import ALL_TOKENS, PLACEBOS, TECHNIQUES

ROOT = Path(__file__).resolve().parents[2]


def analyse_token(r, pop, tok, B, seed, with_hazard=True):
    flags = token_flags(r, tok)
    first_order, t0 = first_appearance(r, flags)
    adopt = adoption_table(r, flags, pop)
    out = {"token": tok.name, "kind": tok.kind, "family": tok.family,
           "revisions_with_token": int(flags["body_has"].sum()),
           "revisions_adding_token": int(flags["added_has"].sum()),
           "n_adopters": int(len(adopt)), "n_founders": int(adopt["founder"].sum()),
           "n_page_novel": int(adopt["page_novel"].sum())}
    if first_order is None or len(adopt) == 0:
        return out, adopt, None, None, first_order
    out["t0"] = pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(seconds=t0)
    expo = exposure_table(r, flags, pop)
    elig = eligible_rows(expo, adopt, t0, first_order)
    design = ShuffleDesign(elig)
    st = shuffle_test(design, B=B, seed=seed)
    out["shuffle"] = st
    if design.n:
        founder_ts = adopt.loc[adopt["founder"], "ts"].to_numpy()
        out["curve"] = curve_and_acceleration(design, founder_ts, t0, st["_draws"][:2000])
    if with_hazard:
        out["hazard"] = {c: hazard_table(expo, adopt, t0, first_order, col=c, seed=seed)
                         for c in ("E_prior", "E_cross", "E_here", "E_wiki")}
    # share of (non-founder) adopters whose adoption is their label's first revision
    first_rev = r[r["label"].isin(pop)].groupby("label")["order"].min()
    nf = adopt[~adopt["founder"]]
    if len(nf):
        at_first = (nf["order"].to_numpy() == first_rev.reindex(nf["label"]).to_numpy())
        out["share_adopt_at_first_revision"] = float(at_first.mean())
        out["share_adopt_at_first_revision_ci"] = list(wilson_ci(int(at_first.sum()), len(nf)))
    return out, adopt, design, expo, first_order


def pooled(results, names, col="E_prior"):
    """Equal-weight mean of per-token excess, and pooled permutation p-value."""
    ex = [results[n]["shuffle"][col]["excess"] for n in names
          if "shuffle" in results[n] and col in results[n]["shuffle"]]
    obs = [results[n]["shuffle"][col]["observed"] for n in names if "shuffle" in results[n] and col in results[n]["shuffle"]]
    nulls = [results[n]["shuffle"][col]["null_samples"] for n in names if "shuffle" in results[n] and col in results[n]["shuffle"]]
    if not ex:
        return {}
    m_obs = float(np.mean(obs))
    m_null = np.mean(np.vstack(nulls), axis=0)
    return {"n_tokens": len(ex), "mean_excess": float(np.mean(ex)),
            "mean_observed": m_obs, "mean_null": float(m_null.mean()),
            "p_upper": float((1 + (m_null >= m_obs - 1e-12).sum()) / (len(m_null) + 1))}


def run_variant(r, pop, tokens, B, seed):
    res = {}
    for tok in tokens:
        o, a, _, e, fo = analyse_token(r, pop, tok, B, seed, with_hazard=False)
        res[tok.name] = o
        res.setdefault("_cl", {})[tok.name] = (e, a, fo)
    return res


def strip(o):
    """JSON-safe copy without private arrays."""
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if not k.startswith("_") and k != "null_samples"}
    if isinstance(o, (list, tuple)):
        return [strip(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    return o


def validation_precision(adopts: dict, ann_path: Path, sample_out: Path | None, r: pd.DataFrame,
                         n: int = 10, seed: int = 7) -> pd.DataFrame:
    """Deterministic validation sample (10 adoption events per technique) and
    precision from hand annotations (annotations/validation_labels.csv)."""
    rows = []
    for tok in TECHNIQUES:
        a = adopts[tok.name]
        s = a.sample(min(n, len(a)), random_state=seed) if len(a) else a
        for rid, lab in zip(s["rev_id"], s["label"]):
            rows.append({"token": tok.name, "rev_id": rid, "label": lab})
    sample = pd.DataFrame(rows)
    if sample_out is not None:  # local reading aid only; not part of results/
        body = dict(zip(r["rev_id"], r["added"]))
        with open(sample_out, "w", encoding="utf-8") as fh:
            for row in rows:
                rx = next(t for t in TECHNIQUES if t.name == row["token"]).rx
                lines = [ln for ln in body[row["rev_id"]].splitlines() if rx.search(ln)]
                fh.write(f"## {row['token']} | {row['rev_id']} | {row['label']}\n")
                for ln in lines[:2]:
                    m = rx.search(ln)
                    fh.write("   " + ln[max(0, m.start() - 160): m.end() + 160] + "\n")
    if ann_path.exists():
        ann = pd.read_csv(ann_path)
        sample = sample.merge(ann[["token", "rev_id", "correct", "strict_correct", "note"]],
                              on=["token", "rev_id"], how="left")
    else:
        sample["correct"] = np.nan
        sample["strict_correct"] = np.nan
        sample["note"] = ""
    return sample


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="results")
    ap.add_argument("--B", type=int, default=5000, help="permutation draws")
    ap.add_argument("--seed", type=int, default=20261109)
    ap.add_argument("--sample-out", default=None, help="write validation contexts here (local only)")
    ap.add_argument("--skip-robustness", action="store_true")
    ap.add_argument("--n-boot-cl", type=int, default=200, help="bootstrap reps, conditional logit")
    args = ap.parse_args(argv)
    out = Path(args.out)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    r, labels = load_dataset(args.data)
    pop, pop_info = agent_population(r, labels)
    summary = {"dataset": {"revisions": int(len(r)), "pages": int(r["page_id"].nunique()),
                           "wikis": r["wiki"].value_counts().to_dict(),
                           "first_revision": r["t"].min().isoformat(), "last_revision": r["t"].max().isoformat(),
                           "uncertainty_seconds_values": sorted(r["uncertainty"].unique().tolist()),
                           "distinct_ip16_in_revisions": int(r["ip16"].nunique()) if "ip16" in r else None,
                           **pop_info}}
    lab_ip16 = r[r["label"].isin(pop)].groupby("label")["ip16"].nunique()
    summary["dataset"]["median_ip16_per_label"] = float(lab_ip16.median())
    summary["dataset"]["share_labels_multi_ip16"] = float((lab_ip16 > 1).mean())
    daily = r["t"].dt.strftime("%Y-%m-%d").value_counts()
    summary["dataset"]["busiest_day"] = str(daily.idxmax())
    summary["dataset"]["busiest_day_revisions"] = int(daily.max())
    ra = r[r["label"].isin(pop)].groupby("label")["ts"].agg(["count", "min", "max"])
    summary["dataset"]["agent_labels_with_revisions"] = int(len(ra))
    summary["dataset"]["median_revisions_per_label"] = float(ra["count"].median())
    summary["dataset"]["share_single_revision_labels"] = float((ra["count"] == 1).mean())
    summary["dataset"]["median_label_span_minutes"] = float(((ra["max"] - ra["min"]) / 60).median())
    summary["dataset"]["p90_label_span_hours"] = float(((ra["max"] - ra["min"]) / 3600).quantile(0.9))

    # ------------------------------------------------------------ main run
    results, adopts, designs, expos, forders = {}, {}, {}, {}, {}
    for i, tok in enumerate(ALL_TOKENS):
        o, a, d, e, fo = analyse_token(r, pop, tok, args.B, args.seed + i)
        results[tok.name], adopts[tok.name], designs[tok.name] = o, a, d
        expos[tok.name], forders[tok.name] = e, fo
        print(f"  {tok.name}: {o['n_adopters']} adopters", flush=True)
    # burst diagnostic: busiest 24h window of adoptions vs label arrivals in that window
    first_seen = r[r["label"].isin(pop)].groupby("label")["ts"].min().to_numpy()
    for tok in ALL_TOKENS:
        a = adopts[tok.name]
        if len(a) < 5:
            continue
        t = np.sort(a["ts"].to_numpy())
        cnt = np.searchsorted(t, t + 86400, side="left") - np.arange(len(t))
        i = int(np.argmax(cnt))
        lo, hi = t[i], t[i] + 86400
        in_win = a[(a["ts"] >= lo) & (a["ts"] < hi)]
        arrivals = int(((first_seen >= lo) & (first_seen < hi)).sum())
        new_in_win = int((in_win["order"].to_numpy() ==
                          r[r["label"].isin(set(in_win["label"]))].groupby("label")["order"].min()
                          .reindex(in_win["label"]).to_numpy()).sum())
        results[tok.name]["burst"] = {
            "window_start": (pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(seconds=float(lo))).isoformat(),
            "adopters_in_window": int(cnt[i]), "share_adopters_in_window": float(cnt[i] / len(t)),
            "label_arrivals_in_window": arrivals, "share_all_labels_arriving_in_window": float(arrivals / len(first_seen)),
            "window_adopters_at_first_revision": new_in_win,
            # shared task target: the 18 June cohort fetched one public data file
            "window_share_targeting_county_file": float(np.mean([
                "county.json" in t for t in r.set_index("rev_id").loc[in_win["rev_id"], "added"]]))}
    adopt_all = pd.concat([a.assign(token=k) for k, a in adopts.items()], ignore_index=True)
    adopt_all.drop(columns=["rev_id"]).to_csv(out / "adoptions.csv", index=False)

    tech = [t.name for t in TECHNIQUES]
    plac = [t.name for t in PLACEBOS]
    p_main = {n: results[n]["shuffle"]["E_prior"]["p_upper"] for n in tech if "E_prior" in results[n].get("shuffle", {})}
    p_cross = {n: results[n]["shuffle"]["E_cross"]["p_upper"] for n in tech if "E_cross" in results[n].get("shuffle", {})}
    p_lag = {n: results[n]["shuffle"]["lag"]["p_shorter"] for n in tech if "lag" in results[n].get("shuffle", {})}
    p_acc = {n: results[n]["curve"].get("p_accel_stronger", math.nan) for n in tech if "curve" in results[n]}
    p_t50 = {n: results[n]["curve"]["p_t50_faster"] for n in tech if "curve" in results[n]}
    for name, fam in (("E_prior", p_main), ("E_cross", p_cross), ("lag", p_lag), ("accel", p_acc), ("t50", p_t50)):
        adj = holm(fam)
        for n, p in adj.items():
            results[n].setdefault("holm", {})[name] = p
    # placebos get their own Holm family
    for name, col in (("E_prior", "E_prior"), ("E_cross", "E_cross")):
        fam = {n: results[n]["shuffle"][col]["p_upper"] for n in plac if col in results[n].get("shuffle", {})}
        for n, p in holm(fam).items():
            results[n].setdefault("holm", {})[name] = p

    # within-label choice design (conditional logit), techniques and placebos separately
    summary["choice"] = {}
    fetch = [t.name for t in TECHNIQUES if t.family == "fetch-proxy"]
    nonfetch = [t.name for t in TECHNIQUES if t.family != "fetch-proxy"]
    for kind, names in (("techniques", tech), ("placebos", plac), ("fetchproxy", fetch), ("envcoord", nonfetch)):
        for col in ("E_prior", "E_cross", "E_here"):
            cd = build_choice_data({n: expos[n] for n in names}, {n: adopts[n] for n in names},
                                   {n: forders[n] for n in names}, col)
            summary["choice"][f"{kind}_{col}"] = conditional_logit_exposure(cd, n_boot=args.n_boot_cl,
                                                                            seed=args.seed)
            print(f"  choice {kind} {col}: {summary['choice'][f'{kind}_{col}']}", flush=True)

    summary["pooled"] = {f"{kind}_{col}": pooled(results, names, col)
                         for kind, names in (("techniques", tech), ("placebos", plac))
                         for col in EXPO_COLS}

    # technique-vs-placebo contrast in excess (bootstrap over tokens)
    rng = np.random.default_rng(args.seed)
    for col in ("E_prior", "E_cross"):
        te = np.array([results[n]["shuffle"][col]["excess"] for n in tech if "shuffle" in results[n]])
        pe = np.array([results[n]["shuffle"][col]["excess"] for n in plac if "shuffle" in results[n]])
        bs = [rng.choice(te, len(te)).mean() - rng.choice(pe, len(pe)).mean() for _ in range(5000)]
        summary[f"contrast_{col}"] = {"tech_minus_placebo_excess": float(te.mean() - pe.mean()),
                                      "ci": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]}

    # ------------------------------------------------------- robustness
    robust = {}
    if not args.skip_robustness:
        Bv = max(1000, args.B // 5)
        # (1) sign-off label merging
        canon = merge_labels_by_signoff(r, pop)
        sizes = pd.Series(canon).value_counts()
        r_m = r.copy()
        r_m["label"] = r_m["label"].map(lambda x: canon.get(x, x))
        pop_m = set(canon.values())
        robust["merged_signoff"] = {"info": {"agents_after_merge": len(pop_m), "labels_merged": int((sizes > 1).sum()),
                                             "largest_cluster": int(sizes.max())},
                                    "res": run_variant(r_m, pop_m, ALL_TOKENS, Bv, args.seed)}
        # (2) exclude the 10 most active labels
        act = r[r["label"].isin(pop)]["label"].value_counts()
        top = set(act.index[:10])
        robust["exclude_top10"] = {"info": {"excluded": int(len(top)), "their_revisions": int(act.iloc[:10].sum())},
                                   "res": run_variant(r, pop - top, ALL_TOKENS, Bv, args.seed)}
        # (3) timestamp jitter within the stated uncertainty (re-orders same-second ties)
        jit_rng = np.random.default_rng(args.seed + 99)
        r_j = r.drop(columns=["order"]).copy()
        r_j["ts"] = r_j["ts"] + jit_rng.uniform(-1, 1, len(r_j)) * np.maximum(r_j["uncertainty"], 1.0)
        r_j = r_j.sort_values(["ts", "page_id", "seq"], kind="mergesort").reset_index(drop=True)
        r_j["order"] = np.arange(len(r_j))
        robust["time_jitter"] = {"info": {"jitter_seconds": "uniform(-u,u), u=max(uncertainty_seconds,1)"},
                                 "res": run_variant(r_j, pop, ALL_TOKENS, Bv, args.seed)}
        # (4) only the main wiki (dse)
        r_d = r[r["wiki"] == "dse"].reset_index(drop=True)
        r_d["order"] = np.arange(len(r_d))
        robust["dse_only"] = {"info": {"revisions": int(len(r_d))},
                              "res": run_variant(r_d, pop, ALL_TOKENS, Bv, args.seed)}

    # ------------------------------------------------------- validation
    ann_path = ROOT / "annotations" / "validation_labels.csv"
    sample = validation_precision(adopts, ann_path,
                                  Path(args.sample_out) if args.sample_out else None, r)
    sample.drop(columns=["label"]).to_csv(out / "validation_sample.csv", index=False)

    # ------------------------------------------------------- tables
    cat_rows = []
    for tok in ALL_TOKENS:
        o = results[tok.name]
        sv = sample[sample["token"] == tok.name]
        prec = sv["correct"].mean() if len(sv) and sv["correct"].notna().any() else math.nan
        cat_rows.append({"token": tok.name, "kind": tok.kind, "family": tok.family,
                         "description": tok.description, "regex": tok.pattern,
                         "revisions_with_token": o["revisions_with_token"],
                         "revisions_adding_token": o["revisions_adding_token"],
                         "adopters": o["n_adopters"], "founders": o["n_founders"],
                         "page_novel_adoptions": o["n_page_novel"],
                         "first_appearance": o.get("t0").isoformat() if o.get("t0") is not None else "",
                         "validated_n": int(sv["correct"].notna().sum()) if len(sv) else 0,
                         "precision": prec,
                         "precision_strict": sv["strict_correct"].mean() if len(sv) else math.nan,
                         "share_adopt_at_first_revision": o.get("share_adopt_at_first_revision", math.nan)})
    catalogue = pd.DataFrame(cat_rows)
    catalogue.to_csv(out / "technique_catalogue.csv", index=False)

    main_rows = []
    for tok in ALL_TOKENS:
        o = results[tok.name]
        s = o.get("shuffle", {})
        row = {"token": tok.name, "kind": tok.kind, "adopters": o["n_adopters"], "tested": s.get("n_tested", 0)}
        for col in EXPO_COLS:
            if col in s:
                row[f"{col}_obs"] = s[col]["observed"]
                row[f"{col}_null"] = s[col]["null_mean"]
                row[f"{col}_excess"] = s[col]["excess"]
                row[f"{col}_excess_lo"], row[f"{col}_excess_hi"] = s[col]["excess_ci"]
                row[f"{col}_p"] = s[col]["p_upper"]
        if "first_position" in s:
            row.update({"firstpos_obs": s["first_position"]["observed"],
                        "firstpos_null": s["first_position"]["null_mean"],
                        "median_eligible_revs": s["first_position"]["median_eligible_revisions"]})
        if "lag" in s:
            row.update({"lag_obs_h": s["lag"]["median_obs_h"], "lag_null_h": s["lag"]["median_null_h"],
                        "lag_p_shorter": s["lag"]["p_shorter"]})
        for k, v in o.get("holm", {}).items():
            row[f"holm_{k}"] = v
        bu = o.get("burst", {})
        for k in ("adopters_in_window", "share_adopters_in_window", "label_arrivals_in_window",
                  "share_all_labels_arriving_in_window", "window_adopters_at_first_revision", "window_start",
                  "window_share_targeting_county_file"):
            row[f"burst_{k}"] = bu.get(k, math.nan)
        c = o.get("curve", {})
        for k in ("t50_obs_h", "t50_null_h", "p_t50_faster", "accel_rho_obs", "accel_rho_null", "p_accel_stronger"):
            row[k] = c.get(k, math.nan)
        h = o.get("hazard", {})
        for col in ("E_prior", "E_cross", "E_here", "E_wiki"):
            if col in h:
                row[f"hz_{col}_rr"] = h[col]["rate_ratio"]
                row[f"hz_{col}_rr_lo"], row[f"hz_{col}_rr_hi"] = h[col]["rate_ratio_ci"]
                row[f"hz_{col}_rate1"] = h[col]["rate_exposed"]
                row[f"hz_{col}_rate0"] = h[col]["rate_unexposed"]
                row[f"hz_{col}_opps1"] = h[col]["opps_exposed"]
                row[f"hz_{col}_opps0"] = h[col]["opps_unexposed"]
        main_rows.append(row)
    main_df = pd.DataFrame(main_rows)
    main_df.to_csv(out / "main_results.csv", index=False)

    for vname, v in robust.items():
        cl = v["res"]["_cl"]
        v["choice"] = {}
        for kind, names in (("techniques", tech), ("placebos", plac)):
            for col in ("E_prior", "E_here"):
                cd = build_choice_data({n: cl[n][0] for n in names if cl[n][0] is not None},
                                       {n: cl[n][1] for n in names if cl[n][0] is not None},
                                       {n: cl[n][2] for n in names if cl[n][0] is not None}, col)
                v["choice"][f"{kind}_{col}"] = conditional_logit_exposure(cd, n_boot=max(50, args.n_boot_cl // 2),
                                                                          seed=args.seed)
    summary["robustness_choice"] = {k: v["choice"] for k, v in robust.items()}

    rob_rows = []
    for vname, v in robust.items():
        for tok in ALL_TOKENS:
            s = v["res"][tok.name].get("shuffle", {})
            if "E_prior" not in s:
                continue
            rob_rows.append({"variant": vname, "token": tok.name, "kind": tok.kind,
                             "adopters": v["res"][tok.name]["n_adopters"], "tested": s["n_tested"],
                             "E_prior_obs": s["E_prior"]["observed"], "E_prior_null": s["E_prior"]["null_mean"],
                             "E_prior_excess": s["E_prior"]["excess"], "E_prior_p": s["E_prior"]["p_upper"],
                             "E_cross_excess": s["E_cross"]["excess"], "E_cross_p": s["E_cross"]["p_upper"]})
    rob_df = pd.DataFrame(rob_rows)
    rob_df.to_csv(out / "robustness.csv", index=False)
    summary["robustness_info"] = {k: v["info"] for k, v in robust.items()}
    summary["robustness_pooled"] = {k: {kind: pooled(v["res"], names, "E_prior")
                                        for kind, names in (("techniques", tech), ("placebos", plac))}
                                    for k, v in robust.items()}

    summary["tokens"] = {k: strip(v) for k, v in results.items()}
    summary["runtime_seconds"] = round(time.time() - t_start, 1)
    summary["config"] = {"B": args.B, "seed": args.seed}
    with open(out / "results.json", "w", encoding="utf-8") as fh:
        json.dump(strip(summary), fh, indent=1, default=str)

    figures.make_all(results, designs, adopts, main_df, rob_df, out / "figures", tech, plac, summary=summary)
    from .report import build
    build(out)
    print(f"done in {time.time() - t_start:.0f}s -> {out}")
    return summary, results, main_df


if __name__ == "__main__":
    main()
