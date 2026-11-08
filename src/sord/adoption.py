"""Adoption events: the first revision in which a label introduces a token."""
from __future__ import annotations

import pandas as pd

from .techniques import Token


def token_flags(r: pd.DataFrame, tok: Token) -> pd.DataFrame:
    """Per-revision booleans for one token.

    added_has: the token occurs in text new to the page (page-history novelty)
    base_has:  the token occurs in the page version the revision was based on
               (what an editor submitting a full-page save had in front of it)
    body_has:  the token occurs anywhere in the saved body
    """
    rx = tok.rx
    f = pd.DataFrame(index=r.index)
    f["added_has"] = [bool(s) and bool(rx.search(s)) for s in r["added"]]
    f["base_has"] = [bool(s) and bool(rx.search(s)) for s in r["base_body"]]
    f["body_has"] = [bool(s) and bool(rx.search(s)) for s in r["body"]]
    return f


def first_appearance(r: pd.DataFrame, flags: pd.DataFrame) -> tuple[int | None, float | None]:
    """(order, ts) of the first revision whose body contains the token."""
    hit = r.loc[flags["body_has"].to_numpy(), ["order", "ts"]]
    if hit.empty:
        return None, None
    row = hit.sort_values("order").iloc[0]
    return int(row["order"]), float(row["ts"])


def adoption_table(r: pd.DataFrame, flags: pd.DataFrame, population: set[str]) -> pd.DataFrame:
    """One row per adopting label: its first revision that adds the token.

    A label adopts the token at its earliest revision whose page-novel text
    contains it. ``founder`` marks adoptions at or before the token's first
    appearance anywhere in the corpus (no observable prior exposure is
    possible); founders are excluded from the exposure tests. ``page_novel``
    marks adoptions on a page whose base version did not already contain the
    token (the adopter did not merely continue a page that used it).
    """
    first_order, t0 = first_appearance(r, flags)
    sel = flags["added_has"].to_numpy() & r["label"].isin(population).to_numpy()
    cols = ["order", "ts", "label", "page_id", "wiki", "rev_id"]
    cand = r.loc[sel, cols].copy()
    cand["base_has"] = flags.loc[sel, "base_has"].to_numpy()
    cand = cand.sort_values("order")
    adopt = cand.drop_duplicates("label", keep="first").reset_index(drop=True)
    adopt["page_novel"] = ~adopt.pop("base_has").astype(bool)
    if first_order is None:
        adopt["founder"] = False
    else:
        adopt["founder"] = (adopt["order"] <= first_order) | (adopt["ts"] <= t0)
    return adopt
