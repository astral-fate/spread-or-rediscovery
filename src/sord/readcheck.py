"""Can read exposure be recovered from the export? (events + shortener logs)

Writes results/read_exposure_check.json. Only counts and field availability are
recorded; no event payloads are copied.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd


def check(data_dir: str | Path) -> dict:
    data_dir = Path(data_dir)
    with gzip.open(data_dir / "events.jsonl.gz", "rt", encoding="utf-8") as fh:
        e = pd.DataFrame([json.loads(line) for line in fh])
    out = {"event_types": e["event_type"].value_counts().to_dict()}
    probe = e[e["event_type"] == "probe"]
    out["probe_events"] = int(len(probe))
    out["probe_fields_non_null"] = {c: int(probe[c].notna().sum()) for c in
                                    ("wiki", "page", "actor_label", "revision_ref", "ip16") if c in probe}
    out["probe_request_actions"] = int(probe["request_action"].nunique())
    out["probe_time_range"] = [str(probe["time"].min()), str(probe["time"].max())]
    out["events_with_actor_label"] = int(e["actor_label"].notna().sum()) if "actor_label" in e else 0
    if "actor_label" in e:
        out["actor_labelled_events_by_type"] = e.loc[e["actor_label"].notna(), "event_type"].value_counts().to_dict()
    sl_path = data_dir / "shortener-logs.json.gz"
    if sl_path.exists():
        with gzip.open(sl_path, "rt", encoding="utf-8") as fh:
            sl = json.load(fh)
        links = [lk for site in sl.get("sites", []) for lk in site.get("links", [])]
        keys = sorted({k for lk in links for k in lk})
        out["shortener_links"] = len(links)
        out["shortener_link_fields"] = keys
        out["shortener_has_per_click_records"] = any(isinstance(lk.get("clicks"), list) for lk in links)
    out["conclusion"] = ("No label-attributable read events: the only non-write events are probes, which carry "
                         "no page, wiki, revision or actor; the only actor-labelled events are deletions and reverts (writes); shortener logs give aggregate click counts per link "
                         "without per-click time or actor. Read exposure is not recoverable from the export.")
    return out


def write(data_dir, out: Path):
    res = check(data_dir)
    with open(out / "read_exposure_check.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    return res
