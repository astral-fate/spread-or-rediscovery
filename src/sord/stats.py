"""Statistical tests: time-shuffle permutation, exposure hazards, acceleration."""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd

EXPO_COLS = ("E_prior", "E_cross", "E_here", "E_wiki")


# ----------------------------------------------------------------- helpers
def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values (NaNs passed through)."""
    items = [(k, p) for k, p in pvals.items() if p == p]
    items.sort(key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    for k, p in pvals.items():
        adj.setdefault(k, math.nan)
    return adj


def _rank_rows(a: np.ndarray) -> np.ndarray:
    """Average-free ordinal ranks along the last axis (ties broken by position)."""
    return np.argsort(np.argsort(a, axis=-1, kind="mergesort"), axis=-1).astype(float)


def spearman_rows(x: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """Spearman correlation of a fixed vector x with each row of Y."""
    rx = _rank_rows(x[None, :])[0]
    rY = _rank_rows(Y)
    rx = rx - rx.mean()
    rY = rY - rY.mean(axis=1, keepdims=True)
    den = np.sqrt((rx ** 2).sum() * (rY ** 2).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return (rY @ rx) / den


# ------------------------------------------------ time-shuffle permutation
class ShuffleDesign:
    """Packed arrays for the rediscovery null (re-time each adoption to a
    uniformly chosen eligible revision of the same label)."""

    def __init__(self, elig: dict):
        self.labels = list(elig)
        sizes, obs_pos, chunks = [], [], {c: [] for c in EXPO_COLS + ("ts", "first_exp_ts")}
        for lab in self.labels:
            rows, pos = elig[lab]
            sizes.append(len(rows))
            obs_pos.append(pos)
            for c in chunks:
                chunks[c].append(rows[c].to_numpy(dtype=float))
        self.sizes = np.array(sizes, dtype=int)
        self.offsets = np.concatenate([[0], np.cumsum(self.sizes)[:-1]]) if sizes else np.array([], int)
        self.obs_idx = self.offsets + np.array(obs_pos, dtype=int) if sizes else np.array([], int)
        self.arr = {c: (np.concatenate(v) if v else np.array([])) for c, v in chunks.items()}

    @property
    def n(self) -> int:
        return len(self.labels)

    def draw(self, rng: np.random.Generator, B: int) -> np.ndarray:
        u = rng.random((B, self.n))
        return self.offsets[None, :] + np.floor(u * self.sizes[None, :]).astype(int)

    def expected(self, col: str) -> np.ndarray:
        """Per-adopter null expectation of an exposure indicator."""
        a = self.arr[col]
        return np.array([a[o:o + s].mean() for o, s in zip(self.offsets, self.sizes)])

    def lag(self, idx: np.ndarray) -> np.ndarray:
        """Exposure->adoption lag (seconds), NaN where not exposed."""
        return self.arr["ts"][idx] - self.arr["first_exp_ts"][idx]


def shuffle_test(design: ShuffleDesign, B: int = 5000, seed: int = 0, n_boot: int = 2000) -> dict:
    """Observed vs rediscovery-null exposure fractions and lags for one token."""
    res: dict = {"n_tested": design.n}
    if design.n == 0:
        return res
    rng = np.random.default_rng(seed)
    draws = design.draw(rng, B)
    obs = design.obs_idx
    boot_idx = rng.integers(0, design.n, size=(n_boot, design.n))
    for col in EXPO_COLS:
        a = design.arr[col]
        o = a[obs]
        null = a[draws].mean(axis=1)
        exp_i = design.expected(col)
        excess_i = o - exp_i
        bs = excess_i[boot_idx].mean(axis=1)
        res[col] = {
            "observed": float(o.mean()),
            "null_mean": float(null.mean()),
            "null_q025": float(np.quantile(null, 0.025)),
            "null_q975": float(np.quantile(null, 0.975)),
            "excess": float(excess_i.mean()),
            "excess_ci": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))],
            "ratio": float(o.mean() / null.mean()) if null.mean() > 0 else math.nan,
            "p_upper": float((1 + (null >= o.mean() - 1e-12).sum()) / (B + 1)),
            "p_lower": float((1 + (null <= o.mean() + 1e-12).sum()) / (B + 1)),
            "null_samples": null,
        }
    # position diagnostic: is the adoption the label's first eligible revision?
    first_obs = (obs == design.offsets)
    res["first_position"] = {"observed": float(first_obs.mean()),
                             "null_mean": float(np.mean(1.0 / design.sizes)),
                             "median_eligible_revisions": float(np.median(design.sizes))}
    lag_obs = design.lag(obs)
    lag_null = design.lag(draws)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med_obs = float(np.nanmedian(lag_obs)) if np.isfinite(lag_obs).any() else math.nan
        med_null = np.nanmedian(lag_null, axis=1)
    med_null = med_null[np.isfinite(med_null)]
    res["lag"] = {
        "n_exposed": int(np.isfinite(lag_obs).sum()),
        "median_obs_h": med_obs / 3600 if med_obs == med_obs else math.nan,
        "median_null_h": float(np.median(med_null)) / 3600 if len(med_null) else math.nan,
        "p_shorter": float((1 + (med_null <= med_obs).sum()) / (len(med_null) + 1))
        if len(med_null) and med_obs == med_obs else math.nan,
    }
    res["_draws"] = draws
    return res


# ------------------------------------------------------- exposure hazards
def hazard_table(expo: pd.DataFrame, adopt: pd.DataFrame, t0: float, first_order: int,
                 col: str = "E_prior", n_boot: int = 1000, seed: int = 0) -> dict:
    """Discrete-time adoption hazard per revision opportunity, by exposure state.

    Opportunities: revisions of non-founder population labels saved after the
    token's first appearance, up to and including the label's adoption.
    """
    founders = set(adopt.loc[adopt["founder"], "label"])
    a_order = dict(zip(adopt["label"], adopt["order"]))
    e = expo[(expo["order"] > first_order) & (expo["ts"] >= t0) & ~expo["label"].isin(founders)]
    lim = e["label"].map(a_order).fillna(np.inf)
    e = e[e["order"] <= lim]
    ev = (e["order"] == e["label"].map(a_order)).to_numpy()
    x = e[col].to_numpy(bool)
    lab_codes, lab_index = pd.factorize(e["label"])

    def rates(mask_ev, mask_x):
        n1, n0 = mask_x.sum(), (~mask_x).sum()
        k1, k0 = (mask_ev & mask_x).sum(), (mask_ev & ~mask_x).sum()
        return k1, n1, k0, n0

    k1, n1, k0, n0 = rates(ev, x)
    r1 = k1 / n1 if n1 else math.nan
    r0 = k0 / n0 if n0 else math.nan
    rr = r1 / r0 if (n1 and n0 and k0) else math.nan
    # cluster bootstrap over labels
    rng = np.random.default_rng(seed)
    L = len(lab_index)
    rrs = []
    if L and n1 and n0:
        agg = np.column_stack([np.bincount(lab_codes, weights=(ev & x), minlength=L),
                               np.bincount(lab_codes, weights=x, minlength=L),
                               np.bincount(lab_codes, weights=(ev & ~x), minlength=L),
                               np.bincount(lab_codes, weights=~x, minlength=L)]).astype(float)
        for _ in range(n_boot):
            s = agg[rng.integers(0, L, L)].sum(axis=0)
            if s[1] > 0 and s[3] > 0 and s[2] > 0 and s[0] > 0:
                rrs.append((s[0] / s[1]) / (s[2] / s[3]))
    ci = [float(np.quantile(rrs, 0.025)), float(np.quantile(rrs, 0.975))] if len(rrs) > 50 else [math.nan, math.nan]
    return {"col": col, "events_exposed": int(k1), "opps_exposed": int(n1),
            "events_unexposed": int(k0), "opps_unexposed": int(n0),
            "rate_exposed": r1, "rate_unexposed": r0,
            "rate_exposed_ci": list(wilson_ci(int(k1), int(n1))),
            "rate_unexposed_ci": list(wilson_ci(int(k0), int(n0))),
            "rate_ratio": rr, "rate_ratio_ci": ci, "n_labels": int(L)}


# ---------------------------------------------------- curves and acceleration
def curve_and_acceleration(design: ShuffleDesign, founder_ts: np.ndarray, t0: float,
                           draws: np.ndarray) -> dict:
    """Diffusion speed (T50) and acceleration (Spearman of gap vs k) against the null."""
    ts = design.arr["ts"]
    obs_times = np.sort(np.concatenate([founder_ts, ts[design.obs_idx]]))
    null_times = np.sort(np.concatenate([np.broadcast_to(founder_ts, (draws.shape[0], len(founder_ts))),
                                         ts[draws]], axis=1), axis=1)
    out: dict = {"n_adopters": int(len(obs_times))}
    t50_obs = (np.median(obs_times) - t0) / 3600
    t50_null = (np.median(null_times, axis=1) - t0) / 3600
    out["t50_obs_h"] = float(t50_obs)
    out["t50_null_h"] = float(np.median(t50_null))
    out["t50_null_ci"] = [float(np.quantile(t50_null, 0.025)), float(np.quantile(t50_null, 0.975))]
    out["p_t50_faster"] = float((1 + (t50_null <= t50_obs).sum()) / (len(t50_null) + 1))
    if len(obs_times) >= 5:
        k = np.arange(1, len(obs_times), dtype=float)
        g_obs = np.diff(obs_times)
        g_null = np.diff(null_times, axis=1)
        rho_obs = float(spearman_rows(k, g_obs[None, :])[0])
        rho_null = spearman_rows(k, g_null)
        rho_null = rho_null[np.isfinite(rho_null)]
        out["accel_rho_obs"] = rho_obs
        out["accel_rho_null"] = float(np.median(rho_null))
        out["accel_rho_null_ci"] = [float(np.quantile(rho_null, 0.025)), float(np.quantile(rho_null, 0.975))]
        # negative rho = gaps shrink as adopters accumulate (acceleration)
        out["p_accel_stronger"] = float((1 + (rho_null <= rho_obs).sum()) / (len(rho_null) + 1))
    out["_obs_times"] = obs_times
    out["_null_times"] = null_times
    return out


# ------------------------------------------- within-label choice (conditional logit)
def build_choice_data(expos: dict, adopts: dict, first_orders: dict, col: str) -> pd.DataFrame:
    """Long-format choice sets for the within-label, within-moment design.

    For every (label L, token X) adoption at revision a (X not founded by L),
    the choice set is X plus every other token Y of the same set that already
    existed at a and that L had not adopted at or before a. The covariate is
    L's exposure to each alternative at a. Comparing alternatives for the same
    label at the same moment removes label activity, label position in its
    own history and calendar time as confounders.
    """
    names = list(expos)
    # exposure lookup: token -> {order: value}
    lookup = {n: dict(zip(expos[n]["order"], expos[n][col].astype(int))) for n in names}
    adopted = {}
    for n in names:
        for lab, o in zip(adopts[n]["label"], adopts[n]["order"]):
            adopted.setdefault(lab, {})[n] = o
    rows, gid = [], 0
    for n in names:
        a = adopts[n]
        for lab, o, fnd in zip(a["label"], a["order"], a["founder"]):
            if fnd:
                continue
            alts = [n] + [y for y in names if y != n and first_orders[y] is not None and first_orders[y] < o
                          and adopted[lab].get(y, np.inf) > o]
            if len(alts) < 2:
                continue
            for y in alts:
                rows.append((gid, lab, y, int(y == n), lookup[y].get(o, 0)))
            gid += 1
    return pd.DataFrame(rows, columns=["group", "label", "alt", "chosen", "x"])


def _clogit_arrays(g, alt_codes, x, y, n_alt):
    """Fit a conditional logit. Inputs must be sorted by group id g."""
    from scipy.optimize import minimize
    X = np.zeros((len(g), n_alt))
    X[:, 0] = x
    if n_alt > 1:
        m = alt_codes > 0
        X[np.flatnonzero(m), alt_codes[m]] = 1.0
    starts = np.flatnonzero(np.r_[True, g[1:] != g[:-1]])
    sizes = np.diff(np.r_[starts, len(g)])

    def nll(theta):
        eta = X @ theta
        m_ = np.maximum.reduceat(eta, starts)
        ex = np.exp(eta - np.repeat(m_, sizes))
        den = np.add.reduceat(ex, starts)
        p = ex / np.repeat(den, sizes)
        ll = (y * eta).sum() - (np.log(den) + m_).sum()
        return -ll, -(X.T @ (y - p))

    res = minimize(nll, np.zeros(n_alt), jac=True, method="L-BFGS-B", bounds=[(-20, 20)] * n_alt)
    return res.x


def conditional_logit_exposure(df: pd.DataFrame, n_boot: int = 200, seed: int = 0) -> dict:
    """Exposure odds ratio from a conditional logit with alternative fixed effects;
    95% CI from a cluster bootstrap over labels."""
    if df.empty:
        return {}
    df = df.sort_values("group", kind="mergesort").reset_index(drop=True)
    alt_codes, alt_index = pd.factorize(df["alt"], sort=True)
    g = df["group"].to_numpy()
    x = df["x"].to_numpy(float)
    y = df["chosen"].to_numpy(float)
    n_alt = len(alt_index)
    beta = _clogit_arrays(g, alt_codes, x, y, n_alt)[0]
    var = df.groupby("group")["x"].agg(lambda s: s.nunique() > 1)
    lab_codes, labs = pd.factorize(df["label"])
    rows_by_lab = [np.flatnonzero(lab_codes == k) for k in range(len(labs))]
    G = int(g.max()) + 1
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(labs), len(labs))
        idx = np.concatenate([rows_by_lab[k] for k in pick])
        rep = np.concatenate([np.full(len(rows_by_lab[k]), j) for j, k in enumerate(pick)])
        gb = g[idx] + G * rep
        o = np.argsort(gb, kind="mergesort")
        bs.append(_clogit_arrays(gb[o], alt_codes[idx][o], x[idx][o], y[idx][o], n_alt)[0])
    bs = np.array(bs)
    chosen = df[df["chosen"] == 1]
    return {"n_events": int(df["group"].nunique()), "n_informative": int(var.sum()),
            "n_labels": int(len(labs)), "mean_choice_set": float(df.groupby("group").size().mean()),
            "share_chosen_exposed": float(chosen["x"].mean()),
            "share_alternatives_exposed": float(df.loc[df["chosen"] == 0, "x"].mean()),
            "beta": float(beta), "odds_ratio": float(np.exp(beta)),
            "or_ci": [float(np.exp(np.quantile(bs, 0.025))), float(np.exp(np.quantile(bs, 0.975)))],
            "p_boot_le0": float((1 + (bs <= 0).sum()) / (len(bs) + 1))}
