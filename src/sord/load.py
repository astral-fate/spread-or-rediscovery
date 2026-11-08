"""Load the collusion.wiki export into analysis-ready tables.

The raw export is treated as untrusted data: bodies are only ever matched
against regular expressions, never executed or rendered.
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ANON_LABEL = ""  # revisions saved without a username


def _read_jsonl_gz(path: Path) -> pd.DataFrame:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return pd.DataFrame([json.loads(line) for line in fh])


def _none_to_empty(x):
    return "" if x is None or x == "None" else x


def prepare_revisions(rev: pd.DataFrame) -> pd.DataFrame:
    """Normalise a revisions table (raw export or synthetic test data).

    Required columns: rev_id, page_id, wiki, seq, body, label, time, diff_base.
    Adds: t (UTC datetime), ts (float seconds), order (global chronological
    index), base_body (body of the diff base, '' for page creations),
    added (lines new to the page's whole history), uncertainty (seconds).
    """
    r = rev.copy()
    r["body"] = r["body"].map(_none_to_empty).astype(str)
    r["label"] = r["label"].map(lambda x: ANON_LABEL if x is None or x == "None" else str(x))
    r["diff_base"] = r["diff_base"].map(_none_to_empty).astype(str)
    r["seq"] = r["seq"].astype(int)
    # explicit ISO-8601 format: avoid silent NaT coercion (Murtuza 2026, pitfall iii-c)
    r["t"] = pd.to_datetime(r["time"], format="ISO8601", utc=True)
    if r["t"].isna().any():
        raise ValueError("unparseable timestamps in revisions")
    r["ts"] = (r["t"] - pd.Timestamp("2026-01-01", tz="UTC")).dt.total_seconds()
    if "uncertainty_seconds" in r:
        r["uncertainty"] = pd.to_numeric(r["uncertainty_seconds"], errors="coerce").fillna(0.0)
    else:
        r["uncertainty"] = 0.0
    r = r.sort_values(["ts", "page_id", "seq"], kind="mergesort").reset_index(drop=True)
    r["order"] = np.arange(len(r))
    body_by_id = dict(zip(r["rev_id"], r["body"]))
    r["base_body"] = [body_by_id.get(b, "") if b else "" for b in r["diff_base"]]
    r["added"] = page_history_added(r)
    return r


def page_history_added(r: pd.DataFrame) -> list[str]:
    """Text a revision introduces to its page.

    A line counts as added only if it never appeared in any earlier revision of
    the same page. This guards against full-page API overwrites and moderator
    restores re-submitting old text, which a diff against the immediate
    predecessor alone would count as new.
    """
    added = [""] * len(r)
    by_page = r.sort_values(["page_id", "seq"], kind="mergesort")
    seen: dict[str, set[str]] = {}
    for idx, page, body in zip(by_page.index, by_page["page_id"], by_page["body"]):
        s = seen.setdefault(page, set())
        lines = body.splitlines()
        new = [ln for ln in lines if ln not in s]
        added[idx] = "\n".join(new)
        s.update(lines)
    return added


def load_dataset(data_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_dir = Path(data_dir)
    rev = _read_jsonl_gz(data_dir / "revisions.jsonl.gz")
    labels = _read_jsonl_gz(data_dir / "labels.jsonl.gz")
    labels["is_human_handle"] = labels["is_human_handle"].astype(str).str.lower() == "true"
    return prepare_revisions(rev), labels


def agent_population(r: pd.DataFrame, labels: pd.DataFrame) -> tuple[set[str], dict]:
    """Labels treated as candidate adopters: named, non-human handles."""
    human = set(labels.loc[labels["is_human_handle"], "label"])
    all_labels = set(r["label"])
    pop = {lab for lab in all_labels if lab != ANON_LABEL and lab not in human}
    info = {
        "labels_in_revisions": len(all_labels),
        "human_handles_excluded": sorted(human & all_labels),
        "n_human_handles_excluded": len(human & all_labels),
        "anonymous_revisions_excluded_as_adopters": int((r["label"] == ANON_LABEL).sum()),
        "agent_labels": len(pop),
    }
    return pop, info


SIGNOFF_RX = re.compile(r"--\s*([A-Za-z][A-Za-z0-9_]{2,40})\s*\??\s*$")


def merge_labels_by_signoff(r: pd.DataFrame, population: set[str]) -> dict[str, str]:
    """Union labels linked by sign-offs.

    Agents sign posts '-- Name'. When a revision saved under label A signs as
    B and B is itself a population label, A and B are treated as one agent.
    Returns {label: canonical label} (canonical = most active member).
    """
    parent = {lab: lab for lab in population}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for lab, text in zip(r["label"], r["added"]):
        if lab not in parent or "--" not in text:
            continue
        for line in text.splitlines():
            m = SIGNOFF_RX.search(line)
            if m and m.group(1) in parent and m.group(1) != lab:
                ra, rb = find(lab), find(m.group(1))
                if ra != rb:
                    parent[ra] = rb
    activity = r["label"].value_counts()
    groups: dict[str, list[str]] = {}
    for lab in population:
        groups.setdefault(find(lab), []).append(lab)
    canon = {}
    for members in groups.values():
        head = max(members, key=lambda m: (activity.get(m, 0), m))
        for m in members:
            canon[m] = head
    return canon
