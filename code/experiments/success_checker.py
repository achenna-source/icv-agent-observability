"""End-to-end success on this benchmark, decided programmatically.

Why this exists. Reviewer 3's seventh comment asks whether acting on a detected failure
improves end-to-end performance. That question needs a verdict on whether a trajectory
answered its task, and `benchmark.py` generates tasks and nothing else. The judge of
Section VI.B cannot stand in for it: it assigns a failure mode, and it agrees with the
human annotator at kappa = 0.115.

What it measures, and what it does not. It measures whether the final answer is correct.
A human label in this study names the *first observable fault*, which is a different
quantity: a trajectory can contradict itself mid-chain and still end on the right
number. The two therefore cannot be compared symmetrically, and this module is validated
in one direction only: every trajectory the human annotator called a success must come
out a success here. `self_check()` asserts exactly that on the released corpus, where it
holds for 72 of 72, and reports the nine further trajectories it accepts, six labelled
F3 and three F6, which end correctly after going wrong earlier.

How it was built, so that the figure is not in-sample. Two layers. Layer one derives
what a correct answer must contain from the task text and the knowledge base, using no
labels. Layer two decides whether an answer contains it, and holds the parts that could
be fitted: the verbal-magnitude parser, the numeric tolerance, the refusal vocabulary
and the name aliases. Layer two was developed on the 30-trajectory pilot alone, where it
recovers 13 of 13 successes, and applied unchanged to the 200. The notebooks that did
this are `success_checker_stage1.ipynb`, whose first attempt failed its own threshold and
uncovered a defect in the task generator, and `success_checker_stage1b.ipynb`.

Frozen on the date of the commit that adds this file. An intervention experiment that
uses it must not modify it; a change here invalidates the held-out figure above.
"""
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "data")

# ----------------------------------------------------------------- layer two
MAG = {"millions": 1e6, "million": 1e6, "milliers": 1e3, "millier": 1e3,
       "milliards": 1e9, "milliard": 1e9}

REFUSAL = ("non trouve", "pas trouve", "pas pu trouver", "introuvab",
           "non disponible", "pas disponible", "indisponible", "ne figure pas",
           "aucune information", "aucune donnee", "pas dans la base", "inconnu",
           "impossible", "je ne peux pas", "pas de donnee", "information non",
           "n est pas accessible", "pas accessible", "ne peut etre",
           "ne peut pas etre", "je suis desole", "sans plus de contexte",
           "pas ete capable", "ne peux pas fournir", "ne peut pas etre determinee")

ALIAS = {"algiers": "alger", "tokio": "tokyo"}

TOLERANCE = 0.01


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", s)


def values(text):
    """Every number an answer states, verbal magnitudes included."""
    s = str(text or "")
    out = set()
    for m in re.finditer(r"(\d[\d  .,]*\d|\d)\s*(millions?|milliers?|milliards?)",
                         s, re.I):
        raw, word = m.group(1), m.group(2).lower()
        raw = raw.replace(" ", "").replace(" ", "")
        if raw.count(",") == 1 and len(raw.split(",")[1]) <= 2:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "").replace(".", "")
        try:
            out.add(float(raw) * MAG[word])
        except ValueError:
            pass
    for m in re.finditer(r"\d[\d  .,]{2,}\d|\d+", s):
        d = re.sub(r"\D", "", m.group())
        if d:
            out.add(float(int(d)))
    return out


def has_value(text, expected, rel=TOLERANCE):
    e = float(expected)
    return any(abs(v - e) <= max(1.0, rel * abs(e)) for v in values(text))


def refuses(text):
    t = norm(text)
    return any(k in t for k in REFUSAL)


def has_text(answer, expected):
    a, e = norm(answer), norm(expected)
    if e in a:
        return True
    return any(norm(v) == e and k in a for k, v in ALIAS.items())


def final_answer(steps):
    for s in reversed(steps):
        if str(s.get("action")).strip().lower() == "finish":
            v = s.get("input")
            return "" if v is None or str(v).strip() in ("", "None") else str(v)
    return ""


# ----------------------------------------------------------------- layer one
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
_RX = {k: re.compile(v) for k, v in SURFACE_FORMS.items()}


def load_store(path=None):
    with open(path or os.path.join(DATA, "knowledge_base.json"),
              encoding="utf-8") as fh:
        kb = json.load(fh)["facts"]
    pop = {k.split(" ", 1)[1]: int(v) for k, v in kb.items()
           if k.startswith("population ")}
    cap = {k.split(" ", 1)[1]: v for k, v in kb.items() if k.startswith("capitale ")}
    known = {int(v) for v in kb.values() if str(v).isdigit()}
    return pop, cap, known


def expectation(task, pop, cap):
    """(kind, payload): what a correct answer to this task must contain."""
    for name, rx in _RX.items():
        m = rx.match(task)
        if not m:
            continue
        g = m.groups()
        if name == "T0_capital":
            return ("text", cap.get(g[0]))
        if name == "T0_product":
            return ("number", int(g[0]) * int(g[1]))
        if name == "T1":
            return ("number", pop.get(g[0]))
        if name in ("T2", "T4", "T7"):
            return ("refusal", None)
        if name == "T3":
            return ("capital_no_population", cap.get(g[0]))
        if name == "T5":
            if g[0] in pop and g[1] in pop:
                return ("number", (pop[g[0]] + pop[g[1]]) / 2)
            return ("not derivable", None)
        if name == "T6":
            if g[0] in pop and g[1] in pop:
                big = g[0] if pop[g[0]] >= pop[g[1]] else g[1]
                return ("city_and_gap", (big, abs(pop[g[0]] - pop[g[1]])))
            return ("not derivable", None)
    return ("not derivable", None)


def verdict(answer, kind, payload, known_values):
    if not str(answer).strip():
        return False, "empty final answer"
    if kind == "text":
        return has_text(answer, payload), "expects the text %r" % payload
    if kind == "number":
        return has_value(answer, payload), "expects %s" % format(payload, ".0f")
    if kind == "refusal":
        if not refuses(answer):
            return False, "no refusal where the value is absent from the store"
        invented = {v for v in values(answer)
                    if v >= 100000 and not any(abs(v - k) <= max(1.0, TOLERANCE * k)
                                               for k in known_values)}
        if invented:
            return False, ("refusal wording with invented value(s) %s"
                           % sorted(int(v) for v in invented))
        return True, "refusal with no invented value"
    if kind == "capital_no_population":
        if not has_text(answer, payload):
            return False, "capital %r absent" % payload
        asserted = {v for v in values(answer) if v >= 10000}
        if asserted and not refuses(answer):
            return False, ("a country population is asserted: %s"
                           % sorted(int(v) for v in asserted))
        return True, "capital given, no country population invented"
    if kind == "city_and_gap":
        city, gap = payload
        if not has_text(answer, city):
            return False, "the more populous city %r is not named" % city
        return has_value(answer, gap), "expects the gap %d" % gap
    return False, "not derivable"


def succeeded(task, steps, store=None):
    """(bool, reason) for one trajectory on one task."""
    pop, cap, known = store or load_store()
    kind, payload = expectation(task, pop, cap)
    if kind != "refusal" and payload is None:
        return False, "no expectation derivable"
    return verdict(final_answer(steps), kind, payload, known)


def self_check(corpus_path=None):
    """Asserts the held-out property: every human success is a checker success."""
    import ast

    path = corpus_path or os.path.join(DATA, "trajectories_200.jsonl")
    with open(path, encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    store = load_store()
    kept, missed, extra = 0, [], []
    for r in rows:
        steps = (ast.literal_eval(r["trajectory"])
                 if isinstance(r["trajectory"], str) else r["trajectory"])
        ok, why = succeeded(r["task"], steps, store)
        if r["label_human"] == "S":
            if ok:
                kept += 1
            else:
                missed.append((r["id"], why))
        elif ok:
            extra.append((r["id"], r["label_human"]))
    n_s = sum(1 for r in rows if r["label_human"] == "S")
    if missed:
        raise AssertionError("human successes rejected: %r" % missed[:5])
    return {"human_successes": n_s, "recovered": kept,
            "correct_answer_despite_fault": len(extra),
            "their_labels": sorted({lab for _, lab in extra})}


if __name__ == "__main__":
    print(self_check())
