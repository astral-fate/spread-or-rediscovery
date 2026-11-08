"""Exposure states: could a label have seen a token before a given revision?

Reads are not observed in the export. Exposure is therefore proxied by what a
label demonstrably had in front of it when it *wrote*: the base version of a
page it saved. Three definitions are computed per revision r of label L:

E_prior  (strict, page-level): some earlier revision of L was saved on top of
         a page version that contained the token.
E_cross  (strict, cross-page): as E_prior, restricted to pages other than the
         page of r. Excludes simple continuation of a page that uses the token.
E_here   the base version of r itself contains the token (same-page context).
E_wiki   (loose, wiki-level): the token had already appeared anywhere on the
         wiki of r before r was saved.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def exposure_table(r: pd.DataFrame, flags: pd.DataFrame, population: set[str]) -> pd.DataFrame:
    """Per-revision exposure states for revisions by population labels.

    Returns columns: order, ts, label, page_id, wiki, added_has, E_prior,
    E_cross, E_here, E_wiki, first_exp_ts (NaN if not E_prior).
    """
    base_has = flags["base_has"].to_numpy()
    body_has = flags["body_has"].to_numpy()
    order = r["order"].to_numpy()
    ts = r["ts"].to_numpy()
    wiki = r["wiki"].to_numpy()

    # loose wiki-level exposure: first body appearance (by order) per wiki
    first_in_wiki: dict[str, int] = {}
    for o, w, h in zip(order, wiki, body_has):
        if h and w not in first_in_wiki:
            first_in_wiki[w] = o
    e_wiki = np.array([w in first_in_wiki and first_in_wiki[w] < o for o, w in zip(order, wiki)])

    n = len(r)
    e_prior = np.zeros(n, bool)
    e_cross = np.zeros(n, bool)
    first_exp = np.full(n, np.nan)
    in_pop = r["label"].isin(population).to_numpy()
    page_arr = r["page_id"].to_numpy()
    sub = r.loc[in_pop, ["label", "page_id"]]
    # r is sorted by order, so groupby preserves chronological order within label
    for _, idx in sub.groupby("label", sort=False).indices.items():
        rows = sub.index.to_numpy()[idx]
        exposed_pages: set[str] = set()
        fexp = np.nan
        for i in rows:
            page = page_arr[i]
            if exposed_pages:
                e_prior[i] = True
                first_exp[i] = fexp
                e_cross[i] = bool(exposed_pages - {page})
            if base_has[i]:
                if not exposed_pages:
                    fexp = ts[i]
                exposed_pages.add(page)
    out = r.loc[in_pop, ["order", "ts", "label", "page_id", "wiki"]].copy()
    out["added_has"] = flags.loc[in_pop, "added_has"].to_numpy()
    out["E_prior"] = e_prior[in_pop]
    out["E_cross"] = e_cross[in_pop]
    out["E_here"] = base_has[in_pop]
    out["E_wiki"] = e_wiki[in_pop]
    out["first_exp_ts"] = first_exp[in_pop]
    return out.reset_index(drop=True)


def eligible_rows(expo: pd.DataFrame, adopt: pd.DataFrame, t0: float, first_order: int) -> dict:
    """For each non-founder adopter: its revisions after the token existed.

    The rediscovery null re-times each adoption to a uniformly chosen revision
    of the same label among those saved after the token's first appearance.
    This preserves each label's activity window and volume.
    Returns {label: (DataFrame of eligible rows, position of observed adoption)}.
    """
    out = {}
    nonf = adopt[~adopt["founder"]]
    g = expo.groupby("label", sort=False)
    for lab, a_order in zip(nonf["label"], nonf["order"]):
        rows = g.get_group(lab)
        rows = rows[(rows["order"] > first_order) & (rows["ts"] >= t0)]
        pos = np.flatnonzero(rows["order"].to_numpy() == a_order)
        if len(pos) == 0:  # should not happen; adoption is after first appearance
            continue
        out[lab] = (rows, int(pos[0]))
    return out
