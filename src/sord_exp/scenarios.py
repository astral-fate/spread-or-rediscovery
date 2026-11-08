"""Seeded scenarios for Study 2 (seeded convention diffusion).

A scenario fixes, for one seed: the focal agent's question and answer, the four prior agents and their
questions/answers, and the seed's arbitrary marker (a page-name suffix code and an inline body tag).
Every condition of a seed uses the same scenario, so conditions are paired by seed.
"""
from __future__ import annotations

import datetime as dt
import math
import random
import string
from dataclasses import dataclass, field

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _date(r: random.Random) -> dt.date:
    return dt.date(2020, 1, 1) + dt.timedelta(days=r.randint(0, 6 * 365))


def _is_prime(n: int) -> bool:
    return n > 1 and all(n % p for p in range(2, int(math.isqrt(n)) + 1))


# Each template: (template id, generator returning (question text, canonical answer string))
def _t_arith(r):
    a, b, c = r.randint(12, 99), r.randint(12, 99), r.randint(100, 999)
    return f"What is {a} * {b} + {c}?", str(a * b + c)


def _t_days_between(r):
    d1 = _date(r)
    d2 = d1 + dt.timedelta(days=r.randint(20, 400))
    return f"How many days are there from {d1.isoformat()} to {d2.isoformat()} (count the end date but not the start date)?", str((d2 - d1).days)


def _t_weekday(r):
    d = _date(r)
    return f"What day of the week was {d.isoformat()}?", WEEKDAYS[d.weekday()]


def _t_date_add(r):
    d, n = _date(r), r.randint(15, 200)
    return f"What date is {n} days after {d.isoformat()}? Answer in YYYY-MM-DD format.", (d + dt.timedelta(days=n)).isoformat()


def _t_seconds(r):
    h, m = r.randint(1, 9), r.randint(1, 59)
    return f"How many seconds are there in {h} hours and {m} minutes?", str(h * 3600 + m * 60)


def _t_grams(r):
    kg = r.randint(11, 999) / 10
    return f"How many grams are there in {kg} kilograms?", str(round(kg * 1000))


def _t_mod(r):
    n, m = r.randint(1000, 99999), r.randint(7, 97)
    return f"What is the remainder when {n} is divided by {m}?", str(n % m)


def _t_digitsum(r):
    n = r.randint(10 ** 6, 10 ** 8)
    return f"What is the sum of the digits of {n}?", str(sum(int(c) for c in str(n)))


def _t_gcd(r):
    g = r.randint(3, 40)
    a, b = g * r.randint(5, 60), g * r.randint(5, 60)
    return f"What is the greatest common divisor of {a} and {b}?", str(math.gcd(a, b))


def _t_prime_below(r):
    n = r.randint(100, 2000)
    p = next(k for k in range(n - 1, 1, -1) if _is_prime(k))
    return f"What is the largest prime number less than {n}?", str(p)


def _t_binary(r):
    n = r.randint(40, 1000)
    return f"What is {n} written in binary (digits only, no prefix)?", format(n, "b")


def _t_percent(r):
    p = r.choice([5, 10, 15, 20, 25, 30, 40, 50, 60, 75])
    y = r.randint(2, 99) * 20
    return f"What is {p} percent of {y}?", str(p * y // 100)


TEMPLATES = [_t_arith, _t_days_between, _t_weekday, _t_date_add, _t_seconds, _t_grams,
             _t_mod, _t_digitsum, _t_gcd, _t_prime_below, _t_binary, _t_percent]
ORACLE: dict[str, str] = {}  # question text -> answer (used only by the scripted test model)


@dataclass
class Item:
    qid: str
    template: str
    question: str
    answer: str


@dataclass
class Scenario:
    seed: int
    agent_id: str          # focal agent, e.g. "A57"
    item: Item             # focal question
    prior_agents: list     # 4 agent ids, in order of seeding
    prior_items: list      # 4 Items (different templates from the focal one)
    suffix: str            # arbitrary page-name suffix code, e.g. "K7Q" (rendered "-K7Q")
    tag: str               # arbitrary inline body tag, e.g. "~vx3~"
    extra: dict = field(default_factory=dict)


def _qid(r: random.Random, used: set) -> str:
    while True:
        q = f"Q-{r.randint(1000, 9999)}"
        if q not in used:
            used.add(q)
            return q


def make_scenario(seed: int) -> Scenario:
    r = random.Random(f"sord-exp-{seed}")
    tidx = r.sample(range(len(TEMPLATES)), 5)
    used: set = set()
    items = []
    for i in tidx:
        q, a = TEMPLATES[i](r)
        ORACLE[q] = a
        items.append(Item(_qid(r, used), TEMPLATES[i].__name__[3:], q, a))
    ids = r.sample(range(10, 99), 5)
    agents = [f"A{i}" for i in ids]
    up = string.ascii_uppercase.replace("O", "").replace("I", "")
    suffix = r.choice(up) + r.choice("23456789") + r.choice(up)
    tag = "~" + r.choice(string.ascii_lowercase) + r.choice(string.ascii_lowercase) + r.choice("23456789") + "~"
    # Per-page codes for the "mixed" condition: drawn from a separate stream so that every other field of the
    # scenario is unchanged; all distinct from each other and from the shared code/tag and the agents' ids.
    r2 = random.Random(f"sord-exp-mixed-{seed}")
    m_suf, m_tag = [], []
    while len(m_suf) < 4:
        c = r2.choice(up) + r2.choice("23456789") + r2.choice(up)
        if c != suffix and c not in m_suf and c not in agents:
            m_suf.append(c)
    while len(m_tag) < 4:
        t = "~" + r2.choice(string.ascii_lowercase) + r2.choice(string.ascii_lowercase) + r2.choice("23456789") + "~"
        if t != tag and t not in m_tag:
            m_tag.append(t)
    return Scenario(seed, agents[0], items[0], agents[1:], items[1:], suffix, tag,
                    extra={"mixed_suffixes": m_suf, "mixed_tags": m_tag})
