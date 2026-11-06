# -*- coding: utf-8 -*-
"""Ce que la detection perd quand l'oracle se degrade, et les echecs que la
recomputation rate.

POURQUOI CES DEUX MESURES

La recomputation deterministe domine les signaux du papier, MCC +0,876 contre +0,485, et
rien ne s'ajoute a elle. Le papier pourrait repondre que ce validateur lit le gabarit de
la tache et une base de 28 faits enumeres, ce que les signaux ne lisent pas, et que dans
un environnement reel cet oracle n'existe pas. Tant que cela reste un argument, un
relecteur le refusera. Ces deux mesures le transforment en resultat, ou le refutent.

  1. Les echecs que la recomputation rate. S'ils sont attrapes par les signaux du papier,
     la contribution est chiffree et non plaidee. Sinon, la concession est entiere.

  2. L'echelle d'oracle. Le validateur est reconstruit a quatre niveaux d'acces, et la
     performance est mesuree a chaque barreau. L'avantage de la recomputation se lit alors
     comme une fonction de ce qu'elle sait, et non comme une superiorite de methode.

       L3  gabarit connu et base connue      l'oracle complet, le validateur publie
       L2  base connue, gabarit inconnu      on ne sait plus quelle operation attendre,
                                             seul l'ancrage des nombres est verifiable
       L1  gabarit connu, base inconnue      l'operation est connue mais on ne dispose
                                             que des valeurs que la trajectoire a
                                             reellement recues
       L0  ni l'un ni l'autre                la trajectoire seule, c'est a dire les
                                             signaux du papier

Le barreau L3 doit reproduire le chiffre deja publie par cheap_baselines.py, et le script
echoue sinon : c'est le controle qui empeche ce fichier de deriver de l'autre.

Sortie : results/oracle_degradation.json

    python experiments/oracle_degradation.py
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
PUBLISHED = json.load(io.open(os.path.join(ART, "results", "cheap_baselines.json"),
                              encoding="utf-8"))


def fold(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def pop(city):
    v = FACTS.get("population %s" % fold(city))
    return int(v) if v is not None else None


def numbers(text):
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


def parse(task):
    t = fold(task)
    for pat, kind in ((r"combien font (\d+) multiplie par (\d+)", "multiply"),
                      (r"additionne les populations de (\w[\w'-]*) et (\w[\w'-]*)",
                       "mean"),
                      (r"la plus peuplee, (\w[\w'-]*) ou (\w[\w'-]*)", "compare"),
                      (r"difference de population entre (\w[\w'-]*) et (\w[\w'-]*)",
                       "difference"),
                      (r"capitale et la population de (\w[\w'-]*)",
                       "capital_and_population"),
                      (r"capitale de (\w[\w'-]*)", "capital"),
                      (r"population de (\w[\w'-]*)", "population")):
        m = re.search(pat, t)
        if m:
            return kind, list(m.groups())
    return "unknown", []


def expected(kind, ents):
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


def derive(kind, vals):
    """L'operation de la tache appliquee aux valeurs dont on dispose reellement."""
    if kind == "multiply":
        return set()
    vals = sorted(vals)
    if len(vals) < 2:
        return set(vals)
    out = set(vals)
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i], vals[j]
            if kind == "mean":
                out |= {(a + b) // 2, a + b}
            elif kind in ("difference", "compare"):
                out |= {abs(a - b), max(a, b)}
    return out


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


# ------------------------------------------------------- les quatre barreaux
def L3(r):
    """gabarit connu, base connue : le validateur publie."""
    kind, ents = parse(r["task"])
    ans = final(r["trajectory"])
    if ans is None:
        return True
    exp = expected(kind, ents)
    if exp is None:
        return bool(numbers(ans))
    if not exp:
        return False
    return not (numbers(ans) & {int(v) for v in exp})


def L2(r):
    """base connue, gabarit inconnu : on ignore quelle operation attendre, donc on ne
    verifie que l'ancrage des nombres dans la base ou dans ce que la trajectoire a
    recu."""
    ans = final(r["trajectory"])
    if ans is None:
        return True
    store = {int(v) for k, v in FACTS.items()
             if k.startswith("population") and str(v).isdigit()}
    ok = store | retrieved(r["trajectory"])
    return any(v not in ok for v in numbers(ans) if v >= 1000)


def L1(r):
    """gabarit connu, base inconnue : l'operation est connue mais seules les valeurs que
    la trajectoire a effectivement recues sont disponibles."""
    kind, ents = parse(r["task"])
    ans = final(r["trajectory"])
    if ans is None:
        return True
    got = retrieved(r["trajectory"])
    if kind == "multiply":
        exp = expected(kind, ents)
        return not (numbers(ans) & {int(v) for v in exp})
    if not got:
        return bool(v for v in numbers(ans) if v >= 1000)
    ok = derive(kind, got)
    vals = [v for v in numbers(ans) if v >= 1000]
    return any(v not in {int(x) for x in ok} for v in vals)


def L0(r):
    """la trajectoire seule : les signaux du papier, meilleure configuration."""
    return (signals.tier1_exempt(r["trajectory"])[0]
            or signals.tier2(r["trajectory"])[0])


LADDER = [("L3 task+store", L3), ("L2 store only", L2), ("L1 task only", L1),
          ("L0 trace only", L0)]
FAIL = {r["id"]: r["label_human"] != "S" for r in ROWS}
CATS = sorted({r["label_human"] for r in ROWS if r["label_human"] != "S"})


def score(fn):
    tp = fp = fn_ = tn = 0
    fired = set()
    for r in ROWS:
        f = bool(fn(r))
        if f:
            fired.add(r["id"])
        if f and FAIL[r["id"]]:
            tp += 1
        elif f:
            fp += 1
        elif FAIL[r["id"]]:
            fn_ += 1
        else:
            tn += 1
    return dict(precision=round(tp / (tp + fp), 3) if tp + fp else None,
                recall=round(tp / (tp + fn_), 3) if tp + fn_ else None,
                mcc=round(mcc(tp, fp, fn_, tn), 3), false_alarms=fp,
                tp=tp, fp=fp, fn=fn_, tn=tn), fired


print()
print("=" * 78)
print("1. L'ECHELLE D'ORACLE")
print()
print("%-16s %9s %8s %8s %8s" % ("acces", "precision", "rappel", "MCC", "FA"))
OUT, FIRED = {}, {}
for name, fn in LADDER:
    s, fired = score(fn)
    OUT[name], FIRED[name] = s, fired
    print("%-16s %9.3f %8.3f %+8.3f %8d"
          % (name, s["precision"], s["recall"], s["mcc"], s["false_alarms"]))

# controle : le barreau complet doit reproduire le chiffre deja publie
pub = PUBLISHED["validators"]["1 recompute"]
assert OUT["L3 task+store"]["mcc"] == pub["mcc"], (OUT["L3 task+store"], pub)
assert OUT["L3 task+store"]["recall"] == pub["recall"]
print()
print("  controle : L3 reproduit le MCC %.3f de cheap_baselines.py" % pub["mcc"])
print("  l'avantage de l'oracle complet sur la trajectoire seule est de %+0.3f en MCC"
      % (OUT["L3 task+store"]["mcc"] - OUT["L0 trace only"]["mcc"]))
print("  retirer le gabarit coute %+0.3f, retirer la base coute %+0.3f"
      % (OUT["L2 store only"]["mcc"] - OUT["L3 task+store"]["mcc"],
         OUT["L1 task only"]["mcc"] - OUT["L3 task+store"]["mcc"]))

print()
print("=" * 78)
print("2. LES ECHECS QUE LA RECOMPUTATION RATE")
print()
missed = sorted(r["id"] for r in ROWS
                if FAIL[r["id"]] and r["id"] not in FIRED["L3 task+store"])
by = {r["id"]: r for r in ROWS}
print("  %d echecs rates par l'oracle complet" % len(missed))
print("  par categorie : %s"
      % " ".join("%s %d" % (k, v) for k, v in
                 sorted(Counter(by[i]["label_human"] for i in missed).items())))
print()
print("  %-7s %-5s %-9s %-9s %-9s %s" % ("item", "ref", "tier1", "tier2", "B*vC",
                                         "gabarit"))
caught = Counter()
for i in missed:
    r = by[i]
    t1 = signals.tier1(r["trajectory"])[0]
    t2 = signals.tier2(r["trajectory"])[0]
    bc = L0(r)
    for n, v in (("tier1", t1), ("tier2", t2), ("B*vC", bc)):
        caught[n] += 1 if v else 0
    print("  %-7s %-5s %-9s %-9s %-9s %s"
          % (i, r["label_human"], "oui" if t1 else "non", "oui" if t2 else "non",
             "oui" if bc else "non", r["template"]))
print()
print("  rattrapes par les signaux du papier : tier1 %d, tier2 %d, B*vC %d sur %d"
      % (caught["tier1"], caught["tier2"], caught["B*vC"], len(missed)))
union = sorted(set(missed) & (FIRED["L0 trace only"] | {
    r["id"] for r in ROWS if signals.tier1(r["trajectory"])[0]}))
print("  rattrapes par au moins un signal du papier : %d sur %d"
      % (len(union), len(missed)))

res = os.path.join(ART, "results", "oracle_degradation.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(
    what_this_is=(
        "Two measurements that turn the paper's defence into a result or refute it. The "
        "oracle ladder rebuilds the deterministic validator at four levels of access and "
        "scores each, so the baseline's advantage reads as a function of what it knows. "
        "The missed-failure list asks whether the paper's trace-only signals catch what "
        "the full oracle does not, which is the only place they can claim value of "
        "their own."),
    ladder=OUT,
    advantage_of_full_oracle_over_trace_only=round(
        OUT["L3 task+store"]["mcc"] - OUT["L0 trace only"]["mcc"], 3),
    cost_of_losing_the_task_template=round(
        OUT["L2 store only"]["mcc"] - OUT["L3 task+store"]["mcc"], 3),
    cost_of_losing_the_store=round(
        OUT["L1 task only"]["mcc"] - OUT["L3 task+store"]["mcc"], 3),
    missed_by_full_oracle=dict(
        n=len(missed), ids=missed,
        by_category=dict(Counter(by[i]["label_human"] for i in missed)),
        caught_by_tier1=caught["tier1"], caught_by_tier2=caught["tier2"],
        caught_by_B_star_or_C=caught["B*vC"],
        caught_by_any_paper_signal=len(union)),
), indent=1, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
