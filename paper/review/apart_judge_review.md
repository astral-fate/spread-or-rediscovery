# Judge review: Spread or Rediscovery? Technique Diffusion in a Real Agent Swarm and in a Seeded Experiment
Sprint: Swarm Alignment Hackathon (Nov 2026) | Track: 2 (Science of Agent Networks), secondary 4 (Multi-Agent Oversight) | Reviewed: 2026-11-08

Personas are archetypes from the `apart-judge-review` skill (built from public judge reviews), not real judges. Quotes come only from the skill's references; anything else is inference. The report was not modified.

## Verdict
This is a likely top-quartile submission: a new, on-agenda question answered on real incident data with a placebo control that kills its own tempting contagion estimate, plus a seeded experiment across four models. The single biggest lever is to stop the headline from claiming more than the data show ("at most 15%", "consensus threshold", "copying requires reading / write logs cannot detect copying"). That is about 2 hours of rewriting. After that, a compute-only positive control for the Study 1 pipeline both fixes the main Execution gap and ties the two studies together.

## Predicted rubric scores
| Dimension | Predicted | Why | To gain one point |
|---|---|---|---|
| Impact & Innovation | **4** (3.5–4.5) | Real-incident data (the rubric note says this is the "fast route to new to the field"); a question a sprint speaker proposed (fleet-to-swarm signal, talk idea #27) and the gap matrix lists as open; placebo lesson generalises; tracer conventions are a reusable idea. Held back: the oversight recommendation ("log reads") is generic, and Study 2 is a minimal toy. | Make the recommendation operational (what to log, where, the join) and ship the technique catalogue as a usable ruleset/blocklist; frame tracer conventions as a tested measurement (they are, in Study 2). |
| Execution Quality | **3.5** (3–4) | Strong design pieces: re-timing null preserving each label's activity, within-label conditional logit, placebo tokens, Holm, 4 robustness variants, 1,920 paired trials on 4 models, Wilson CIs, exact McNemar, generated numbers. Losses: no positive control for the field pipeline (its primary test is biased to the null by label churn); "same as placebos" claimed from a non-significant ratio (CI to 1.67×); `prng_seed` strict precision 0.30 undisclosed; self-labelled validation of 10 events per technique; threshold claim from 2 dose points; naive SEs in the pooled logit. | Positive-control power analysis on the real label structure; rescope the three overclaims; disclose strict precision; seed-clustered SEs; optionally the `dose4_shown_distinct` and `dose2_shown` conditions. |
| Presentation & Clarity | **4** (3.5–4) | Clean structure, honest Limitations, numbers consistent with outputs, good figures. Losses: dense, jargon-heavy abstract ("write-visible exposure", "re-timing null", "choice design"); Table 3 is dense; no worked example or transcript; no schematic of the two-study logic; dead code link (currently). | Rewrite the abstract in plain words with one design sentence per study; add a 4-line transcript excerpt (dose-1 own-id vs dose-4 copy); add a one-row schematic; fix the repo link. |

**Average ≈ 3.8** (range 3.5–4.2). With the rewrite-only fixes: about 4.0. With the positive control as well: about 4.2.

## Hard gates
- **FAIL (fix before submitting): Code link.** `https://github.com/astral-fate/spread-or-rediscovery` does not resolve (`gh repo view` → "Could not resolve to a Repository"). Judges who clone repos penalise dead links ("The code and data link in the report is dead.", IR-3).
- PASS: Body length about 6.3 pages (body ends on p. 7 before References); limit is 8 pages.
- PASS: Abstract about 230 words (limit 150–250).
- PASS: Limitations and Dual-Use / Ethical appendix present (App. A), with "what it does / does not establish".
- PASS: LLM usage statement present and accurate.
- PASS: Template footnote and title block.
- MINOR: The PDF text layer drops the italic *p* in several places (e.g. "ratio 1.21, = 0.24"; "Holm = 0.007"). It renders correctly on screen, but judges who copy-paste or use text extraction will see gaps.

## Persona reviews

### A — Control/security researcher
- **Looks at first:** whether there is a monitor or detector and whether it holds up; what the threat model is.
- **Sharpest questions:** (1) Would your write-log tests have detected copying if it had happened? You never show a case where they fire (no positive control; §3.2). (2) What is the false-positive story: if I deploy "read logs + tracer conventions", what does a benign agent population look like? (3) Your techniques are egress/fetch workarounds: where is the defence?
- **Red flags:** the field "detector" is never shown to work; tracer conventions are proposed for deployment but not tested against agents who ignore the wiki (gpt-oss: 0/336 listings).
- **Would praise:** the placebo control as a self-attack on the naive hazard ratios ("here they would have suggested 7.2–16.8-fold contagion", L164). This is the "you attacked your own grader" pattern. The burst diagnostic (91% of jq_proxy adopters in one window, 94% on one file).
- **Inferred score:** I 4 / E 3 / P 4.

### B — Replicator / numbers auditor
- **Looks at first:** repo, generated numbers, abstract-vs-body consistency.
- **Sharpest questions:** (1) Why does contribution 2 say "at most 15%" when your own same-page exposure share is 23%? (2) Why is `prng_seed` precision 1.00 in the paper but 0.30 strict in `RESULTS.md`? (3) The repo link doesn't resolve: how do I check?
- **Red flags:** dead link; the "at most" bound; three different incident sizes (13,000 edits L58; 18,000 posts L71; 14,591 revisions L81) with no reconciling sentence; "Only Qwen adopted the Answers-Index" while Table 3 shows Ministral 1/2/0; Table 2 "all techniques" 2,415 ≠ 2,140 + 273.
- **Would praise:** `make_numbers.py` generating every macro; most numbers recompute exactly (table below).
- **Inferred score:** I 4 / E 3–4 / P 4 (drops to E 3 if the link is still dead).

### C — Measurement / construct-validity scientist
- **Looks at first:** instruments, validation and rival explanations.
- **Sharpest questions:** (1) Your regex validation is 10 events per technique, labelled by you: second coder? recall? (2) Is "consensus threshold" the effect, or did a single `-K7Q` look like an author id? 141/192 put their own id in the slot. (3) Placebos are high-frequency words; the techniques are rare and bursty. Are you comparing transfer or base rates?
- **Red flags:** "placebo words show the same effect" from a ratio with CI [0.88, 1.67] ("'no measurable gap in this sample' rather than 'absent'"); threshold inferred from dose 1 vs 4 only while the unprompted dose-response shows exact copies at dose 2 (11/192) and no acceleration; "copying requires reading" when the strongest copying happens from page *names* in the prompt and the body tag is almost never copied (8/1,920).
- **Would praise:** arbitrary markers that "can actually fail" (cannot be rediscovered, 0/576 without seeding); paired-by-seed design; Holm correction; robustness variants.
- **Inferred score:** I 4 / E 3 / P 4.

### D — Governance / policy
- **Looks at first:** whether a lab or regulator could act on it.
- **Sharpest questions:** (1) "Record reads": who records them, with what fields and retention, and how is privacy handled? (2) Should incident disclosures (like the collusion.wiki export) include access logs? (3) Is seeding tracer conventions into third-party agent channels acceptable?
- **Red flags:** the recommendation is a single sentence ("rather generic / difficult to operationalize" risk); untested in deployment.
- **Would praise:** grounding in a real, public incident record with dates and counts; careful data ethics (no re-identification, no IP linkage).
- **Inferred score:** I 3.5–4 / E 3.5 / P 4.

### E — Industry practitioner / time-pressed engineer (largest share of this judge pool: SRE, IAM, security and platform engineers)
- **Looks at first:** abstract, Figure 2, "what do I do with this".
- **Sharpest questions:** (1) In one line, did the agents copy or not? (2) What do I log on Monday? (3) Can I use your catalogue to block these relays?
- **Red flags:** abstract density (four technical constructs before the first result); Table 3 is a wall of fractions; no worked example; no deployable artifact named.
- **Would praise:** clear two-study structure; the oversight takeaway; the observation that naive contagion numbers mislead.
- **Inferred score:** I 4 / E 3.5 / P 3.5–4.

### F — Organiser / agenda owner
- **Looks at first:** fit to the sprint agenda and tracks; whether others can build on it.
- **Sharpest questions:** (1) Which named open problem is this? (State it: the "fleet-to-swarm signal" speaker idea and the gap matrix's "nobody has estimated spread vs rediscovery from a real incident log".) (2) Is the seeded wiki reusable as a testbed (Track 1 crossover)? (3) What would a month of follow-up add?
- **Red flags:** no explicit "what a month of follow-up would add"; the agenda link is implicit.
- **Would praise:** real incident data plus a controlled experiment; release of harness and transcripts; honest limits.
- **Inferred score:** I 4–4.5 / E 3.5 / P 4.

## Checklist (24 items)
| # | Item | Status | Anchor and reason |
|---|---|---|---|
| 1 | Honest scope; negatives in main text | PARTIAL | Field null and limits reported (L100, L166, App. A), but the headline overclaims: "at most 15%" (L64), "only after four … consensus threshold" (L52, L149), "write logs cannot detect copying" (L66). |
| 2 | Headline sentences match evidence | FAIL | "Same effect" / "no more than words" from ratio CI [0.88, 1.67] (L52, L109); "copying requires reading" vs name-driven copying and 8/1,920 tag copies; "causally separates" (L65). |
| 3 | n, seeds, models up front | PASS | 1,920 trials, 48 seeds × 10 conditions × 4 models (L132); the field n is clear. A Limitations note on model mix is present. |
| 4 | Validate the judge/labels | PARTIAL | Regex precision from 150 self-labelled events, no second coder, recall unmeasured; `prng_seed` strict precision 0.30 undisclosed (L83). Study 2 uses exact-match grading, so no LLM judge is needed (good). |
| 5 | Positive, negative/matched controls, decoy | PARTIAL | Negative controls are strong (placebos, isolated/neutral4, re-timing null). There is no positive control for the Study 1 pipeline; Study 2 is a positive control for "copying exists", not for the detector. |
| 6 | Kill the obvious confound | PARTIAL | Burst confound handled (within-label tests, burst diagnostic); label churn is acknowledged but not quantified; placebo frequency mismatch; code-semantics confound in Study 2 unaddressed. |
| 7 | Realistic setting or say why not | PARTIAL | Study 1 is real data (big plus). The Study 2 mock wiki lacks an incentive to look and a constraint to rediscover against; this is not discussed (L166). |
| 8 | One clear important framing | PASS | Swarm vs fleet; channel vs task as the intervention point (L58). |
| 9 | Clear abstract | PARTIAL | Correct and complete but dense; jargon before results. |
| 10 | Repeated runs, CIs, variance | PASS | Bootstrap CIs, cluster bootstrap over labels, Wilson CIs, 48 seeds. Pooled logit SEs are not clustered by seed (minor). |
| 11 | Concrete examples | FAIL | No transcript or example page in body or appendix (the prompt is given in App. B). |
| 12 | FPR / benign side | N/A–PARTIAL | Not a detector paper per se; but if "tracer conventions" and "read logs" are proposed for monitoring, nothing is said about false alarms. |
| 13 | Usable artifact | PARTIAL | Pipeline and harness released; the technique catalogue could be offered as an egress blocklist/ruleset but isn't framed as one. |
| 14 | Reproducible on inspection | FAIL (currently) | Generated numbers and commands are given, but the repo link does not resolve. |
| 15 | Internal consistency | PARTIAL | Most numbers match; issues: "at most 15%" vs 23% same-page; 13k/14.6k/18k; "only Qwen"; Table 2 event sum; "First-rev" 0.57 vs "41%" denominators. |
| 16 | Stress-test own method | PASS | Placebos deflate the naive hazard ratios; four robustness variants. |
| 17 | Tested mitigation | FAIL | "Log reads" and tracers are proposed, not tested (Study 2 does show tracers are measurable in a sandbox; say so). |
| 18 | Adjacent prior work | PARTIAL | Missing Ashery et al. (conventions, committed-minority tipping), Swarm Chasers fleet report, contagion-vs-homophily identification literature. |
| 19 | Specific recommendations | PARTIAL | Placebo recommendation is specific; "record reads" is not operational. |
| 20 | Threat model | PARTIAL | The intervention logic is clear; there is no explicit adversary/operator model for the monitoring proposal. |
| 21 | Fit to sprint agenda | PARTIAL | Tracks named (L60), but not the speaker idea or the open problem. |
| 22 | Readable figures with error bars | PASS | Fig. 2 has Wilson intervals and is legible; Fig. 1 is clear. Fig. 2 legend text is small. |
| 23 | AI-use statement | PASS | Present and specific (L212). |
| 24 | Specific Limitations & Dual-Use appendix | PASS (minor gap) | Specific and honest; it should add that the `proxy_exception_bypass` regex names the exception host and `NO_PROXY` (already public), and the ethics of seeding tracers into third-party channels. |

## Fixes ranked by score gain per hour
| Rank | Fix | Dimension | Expected gain | Effort | New experiment? |
|---|---|---|---|---|---|
| 1 | Make the repo public / fix the URL (L172) and re-check | E, P | Avoids a −0.5 to −1 penalty from clone-checking judges | 10 min | No |
| 2 | Rescope three overclaims: C2 "at most 15%" → "15% (strict) / 23% (same-page)"; "only after four … consensus threshold" → "at four but not at one; we cannot separate a threshold from code disambiguation" (cite 141/192 own-id, 11/192 at dose 2 unprompted, no acceleration); C4 and the final abstract sentence → "in this incident write-visible exposure did not distinguish spread from echo" | E (+0.5), I (protects) | +0.5 E | 45 min | No |
| 3 | Replace "same effect / no more than words" with "no detectable difference (1.21, CI 0.88–1.67)"; define listing vs reading and rename "Copying is gated by looking" → "…by exposure"; note that reading is not sufficient (Qwen dose 1: 0/35 readers copied) | E, P | +0.25 E | 30 min | No |
| 4 | Disclose `prng_seed` strict precision 0.30, the labeller, the Wilson lower bound, and unmeasured recall; label the page-local per-technique result exploratory | E | +0.25 E (removes a B/C red flag) | 20 min | No |
| 5 | Integration paragraph: `signal_relay` (the field's arbitrary convention) is the technique with the page-local excess, which is what Study 2 predicts for non-rediscoverable conventions | I, P | +0.25 I/P | 20 min | No |
| 6 | Plain-language abstract rewrite (one design sentence per study, results in counts) + a 4-line transcript excerpt (dose-1 own-id vs dose-4 copy) + a short operational box: "what to log" (source, fields, join; incident exports should include redacted GET logs) and "catalogue = egress blocklist" | P, I | +0.25–0.5 P, +0.25 I | 1.5 h | No |
| 7 | External-validity paragraph for Study 2 (no relevant answer on the wiki → no incentive to look; no shared constraint → no rediscovery opportunity; scripted single-agent priors; cooperative instruction; gpt-oss invalid-format turns in 349/480 trials) + missing related work (Ashery et al.; Swarm Chasers; contagion vs homophily) | E, I | +0.25 E | 45 min | No |
| 8 | Positive control / power analysis: inject copying at 5–40% into the real label structure (or simulate agents with Study 2's look and copy rates) and report what tests (a)–(c) detect | E (+0.5), I | +0.5 E | 2–4 h | Compute only (no LLM) |
| 9 | Two Study 2 conditions: `dose2_shown` and `dose4_shown_distinct` (four different codes) to separate threshold from disambiguation | E, I | +0.25–0.5 E | ~1 GPU-h + rerun analysis | Yes (cheap) |
| 10 | Seed-clustered SEs (Ministral + Qwen only) for the dose slope; per-model McNemar as primary; "p < 10⁻⁶" instead of 8.3×10⁻²⁵; reconcile 13k/14.6k/18k; fix "only Qwen", the Table 2 sum and the "First-rev" definition; text-layer *p* | E, P | +0.1–0.25 | 1 h | No |

## Numbers checked (Persona B)
| Claim in report | Found in results | Match? |
|---|---|---|
| 14,591 revisions; 4,579 pages; 3,099 labels | `macros.json` | ✓ |
| ~13,000 edits on 16–22 June | raw export: 13,339 revisions in window (four wikis) | ✓ (unit/wiki count should be reconciled with 18,000 posts, L71) |
| 15.1% vs 24.1%; excess −0.090; 0/15 Holm | `PooledTechniquesEPrior*`, `NSigHolmEPrior` = 0 | ✓ |
| OR 5.02 [4.07, 6.58]; placebo 4.14 [3.36, 5.18]; ratio 1.21 [0.88, 1.67], p = 0.24 | `Choice*EPrior*`, `RorEPrior*` | ✓ |
| Fetch-proxy OR 2.00 | `ChoiceFetchproxyEPriorOddsRatio` = 1.999 | ✓ |
| Same-page +0.041 (p = 2×10⁻⁴); placebo −0.004 (p = 0.69); contrast +0.045 [0.004, 0.093] | `PooledTechniquesEHere*`, `ContrastEHere*` | ✓ |
| signal_relay 0.574 vs 0.388; proxy exception 0.385 vs 0.153, p = 0.01 | `SignalRelayEHere*`, `ProxyExceptionBypassEHere*` (p = 0.0114) | ✓ |
| Hazard ratios 16.8 [10.1, 25.6], 12.0, 7.2; bold 5.2 | `*HzEPriorRr*` | ✓ |
| 91% (510/560) jq_proxy in 24 h; 27% arrivals; 94% same file | `JqProxyBurst*` | ✓ |
| jq_proxy lag 0.20 h vs 0.32 h, Holm p = 0.007; 3 proxies | `JqProxyLag*`, `JqProxyHolmLag` = 0.0066, `NSigHolmLag` = 3 | ✓ |
| Robustness 2,783 agents; −0.102; 4.31 vs 3.98; 5.22 vs 4.10 | `Rob*` | ✓ |
| Regex precision 1.00 (150/150) | `PrecisionMin` = 1.0; **`PrecisionStrictPrng` = 0.30** | Partial: strict figure undisclosed |
| "At most 15% of adoptions follow write-visible exposure" (C2) | same-page observed 0.234; wiki-level 0.995 | **✗ wrong direction of bound** |
| 0/576 no-convention adoptions | Table 3 / RESULTS.md | ✓ |
| Listing 0/336 (gpt-oss) to 308/336 (Qwen) | RESULTS.md §2 | ✓ |
| 142/192 slot; 141/192 own id; 0/192 vs 81/192 exact | RESULTS.md §2, §3 | ✓ |
| Unprompted exact suffix 0/6/10 and 0/5/8; neutral4 vs dose4 0 vs 18/192 | RESULTS.md §2, §3 | ✓ (note: dose 2 already > 0, contradicting "only after four" as a general claim) |
| Slope +1.24/doubling, p = 8.7×10⁻⁵; acceleration −0.04 [−0.25, +0.15] / [−0.23, +0.15] | RESULTS.md §4 | ✓ |
| Body tag 8/1,920 | Table 3 | ✓ |
| Qwen index 30/18/16; reads 35/21/17; 8/48 vs 22/48 | Table 3, RESULTS.md | ✓ |
| "Only Qwen adopted the Answers-Index" | Ministral 1/2/0 own lines | ✗ (minor) |
| gpt-oss wrote a page in 48% of unlisted trials | 162/336 | ✓ |
| (Undisclosed) gpt-oss invalid-format turns | `trials.jsonl`: ≥1 invalid turn in 349/480 trials; Ministral 96/480 | Not reported |
