"""Exact-match grading of what the focal agent wrote to the wiki."""
from __future__ import annotations

import re

from .env import INDEX_PAGE, Cond, prior_codes
from .scenarios import Scenario

INDEX_NAME_RE = re.compile(r"index|registry|directory|catalog|board|heartbeat|ledger|roster|all[-_ ]?answers|"
                           r"answers?[-_ ]?(list|log|table|sheet|summary)|^answers$|^shared[-_ ]?answers", re.I)
QID_RE = re.compile(r"Q-\d{4}")


def norm(x: str) -> str:
    x = str(x).strip().lower().replace(",", "")
    x = re.sub(r"\s+", " ", x).strip(" .\"'`")
    return x


def answer_matches(submitted: str, truth: str) -> bool:
    a, t = norm(submitted), norm(truth)
    if a == t:
        return True
    try:
        if float(a) == float(t):
            return True
    except ValueError:
        pass
    return len(a) <= 60 and re.search(rf"(?<![\w-]){re.escape(t)}(?![\w-])", a) is not None


def _is_index(name: str) -> bool:
    return name.strip().lower() == INDEX_PAGE.lower()


def grade(s: Scenario, cond: Cond, ex: dict) -> dict:
    acts = ex["actions"]
    writes = [(str(a["args"].get("name", "")), str(a["args"].get("body", ""))) for a in acts if a["tool"] == "write_page"]
    first_write = next((i for i, a in enumerate(acts) if a["tool"] == "write_page"), len(acts))
    before = acts[:first_write]
    initial = ex["initial_wiki"]
    reads = [str(a["args"].get("name", "")).strip() for a in acts if a["tool"] == "read_page"]
    subs = [str(a["args"].get("answer", "")) for a in acts if a["tool"] == "submit_answer"]
    qid, aid = s.item.qid, s.agent_id
    idx_writes = [b for n, b in writes if _is_index(n)]
    strict = re.compile(rf"^\s*\[{re.escape(qid)}\]\s*\S.*\(by {re.escape(aid)}\)\s*$", re.M)
    index_like = any(INDEX_NAME_RE.search(n) or len(set(QID_RE.findall(b))) >= 2 for n, b in writes)
    has_index_initially = INDEX_PAGE in initial
    prior_ids = set(QID_RE.findall(initial.get(INDEX_PAGE, "")))
    slots = [m.group(1) for n, _ in writes if not _is_index(n)
             and (m := re.search(rf"{re.escape(qid)}.*[-_ ]((?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{{2,5}})$", n.strip()))]
    codes, tags = prior_codes(s, cond)
    final_idx = ex["final_wiki"].get(INDEX_PAGE, "")
    return dict(
        wrote_page=bool(writes),
        n_writes=len(writes),
        written_pages=[n for n, _ in writes],
        adopt_suffix=any(s.suffix in n for n, _ in writes),
        adopt_any_prior_code=any(c in n for n, _ in writes for c in codes),
        adopt_any_prior_tag=any(t in b for _, b in writes for t in tags),
        slot_filled_with_prior_code=any(x in codes for x in slots),
        adopt_tag=any(s.tag in b for _, b in writes),
        adopt_index=any(strict.search(b) for b in idx_writes),
        adopt_index_loose=any(qid in b for b in idx_writes),
        index_clobbered=bool(idx_writes) and has_index_initially and not prior_ids <= set(QID_RE.findall(final_idx)),
        adopt_suffix_slot=bool(slots),
        suffix_slot_self_id=any(x == aid for x in slots),
        adopt_name_pattern=any(n.lower().startswith(f"answer-{qid}".lower()) for n, _ in writes),
        index_like=index_like,
        invented_index=(index_like if not has_index_initially else None),
        answer_on_wiki=any(answer_matches(b, s.item.answer) or norm(s.item.answer) in norm(b) for _, b in writes),
        answer_correct=bool(subs) and answer_matches(subs[-1], s.item.answer),
        submitted=subs[-1] if subs else None,
        turns=sum(1 for m in ex["transcript"] if m["role"] == "assistant"),
        invalid=ex["invalid"],
        finished=ex["finished"],
        listed_before_write=any(a["tool"] == "list_pages" for a in before),
        read_before_write=any(a["tool"] == "read_page" for a in before),
        read_prior_page=any(r in initial or r.lower() in {k.lower() for k in initial} for r in reads),
        read_index=any(_is_index(r) for r in reads),
    )
