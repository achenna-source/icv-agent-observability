# -*- coding: utf-8 -*-
"""Les deux dorsales cote a cote, et ce que la comparaison peut dire sans etiquettes.

CE QUI EST COMPARABLE SANS ETIQUETTES, ET CE QUI NE L'EST PAS

Le second corpus n'a pas d'etiquettes. Precision, rappel et correlation de Matthews n'y
sont donc pas calculables, et ce script refuse de les imprimer pour un corpus qui n'en a
pas plutot que de les tirer d'une cible improvisee.

Ce qui se compare tout de meme, et qui n'est pas rien :

  le comportement de l'agent   etapes par trajectoire, trajectoires au budget, absence
                               d'etape terminale, appels nommant un outil non enregistre
  le taux de declenchement     pour chaque signal, sur chaque corpus, avec un intervalle
                               par grappes de gabarits
  l'accord par tache           les deux corpus portent les memes deux cents enonces, donc
                               on peut demander si un signal se declenche sur les memes
                               taches sous les deux dorsales, ce qui est une affirmation
                               de transfert sur le detecteur et non sur la taxonomie

CE QUE CELA NE REMPLACE PAS

Un signal qui se declenche au meme taux sur les deux corpus peut y attraper des fautes
differentes. Seule une ronde d'etiquetage le dirait, et le script le rappelle en sortie
plutot que de laisser le taux passer pour une mesure de qualite.

    python experiments/backbone_comparison.py
    python experiments/backbone_comparison.py --second trajectories_200_falcon3_7b.jsonl

Sortie : results/backbone_comparison.json
"""
import argparse
import io
import json
import os
import random
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ART = os.path.dirname(CODE)
sys.path.insert(0, CODE)
import signals                      # noqa: E402
from agent import NOT_FOUND_FORMS   # noqa: E402
from metrics import mcc             # noqa: E402

TOOLS = {"knowledge_base", "calculator", "finish"}
MAX_STEPS = 6
B = 10000
SEED = 20261105
SIG = (("B, schema", lambda t: signals.tier1(t)[0]),
       ("B*, exempted", lambda t: signals.tier1_exempt(t)[0]),
       ("C, consistency", lambda t: signals.tier2(t)[0]),
       ("B* or C", lambda t: (signals.tier1_exempt(t)[0] or signals.tier2(t)[0])))

ap = argparse.ArgumentParser()
ap.add_argument("--second", default="trajectories_200_falcon3_7b.jsonl",
                help="le corpus de la seconde dorsale, dans data/ ou en chemin complet")
a = ap.parse_args()


def load(path):
    q = path if os.path.isabs(path) else os.path.join(ART, "data", path)
    if not os.path.exists(q):
        return None, q
    return [json.loads(l) for l in io.open(q, encoding="utf-8") if l.strip()], q


FIRST, p1 = load("trajectories_200.jsonl")
assert FIRST is not None, p1
SECOND, p2 = load(a.second)

print()
print("corpus 1 : %s, %d trajectoires, etiquettes %s"
      % (os.path.basename(p1), len(FIRST),
         "oui" if "label_human" in FIRST[0] else "non"))
if SECOND is None:
    print("corpus 2 : %s absent" % os.path.basename(p2))
    print()
    print("La campagne de la seconde dorsale n'a pas encore rendu. Ce script attend")
    print("son fichier dans data/ et ne produit rien tant qu'il manque, plutot que de")
    print("comparer un corpus a lui meme.")
    sys.exit(1)
print("corpus 2 : %s, %d trajectoires, etiquettes %s"
      % (os.path.basename(p2), len(SECOND),
         "oui" if "label_human" in SECOND[0] else "non"))

A = {r["id"]: r for r in FIRST}
Bc = {r["id"]: r for r in SECOND}
ids = sorted(set(A) & set(Bc))
assert len(ids) == len(A) == len(Bc), (
    "les deux corpus ne portent pas les memes identifiants : %d communs sur %d et %d"
    % (len(ids), len(A), len(Bc)))
TPL = {i: A[i]["template"] for i in ids}
clusters = {}
for i in ids:
    clusters.setdefault(TPL[i], []).append(i)
print("%d identifiants communs, %d gabarits" % (len(ids), len(clusters)))


def behaviour(rows):
    st = [len(r["trajectory"]) for r in rows]
    return dict(
        mean_steps=round(sum(st) / len(st), 2),
        at_budget=sum(1 for n in st if n >= MAX_STEPS),
        no_finish=sum(1 for r in rows
                      if r["trajectory"][-1].get("action") != "finish"),
        unregistered_steps=sum(1 for r in rows for s in r["trajectory"]
                               if s.get("action") not in TOOLS),
        trajectories_with_unregistered=sum(
            1 for r in rows if any(s.get("action") not in TOOLS
                                   for s in r["trajectory"])))


print()
print("=" * 78)
print("1. LE COMPORTEMENT DE L'AGENT")
print()
BEH = {"first": behaviour(FIRST), "second": behaviour(SECOND)}
print("%-32s %10s %10s" % ("", "dorsale 1", "dorsale 2"))
for k in ("mean_steps", "at_budget", "no_finish", "unregistered_steps",
          "trajectories_with_unregistered"):
    print("%-32s %10s %10s" % (k, BEH["first"][k], BEH["second"][k]))
print()
print("  Le dernier compte decide de ce que la validation de schema peut trouver, et il")
print("  releve de l'agent et non du detecteur.")

# Combien de fois l'agent interroge le magasin, et sur quelle part il obtient une
# reponse. C'est une mesure du comportement, pas du detecteur, et elle explique une
# part des ecarts qui suivent.
STORE = {}
for which, rows in (("first", FIRST), ("second", SECOND)):
    calls = [st for r in rows for st in r["trajectory"]
             if st.get("action") == "knowledge_base"]
    served = [st for st in calls if st.get("observation") is not None
              and st.get("observation") not in NOT_FOUND_FORMS]
    unserved = sorted({str(st.get("input") or "").lower() for st in calls
                       if st.get("observation") is None
                       or st.get("observation") in NOT_FOUND_FORMS})
    STORE[which] = dict(
        calls=len(calls), served=len(served),
        served_share=round(len(served) / len(calls), 3) if calls else None,
        distinct_unserved=len(unserved),
        unserved_english_capital=sum(1 for q in unserved
                                     if "capital" in q and "capitale" not in q))
print()
print("%-32s %10s %10s" % ("", "dorsale 1", "dorsale 2"))
for k in ("calls", "served", "served_share", "distinct_unserved",
          "unserved_english_capital"):
    print("%-32s %10s %10s" % (k, STORE["first"][k], STORE["second"][k]))
print()
print("  La derniere ligne compte les requetes distinctes restees sans reponse qui")
print("  ecrivent capital la ou toutes les cles du magasin portent capitale.")


# Chaque signal est evalue une fois par trajectoire et le bootstrap travaille ensuite
# sur ces booleens. Le reevaluer a chaque tirage ferait seize millions d'appels pour
# rien, ce qui rendait ce script inutilisable.
FLAG = {}
for _name, _fn in SIG:
    FLAG[_name] = {"A": {i: bool(_fn(A[i]["trajectory"])) for i in ids},
                   "B": {i: bool(_fn(Bc[i]["trajectory"])) for i in ids}}
print("signaux precalcules : %d x %d trajectoires x 2 dorsales"
      % (len(SIG), len(ids)))

DRAWS = []
_rng = random.Random(SEED)
_keys = sorted(clusters)
for _ in range(B):
    _s = []
    for _ in range(len(_keys)):
        _s.extend(clusters[_rng.choice(_keys)])
    DRAWS.append(_s)


def rate(name, side, sub):
    f = FLAG[name][side]
    return sum(1 for i in sub if f[i]) / len(sub)


def ci(name, side):
    vals = sorted(rate(name, side, s) for s in DRAWS)
    return [round(vals[int(0.025 * (len(vals) - 1))], 3),
            round(vals[int(0.975 * (len(vals) - 1))], 3)]


print()
print("=" * 78)
print("2. LE TAUX DE DECLENCHEMENT, ET L'ACCORD PAR TACHE")
print()
print("%-16s %18s %18s   %s" % ("signal", "dorsale 1", "dorsale 2",
                                "memes taches"))
OUT = {}
for name, fn in SIG:
    r1, r2 = rate(name, "A", ids), rate(name, "B", ids)
    c1, c2 = ci(name, "A"), ci(name, "B")
    fa, fb = FLAG[name]["A"], FLAG[name]["B"]
    both = sum(1 for i in ids if fa[i] and fb[i])
    only1 = sum(1 for i in ids if fa[i] and not fb[i])
    only2 = sum(1 for i in ids if fb[i] and not fa[i])
    neither = len(ids) - both - only1 - only2
    agree = (both + neither) / len(ids)
    k = mcc(both, only2, only1, neither)
    OUT[name] = dict(rate_first=round(r1, 3), ci_first=c1,
                     rate_second=round(r2, 3), ci_second=c2,
                     both=both, only_first=only1, only_second=only2,
                     neither=neither, agreement=round(agree, 3),
                     phi=round(k, 3))
    print("%-16s %6.3f [%.3f,%.3f] %6.3f [%.3f,%.3f]   %d/%d, phi %+0.3f"
          % (name, r1, c1[0], c1[1], r2, c2[0], c2[1],
             both + neither, len(ids), k))

print()
print("  « memes taches » compte les taches ou les deux dorsales donnent le meme verdict")
print("  du signal, et phi mesure cet accord corrige du hasard. Un taux identique sur les")
print("  deux corpus n'implique pas que le signal y attrape les memes fautes.")

print()
print("=" * 78)
print("2b. LA CAUSE DU DECLENCHEMENT DE LA VALIDATION DE SCHEMA")
print()
print("  Le taux seul ne dit pas pourquoi le signal se declenche. La validation de")
print("  schema a cinq causes possibles, et le code les examine dans cet ordre. Deux")
print("  corpus peuvent donc donner le meme taux par des chemins differents.")
print()


def cause(tr):
    for st in tr:
        a, g = st.get("action"), st.get("input")
        if a is None:
            return "action absente"
        if a not in TOOLS:
            return "outil inconnu"
        if g is None or (isinstance(g, str) and g.strip() == ""):
            return "argument vide"
        if a == "calculator" and not signals._parses(g):
            return "calculator illisible"
        if a == "finish" and str(g).strip() in ("", "None"):
            return "finish vide"
    return None


CAUSES = ("action absente", "outil inconnu", "argument vide",
          "calculator illisible", "finish vide")
CAU = {}
for which, by in (("first", A), ("second", Bc)):
    c = Counter(cause(by[i]["trajectory"]) for i in ids)
    CAU[which] = {k: c.get(k, 0) for k in CAUSES}
print("%-24s %10s %10s" % ("cause", "dorsale 1", "dorsale 2"))
for k in CAUSES:
    print("%-24s %10d %10d" % (k, CAU["first"][k], CAU["second"][k]))
print("%-24s %10d %10d" % ("total", sum(CAU["first"].values()),
                           sum(CAU["second"].values())))

print()
print("=" * 78)
print("2c. L'EXEMPTION DE DETOUR, ET CE QU'ELLE SUPPOSE")
print()
print("  B* annule un appel a un outil inexistant quand l'agent emet ensuite une")
print("  action valide et termine par une reponse non vide. La seconde condition est")
print("  une hypothese sur le comportement de l'agent, et elle ne tient pas partout.")
print()
EXE = {}
for which, by in (("first", A), ("second", Bc)):
    det = [i for i in ids
           if any(s.get("action") not in TOOLS for s in by[i]["trajectory"])]
    rec = []
    for i in det:
        tr = by[i]["trajectory"]
        k = next(j for j, s in enumerate(tr) if s.get("action") not in TOOLS)
        if signals._recovers(tr[k + 1:]):
            rec.append(i)
    nb = sum(1 for i in ids if FLAG["B, schema"]["A" if which == "first" else "B"][i])
    nbs = sum(1 for i in ids
              if FLAG["B*, exempted"]["A" if which == "first" else "B"][i])
    EXE[which] = dict(detours=len(det), recovered=len(rec),
                      b=nb, b_star=nbs, exempted=nb - nbs)
    print("  dorsale %s : %d trajectoires avec detour, %d retablies, "
          "B %d, B* %d, soit %d exemptions"
          % ("1" if which == "first" else "2", len(det), len(rec), nb, nbs,
             nb - nbs))

print()
print("=" * 78)
print("2d. LE TAUX PAR GABARIT")
print()
print("  Le declenchement est concentre par gabarit sur chaque corpus, ce qui est la")
print("  raison des intervalles larges ci-dessus. La question est de savoir si ce sont")
print("  les memes gabarits des deux cotes.")
print()
PER = {}
print("%-10s %12s %12s %12s %12s" % ("gabarit", "B d1", "B d2",
                                     "B* ou C d1", "B* ou C d2"))
for t in sorted(clusters):
    sub = clusters[t]
    row = dict(n=len(sub))
    for nm, key in (("b", "B, schema"), ("bc", "B* or C")):
        row[nm + "1"] = round(rate(key, "A", sub), 3)
        row[nm + "2"] = round(rate(key, "B", sub), 3)
    PER[t] = row
    print("%-10s %12.2f %12.2f %12.2f %12.2f"
          % (t, row["b1"], row["b2"], row["bc1"], row["bc2"]))

print()
print("=" * 78)
print("3. LA QUALITE DE DETECTION")
print()
QUAL = {}
for which, rows, by in (("first", FIRST, A), ("second", SECOND, Bc)):
    if "label_human" not in rows[0]:
        print("  dorsale %s : aucune etiquette, donc ni precision ni rappel."
              % ("1" if which == "first" else "2"))
        QUAL[which] = None
        continue
    fail = {r["id"]: r["label_human"] != "S" for r in rows}
    QUAL[which] = {}
    print("  dorsale %s, taux de base %.3f"
          % ("1" if which == "first" else "2",
             sum(fail.values()) / len(fail)))
    for name, fn in SIG:
        tp = fp = fn_ = tn = 0
        side = "A" if which == "first" else "B"
        for i in ids:
            f, bad = FLAG[name][side][i], fail[i]
            if f and bad:
                tp += 1
            elif f:
                fp += 1
            elif bad:
                fn_ += 1
            else:
                tn += 1
        p = tp / (tp + fp) if tp + fp else None
        r = tp / (tp + fn_) if tp + fn_ else None
        QUAL[which][name] = dict(precision=None if p is None else round(p, 3),
                                 recall=None if r is None else round(r, 3),
                                 mcc=round(mcc(tp, fp, fn_, tn), 3), false_alarms=fp)
        print("    %-16s precision %s rappel %s MCC %+0.3f FA %d"
              % (name, "n/a" if p is None else "%.3f" % p,
                 "n/a" if r is None else "%.3f" % r,
                 QUAL[which][name]["mcc"], fp))

res = os.path.join(ART, "results", "backbone_comparison.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(
    what_this_is=(
        "Two agent backbones on the same 200 task statements, compared on what can be "
        "compared without labels: the agent's own behaviour, each signal's firing rate "
        "with a cluster-bootstrap interval, and whether a signal fires on the same tasks "
        "under both backbones. Detection quality is reported only for a corpus that "
        "carries labels, and the second does not until a labelling round is run."),
    first=os.path.basename(p1), second=os.path.basename(p2), n_items=len(ids),
    bootstrap={"replicates": B, "seed": SEED, "clusters": "task templates"},
    behaviour=BEH, store=STORE, firing=OUT, schema_cause=CAU, detour_exemption=EXE,
    per_template=PER, detection_quality=QUAL,
    what_this_cannot_say=(
        "A signal firing at the same rate on both corpora may be catching different "
        "faults on each. Only labels on the second corpus would settle that, and that is "
        "why the labelling round is the step after this one.")),
    indent=1, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
print()
print("Ce que ce fichier ne peut pas dire : un signal qui se declenche au meme taux sur")
print("les deux corpus peut y attraper des fautes differentes. Il faut des etiquettes sur")
print("le second corpus, et c'est l'etape suivante.")
