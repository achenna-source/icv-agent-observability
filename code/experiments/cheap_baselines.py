# -*- coding: utf-8 -*-
"""Les validateurs bon marche que le relecteur 7 demande, mesures contre ICV.

Ce que le commentaire demande. ICV combine des techniques etablies, et son test de
coherence numerique depend de plages et d'operations propres au banc. Des comparaisons
avec la recomputation deterministe, la verification d'operation propre a la tache et
d'autres validateurs bon marche etabliraient ce que la methode apporte.

Le reproche sur les plages est verifiable et il est juste. Le test de contradiction de
signals.tier2 ne se declenche que sur une valeur superieure a 50000, tolere un ecart de
1000, et n'essaie que trois operations ecrites en dur, la somme, la difference et la
moyenne. Les validateurs ci-dessous n'ont ni seuil de grandeur ni liste d'operations :
l'operation vient de la tache.

CE QUE CHAQUE LIGNE DE BASE SAIT, ET C'EST LA QUE LA COMPARAISON SE JOUE

ICV ne lit que la trajectoire. Les validateurs 1 a 4 lisent en plus le gabarit de la
tache et la base de connaissances, c'est a dire un environnement enumere et connu. La
comparaison n'est donc pas a armes egales, et c'est precisement l'information utile :
elle dit ce que coute a ICV son agnosticisme au contenu, et elle borne ce que la methode
peut revendiquer. Le script le rapporte dans les deux sens plutot que de choisir le
cadrage favorable.

  1 recompute          l'operation que la tache implique est refaite sur les valeurs que
                       la base contient vraiment, et le resultat est compare au nombre de
                       la reponse finale. Aucune tolerance, aucun seuil.
  2 operation_check    l'expression passee au calculateur doit porter l'operateur que la
                       tache implique.
  3 grounded_numbers   tout nombre de la reponse finale doit etre une valeur de la base,
                       ou se deduire exactement de valeurs de la base par l'operation de
                       la tache.
  4 answerability      si l'entite de la tache est absente de la base, une reponse finale
                       qui avance un nombre est signalee.
  5 tier1, tier2, B*vC les signaux du papier, sur le meme corpus et la meme metrique.

Sortie : results/cheap_baselines.json

    python experiments/cheap_baselines.py
"""
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ART = os.path.dirname(CODE)
sys.path.insert(0, CODE)
import signals                       # noqa: E402
from metrics import mcc              # noqa: E402

ROWS = [json.loads(l) for l in
        io.open(os.path.join(ART, "data", "trajectories_200.jsonl"), encoding="utf-8")
        if l.strip()]
KB = json.load(io.open(os.path.join(ART, "data", "knowledge_base.json"),
                       encoding="utf-8"))
FACTS = KB["facts"]
ABSENT = set(KB["populations_absent_by_design"])


def fold(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def pop(city):
    v = FACTS.get("population %s" % fold(city))
    return int(v) if v is not None else None


def numbers(text):
    """Tous les entiers de la reponse, les milliers espaces recolles, et les tournures
    en millions converties. Aucun seuil de grandeur."""
    t = fold(text)
    out = set()
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:millions?|m\b)", t):
        try:
            out.add(int(round(float(m.group(1).replace(",", ".")) * 1_000_000)))
        except ValueError:
            pass
    t = re.sub(r"(?<=\d)[   ](?=\d{3}(?!\d))", "", t)
    for m in re.finditer(r"\d+", t):
        out.add(int(m.group()))
    return out


# ------------------------------------------------------------------ les gabarits
def parse(task):
    """Ce que la tache demande, lu de son gabarit. Rend (type, entites)."""
    t = fold(task)
    m = re.search(r"combien font (\d+) multiplie par (\d+)", t)
    if m:
        return "multiply", [m.group(1), m.group(2)]
    m = re.search(r"additionne les populations de (\w[\w'-]*) et (\w[\w'-]*)", t)
    if m:
        return "mean", [m.group(1), m.group(2)]
    m = re.search(r"la plus peuplee, (\w[\w'-]*) ou (\w[\w'-]*)", t)
    if m:
        return "compare", [m.group(1), m.group(2)]
    m = re.search(r"difference de population entre (\w[\w'-]*) et (\w[\w'-]*)", t)
    if m:
        return "difference", [m.group(1), m.group(2)]
    m = re.search(r"capitale et la population de (\w[\w'-]*)", t)
    if m:
        return "capital_and_population", [m.group(1)]
    m = re.search(r"capitale de (\w[\w'-]*)", t)
    if m:
        return "capital", [m.group(1)]
    m = re.search(r"population de (\w[\w'-]*)", t)
    if m:
        return "population", [m.group(1)]
    return "unknown", []


OPERATOR = {"mean": ("+", "/"), "compare": ("-",), "difference": ("-",),
            "multiply": ("*",)}


def expected(kind, ents):
    """Les valeurs qu'une reponse juste doit porter, ou None si la base ne permet pas."""
    if kind == "multiply":
        return {int(ents[0]) * int(ents[1])}
    if kind == "population":
        v = pop(ents[0])
        return None if v is None else {v}
    if kind == "capital":
        return set()
    if kind == "capital_and_population":
        return None if pop(ents[0]) is None else {pop(ents[0])}
    vals = [pop(e) for e in ents]
    if any(v is None for v in vals):
        return None
    a, b = vals
    if kind == "mean":
        return {(a + b) // 2, (a + b) / 2, a + b}
    if kind == "difference":
        return {abs(a - b)}
    if kind == "compare":
        return {abs(a - b), max(a, b)}
    return None


def final(traj):
    last = traj[-1]
    if last.get("action") != "finish":
        return None
    s = str(last.get("input") or "").strip()
    return s if s and s != "None" else None


def retrieved(traj):
    out = set()
    for s in traj:
        if s.get("action") == "knowledge_base":
            ob = s.get("observation")
            if ob not in (None, "Information non trouvee", "Information non trouvée"):
                out |= numbers(ob)
    return out


# ------------------------------------------------------------------ validateurs
def v_recompute(r):
    """L'operation de la tache, refaite sur la base, contre le nombre de la reponse."""
    kind, ents = parse(r["task"])
    ans = final(r["trajectory"])
    if ans is None:
        return True
    exp = expected(kind, ents)
    if exp is None:
        # la base ne porte pas la valeur : une reponse qui avance un nombre est fausse
        return bool(numbers(ans))
    if not exp:
        return False
    got = numbers(ans)
    return not (got & {int(v) for v in exp})


def v_operation(r):
    """L'expression du calculateur doit porter l'operateur que la tache implique."""
    kind, _ = parse(r["task"])
    need = OPERATOR.get(kind)
    if not need:
        return False
    exprs = [str(s.get("input") or "") for s in r["trajectory"]
             if s.get("action") == "calculator"]
    if not exprs:
        return True
    return not any(all(op in e for op in need) for e in exprs)


def v_grounded(r):
    """Tout nombre de la reponse est une valeur de la base, ou s'en deduit exactement."""
    ans = final(r["trajectory"])
    if ans is None:
        return True
    kind, ents = parse(r["task"])
    ok = set(retrieved(r["trajectory"]))
    exp = expected(kind, ents)
    if exp:
        ok |= {int(v) for v in exp}
    vals = [v for v in numbers(ans) if v >= 1000]
    return any(v not in ok for v in vals)


def v_answerable(r):
    """Entite absente de la base et reponse qui avance tout de meme un nombre."""
    kind, ents = parse(r["task"])
    if not ents or fold(ents[0]) not in ABSENT:
        return False
    ans = final(r["trajectory"])
    if ans is None:
        return True
    return any(v >= 1000 for v in numbers(ans))


VALIDATORS = [
    ("1 recompute", v_recompute, "task + store"),
    ("2 operation", v_operation, "task"),
    ("3 grounded", v_grounded, "task + store"),
    ("4 answerable", v_answerable, "task + store"),
    ("1 or 3", lambda r: v_recompute(r) or v_grounded(r), "task + store"),
    ("tier1 (B)", lambda r: signals.tier1(r["trajectory"])[0], "trace only"),
    ("tier2 (C)", lambda r: signals.tier2(r["trajectory"])[0], "trace only"),
    ("B* or C", lambda r: (signals.tier1_exempt(r["trajectory"])[0]
                           or signals.tier2(r["trajectory"])[0]), "trace only"),
    # La question que le relecteur pose vraiment : les signaux du papier ajoutent-ils
    # quelque chose par dessus une ligne de base forte, ou sont-ils absorbes par elle ?
    ("1 + tier1", lambda r: v_recompute(r) or signals.tier1(r["trajectory"])[0],
     "task + store"),
    ("1 + B*vC", lambda r: (v_recompute(r)
                            or signals.tier1_exempt(r["trajectory"])[0]
                            or signals.tier2(r["trajectory"])[0]), "task + store"),
]

FAIL = {r["id"]: r["label_human"] != "S" for r in ROWS}
NF = sum(FAIL.values())
print()
print("corpus : %d trajectoires, %d echecs, taux de base %.3f"
      % (len(ROWS), NF, NF / len(ROWS)))
kinds = Counter(parse(r["task"])[0] for r in ROWS)
assert "unknown" not in kinds, dict(kinds)
print("gabarits reconnus : %s" % " ".join("%s %d" % (k, v) for k, v in
                                          sorted(kinds.items())))
print()
print("%-14s %-14s %7s %7s %7s %7s %7s"
      % ("validator", "reads", "prec", "rec", "MCC", "FA", "flags"))

OUT = {}
for name, fn, reads in VALIDATORS:
    tp = fp = fn_ = tn = 0
    flagged = []
    for r in ROWS:
        f = bool(fn(r))
        if f:
            flagged.append(r["id"])
        if f and FAIL[r["id"]]:
            tp += 1
        elif f:
            fp += 1
        elif FAIL[r["id"]]:
            fn_ += 1
        else:
            tn += 1
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn_) if tp + fn_ else float("nan")
    m = mcc(tp, fp, fn_, tn)
    OUT[name] = dict(reads=reads, precision=round(prec, 3), recall=round(rec, 3),
                     mcc=round(m, 3), false_alarms=fp, n_flagged=len(flagged),
                     tp=tp, fp=fp, fn=fn_, tn=tn)
    print("%-14s %-14s %7.3f %7.3f %+7.3f %7d %7d"
          % (name, reads, prec, rec, m, fp, len(flagged)))

# ------------------------------------------------ par categorie de faute
print()
print("rappel par categorie de la reference")
cats = sorted({r["label_human"] for r in ROWS if r["label_human"] != "S"})
print("%-14s %s" % ("validator", " ".join("%6s" % c for c in cats)))
for name, fn, _ in VALIDATORS:
    line = []
    for c in cats:
        sub = [r for r in ROWS if r["label_human"] == c]
        line.append(sum(1 for r in sub if fn(r)) / len(sub))
    OUT[name]["recall_by_category"] = {c: round(v, 3) for c, v in zip(cats, line)}
    print("%-14s %s" % (name, " ".join("%6.2f" % v for v in line)))

# l'increment des signaux du papier par dessus la recomputation seule
base = OUT["1 recompute"]["mcc"]
INCR = {n: round(OUT[n]["mcc"] - base, 3) for n in ("1 + tier1", "1 + B*vC")}
print()
print("increment des signaux du papier par dessus la recomputation seule (MCC %.3f)"
      % base)
for n, d in INCR.items():
    print("   %-12s %+0.3f" % (n, d))
f6 = {n: OUT[n]["recall_by_category"].get("F6") for n in OUT}
print("   rappel sur F6 : recomputation %.2f, tier1 %.2f, les deux %.2f"
      % (f6["1 recompute"], f6["tier1 (B)"], f6["1 + tier1"]))

best_all = max(OUT, key=lambda n: OUT[n]["mcc"])
best_trace = max((n for n in OUT if OUT[n]["reads"] == "trace only"),
                 key=lambda n: OUT[n]["mcc"])
print()
print("meilleur MCC toutes lectures confondues : %s, %.3f"
      % (best_all, OUT[best_all]["mcc"]))
print("meilleur MCC parmi les signaux qui ne lisent que la trajectoire : %s, %.3f"
      % (best_trace, OUT[best_trace]["mcc"]))

res = os.path.join(ART, "results", "cheap_baselines.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(
    what_this_is=(
        "Inexpensive deterministic validators asked for by reviewer 7, measured against "
        "the paper's own signals on the same 200 trajectories and the same metric. The "
        "validators numbered 1 to 4 read the task template and the knowledge base as "
        "well as the trace; the paper's signals read the trace alone. The comparison is "
        "therefore not between equals, and the column that says what each one reads is "
        "part of the result."),
    n_items=len(ROWS), n_failures=NF, base_rate=round(NF / len(ROWS), 3),
    best_overall=best_all, best_trace_only=best_trace,
    increment_over_recompute=INCR,
    validators=OUT), indent=1, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
