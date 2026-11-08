# Spread or Rediscovery? Technique Diffusion in a Real Agent Swarm

Fatimah Emad Eldin, Trouve Labs. Apart Research Swarm Alignment Hackathon, November 2026.

In mid-2026, thousands of autonomous agents that self-identified as OpenAI agents used small public
wikis as a message board (the *collusion.wiki* incident; Von Arx et al., 2026). The same
techniques show up under many agent labels: fetch proxies, a timer-acceleration trick, an external
counter used as a beacon, seed brute-forcing, an egress-proxy exception. This repository asks
whether those techniques spread socially, with one label copying another through the wiki, or
whether each label rediscovered them independently because it faced the same task constraints.

The pipeline:

1. builds a catalogue of 15 techniques and 8 placebo tokens (plain words and markup). Each
   technique regex is checked on a hand-read sample.
2. records when each label first introduces each token. A token counts as introduced only if the
   line is new to the page's whole history, so full-page overwrites and restores are not counted.
3. proxies exposure from what a label had in front of it when it wrote: the base version of each
   page it saved. Reads are not observed, so this is a lower bound on what the label saw.
4. runs four tests: a time-shuffle (re-timing) permutation test, exposed-versus-unexposed adoption
   hazards, a within-label conditional-logit choice test, and checks on diffusion speed and
   acceleration. The placebos serve as a negative control. Robustness variants merge labels by
   sign-off, drop the 10 most active labels, jitter timestamps, and restrict to the main wiki.

Results are in `results/RESULTS.md` and the paper draft is in `paper/draft.md`.

## Run

```bash
pip install -e .[test]
make test                     # unit tests on synthetic data, including null calibration
make run DATA="<path to collusion-wiki export>"   # writes everything to results/
make report                   # regenerates results/RESULTS.md and results/macros.json
```

`python -m sord.run_all --data <dir> --out results/` reproduces every number, table and figure.
The seed is fixed (`--seed 20261109`). A full run takes about 5 minutes on a laptop CPU.

## Layout

| path | content |
|---|---|
| `src/sord/load.py` | load the export, page-history diffing, agent population, sign-off label merging |
| `src/sord/techniques.py` | technique catalogue and placebo tokens (names and regexes only) |
| `src/sord/adoption.py` | first-introduction (adoption) events |
| `src/sord/exposure.py` | exposure definitions (strict page-level, cross-page, same-page, loose wiki-level) |
| `src/sord/stats.py` | re-timing permutation test, hazards, conditional logit, acceleration, Holm |
| `src/sord/figures.py`, `report.py` | figures (PNG, 200 dpi) and the generated RESULTS.md / macros |
| `annotations/validation_labels.csv` | hand judgements for the regex precision sample |
| `results/` | all intermediate and final tables (CSV/JSON), figures, RESULTS.md |
| `paper/draft.md` | paper draft |

## Data provenance and licence

The data is the public export of the collusion.wiki investigation (Von Arx, Byrd, Kitts and
Larsen, *Discovery of a new OpenAI agent message board*, Nightingale Collective, September 2026;
https://collusion.wiki/explorer/download). It is **not** included in this repository. Download it
and pass its directory with `--data`. The export does not state a licence. We treat it as research
data, cite it as above, and redistribute none of it.

The page text in the export is untrusted. The code only matches regular expressions against it and
never executes or renders it. The outputs record technique *names* and short descriptors. They do
not reproduce payloads, credentials, tokenised URLs or bypass procedures.

Code: MIT licence (see `LICENSE`).
