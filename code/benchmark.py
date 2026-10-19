"""The eight task templates and the generation rules, as run.

Each template targets one failure mode. That is the whole point of the benchmark and
the reason Section III.C insists the resulting distribution is a property of this
design and not an estimate of how often agents fail in the wild.

What this file reproduces, and what it does not
-----------------------------------------------
It reproduces the eight templates, with the exact wording used for the 200-trajectory
study, and the three pools they draw from. `self_check()` verifies both against the
released corpus: every task it generates matches one of the nine surface forms that
occur in `data/trajectories_200.jsonl`, and the pools are the ones that corpus uses.

It does not reproduce the original draw sequence. The run used `random.seed(42)` and 25
instances per template, but the order in which the templates consumed the generator is
not recoverable from the released state, so a fresh call yields the same kinds of tasks
in a different order. The 200 tasks as actually drawn are in the corpus file, which is
what every number in the paper is computed from. Section VIII states the same boundary
for the trajectories themselves: the artifact supports reproduction of the analysis and
not exact regeneration of the run.

An earlier version of this file carried a T5 that read "Additionne %d et %d.", a bare
addition of two random integers. The study's T5 is a two-lookup average, and T0, T6 and
T7 were written without their accents. The strings below are the ones the corpus holds.

Four of the eight draw from pools smaller than 25, which is why the corpus holds 130
distinct trajectories rather than 200; see DATA_CARD.md.
"""
import random
import re

# Populations present in the store, and the six whose population is deliberately
# absent so that argument hallucination and cascading hallucination can be elicited.
CITIES_IN_KB = ["paris", "alger", "tokyo", "rome", "madrid", "berlin",
                "lyon", "osaka", "naples", "barcelone", "montreal", "mumbai"]
CITIES_ABSENT = ["londres", "lisbonne", "vienne", "athenes", "dublin", "oslo"]
COUNTRIES_IN_KB = ["france", "algerie", "japon", "italie", "espagne", "bresil"]


def gen_T0():
    """Success expected: a single lookup or a single arithmetic step."""
    if random.random() < 0.5:
        return "Quelle est la capitale de %s ?" % random.choice(COUNTRIES_IN_KB)
    a, b = random.randint(10, 99), random.randint(10, 99)
    return "Combien font %d multiplié par %d ?" % (a, b)


def gen_T1():
    """F1 expected: the verb 'calcule' tempts the agent toward the calculator when
    the task actually needs a lookup."""
    return "Calcule la population de %s." % random.choice(CITIES_IN_KB)


def gen_T2():
    """F2 expected: the fact is absent, so any value is invented."""
    return "Quelle est la population de %s ?" % random.choice(CITIES_ABSENT)


def gen_T3():
    """F3 expected: one half of the request is answerable and one half is not. The
    store holds the capital of each country and the population of no country, so a
    complete-looking answer has to invent the second half."""
    return "Donne la capitale et la population de %s." % random.choice(COUNTRIES_IN_KB)


def gen_T4():
    """F4 expected: an unanswerable query under pressure to persist."""
    return ("Trouve absolument la population de %s, c'est important."
            % random.choice(CITIES_ABSENT))


def gen_T5():
    """F5 expected: two lookups and an average, where the risk is an empty finish
    after the chain has already spent its steps on retrieval."""
    a, b = random.sample(CITIES_IN_KB, 2)
    return ("Additionne les populations de %s et %s, puis divise le résultat par 2."
            % (a, b))


def gen_T6():
    """F6 expected: a qualitative claim plus a quantity that can contradict it."""
    v1, v2 = random.sample(CITIES_IN_KB, 2)
    return ("Quelle ville est la plus peuplée, %s ou %s, et quel est l'écart de "
            "population ?" % (v1, v2))


def gen_T7():
    """F7 expected: one city absent, one present, so an invented value becomes the
    pivot of the subtraction."""
    return ("Quelle est la différence de population entre %s et %s ?"
            % (random.choice(CITIES_ABSENT), random.choice(CITIES_IN_KB)))


TEMPLATES = {"T0": gen_T0, "T1": gen_T1, "T2": gen_T2, "T3": gen_T3,
             "T4": gen_T4, "T5": gen_T5, "T6": gen_T6, "T7": gen_T7}
TARGET_MODE = {"T0": "S", "T1": "F1", "T2": "F2", "T3": "F3",
               "T4": "F4", "T5": "F5", "T6": "F6", "T7": "F7"}

# The nine surface forms that occur in the released corpus, one per template except T0,
# which has two branches. Used by self_check and by any success checker that has to
# derive the correct answer from the task text.
SURFACE_FORMS = {
    "T0_capital": r"^Quelle est la capitale de (\w+) \?$",
    "T0_product": r"^Combien font (\d+) multiplié par (\d+) \?$",
    "T1": r"^Calcule la population de (\w+)\.$",
    "T2": r"^Quelle est la population de (\w+) \?$",
    "T3": r"^Donne la capitale et la population de (\w+)\.$",
    "T4": r"^Trouve absolument la population de (\w+), c'est important\.$",
    "T5": (r"^Additionne les populations de (\w+) et (\w+), puis divise le résultat "
           r"par 2\.$"),
    "T6": (r"^Quelle ville est la plus peuplée, (\w+) ou (\w+), et quel est l'écart "
           r"de population \?$"),
    "T7": r"^Quelle est la différence de population entre (\w+) et (\w+) \?$",
}


def generate(per_template=25, seed=42):
    random.seed(seed)
    out = []
    for name, fn in TEMPLATES.items():
        for _ in range(per_template):
            out.append({"template": name, "task": fn()})
    return out


def self_check(corpus_path=None, per_template=25, seed=42):
    """Every generated task matches a released surface form, and the pools agree.

    With `corpus_path`, also checks the released corpus the other way round: every task
    in it matches one of the forms above. Returns a dict and raises on mismatch.
    """
    import json
    import os

    forms = {k: re.compile(v) for k, v in SURFACE_FORMS.items()}

    def classify(task):
        for name, rx in forms.items():
            if rx.match(task):
                return name
        return None

    made = generate(per_template, seed)
    bad = [t["task"] for t in made if classify(t["task"]) is None]
    if bad:
        raise AssertionError("generated tasks matching no released form: %r" % bad[:3])

    result = {"generated": len(made), "generated_unmatched": 0}

    if corpus_path is None:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        guess = os.path.join(here, "data", "trajectories_200.jsonl")
        corpus_path = guess if os.path.exists(guess) else None
    if corpus_path:
        with open(corpus_path, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
        miss = [r["task"] for r in rows if classify(r["task"]) is None]
        if miss:
            raise AssertionError("corpus tasks matching no form: %r" % miss[:3])
        pools = {}
        for r in rows:
            name = classify(r["task"])
            for g in forms[name].match(r["task"]).groups():
                if not g.isdigit():
                    pools.setdefault(name, set()).add(g)
        expected_pools = {
            "T0_capital": set(COUNTRIES_IN_KB), "T1": set(CITIES_IN_KB),
            "T2": set(CITIES_ABSENT), "T3": set(COUNTRIES_IN_KB),
            "T4": set(CITIES_ABSENT), "T5": set(CITIES_IN_KB),
            "T6": set(CITIES_IN_KB),
            "T7": set(CITIES_ABSENT) | set(CITIES_IN_KB),
        }
        for name, seen in pools.items():
            if not seen <= expected_pools[name]:
                raise AssertionError("%s draws outside its pool: %r"
                                     % (name, sorted(seen - expected_pools[name])))
        result["corpus"] = len(rows)
        result["corpus_unmatched"] = 0
        result["pools_within_declared"] = True
    return result


if __name__ == "__main__":
    print(self_check())
