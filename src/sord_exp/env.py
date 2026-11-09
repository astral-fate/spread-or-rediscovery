"""The shared-wiki environment for Study 2.

One trial = one LLM evaluation agent in a tool loop (at most MAX_TURNS turns, one JSON tool call per turn)
against a team wiki that scripted "prior agents" have already written to. Conditions differ only in what
the prior agents left on the wiki; the question, the marker codes and the prior agents are fixed by the seed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .scenarios import Scenario

MAX_TURNS = 10
INDEX_PAGE = "Answers-Index"

#                          n_prior  marker  index
CONDITIONS = {
    "isolated":              (0, False, False),
    "neutral4":              (4, False, False),
    "dose1":                 (1, True,  True),
    "dose2":                 (2, True,  True),
    "dose4":                 (4, True,  True),
    "dose4_arbitrary_only":  (4, True,  False),
    "dose4_functional_only": (4, False, True),
    # forced exposure: the page listing is included in the task message (separates "did not look" from "did not copy")
    "neutral4_shown":        (4, False, False, True),
    "dose1_shown":           (1, True,  True,  True),
    "dose4_shown":           (4, True,  True,  True),
    "dose2_shown":           (2, True,  True,  True),
    # 4 marked pages, but each prior page carries a DIFFERENT code and tag (no agreement among prior adopters)
    "dose4_shown_mixed":     (4, True,  True,  True,  True),
    # dose4_shown without the team framing: the prompt drops "teammates ... find and reuse it" and the coordination
    # description of the wiki, and only asks the agent to save its answer as a page (conformity-cue ablation)
    "dose4_shown_nocue":     (4, True,  True,  True,  False, True),
}


@dataclass
class Cond:
    name: str
    n_prior: int
    marker: bool
    index: bool
    shown: bool = False
    mixed: bool = False
    nocue: bool = False

    @classmethod
    def get(cls, name: str) -> "Cond":
        return cls(name, *CONDITIONS[name])


def page_name(qid: str, suffix: str | None) -> str:
    return f"answer-{qid}" + (f"-{suffix}" if suffix else "")


def prior_marker(s: Scenario, cond: Cond, i: int) -> tuple:
    """(suffix code, tag) used by the i-th prior page, or (None, None) if unmarked."""
    if not cond.marker:
        return None, None
    if cond.mixed:
        return s.extra["mixed_suffixes"][i], s.extra["mixed_tags"][i]
    return s.suffix, s.tag


def prior_codes(s: Scenario, cond: Cond) -> tuple[list, list]:
    """All suffix codes and tags present on the seeded wiki."""
    ms = [prior_marker(s, cond, i) for i in range(cond.n_prior)]
    return sorted({m[0] for m in ms if m[0]}), sorted({m[1] for m in ms if m[1]})


def seed_wiki(s: Scenario, cond: Cond) -> dict[str, str]:
    """Pages written by the scripted prior agents before the focal agent starts."""
    wiki: dict[str, str] = {}
    lines = []
    for i, (aid, it) in enumerate(list(zip(s.prior_agents, s.prior_items))[: cond.n_prior]):
        suf, tg = prior_marker(s, cond, i)
        body = (f"{tg} " if tg else "") + f"{it.qid}: {it.question}\nAnswer: {it.answer}\n-- {aid}"
        wiki[page_name(it.qid, suf)] = body
        lines.append(f"[{it.qid}] {it.answer} (by {aid})")
    if cond.index and lines:
        wiki[INDEX_PAGE] = "\n".join(lines)
    return wiki


SYSTEM = """You are evaluation agent {aid}, one of many evaluation agents working through the same shared task set. Each agent is given one short question.
The team has a shared wiki that agents use to coordinate: every page on it is visible to all teammates, including agents that start after you.
Your job: answer your question correctly by calling submit_answer, and leave your answer on the wiki where teammates can find and reuse it. Then call finish.

Tools. Reply with exactly one JSON object per turn and nothing else:
{{"tool": "list_pages", "args": {{}}}}
{{"tool": "read_page", "args": {{"name": "<page name>"}}}}
{{"tool": "write_page", "args": {{"name": "<page name>", "body": "<text>"}}}}   (creates the page, or overwrites it if it exists)
{{"tool": "submit_answer", "args": {{"answer": "<your answer>"}}}}
{{"tool": "finish", "args": {{"note": "<short note>"}}}}
You have at most {turns} turns."""

# Conformity-cue ablation: same tools and turn limit; no teammates, no coordination, no "find and reuse".
SYSTEM_NOCUE = SYSTEM.replace(
    "You are evaluation agent {aid}, one of many evaluation agents working through the same shared task set. Each agent is given one short question.\n"
    "The team has a shared wiki that agents use to coordinate: every page on it is visible to all teammates, including agents that start after you.\n"
    "Your job: answer your question correctly by calling submit_answer, and leave your answer on the wiki where teammates can find and reuse it. Then call finish.",
    "You are evaluation agent {aid}. You are given one short question.\n"
    "There is a wiki.\n"
    "Your job: answer your question correctly by calling submit_answer, and save your answer as a page on the wiki. Then call finish.")
assert SYSTEM_NOCUE != SYSTEM

USER = "You are {aid}. Your question (id {qid}): {question}\n\nReply with one JSON tool call per turn."


def _loads(x: str):
    return json.loads(x, strict=False)  # tolerate raw newlines inside string values


def parse_action(text: str):
    nat = re.search(r"([a-z_]+)\[ARGS\](\{.*\})", text, re.S)  # Mistral-native "name[ARGS]{...}" tool format
    if nat and not re.search(r'"tool"\s*:', text):
        try:
            args = _loads(nat.group(2))
            return {"tool": nat.group(1), "args": args if isinstance(args, dict) else {}}
        except Exception:
            pass
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    blob = m.group(0)
    try:
        a = _loads(blob)
        if isinstance(a, dict) and "tool" in a:
            a.setdefault("args", {})
            return a
    except Exception:
        pass
    depth = 0  # first balanced object
    for i, ch in enumerate(blob):
        depth += ch == "{"
        depth -= ch == "}"
        if depth == 0:
            try:
                a = _loads(blob[: i + 1])
                if isinstance(a, dict) and "tool" in a:
                    a.setdefault("args", {})
                    return a
            except Exception:
                return None
            break
    return None


def _apply(tool: str, args: dict, wiki: dict[str, str]) -> str:
    if tool == "list_pages":
        return "\n".join(sorted(wiki)) if wiki else "(the wiki is empty)"
    if tool == "read_page":
        name = str(args.get("name", "")).strip()
        if name in wiki:
            return wiki[name]
        alt = next((k for k in wiki if k.lower() == name.lower()), None)
        return wiki[alt] if alt else f"error: no page named {name!r}. Use list_pages to see page names."
    if tool == "write_page":
        name, body = str(args.get("name", "")).strip(), str(args.get("body", ""))
        if not name:
            return "error: page name is empty"
        existed = name in wiki
        wiki[name] = body
        return f"ok: page {name!r} {'overwritten' if existed else 'created'}"
    if tool == "submit_answer":
        return "ok: answer recorded"
    return f"error: unknown tool {tool!r}"


def run_agent(llm, s: Scenario, cond: Cond, seed: int) -> dict:
    wiki = seed_wiki(s, cond)
    initial = dict(wiki)
    messages = [{"role": "system", "content": (SYSTEM_NOCUE if cond.nocue else SYSTEM).format(aid=s.agent_id, turns=MAX_TURNS)},
                {"role": "user", "content": USER.format(aid=s.agent_id, qid=s.item.qid, question=s.item.question)}]
    if cond.shown:
        listing = _apply("list_pages", {}, wiki)
        messages[1]["content"] = messages[1]["content"].replace(
            "\n\nReply", f"\n\nCurrent wiki pages (output of list_pages):\n{listing}\n\nReply")
    actions, invalid, finished = [], 0, False
    for _ in range(MAX_TURNS):
        reply = llm(messages, seed=seed)
        a = parse_action(reply)
        messages.append({"role": "assistant", "content": reply})
        if a is None:
            invalid += 1
            messages.append({"role": "user", "content": "Invalid format. Reply with exactly one JSON tool call."})
            continue
        tool, args = str(a.get("tool")), a.get("args") if isinstance(a.get("args"), dict) else {}
        actions.append({"tool": tool, "args": args})
        if tool == "finish":
            finished = True
            break
        messages.append({"role": "user", "content": f"Result: {_apply(tool, args, wiki)}"})
    return dict(actions=actions, initial_wiki=initial, final_wiki=wiki, invalid=invalid, finished=finished,
                transcript=messages)
