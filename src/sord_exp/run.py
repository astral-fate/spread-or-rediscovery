"""Resumable runner for Study 2.

Each finished trial is appended to <out>/trials.jsonl immediately (one transcript per trial in <out>/transcripts/).
Re-running the same command skips completed (model, condition, seed) triples and retries failed ones
(failures go to errors.jsonl). Run one process per output directory: never two writers on one trials.jsonl.
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .env import CONDITIONS, Cond, run_agent
from .grade import grade
from .llm import load_env_file, make_backend
from .scenarios import make_scenario

LOCK = threading.Lock()


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def _append(p: Path, rec: dict) -> None:
    with LOCK, p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _log(out: Path, msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOCK, (out / "run.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_trial(backend: str, model: str, cond_name: str, seed: int, out: Path) -> dict:
    llm = make_backend(backend, model)
    s = make_scenario(seed)
    cond = Cond.get(cond_name)
    t0 = time.time()
    ex = run_agent(llm, s, cond, seed)
    g = grade(s, cond, ex)
    tdir = out / "transcripts"
    tdir.mkdir(exist_ok=True)
    tid = f"{model.replace('/', '_').replace(':', '-')}__{cond_name}__{seed}"
    (tdir / f"{tid}.json").write_text(json.dumps({"initial_wiki": ex["initial_wiki"], "final_wiki": ex["final_wiki"],
                                                  "actions": ex["actions"], "transcript": ex["transcript"]},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    return dict(model=model, condition=cond_name, seed=seed, agent=s.agent_id, qid=s.item.qid, template=s.item.template,
                truth=s.item.answer, suffix=s.suffix, tag=s.tag, **g, actions=ex["actions"], usage=llm.usage,
                secs=round(time.time() - t0, 1), ts=time.time())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="openai", choices=["openai", "scripted"])
    ap.add_argument("--model", default="scripted", help="one model id per process, e.g. modal:gemma-4-31b-it")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--seeds", type=int, default=48)
    ap.add_argument("--seed-start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    ap.add_argument("--env-file", default=None, help="file with API keys (KEY=value lines); values are never logged")
    a = ap.parse_args(argv)
    load_env_file(a.env_file)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    trials_p, err_p = out / "trials.jsonl", out / "errors.jsonl"
    done = {(r["model"], r["condition"], r["seed"]) for r in read_jsonl(trials_p)}
    conds = [c.strip() for c in a.conditions.split(",") if c.strip()]
    todo = [(c, s) for s in range(a.seed_start, a.seed_start + a.seeds) for c in conds if (a.model, c, s) not in done]
    _log(out, f"start {a.model}: {len(done)} done, {len(todo)} to run ({len(conds)} conditions)")
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(run_trial, a.backend, a.model, c, s, out): (c, s) for c, s in todo}
        for f in as_completed(futs):
            c, s = futs[f]
            try:
                _append(trials_p, f.result())
                ok += 1
                if ok % 20 == 0:
                    _log(out, f"progress: {ok} ok, {fail} failed of {len(todo)}")
            except Exception as e:
                fail += 1
                _append(err_p, {"model": a.model, "condition": c, "seed": s, "error": repr(e),
                                "tb": traceback.format_exc()[-1500:], "ts": time.time()})
                _log(out, f"FAIL {a.model} {c} {s}: {e!r}")
    _log(out, f"end: {ok} ok, {fail} failed this run")


if __name__ == "__main__":
    main()
