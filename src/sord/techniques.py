"""Technique catalogue and placebo tokens.

Each technique is identified by a regular expression over revision text.
Descriptors are deliberately short names: the catalogue records *that* a
technique was used, never how to reproduce it.

The catalogue was assembled from a frequency analysis of text added in agent
revisions (URL hosts and tokens ranked by the number of distinct labels that
introduced them), cross-referenced with the techniques described in the
collusion.wiki write-up. Precision was checked on hand-read samples (see
annotations/validation_labels.csv and results/technique_catalogue.csv).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    name: str
    pattern: str
    kind: str  # "technique" or "placebo"
    family: str
    description: str
    # "functional": solves a task/environment constraint;
    # "arbitrary": naming/formatting convention with no functional value by itself
    function: str = "functional"
    function_note: str = ""

    @property
    def rx(self) -> re.Pattern:
        return re.compile(self.pattern)


TECHNIQUES: list[Token] = [
    # --- third-party fetch / reformatting proxies (data-access tooling) ---
    Token("jina_reader", r"r\.jina\.ai", "technique", "fetch-proxy",
          "Reader-proxy URL prefix used to fetch a page as plain text"),
    Token("jq_proxy", r"jqp\.vercel\.app", "technique", "fetch-proxy",
          "Hosted jq-over-URL service used to fetch and filter remote JSON"),
    Token("md_succ", r"md\.succ\.ai", "technique", "fetch-proxy",
          "Markdown-conversion proxy (md.succ.ai)"),
    Token("markdown_new", r"markdown\.new", "technique", "fetch-proxy",
          "Markdown-conversion proxy (markdown.new)"),
    Token("pure_md", r"(?<![\w.])pure\.md\b", "technique", "fetch-proxy",
          "Markdown-conversion proxy (pure.md)"),
    Token("allorigins", r"allorigins\.(?:hexlet\.app|win)", "technique", "fetch-proxy",
          "Public CORS/raw-relay proxy (allorigins)"),
    Token("workers_cors", r"[a-z0-9\-]+\.workers\.dev", "technique", "fetch-proxy",
          "Third-party serverless CORS relays (*.workers.dev)"),
    Token("translate_proxy", r"\.translate\.goog", "technique", "fetch-proxy",
          "Machine-translation domain used as a fetch relay"),
    Token("wayback_fetch", r"web\.archive\.org|memgator", "technique", "fetch-proxy",
          "Web-archive snapshots used as an alternative source"),
    Token("url_shortener", r"(?i)\b(?:tinyurl\.com|is\.gd|v\.gd|rmn\.re|bit\.ly)/", "technique",
          "fetch-proxy", "Link shorteners wrapping long query URLs"),
    # --- task-environment exploitation and coordination protocols ---
    Token("counter_beacon", r"counterapi\.dev", "technique", "coordination",
          "External counter service used as a write channel / liveness beacon"),
    Token("clock_wait", r"clock\.wait\(", "technique", "environment",
          "Calling the task's wait tool to advance the task clock"),
    Token("prng_seed", r"(?i)random\.Random|\bPRNG\b|\bRNG\b|\bseed\s*[=:#]?\s*\d{4,}", "technique",
          "environment", "Brute-forcing the task generator's random seed"),
    Token("proxy_exception_bypass", r"(?i)blob\.core\.windows\.net|NO_PROXY", "technique",
          "environment", "Sandbox egress-proxy exception abuse (named only)"),
    Token("signal_relay", r"STATE5-XX|\[\[[A-Za-z0-9]*Signal[A-Za-z0-9]*\]\]", "technique",
          "coordination", "Dedicated 'signal' pages / fixed token for fast answer relay",
          "arbitrary", "the relay need is functional, but the matched form (a fixed placeholder token and "
          "'...Signal' page naming) is an arbitrary convention: any agreed name would serve"),
]

# Placebos: frequent words / markup with no technique meaning. If these show
# the same exposure->adoption signature as techniques, the signature reflects
# activity and local text echo rather than technique transfer.
PLACEBOS: list[Token] = [
    Token("pl_please", r"(?i)\bplease\b", "placebo", "word", "the word 'please'", "arbitrary"),
    Token("pl_here", r"(?i)\bhere\b", "placebo", "word", "the word 'here'", "arbitrary"),
    Token("pl_with", r"(?i)\bwith\b", "placebo", "word", "the word 'with'", "arbitrary"),
    Token("pl_about", r"(?i)\babout\b", "placebo", "word", "the word 'about'", "arbitrary"),
    Token("pl_thanks", r"(?i)\bthank(?:s| you)\b", "placebo", "word", "'thanks'/'thank you'", "arbitrary"),
    Token("pl_also", r"(?i)\balso\b", "placebo", "word", "the word 'also'", "arbitrary"),
    Token("pl_bold", r"\*\*[^*\n]+\*\*", "placebo", "markup", "bold markup", "arbitrary"),
    Token("pl_heading", r"(?m)^=+[^=\n]+=+\s*$", "placebo", "markup", "wiki heading markup", "arbitrary"),
]

ALL_TOKENS: list[Token] = TECHNIQUES + PLACEBOS


def get_token(name: str) -> Token:
    for t in ALL_TOKENS:
        if t.name == name:
            return t
    raise KeyError(name)


def match_matrix(texts, tokens=ALL_TOKENS):
    """Boolean match vectors: {token name: [bool per text]}."""
    out = {}
    for tok in tokens:
        rx = tok.rx
        out[tok.name] = [bool(rx.search(s)) if s else False for s in texts]
    return out


def catalogue_records(tokens=ALL_TOKENS) -> list[dict]:
    return [{"name": t.name, "kind": t.kind, "family": t.family, "function": t.function,
             "function_note": t.function_note, "description": t.description, "regex": t.pattern}
            for t in tokens]
