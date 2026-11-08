"""Positive control: plant synthetic copying into the real label/page timeline
and measure how often the Study 1 tests detect it.

For each replicate a synthetic token is seeded by a founder revision drawn from
the first 50 population revisions after ``t_start``. ``n_adopt`` candidate adopters are sampled
uniformly from population labels with at least one later revision, so the real
structure is preserved: label activity windows, pages edited, and the large
share of one-revision labels. Each candidate is a *copier* with probability f,
and otherwise a *random adopter*.

- A random adopter introduces the token at a revision drawn uniformly from its
  revisions after the founder.
- A copier introduces it at its first revision with write-visible exposure:
  either an earlier save on a page carrying the token, or a save on top of a
  page that carries it. Copiers never exposed in the record never adopt; they
  only copy.

Token presence propagates through page versions. Exposure therefore arises
endogenously from where earlier adopters wrote, exactly as in the real data.
The planted truth is the realised share of non-founder adopters who copied.

    python -m sord.poscontrol --data <dir> --out results/ [--reps 200]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .adoption import adoption_table, first_appearance, token_flags
from .exposure import eligible_rows, exposure_table
from .load import agent_population, load_dataset
from .stats import ShuffleDesign, build_choice_data, clogit_token_specific, shuffle_test
from .techniques import PLACEBOS

SYN = "synthetic"
FS = (0.0, 0.05, 0.1, 0.2, 0.4)
ALPHA = 0.05
ALPHA_STRICT = 0.05 / 15  # the first (most stringent) Holm step across 15 techniques


class Planter:
    def __init__(self, r: pd.DataFrame, pop: set[str], t_start: float):
        self.r = r
        self.n = len(r)
        self.lab = r["label"].to_numpy()
        self.in_pop = r["label"].isin(pop).to_numpy()
        self.page_codes, _ = pd.factorize(r["page_id"])
        self.ts = r["ts"].to_numpy()
        self.t_start = t_start
        # candidate founder revisions: the first 50 population revisions at or after t_start
        self.founder_pool = np.flatnonzero(self.in_pop & (self.ts >= t_start))[:50]
        lab_rows: dict[str, list[int]] = {}
        for i in np.flatnonzero(self.in_pop):
            lab_rows.setdefault(self.lab[i], []).append(i)
        self.lab_rows = {k: np.array(v) for k, v in lab_rows.items()}

    def plant(self, rng: np.random.Generator, f: float, n_adopt: int) -> tuple[pd.DataFrame, dict]:
        i0 = int(rng.choice(self.founder_pool))
        founder = self.lab[i0]
        cands = [k for k, rows in self.lab_rows.items() if k != founder and rows[-1] > i0]
        chosen = rng.choice(len(cands), size=min(n_adopt, len(cands)), replace=False)
        adopters = [cands[j] for j in chosen]
        copier = {a: bool(rng.random() < f) for a in adopters}
        assigned = {}
        for a in adopters:
            rows = self.lab_rows[a]
            rows = rows[rows > i0]
            assigned[a] = int(rng.choice(rows))
        added = np.zeros(self.n, bool)
        base = np.zeros(self.n, bool)
        body = np.zeros(self.n, bool)
        present = np.zeros(self.page_codes.max() + 1, bool)
        exposed: set[str] = set()
        done: set[str] = set()
        how = {}
        added[i0] = True
        present[self.page_codes[i0]] = True
        body[i0] = True
        done.add(founder)
        for i in range(i0 + 1, self.n):
            P = self.page_codes[i]
            L = self.lab[i]
            bh = present[P]
            base[i] = bh
            if L in copier and L not in done:
                if copier[L]:
                    if L in exposed or bh:
                        added[i] = True
                        how[L] = "copy"
                elif assigned[L] == i:
                    added[i] = True
                    how[L] = "random"
                if added[i]:
                    done.add(L)
                    present[P] = True
            if bh:
                exposed.add(L)
            body[i] = present[P]
        flags = pd.DataFrame({"added_has": added, "base_has": base, "body_has": body}, index=self.r.index)
        n_copy = sum(v == "copy" for v in how.values())
        truth = {"n_candidates": len(adopters), "n_copier_candidates": int(sum(copier.values())),
                 "n_adopters": len(how), "n_copied": int(n_copy),
                 "true_copy_share": n_copy / len(how) if how else math.nan}
        return flags, truth


def run(data: str, out: Path, reps: int = 200, n_adopt: int = 300, B: int = 1000, seed: int = 7,
        t_start: str = "2026-06-16T00:00:00Z"):
    t0 = time.time()
    (out / "figures").mkdir(parents=True, exist_ok=True)
    r, labels = load_dataset(data)
    pop, _ = agent_population(r, labels)
    ts0 = (pd.Timestamp(t_start) - pd.Timestamp("2026-01-01", tz="UTC")).total_seconds()
    planter = Planter(r, pop, ts0)
    # real placebo tokens provide the generic-echo baseline for the choice test
    pl_expo, pl_adopt, pl_first = {}, {}, {}
    for tok in PLACEBOS:
        fl = token_flags(r, tok)
        pl_first[tok.name] = first_appearance(r, fl)[0]
        pl_adopt[tok.name] = adoption_table(r, fl, pop)
        pl_expo[tok.name] = exposure_table(r, fl, pop)
    rows = []
    rng = np.random.default_rng(seed)
    for f in FS:
        for rep in range(reps):
            flags, truth = planter.plant(rng, f, n_adopt)
            first_order, tfirst = first_appearance(r, flags)
            adopt = adoption_table(r, flags, pop)
            expo = exposure_table(r, flags, pop)
            design = ShuffleDesign(eligible_rows(expo, adopt, tfirst, first_order))
            st = shuffle_test(design, B=B, seed=int(rng.integers(1 << 31)), n_boot=200)
            row = {"f": f, "rep": rep, **truth, "tested": design.n}
            for col in ("E_prior", "E_here", "E_any", "E_first"):
                row[f"{col}_obs"] = st[col]["observed"]
                row[f"{col}_null"] = st[col]["null_mean"]
                row[f"{col}_excess"] = st[col]["excess"]
                row[f"{col}_p"] = st[col]["p_upper"]
            row["lag_p_shorter"] = st["lag"]["p_shorter"]
            for ccol in ("E_prior", "E_any"):
                cd = build_choice_data({**pl_expo, SYN: expo}, {**pl_adopt, SYN: adopt},
                                       {**pl_first, SYN: first_order}, ccol)
                cl = clogit_token_specific(cd, SYN)
                row.update({f"cl_{ccol}_{k}": v for k, v in cl.items()})
            rows.append(row)
        print(f"f={f}: {reps} reps, {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "positive_control.csv", index=False)
    summ = summarise(df)
    meta = {"reps_per_f": reps, "n_adopt_candidates": n_adopt, "B": B, "seed": seed, "t_start": t_start,
            "alpha": ALPHA, "alpha_strict": ALPHA_STRICT,
            "tests": {"shuffle_E_prior": "re-timing test, prior exposure, p_upper < alpha",
                      "shuffle_E_first": "re-timing test, adoption at the first write-visible encounter",
                      "lag": "median exposure-to-adoption lag shorter than null (prior exposure)",
                      "shuffle_E_here": "re-timing test, page-local exposure",
                      "shuffle_E_any": "re-timing test, prior or page-local exposure",
                      "choice_token_<col>": "conditional logit (synthetic + 8 real placebos): exposure OR for the synthetic token > 1 (Wald, one-sided)",
                      "choice_beyond_echo_<col>": "conditional logit: synthetic exposure effect exceeds the placebo echo "
                                            "effect (interaction > 0, Wald, one-sided)"},
            "runtime_s": round(time.time() - t0, 1)}
    with open(out / "positive_control.json", "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "by_f": summ}, fh, indent=1)
    from .figures import positive_control_figure
    positive_control_figure(summ, out / "figures" / "fig_positive_control.png")
    return df, summ


def summarise(df: pd.DataFrame) -> list[dict]:
    out = []
    for f, d in df.groupby("f"):
        s = {"f": float(f), "reps": int(len(d)),
             "true_copy_share_mean": float(d["true_copy_share"].mean()),
             "true_copy_share_q": [float(d["true_copy_share"].quantile(q)) for q in (0.025, 0.975)],
             "adopters_mean": float(d["n_adopters"].mean()),
             "copier_candidates_mean": float(d["n_copier_candidates"].mean()),
             "copied_mean": float(d["n_copied"].mean())}
        s["power_lag"] = float((d["lag_p_shorter"] < ALPHA).mean())
        for col in ("E_prior", "E_here", "E_any", "E_first"):
            s[f"power_{col}"] = float((d[f"{col}_p"] < ALPHA).mean())
            s[f"power_{col}_strict"] = float((d[f"{col}_p"] < ALPHA_STRICT).mean())
            s[f"excess_{col}_mean"] = float(d[f"{col}_excess"].mean())
            s[f"excess_{col}_q"] = [float(d[f"{col}_excess"].quantile(q)) for q in (0.025, 0.975)]
        for ccol in ("E_prior", "E_any"):
            for k, pc in (("choice_token", "p_token_gt1"), ("choice_beyond_echo", "p_token_beyond_generic")):
                v = d[f"cl_{ccol}_{pc}"]
                s[f"power_{k}_{ccol}"] = float((v < ALPHA).mean())
                s[f"power_{k}_{ccol}_strict"] = float((v < ALPHA_STRICT).mean())
            s[f"or_token_{ccol}_median"] = float(d[f"cl_{ccol}_or_token"].median())
            s[f"or_generic_{ccol}_median"] = float(d[f"cl_{ccol}_or_generic"].median())
        out.append(s)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="results")
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--n-adopt", type=int, default=300)
    ap.add_argument("--B", type=int, default=1000)
    a = ap.parse_args(argv)
    out = Path(a.out)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    run(a.data, out, reps=a.reps, n_adopt=a.n_adopt, B=a.B)


if __name__ == "__main__":
    main()
