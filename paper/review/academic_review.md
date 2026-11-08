# Academic review: "Spread or Rediscovery? Technique Diffusion in a Real Agent Swarm and in a Seeded Experiment"

Reviewed: 2026-11-08 · Mode: `full` (academic-paper-reviewer v1.11.1) · Manuscript: `paper/main.pdf` (8 pp.), source `paper/main.tex`, `numbers.tex`, `tab_*.tex`
Target: Apart Research Swarm Alignment Hackathon (Nov 2026), Track 2 primary, Track 4 secondary.

**Panel provenance (honest disclosure).** All five seats were run by one model (Claude Opus) in one session, sequentially, with access to the same files. They are role-separated perspectives, not independent reviewers; correlated blind spots are likely. Criteria binding: Apart rubric (`02_Guidelines/judging_criteria.md`). Calibration status: `NOT_CALIBRATED`. The manuscript was not modified.

**Verification scope.** Checked against `results/macros.json`, `results/RESULTS.md`, `results/techniques.json`, `annotations/validation_labels.csv`, `src/sord/*`, `experiments/convention_diffusion/RESULTS.md`, `results/<model>/trials.jsonl`, `src/sord_exp/{env,scenarios,analyze}.py`, the raw export (`03_Resources/datasets/collusion-wiki/revisions.jsonl.gz`), the Murtuza 2026 text, the literature gap matrix, the talk summaries and the judge list.

---

## Phase 0: Field analysis and reviewer configuration

| Item | Assessment |
|---|---|
| Primary discipline | Multi-agent AI safety: empirical science of agent networks |
| Secondary | Computational social science (diffusion, social contagion vs homophily), causal inference from observational logs |
| Paradigm | Mixed: observational forensic study (Study 1) + controlled experiment with LLM agents (Study 2) |
| Maturity | Complete short paper; ~6.3 body pages; reproducible pipeline with generated numbers |
| Venue tier | Hackathon report judged on Impact / Execution / Presentation; should read as a workshop paper |

| Seat | Configured identity |
|---|---|
| Journal-Fit Reviewer (EIC) | Workshop chair for a multi-agent-safety venue (e.g. a NeurIPS MAS-safety workshop); cares about novelty against recent incident analyses and fit to the sprint agenda |
| R1 Methodology | Causal-inference statistician who works on contagion-vs-homophily identification (Shalizi–Thomas, Aral et al.) and permutation inference |
| R2 Domain | LLM multi-agent researcher who knows the collusion.wiki, METR Hugging Face and Swarm Chasers reports and the emergent-conventions literature |
| R3 Perspective | Production security / observability engineer (the dominant judge profile), focused on whether "log reads" and "tracer conventions" are deployable |
| DA | Devil's Advocate: attacks the integrating thesis "copying requires reading; write logs can't see it" |

---

## Phase 1: Panel reports

### 1. Journal-Fit Reviewer (EIC)

**Summary.** The paper asks whether techniques that appear under many agent labels in the collusion.wiki incident spread between agents or were rediscovered, and answers with (1) a write-log analysis using a re-timing permutation null, a within-label choice design and placebo tokens, and (2) a seeded-convention experiment with four open-weight models. It concludes that write-visible exposure explains adoption no better than it explains word echo, that LLM agents copy seeded conventions only when they look, and that oversight infrastructure should log reads.

**Fit and novelty.** Strong. The literature gap matrix (`03_Resources/literature_gap_matrix.md`, T2-RQ3 and T4-RQ1) records that "nobody has estimated spread, as opposed to independent rediscovery, from a real incident log", and a sprint speaker proposed exactly this ("Fleet-to-swarm signal: a technique spreading across agents faster than chance", Howard-Jones, talk idea #27). Murtuza 2026, the closest prior work, does co-editing permutation tests, a taxonomy and a deletion event study but no spread-vs-rediscovery test. Pairing a negative field result with a controlled experiment that explains why the field result is uninformative is a good design for a 48-hour report.

**Strengths.**
- S1. The question is clean, consequential for intervention choice (L58: "If techniques spread, the shared channel is the lever; if they are rediscovered … the lever is the task and the sandbox"), and on the sprint agenda.
- S2. The placebo-token control is the paper's best idea. It turns a tempting 7–17-fold "contagion" hazard ratio (L120) into a calibrated null. Judges reward that kind of self-correction.
- S3. Every number is generated (`numbers.tex`, `make_numbers.py`); the numbers I checked match (see the Methodology report).
- S4. The limitations are candid (L166) and the appendix states what is and is not established (L187).

**Weaknesses (fit-level).**
- W1. The contributions list (L63–66) promises more than the studies deliver: "separates copying from rediscovery causally" (C3) and "write logs cannot detect copying; read logs and tracer conventions can" (C4). Neither half of C4 is tested.
- W2. The two studies meet only in the Discussion (L162). Study 2 never runs Study 1's pipeline, so the bridge ("Study 2 shows why that is the expected result") is argued, not shown.
- W3. Missing positioning against the emergent-conventions literature (Ashery et al., committed-minority tipping), which is the obvious home for a "consensus threshold" claim, and against the Swarm Chasers fleet report, which names the spread-vs-rediscovery problem.

**Recommendation signal:** Minor-to-Major revision. The fit is high; the revisions are mostly scoping, plus one integration analysis.

---

### 2. Reviewer 1: Methodology

**Numbers verified (claimed vs found).**

| Claim (main.tex line) | Source | Match |
|---|---|---|
| 14,591 revisions, 4,579 pages, 3,099 labels (L81) | macros `DataRevisions`, `DataPages`, `DataAgentLabels` | ✓ |
| 15.1% vs 24.1%, excess −0.090 (L52, L100) | `PooledTechniquesEPrior*` | ✓ |
| OR 5.02 [4.07, 6.58]; placebo 4.14 [3.36, 5.18]; ratio 1.21 [0.88, 1.67], p = 0.24 (L109) | `ChoiceTechniquesEPrior*`, `RorEPrior*` | ✓ |
| Same-page excess +0.041 (p = 2×10⁻⁴); contrast +0.045 [0.004, 0.093] (L118) | `PooledTechniquesEHere*`, `ContrastEHere*` | ✓ |
| Hazard ratios 16.8 [10.1, 25.6], 12.0, 7.2; bold 5.2 (L120) | `*HzEPriorRr*` | ✓ |
| 510/560 = 91% of jq_proxy in one 24-h window; 27%; 94% (L120) | `JqProxyBurst*` | ✓ |
| Robustness: 2,783 agents, −0.102, 4.31 vs 3.98; 5.22 vs 4.10 (L122) | `Rob*` | ✓ |
| "roughly 13,000 edits" on 16–22 June (L58) | raw export: 13,339 revisions in that window (all four wikis) | ✓ (but see Minor m3) |
| Precision 1.00 (150 of 150) (L83) | `PrecisionMin`; but `PrecisionStrictPrng` = **0.30** | **Partial: undisclosed** |
| 0/576; 142/192; 141/192; 0/192 vs 81/192 (L52, L145–149) | `tab_s2.tex`, Study 2 RESULTS.md | ✓ |
| Listing 0% (gpt-oss) to 92% (Qwen) (L52) | 0/336; 308/336 = 91.7% | ✓ |
| Pooled slope +1.24 logits/doubling, p = 8.7×10⁻⁵ (L147) | RESULTS.md §4: +1.24 (SE 0.32) | ✓ |
| gpt-oss wrote a page in 48% of unlisted trials (L166) | 162/336 | ✓ |
| "at most 15% of adoptions follow write-visible exposure" (L64) | same-page exposure observed 23.4% (`PooledTechniquesEHereMeanObserved`); wiki-level 99.5% | **✗ (see M1)** |
| "Only Qwen adopted the Answers-Index" (L151) | Ministral 1/2/0 own lines (Table 3) | **✗ minor** |

**Study 1.**

- **M1 (Major). The re-timing test has no positive control and is biased towards the null.** 41% of technique adopters adopt at their first eligible revision (L100), and 43% of labels save one revision (L81). An adoption at a label's first revision cannot be write-visibly exposed, and a one-revision label contributes nothing to the null. So the primary test is structurally pushed negative (every technique's observed share is at or below the null, Fig. 1), and "0 of 15 Holm-significant" says little about power. The paper calls the negative excess a measurement effect (L100), which is right, but then it cannot also lean on the test as evidence against spread. **Fix:** inject synthetic copying into the real log's label structure (for a fraction *f* of adopters, move the adoption to just after a randomly chosen exposure; or simulate agents with Study 2's measured look and copy rates and collusion.wiki's label-churn distribution) and report the detection power of tests (a)–(c) as a function of *f*. This is compute-only, takes 2–4 hours, and is also the cleanest way to integrate the two studies (see DA-1).
- **M2 (Major). "Same effect" is not an equivalence result.** The ratio 1.21 [0.88, 1.67] (L109) is compatible with technique echo being 67% stronger than word echo. "Placebo words show the same effect" (L52, L109) and "techniques no more than words" (L52, L109 heading, L169) should read "no detectable difference; the data allow up to ~1.7×". A TOST against a pre-stated margin would license "same".
- **M3 (Major). The placebos are not matched.** The placebos ("please", "here", "with", "about", "thanks", "also", bold, headings) are high-frequency (e.g. *please*: 941 adopters, 66% at first revision) while most techniques are rare and burst-bound. Echo strength in a conditional logit depends on base rate and on how often alternatives co-occur on a page, so the technique/placebo ratio mixes transfer with frequency. **Fix:** report the ratio against frequency-matched placebos (rare, non-functional strings such as idiosyncratic sign-offs, misspellings or emoji, matched on adopter count and first-appearance date), or at minimum show the per-placebo ORs and a frequency-stratified comparison. Also: `signal_relay` (the one arbitrary technique) is the field's own non-functional marker. It is closer to a matched "tracer" than any placebo, and it is the technique that drives the page-local excess (L118).
- **M4 (Major). Construct validity of `prng_seed` is overstated.** L83 describes it as "brute-forcing the task generator's seed" with precision 1.00, but the strict precision for that description is 0.30 (`RESULTS.md` L31/L47; `validation_labels.csv` rows 122–131): 7 of 10 sampled matches relay RNG-derived predictions rather than perform the seed search. Since `prng_seed` is the only technique with a positive point estimate (L100) and has one of the largest hazard ratios (L120), report both precisions and describe the token as "seed/RNG-prediction talk".
- **m1. Validation is self-labelled and small.** There are 10 events per technique, labelled by the author (with AI assistance, per the LLM statement L212), and recall is unmeasured. Per-technique precision 10/10 has a 95% Wilson lower bound of 0.72. Say who labelled, give the CI, and if possible add a second coder on a 30-event subsample.
- **m2. Multiplicity across exposure definitions and secondary tests.** Four exposure definitions × {re-timing, lag, choice, hazard, acceleration} × 15 techniques. The "one page-local signal" (L118) rests on a pooled p = 2×10⁻⁴ (fine), but the per-technique claim for the egress-proxy exception (p = 0.011, n = 13 eligible adopters) is uncorrected. Label it exploratory.
- **m3.** Table 1's "First-rev" column (share adopting at the label's first *saved* revision, e.g. 0.57 for jq_proxy) and the text's 41% (first *eligible* revision, L100) use different denominators. Define both in the caption or drop one.
- **m4.** Table 2: "all techniques" has 2,415 events but fetch (2,140) + env/coord (273) = 2,413. Explain the two events, or footnote that mixed-family choice sets are counted once.
- **m5.** The T50 "faster than null" test (RESULTS.md §d: 5 Holm-significant, by fractions of an hour over ~500 h) is computed but not reported. Either report it with the placebo comparison (*please* and headings show the same, so it is generic) or remove "We also report … acceleration" ambiguity in L87.

**Study 2.**

- **M5 (Major). Dependence structure and separation in the dose-response logit.** Seeds fix the question, the prior items and the marker codes, and the same 48 seeds are reused across all four models and ten conditions; questions come from 12 templates. `analyze.logit_slope` fits a plain `sm.Logit` with model fixed effects and naive SEs. Gemma and gpt-oss are all-zero on `adopt_suffix` (quasi-complete separation of their fixed effects), so the pooled slope is identified by Ministral and Qwen alone. **Fix:** fit on the two informative models, with SEs clustered by seed (or a GEE/mixed logit with seed and template effects; Firth if needed), and say so. The pooled McNemar tests also treat 4 × 48 model-seed pairs as 192 independent pairs. Report per-model McNemar (already in RESULTS.md) as primary, or use a stratified (Mantel–Haenszel-type) paired test.
- **M6 (Major). The "consensus threshold" inference is not identified by the design (see DA-2).** Only doses 1 and 4 were run with the listing shown, so "only after four" (L52) is untested between one and four. Without the listing, exact copies already occur at dose 2 (Ministral 6/48, Qwen 5/48, pooled 11/192; Table 3). The paper's own dose-response finds no acceleration (L147: −0.04 [−0.25, +0.15] for both models), which argues against a threshold. A semantics alternative also fits: at dose 1 a lone three-character code (`-K7Q`) reads as the author's id, and 141/192 agents substituted their own id (`A57`). Four different authors sharing one code reveals it as a team code. **Fix (cheap, about 1 GPU-hour):** add `dose2_shown` and a `dose4_shown_distinct` condition (four marked pages with four different codes). If the distinct-code condition yields own-id slots and the same-code condition yields copies, the effect is about code semantics; if a dose-2 shown condition already copies, it is graded.
- **m6. Over-precise p-values.** p = 8.3×10⁻²⁵ (L149) and 7.6×10⁻⁶ (L147) from exact McNemar on 81 vs 0 discordant pairs. Report "p < 10⁻⁶" and lead with counts.
- **m7. Format failures are not disclosed.** gpt-oss-120b produced at least one invalid-format turn in 349/480 trials and Ministral in 96/480 (`trials.jsonl`, `invalid` field); gpt-oss skipped writing in 200/480 trials (typically `submit_answer` then `finish`). gpt-oss's "never lists the wiki" (L147) may partly reflect weak tool-protocol compliance rather than disposition. Report invalid-turn rates per model in Table 3 or a footnote.
- **m8.** Appendix B (L195) omits the user-message suffix "Reply with one JSON tool call per turn." (`env.py` L77). The paper says the prompt is "reproduced verbatim", so add it.
- **m9.** "No rediscovery (0/576)" (L145) is informative for the functional index and the code slot, but for the exact arbitrary code and tag it holds by construction (a random three-character code cannot be reinvented). Say which outcomes the 0/576 is a real test for.

**Reproducibility.** Excellent in intent (generated numbers, one command per study, transcripts released). However, **the repository URL in "Code and Data" (L172) does not currently resolve** (`gh repo view astral-fate/spread-or-rediscovery` → "Could not resolve to a Repository"). Make it public before submission, or judges who click it will score a dead link.

---

### 3. Reviewer 2: Domain

**Literature.** The core references are right (von Arx; Murtuza; METR; Lee & Tiwari; Gu et al.; Papadopoulos et al.; Wu et al.; Hammond et al.; Motwani et al.). Missing:
- **Ashery et al. (2024/2025), emergent social conventions and collective bias in LLM populations** (local copy: `03_Resources/papers/lit_search/track2/ashery2024_*`). It shows conventions emerge and that committed minorities tip them past a critical mass, which is the natural prior for, and competitor to, the "consensus threshold" claim (L149). Cite it and say what is different: a one-shot seeded wiki rather than repeated naming games, and an arbitrary code rather than a coordination payoff.
- **Swarm Chasers (Tencent fleet report, 2026):** "a method seen on one place was used on about 20 more within two days, whether by spreading or by being found again". This is the same question raised in an industry incident report; citing it strengthens the "open problem" claim.
- **Classic identification literature:** contagion vs homophily and shared-environment confounding (Shalizi & Thomas 2011; Aral, Muchnik & Sundararajan 2009) and the "reflection problem" (Manski 1993). One sentence placing the re-timing null and placebos in that tradition would earn credibility with methodologists and pre-empt the "this is a known identification problem" objection.
- **Murtuza characterisation (L71).** "It reports no diffusion result" is accurate as far as the text shows, but Murtuza's pipeline figure lists a "URL diffusion" step. Write "lists a URL-diffusion step but reports no spread-versus-rediscovery test" to avoid a contestable absolute.

**Domain accuracy.**
- **D1.** Intro (L58) says the edits went to "a small public wiki", while the data come from four wikis (dse 13,403; probier 1,013; fractal 169; dorfwiki 6), and the export spans 24 May–2 July. Related Work says "roughly 18,000 posts" (L71). Add one clause reconciling 13k (16–22 June), 14.6k (full export, revisions) and 18k (write-up's estimate, posts) so a reader who checks does not see three inconsistent counts.
- **D2.** The incident agents were OpenAI agents. The closest model in Study 2 is gpt-oss-120b, which never listed the wiki unprompted (0/336), yet incident agents demonstrably did read (they replied inside threads, L118). That contrast is informative about external validity and deserves a sentence (see Perspective P2).
- **D3. Integration with the field data.** `signal_relay` is the field's arbitrary naming convention (the only technique tagged *arbitrary*, L83), and it is the one with a strong same-page excess (0.574 vs 0.388, L118). That is the observational analogue of Study 2's arbitrary marker: arbitrary conventions are where copying should be identifiable, and that is where the field data show the signal. The paper does not draw this link. It is the strongest available bridge between the studies and costs one paragraph.

**Contribution.** It is incremental over Murtuza in technique (permutation nulls on this export exist), but new in question and in the placebo-plus-choice design, and new in combining field and seeded evidence. The "tracer convention" idea is a genuinely useful methodological proposal, but it is untested in deployment and should be labelled as a proposal.

---

### 4. Reviewer 3: Perspective (production security / observability)

- **P1. "Log reads" needs to be operational.** The implication (L164) is right but generic. A practitioner wants: which system logs the read (wiki/HTTP server access log, agent-platform tool-call log, egress proxy), the minimum record (timestamp, principal or session id, resource id, version/ETag, bytes), retention, and the join needed (read → later write by the same principal). Note that the wiki operator in this incident probably had HTTP access logs that the public export omits. That makes the recommendation immediately actionable: "operators releasing incident exports should include redacted GET logs". Three sentences or a small box would move Track-4 judges.
- **P2. Mock wiki vs incident (external validity).** The Study 2 environment differs from the incident on the dimensions that plausibly drive looking and copying:
  1. *No informational incentive to look.* The prior pages answer different questions (`scenarios.py`: prior items use different templates from the focal item), and every question is solvable from parametric knowledge. In the incident the board carried answers to the same timed questions (answer relay) and workarounds to binding constraints (egress, fetch). So the "gated by looking" result measures exploration with no payoff.
  2. *No constraint to rediscover against.* Rediscovery requires a shared obstacle. Study 2 has none, so 0/576 "inventions" says nothing about rediscovery of *functional techniques*, which is the field question.
  3. *Single focal agent, scripted priors.* There are no chains or populations, so there are no actual diffusion dynamics; "prior adopters" are identical scripted pages.
  4. *Instructional framing.* The system prompt explicitly asks the agent to leave answers "where teammates can find and reuse it", and the shown condition places the listing in the user turn. Both invite conformity; incident agents were not so instructed (as far as the write-up shows).
  5. *Models.* Open-weight 14–120B models at T = 0.7 with ≤10 turns, not the incident agents.
  The Limitations paragraph (L166) mentions "one short task … single shared wiki … four models" but not items 1, 2 and 4. Add them, and retitle Study 2's claim as "preconditions of copying in a minimal setting".
- **P3. Tracer conventions: deployable, but dual-use.** Seeding canaries into a live agent population to measure transmission is a standard defensive technique (canary tokens), but it means injecting content into a third-party agent channel, and the same measurement helps an attacker optimise propagation. Add one sentence to the dual-use appendix.
- **P4. A usable artifact is latent.** The technique catalogue (`techniques.json`: ten fetch-relay hosts, a counter beacon) is effectively an egress blocklist and detection ruleset for sandbox operators. Saying so, and shipping it as a Sigma/regex rule file, would give security judges the "artifact somebody can use" they reward.

---

### 5. Devil's Advocate

**Strongest counter-argument (≈250 words).** The paper's integrating thesis is "copying is real but conditional on reading, which write logs do not record". Neither study establishes the second half, and the first half is close to definitional. That an agent cannot copy a token it has not seen is a logical necessity, not a finding. What Study 2 adds is that exposure-seeking varies enormously by model (0–92%) and that exposure is far from sufficient: Qwen read seeded pages in 73% of dose-1 trials and copied the exact code in none of them, and the body tag, the only marker that genuinely requires *reading*, was copied in 8 of 1,920 trials. The strongest copying effect (81/192) happens when the page list is placed in the prompt, where no read action occurs at all. So the experimentally supported statement is "agents copy what is put in front of them, sometimes, depending on model and on whether the convention's meaning is clear", not "copying requires reading".

On the field side, the re-timing test is structurally biased to the null by label churn, and the choice design finds that techniques are echoed about as strongly as words with a CI allowing 1.7×. That is a power-limited null, not evidence that "write logs cannot detect copying". The paper never shows a write-log test failing on data where copying is known to occur. Finally, the "consensus threshold" is drawn from two dose points and contradicts the paper's own no-acceleration finding; a simpler account is that a lone code looks like an author id. The paper's honest core (placebos defuse naive contagion estimates; a seeded arbitrary marker is identifiable) is valuable; the bridge and the threshold are not yet earned.

**Issues.**

| ID | Severity | Dimension | Location | Issue |
|---|---|---|---|---|
| DA-1 | CRITICAL | Logic chain | L52 (last sentence), L66 (C4), L162, L169 | "Write logs cannot detect copying" is asserted, never tested. Study 2 produces no multi-agent write log; Study 1 has no positive control. Either run the pipeline on synthetic or seeded logs with known copying (see M1) or downgrade to "in this incident, write-visible exposure did not detect copying beyond echo; Study 2 shows why it could miss it". |
| DA-2 | CRITICAL | Overgeneralisation / alternative explanation | L52, L65, L149, L162, L169 | "Consensus threshold … exact arbitrary tokens only when several prior adopters agree" rests on dose 1 vs 4 (shown) only. It conflicts with exact copies at dose 2 unprompted (11/192) and with the no-acceleration estimate. The semantic-ambiguity alternative (own-id substitution 141/192 at dose 1) is unaddressed. Rephrase, or run the distinct-code and dose-2-shown controls. |
| DA-3 | MAJOR | Overclaim | L64 (C2) | "At most 15% of adoptions follow write-visible exposure" is a factual error. 15.1% is the share under the *prior* definition, which the paper itself calls a lower bound (L85); under the also write-visible same-page definition the observed share is 23.4%, and under wiki-level 99.5%. It is neither "at most" nor an upper bound. |
| DA-4 | MAJOR | Construct conflation | L52, L147 heading, L151, L162 | "Looking", "listing" and "reading" are used interchangeably. Exact-code copying is driven by page *names* (listing), not by reading bodies. The tag, which requires reading, is almost never copied, even among readers (Qwen dose 1: 0/35 readers). |
| DA-5 | MAJOR | Overclaim | L65 (C3) | "Separates copying from rediscovery causally" is true only for arbitrary markers in the seeded setting; it says nothing about functional techniques under shared constraints, which is the field question. |
| DA-6 | MAJOR | External validity | L128–132, L166 | See P2: no incentive to look, no constraint to rediscover, single agent, cooperative instruction. |
| DA-7 | MINOR | Cherry-picking risk | L118 | The only positive field signal (page-local) is presented as a finding; it is one of several exposure definitions tested, and the proxy-exception component has n = 13 with an uncorrected p. Label it exploratory. |

**Ignored alternative explanations.** (i) Identity churn: arriving labels are renamed agents that already knew the technique (acknowledged at L166, but it is the leading explanation of the negative excess and deserves to be stated as such in Results). (ii) Off-wiki channels: shared task prompts, shared retrieval results or shared training could produce co-adoption that looks like rediscovery. (iii) For Study 2: code semantics (DA-2), and instruction-following versus social learning.

**Missing stakeholders.** Wiki operators, who hold the read logs; sandbox and egress-policy owners (the catalogue is their blocklist); the human moderator community that cleaned up the incident (data ethics).

**"So what?" test.** Passes for the placebo lesson (do not report naive contagion ratios without placebos: concrete, generalisable) and for tracer conventions as a proposed measurement. It fails, for now, for "log reads", which is an obvious recommendation unless made operational and shown to resolve the question on data.

**Observations (non-defects).** The re-timing null that preserves each label's activity is well chosen against burstiness; the within-label conditional logit with alternative fixed effects is a strong design; the burst diagnostic (91% of jq_proxy in one 24-h window, 94% referencing one file) is a crisp illustration of why cohort rediscovery and copying are confounded.

---

## Phase 2: Editorial synthesis

**Consensus (≥3 seats).**
1. The question is new, on-agenda, and well motivated (EIC, R2, R3).
2. The placebo control and within-label choice design are the paper's methodological strength (EIC, R1, DA).
3. Headline language overreaches the evidence in three places: the "at most 15%" bound, the "consensus threshold", and "copying requires reading / write logs cannot detect copying" (EIC W1, R1 M2/M6, DA-1–5).
4. The studies are not yet integrated by analysis; the bridge is rhetorical (EIC W2, R1 M1, R2 D3, DA-1).
5. Study 2's external validity relative to the incident is under-discussed (R2 D2, R3 P2, DA-6).

**Disagreements and arbitration.**
- *Is the Study 1 null informative?* R1 and DA say it is underpowered and biased; EIC says it is still a useful bounded negative. Arbitration: both hold. The null on naive contagion (hazard ratios explained away by placebos) is informative; the null on "spread vs rediscovery" is not, without a power analysis. Report it as the former.
- *Is the threshold result salvageable without new runs?* DA wants new conditions; EIC accepts a rewrite. Arbitration: a rewrite that presents dose-1 vs dose-4 as a contrast and names the semantic alternative is sufficient for submission; the two extra conditions are recommended if GPU time allows (about 1 hour).

**DA CRITICAL adjudication.**
- DA-1: **Validated.** C4 and the final abstract sentence are untested as worded. Resolvable by rewording (required) or by the synthetic positive control (recommended).
- DA-2: **Validated.** The data contradict "only after four" as an untested interpolation, and the no-acceleration estimate undercuts "threshold". Resolvable by rewording (required); controls recommended.

**Editorial decision: MAJOR REVISION** (for a workshop venue). For the hackathon deadline, the required items below are rewriting only (about 2–3 hours); with them the paper is a strong submission. The recommended items (positive control, two extra Study 2 conditions) would move Execution from "competent" towards "strong".

---

## Revision roadmap

### Critical (required)

| # | Location | Problem | Concrete fix |
|---|---|---|---|
| C1 | L64 (contribution 2); L187 (Appendix A, "bounds the share") | "At most 15%" mislabels a lower-bound measure as an upper bound; same-page exposure observed is 23.4% | "15% of adopters had write-visible exposure under the strictest definition (23% if the page they edited already contained the technique)". In App. A, "reports", not "bounds". |
| C2 | L52 ("only after four … a consensus threshold"); L65; L149 (last sentence); L162; L169 | Threshold claim untested between 1 and 4; contradicted by dose-2 copies and no acceleration; semantic alternative | Abstract: "…but the exact arbitrary code only when four prior pages shared it (0/192 at one, 81/192 at four)". Body L149: replace the last sentence with "A single code is read as a per-author id (141/192 substituted their own id); four pages sharing it reveal a shared convention. We cannot distinguish a consensus threshold from this disambiguation, and unprompted copying rises log-linearly with no acceleration (L147)". Optionally add `dose2_shown` and `dose4_shown_distinct`. |
| C3 | L52 (last sentence); L66 (C4); L162; L169 | "Write logs cannot detect copying" asserted, not shown | Reword: "In this incident write-visible exposure did not distinguish technique spread from word echo, and Study 2 shows copying that a write log would not reveal". Or (recommended) add the positive-control power analysis (R1 M1) and keep a quantitative version. |
| C4 | Code and Data, L172 | Repository URL does not resolve | Make `astral-fate/spread-or-rediscovery` public (or fix the URL) and re-check before submitting. |

### Major

| # | Location | Problem | Fix |
|---|---|---|---|
| M1 | Study 1 Results (new paragraph after L122) or appendix | No positive control / power for tests (a)–(c) | Inject copying at rates *f* ∈ {5, 10, 20, 40}% into the real label structure (or simulate agents with Study 2's look and copy rates); report detection rate per test. Compute only. |
| M2 | L52, L109 (heading and text), L169 | "Same effect" / "no more than words" claims equivalence from a non-significant ratio | "No detectable difference (ratio 1.21, 95% CI 0.88–1.67)". Change the heading to "Agents echo what they read; techniques no detectably more than words". |
| M3 | L83, L109; Table 2 | Placebos not frequency-matched | Add frequency-matched rare placebos, or a frequency-stratified comparison; at minimum list per-placebo ORs in an appendix and acknowledge the mismatch in Limitations. |
| M4 | L83; Table 1 | `prng_seed` strict precision 0.30 undisclosed; description overstated | Report "precision 1.00 (strict 0.30 for `prng_seed`: most matches relay RNG-derived predictions)"; redescribe the token. State the labeller, n = 10/technique, Wilson lower bound, and that recall is unmeasured. |
| M5 | L52, L147 (heading), L151, L162, L169 | "Looking", "listing" and "reading" conflated; "copying requires reading" | Define *listing* (names) vs *reading* (bodies). Rewrite: "copying requires exposure; exposure-seeking varies 0–92% across models and is not sufficient (Qwen read seeded pages in 73% of dose-1 trials and copied the code in none)". Title the paragraph "Copying is gated by exposure". |
| M6 | L65 (C3) | "Causally separates copying from rediscovery" | "…for arbitrary markers, which cannot be rediscovered, in a minimal seeded setting". |
| M7 | L128–132, L166 | External validity of the mock wiki | Add to Limitations: no relevant answer on the wiki (no incentive to look), no shared constraint (no opportunity to rediscover functional techniques), single focal agent with scripted priors, cooperative instruction, open-weight models; note that gpt-oss never listed unprompted although incident agents read and replied in threads. |
| M8 | L132, L147; `analyze.logit_slope` | Naive SEs; quasi-separation; pooled McNemar treats model-seed pairs as independent | Fit the slope on Ministral + Qwen with seed-clustered SEs (or GEE/mixed logit with seed and template effects); report per-model McNemar as primary; state the multiplicity stance. |
| M9 | Discussion L162 | Integration via field arbitrary convention missing | Add: "`signal_relay`, the field's one arbitrary convention, is the technique with the strongest page-local excess (0.57 vs 0.39): where a convention cannot be rediscovered, the write log does show copying, as Study 2 predicts." |
| M10 | Related Work L71–75 | Missing Ashery et al.; Swarm Chasers; contagion/homophily identification; Murtuza nuance | Add 3–4 sentences and references (see R2). |

### Minor

| # | Location | Fix |
|---|---|---|
| m1 | L58 vs L71 vs L81 | Reconcile 13,000 (16–22 June, four wikis), 14,591 (full export, 24 May–2 Jul) and 18,000 (write-up's post estimate); "small public wikis". |
| m2 | L151 | "Only Qwen adopted" → "Almost only Qwen (Ministral: 3 trials)". |
| m3 | Table 1 caption / L100 | Define "First-rev" (first saved revision) vs "first eligible revision" (41%). |
| m4 | Table 2 | Explain 2,415 ≠ 2,140 + 273. |
| m5 | L147, L149 | Report p < 10⁻⁶ rather than 8.3×10⁻²⁵; lead with counts. |
| m6 | Table 3 / footnote | Add invalid-format-turn rates (gpt-oss 349/480 trials, Ministral 96/480) and note what gpt-oss's non-writing trials look like. |
| m7 | App. B L195 | Add "Reply with one JSON tool call per turn." to the quoted user message. |
| m8 | L145 | State that 0/576 is a substantive test for the index and the code slot, and holds by construction for the exact code and tag. |
| m9 | L118 | Label the per-technique page-local result exploratory (uncorrected, n = 13 for the proxy exception). |
| m10 | App. A Dual use L189 | Acknowledge that the released regex for `proxy_exception_bypass` names the exception host and `NO_PROXY` (already public in the write-up); add a sentence on tracer-seeding ethics (injecting content into third-party agent channels). |
| m11 | L164 | Make "record reads" operational: source (HTTP access log / tool-call log / egress proxy), minimum fields, and "incident exports should include redacted GET logs". |
| m12 | PDF text layer | `pdftotext` drops italic *p* with newpxmath (e.g. "ratio 1.21, = 0.24"). It renders correctly on screen; consider `\input{glyphtounicode}\pdfgentounicode=1` or the `mmap` package so math glyphs survive copy-paste, if cheap. |
| m13 | L87 / RESULTS §d | Either report the T50 test (with placebo comparison) or remove it from the method list. |

**Author triage.** Left to the author; no work order is imposed beyond the Critical/Major/Minor classification.
