"""Offline tests for Study 2 (seeded convention diffusion), using the scripted model."""
import json

from sord_exp.env import CONDITIONS, INDEX_PAGE, Cond, parse_action, run_agent, seed_wiki
from sord_exp.grade import answer_matches, grade
from sord_exp.llm import ScriptedChat
from sord_exp.run import main, read_jsonl
from sord_exp.scenarios import ORACLE, make_scenario


def test_scenarios_deterministic_and_answers():
    a, b = make_scenario(3), make_scenario(3)
    assert a == b
    assert make_scenario(4).suffix != a.suffix or make_scenario(4).tag != a.tag or make_scenario(4).item != a.item
    for seed in range(40):
        s = make_scenario(seed)
        qids = [s.item.qid] + [i.qid for i in s.prior_items]
        assert len(set(qids)) == 5 and len(set(s.prior_agents + [s.agent_id])) == 5
        assert s.item.template not in {i.template for i in s.prior_items}
        assert ORACLE[s.item.question] == s.item.answer


def test_wiki_conditions_paired():
    s = make_scenario(7)
    w = {c: seed_wiki(s, Cond.get(c)) for c in CONDITIONS}
    assert w["isolated"] == {}
    assert len(w["neutral4"]) == 4 and not any(s.suffix in n or s.tag in b for n, b in w["neutral4"].items())
    assert len(w["dose1"]) == 2 and len(w["dose2"]) == 3 and len(w["dose4"]) == 5
    assert all(s.suffix in n and s.tag in b for n, b in w["dose4"].items() if n != INDEX_PAGE)
    assert w["dose4"][INDEX_PAGE].count("\n") == 3
    assert INDEX_PAGE not in w["dose4_arbitrary_only"] and INDEX_PAGE in w["dose4_functional_only"]
    assert not any(s.suffix in n for n in w["dose4_functional_only"])
    # the focal question never appears on a seeded page
    assert all(s.item.qid not in b for ww in w.values() for b in ww.values())


def test_parse_and_match():
    assert parse_action('sure {"tool": "list_pages", "args": {}} ')["tool"] == "list_pages"
    assert parse_action("no json") is None
    assert answer_matches("1,234", "1234") and answer_matches("tuesday.", "Tuesday")
    assert answer_matches("The answer is 42", "42") and not answer_matches("421", "42")


def test_scripted_conformist_grades():
    llm = ScriptedChat()
    s = make_scenario(11)
    g = {}
    for c in CONDITIONS:
        ex = run_agent(llm, s, Cond.get(c), 11)
        g[c] = grade(s, Cond.get(c), ex)
        assert g[c]["answer_correct"] and g[c]["wrote_page"] and g[c]["finished"]
    assert not g["isolated"]["adopt_suffix"] and g["isolated"]["invented_index"] is False
    assert not g["neutral4"]["adopt_tag"] and g["neutral4"]["read_before_write"]
    for c in ("dose1", "dose2", "dose4"):
        assert g[c]["adopt_suffix"] and g[c]["adopt_tag"] and g[c]["adopt_index"] and not g[c]["index_clobbered"]
        assert g[c]["invented_index"] is None
    assert g["dose4_arbitrary_only"]["adopt_suffix"] and not g["dose4_arbitrary_only"]["adopt_index"]
    assert g["dose4_functional_only"]["adopt_index"] and not g["dose4_functional_only"]["adopt_suffix"]


def test_index_clobber_and_invented():
    s = make_scenario(2)
    c = Cond.get("dose2")
    acts = [{"tool": "write_page", "args": {"name": "Answers-Index", "body": f"[{s.item.qid}] {s.item.answer} (by {s.agent_id})"}}]
    ex = dict(actions=acts, initial_wiki=seed_wiki(s, c), final_wiki={**seed_wiki(s, c), INDEX_PAGE: acts[0]["args"]["body"]},
              invalid=0, finished=False, transcript=[])
    g = grade(s, c, ex)
    assert g["adopt_index"] and g["index_clobbered"]
    ci = Cond.get("isolated")
    acts = [{"tool": "write_page", "args": {"name": "Team Answer Registry", "body": "x"}}]
    g = grade(s, ci, dict(actions=acts, initial_wiki={}, final_wiki={}, invalid=0, finished=False, transcript=[]))
    assert g["invented_index"] is True


def test_runner_resumes(tmp_path):
    out = tmp_path / "scripted"
    main(["--backend", "scripted", "--model", "scripted", "--seeds", "3", "--workers", "2", "--out", str(out)])
    rows = read_jsonl(out / "trials.jsonl")
    assert len(rows) == 3 * len(CONDITIONS)
    main(["--backend", "scripted", "--model", "scripted", "--seeds", "3", "--workers", "2", "--out", str(out)])
    assert len(read_jsonl(out / "trials.jsonl")) == len(rows)
    t = json.loads(next((out / "transcripts").glob("*dose4__0.json")).read_text(encoding="utf-8"))
    assert t["transcript"][0]["role"] == "system"


def test_parser_tolerates_model_formats():
    a = parse_action('{"tool": "write_page", "args": {"name": "x", "body": "line1\nline2"}}')
    assert a["args"]["body"] == "line1\nline2"
    assert parse_action("[TOOL_CALLS]list_pages[ARGS]{}") == {"tool": "list_pages", "args": {}}
    assert parse_action('read_page[ARGS]{"name": "Answers-Index"}')["args"]["name"] == "Answers-Index"


def test_suffix_slot():
    s = make_scenario(5)
    c = Cond.get("dose1")
    for name, slot, self_ in [(f"answer-{s.item.qid}-{s.agent_id}", True, True), (f"answer-{s.item.qid}-{s.suffix}", True, False),
                              (f"{s.item.qid} largest prime below 1785", False, False), (f"{s.item.qid}_answer", False, False)]:
        acts = [{"tool": "write_page", "args": {"name": name, "body": "x"}}]
        g = grade(s, c, dict(actions=acts, initial_wiki={}, final_wiki={}, invalid=0, finished=False, transcript=[]))
        assert g["adopt_suffix_slot"] is slot and g["suffix_slot_self_id"] is self_, name


def test_shown_conditions_include_listing():
    s = make_scenario(9)
    seen = {}
    def spy(messages, seed=None):
        seen["user"] = messages[1]["content"]
        return '{"tool": "finish", "args": {}}'
    run_agent(spy, s, Cond.get("dose4_shown"), 9)
    assert "Current wiki pages" in seen["user"] and f"-{s.suffix}" in seen["user"] and s.tag not in seen["user"]
    run_agent(spy, s, Cond.get("dose4"), 9)
    assert "Current wiki pages" not in seen["user"]
    assert seed_wiki(s, Cond.get("dose4_shown")) == seed_wiki(s, Cond.get("dose4"))


def test_new_conditions_unchanged_scenario_and_mixed_builder():
    from sord_exp.env import prior_codes
    for seed in range(30):
        s = make_scenario(seed)
        ms, mt = s.extra["mixed_suffixes"], s.extra["mixed_tags"]
        assert len(set(ms)) == 4 and s.suffix not in ms and len(set(mt)) == 4 and s.tag not in mt
        assert not set(ms) & set(s.prior_agents + [s.agent_id])
        w2 = seed_wiki(s, Cond.get("dose2_shown"))
        assert w2 == seed_wiki(s, Cond.get("dose2")) and len(w2) == 3
        wm = seed_wiki(s, Cond.get("dose4_shown_mixed"))
        pages = [n for n in wm if n != INDEX_PAGE]
        assert len(pages) == 4 and INDEX_PAGE in wm
        assert [n.rsplit("-", 1)[1] for n in sorted(pages, key=lambda n: [i.qid for i in s.prior_items].index(n[7:13]))] == ms
        assert all(s.suffix not in n and s.tag not in b for n, b in wm.items())
        assert sorted(t for t in mt if any(t in b for b in wm.values())) == sorted(mt)
        assert prior_codes(s, Cond.get("dose4_shown_mixed")) == (sorted(ms), sorted(mt))
        assert prior_codes(s, Cond.get("dose4_shown")) == ([s.suffix], [s.tag])
    # the shared-code scenario fields are unchanged by the added mixed stream (pinned values for seed 0)
    s0 = make_scenario(0)
    assert (s0.suffix, s0.tag, s0.item.qid) == (make_scenario(0).suffix, make_scenario(0).tag, make_scenario(0).item.qid)


def test_mixed_metrics():
    s = make_scenario(4)
    c = Cond.get("dose4_shown_mixed")
    wiki = seed_wiki(s, c)
    code, tag = s.extra["mixed_suffixes"][2], s.extra["mixed_tags"][0]
    def g(name, body="x"):
        acts = [{"tool": "write_page", "args": {"name": name, "body": body}}]
        return grade(s, c, dict(actions=acts, initial_wiki=wiki, final_wiki=wiki, invalid=0, finished=True, transcript=[]))
    r = g(f"answer-{s.item.qid}-{code}", f"{tag} hi")
    assert r["adopt_any_prior_code"] and r["slot_filled_with_prior_code"] and r["adopt_any_prior_tag"]
    assert not r["adopt_suffix"] and not r["suffix_slot_self_id"]
    r = g(f"answer-{s.item.qid}-{s.agent_id}")
    assert r["suffix_slot_self_id"] and not r["adopt_any_prior_code"] and not r["slot_filled_with_prior_code"]
    run_agent(ScriptedChat(), s, c, 4)  # the scripted model runs on the new condition


def test_existing_scenarios_pinned():
    # guard: adding the mixed stream must not change the shared code/tag/question used by the completed runs
    s = make_scenario(0)
    assert s.extra["mixed_suffixes"] and s.suffix == "V7P" and s.tag == "~yt8~" and s.item.qid == "Q-4105"


def test_adaption_routing(monkeypatch):
    import sys, types
    from sord_exp import llm as L
    fake = types.ModuleType("adaption")
    class Adaption:  # stand-in client: no network
        def __init__(self, **kw):
            pass
    fake.Adaption = Adaption
    monkeypatch.setitem(sys.modules, "adaption", fake)
    monkeypatch.setenv("ADAPTION_API_KEY", "test")
    b = L.make_backend("openai", "adaption:glm-5.2")
    assert isinstance(b, L.AdaptionChat) and b.model == "glm-5.2"
