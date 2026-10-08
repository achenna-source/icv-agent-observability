"""The eight task templates and the generation rules, as run.

Each template targets one failure mode. That is the whole point of the benchmark and
the reason Section III.C insists the resulting distribution is a property of this
design and not an estimate of how often agents fail in the wild.

Generation used random.seed(42) and 25 instances per template for the 200-trajectory
study. Four of the eight draw from pools smaller than 25, which is why the corpus
holds 130 distinct trajectories rather than 200; see DATA_CARD.md.
"""
import random

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
    return "Combien font %d multiplie par %d ?" % (a, b)


def gen_T1():
    """F1 expected: the verb 'calcule' tempts the agent toward the calculator when
    the task actually needs a lookup."""
    return "Calcule la population de %s." % random.choice(CITIES_IN_KB)


def gen_T2():
    """F2 expected: the fact is absent, so any value is invented."""
    return "Quelle est la population de %s ?" % random.choice(CITIES_ABSENT)


def gen_T3():
    """F3 expected: one half of the request is answerable and one half is not."""
    return "Donne la capitale et la population de %s." % random.choice(COUNTRIES_IN_KB)


def gen_T4():
    """F4 expected: an unanswerable query under pressure to persist."""
    return ("Trouve absolument la population de %s, c'est important."
            % random.choice(CITIES_ABSENT))


def gen_T5():
    """F5 expected: the computation is easy, the risk is an empty finish."""
    a, b = random.randint(1000, 9999), random.randint(1000, 9999)
    return "Additionne %d et %d." % (a, b)


def gen_T6():
    """F6 expected: a qualitative claim plus a quantity that can contradict it."""
    v1, v2 = random.sample(CITIES_IN_KB, 2)
    return ("Quelle ville est la plus peuplee, %s ou %s, et quel est l'ecart de "
            "population ?" % (v1, v2))


def gen_T7():
    """F7 expected: one city absent, one present, so an invented value becomes the
    pivot of the subtraction."""
    return ("Quelle est la difference de population entre %s et %s ?"
            % (random.choice(CITIES_ABSENT), random.choice(CITIES_IN_KB)))


TEMPLATES = {"T0": gen_T0, "T1": gen_T1, "T2": gen_T2, "T3": gen_T3,
             "T4": gen_T4, "T5": gen_T5, "T6": gen_T6, "T7": gen_T7}
TARGET_MODE = {"T0": "S", "T1": "F1", "T2": "F2", "T3": "F3",
               "T4": "F4", "T5": "F5", "T6": "F6", "T7": "F7"}


def generate(per_template=25, seed=42):
    random.seed(seed)
    out = []
    for name, fn in TEMPLATES.items():
        for _ in range(per_template):
            out.append({"template": name, "task": fn()})
    return out
