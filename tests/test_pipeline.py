"""Unit tests on synthetic data: diffing, adoption, exposure, test calibration."""
import numpy as np
import pandas as pd
import pytest

from sord.adoption import adoption_table, token_flags
from sord.exposure import eligible_rows, exposure_table
from sord.load import merge_labels_by_signoff, prepare_revisions
from sord.stats import ShuffleDesign, hazard_table, holm, shuffle_test, spearman_rows, wilson_ci
from sord.techniques import ALL_TOKENS, Token

TOK = Token("tk", r"TECHX", "technique", "test", "synthetic technique")


def make_revs(rows):
    """rows: (page, label, minute, body). seq and diff_base derived per page."""
    out, seqs, last = [], {}, {}
    for page, label, minute, body in rows:
        seqs[page] = seqs.get(page, 0) + 1
        rid = f"{page}@{seqs[page]}"
        out.append({"rev_id": rid, "page_id": page, "wiki": "w", "seq": seqs[page], "body": body,
                    "label": label, "time": f"2026-06-16T{10 + minute // 60:02d}:{minute % 60:02d}:00Z",
                    "diff_base": last.get(page, "None"), "ip16": "1.1", "uncertainty_seconds": "1"})
        last[page] = rid
    return prepare_revisions(pd.DataFrame(out))


def test_page_history_added_ignores_restores():
    r = make_revs([("P", "A", 0, "a\nb"), ("P", "B", 1, "a\nb\nc"), ("P", "M", 2, "a"),
                   ("P", "C", 3, "a\nb\nc")])
    added = dict(zip(r["rev_id"], r["added"]))
    assert added["P@1"] == "a\nb"
    assert added["P@2"] == "c"
    assert added["P@3"] == ""
    assert added["P@4"] == ""  # restore of previously seen lines is not an introduction


def test_base_body_is_previous_version():
    r = make_revs([("P", "A", 0, "x"), ("P", "B", 1, "x\ny")])
    assert r.loc[r.rev_id == "P@2", "base_body"].item() == "x"
    assert r.loc[r.rev_id == "P@1", "base_body"].item() == ""


def _world():
    return make_revs([
        ("P1", "A", 0, "hello TECHX"),           # founder introduces technique
        ("P1", "B", 5, "hello TECHX\nreply"),    # B edits page containing it (exposure)
        ("P2", "B", 10, "B page TECHX here"),    # B adopts on a new page (cross-page)
        ("P3", "C", 12, "C own TECHX"),          # C adopts with no observed exposure
        ("P1", "D", 15, "hello TECHX\nreply\nD adds TECHX too"),  # D adopts on the same page
        ("P4", "E", 20, "nothing"),
    ])


def test_adoption_and_founder():
    r = _world()
    f = token_flags(r, TOK)
    a = adoption_table(r, f, {"A", "B", "C", "D", "E"}).set_index("label")
    assert set(a.index) == {"A", "B", "C", "D"}
    assert a.loc["A", "founder"] and not a.loc["B", "founder"]
    assert a.loc["B", "page_novel"] and a.loc["C", "page_novel"]
    assert not a.loc["D", "page_novel"]


def test_exposure_definitions():
    r = _world()
    f = token_flags(r, TOK)
    pop = {"A", "B", "C", "D", "E"}
    e = exposure_table(r, f, pop)
    row = lambda lab, page: e[(e.label == lab) & (e.page_id == page)].iloc[0]
    b2 = row("B", "P2")
    assert b2.E_prior and b2.E_cross and not b2.E_here and b2.E_wiki
    c3 = row("C", "P3")
    assert not c3.E_prior and not c3.E_cross and not c3.E_here and c3.E_wiki
    d1 = row("D", "P1")
    assert d1.E_here and not d1.E_prior
    b1 = row("B", "P1")  # the exposing revision itself is not 'prior'
    assert not b1.E_prior and b1.E_here
    assert row("A", "P1").E_wiki == False  # noqa: E712 (first appearance)


def test_eligible_rows_contains_observed():
    r = _world()
    f = token_flags(r, TOK)
    pop = {"A", "B", "C", "D", "E"}
    a = adoption_table(r, f, pop)
    e = exposure_table(r, f, pop)
    el = eligible_rows(e, a, t0=r.ts.min(), first_order=0)
    assert set(el) == {"B", "C", "D"}
    rows, pos = el["B"]
    assert rows.iloc[pos]["page_id"] == "P2"


def _synthetic_design(rng, n_adopters=60, n_rev=12, effect=False):
    """Each adopter has n_rev eligible revisions; exposure switches on at a random
    revision. Under the null the observed adoption is a uniform draw; under the
    effect it is the first revision after exposure."""
    elig = {}
    for i in range(n_adopters):
        k = rng.integers(1, n_rev)
        ts = np.sort(rng.uniform(0, 1e5, n_rev))
        ep = np.arange(n_rev) >= k
        df = pd.DataFrame({"E_prior": ep, "E_cross": ep, "E_here": rng.random(n_rev) < .2,
                           "E_wiki": np.ones(n_rev, bool), "E_any": ep, "E_first": np.zeros(n_rev, bool), "ts": ts,
                           "first_exp_ts": np.where(ep, ts[k - 1], np.nan)})
        pos = int(k) if effect else int(rng.integers(0, n_rev))
        elig[f"L{i}"] = (df, pos)
    return ShuffleDesign(elig)


def test_permutation_calibrated_under_null():
    rng = np.random.default_rng(1)
    ps = [shuffle_test(_synthetic_design(rng), B=400, seed=s, n_boot=50)["E_prior"]["p_upper"]
          for s in range(300)]
    ps = np.array(ps)
    assert 0.02 <= (ps < 0.05).mean() <= 0.09
    assert 0.40 <= np.mean(ps) <= 0.62


def test_permutation_detects_effect():
    rng = np.random.default_rng(2)
    res = shuffle_test(_synthetic_design(rng, effect=True), B=1000, seed=0, n_boot=200)
    assert res["E_prior"]["p_upper"] < 0.01
    assert res["E_prior"]["excess"] > 0.2
    assert res["lag"]["p_shorter"] < 0.01


def test_hazard_rates():
    r = _world()
    f = token_flags(r, TOK)
    pop = {"A", "B", "C", "D", "E"}
    a = adoption_table(r, f, pop)
    e = exposure_table(r, f, pop)
    h = hazard_table(e, a, t0=r.ts.min(), first_order=0, col="E_prior", n_boot=20)
    # opportunities: B@P1 (unexp), B@P2 (exp, event), C@P3 (unexp, event), D@P1 (unexp, event), E@P4 (unexp)
    assert (h["events_exposed"], h["opps_exposed"]) == (1, 1)
    assert (h["events_unexposed"], h["opps_unexposed"]) == (2, 4)


def test_signoff_merge():
    r = make_revs([("P", "Alpha", 0, "msg -- Beta"), ("Q", "Beta", 1, "x"), ("R", "Gamma", 2, "y -- Nobody")])
    canon = merge_labels_by_signoff(r, {"Alpha", "Beta", "Gamma"})
    assert canon["Alpha"] == canon["Beta"]
    assert canon["Gamma"] == "Gamma"


def test_helpers():
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03) and adj["c"] == pytest.approx(0.06) and adj["b"] == pytest.approx(0.06)
    lo, hi = wilson_ci(5, 10)
    assert lo < 0.5 < hi
    x = np.arange(10.0)
    assert spearman_rows(x, -x[None, :])[0] == pytest.approx(-1.0)


def test_catalogue_regexes_compile_and_are_distinct():
    names = [t.name for t in ALL_TOKENS]
    assert len(names) == len(set(names))
    for t in ALL_TOKENS:
        t.rx  # compiles


def _choice_df(rng, effect, n=400, k=4):
    from sord.stats import conditional_logit_exposure  # noqa: F401
    rows = []
    for g in range(n):
        x = (rng.random(k) < 0.3).astype(int)
        w = np.exp((1.5 if effect else 0.0) * x)
        c = rng.choice(k, p=w / w.sum())
        for j in range(k):
            rows.append((g, f"L{g % 80}", f"a{j}", int(j == c), x[j]))
    return pd.DataFrame(rows, columns=["group", "label", "alt", "chosen", "x"])


def test_conditional_logit_recovers_effect_and_null():
    from sord.stats import conditional_logit_exposure
    rng = np.random.default_rng(3)
    eff = conditional_logit_exposure(_choice_df(rng, True), n_boot=40)
    nul = conditional_logit_exposure(_choice_df(rng, False), n_boot=40)
    assert eff["or_ci"][0] > 2.0
    assert nul["or_ci"][0] < 1.0 < nul["or_ci"][1]


def test_positive_control_planter_copiers_only_adopt_after_exposure():
    from sord.poscontrol import Planter
    rows = []
    for m in range(60):  # 6 labels x 10 revisions over 3 pages
        rows.append((f"P{m % 3}", f"L{m % 6}", m, f"text {m}"))
    r = make_revs(rows)
    pop = {f"L{k}" for k in range(6)}
    pl = Planter(r, pop, t_start=float(r.ts.min()))
    pl.founder_pool = pl.founder_pool[:1]
    rng = np.random.default_rng(0)
    flags, truth = pl.plant(rng, f=1.0, n_adopt=5)
    a = adoption_table(r, flags, pop)
    e = exposure_table(r, flags, pop).set_index("order")
    nonf = a[~a.founder]
    assert truth["n_copied"] == len(nonf)
    assert e.loc[nonf["order"], "E_any"].all()
    flags0, truth0 = pl.plant(rng, f=0.0, n_adopt=5)
    assert truth0["n_copied"] == 0 and truth0["n_adopters"] == 5
