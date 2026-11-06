# -*- coding: utf-8 -*-
"""Les signaux scores contre l'axe d'ancrage des sources, Section VI.C.

CE QUE CE SCRIPT CALCULE, ET POURQUOI IL EXISTE

La Section VI.C note les detecteurs contre une cible qui n'est pas l'etiquette de
reference : l'axe d'ancrage, c'est-a-dire le verdict concorde de deux lecteurs humains sur
la question de savoir si la reponse finale avance un nombre que rien ne justifie. Les
chiffres rapportes sont une precision de 0,130 et un MCC de -0,231 pour la validation de
schema, 0,639 et +0,259 pour le test de coherence, avec leurs intervalles. Le fichier
results/grounding_target.json les portait sans qu'aucun script publie ne les recalcule.
C'est la seule table du manuscrit qui etait dans ce cas.

LA PORTEE DE LA CIBLE, HERITEE DE L'ACCORD ET NON CHOISIE ICI

Trois exclusions, toutes prises dans grounding_agreement.py et reprises telles quelles.
Les trajectoires sans reponse finale sortent, parce que l'axe ne s'y applique pas et que
la lecture en est mecanique. Les taches purement arithmetiques sortent, parce qu'elles
fournissent leurs propres operandes et ne retrouvent rien ou s'ancrer. Les items sur
lesquels les deux lecteurs divergent sortent sans arbitrage, pour qu'aucun troisieme
jugement n'entre dans la cible. Il reste 158 items, dont 64 non ancres.

POURQUOI LE RESULTAT NE DEPEND PAS DE L'ENCODEUR

Le test de doublon du signal C demande un encodeur de phrases. Il signale deux
trajectoires dans ce corpus, t004 et t190. La premiere est hors de l'axe, faute de
reponse finale ; la seconde est dans la cible et le test de contradiction la signale
deja. Sur ce sous-ensemble, le test de doublon ne change donc aucun des quatre chiffres,
ce que le controle ci-dessous verifie contre results/flag_position.json plutot que de le
supposer. Le script tourne sans charger de modele.

CE QU'IL FAUT LIRE DANS CE QU'IL SORT

Le contraste tient aux intervalles et non aux points. La validation de schema est etablie
comme anti-correlee a l'ancrage, son intervalle restant du cote negatif. Le test de
coherence atteint +0,259 mais son intervalle contient zero a huit grappes, donc rien
n'etablit qu'il detecte l'absence d'ancrage a un taux distinguable. La variante exemptee
ne se declenche sur aucun item de ce sous-ensemble, et sa correlation y est indefinie :
elle est rapportee comme telle, et non comme un zero.

    python -I grounding_target.py

Sortie : results/grounding_target.json, et un echec si un chiffre du manuscrit ne tient
plus.
"""
import io
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "code"))

from metrics import mcc                                        # noqa: E402
from signals import tier1, tier1_exempt, tier2                 # noqa: E402

B_REP = 10000
SEED = 20261105
OUT_OF_AXIS = ("no_answer", "not_applicable")

# les valeurs publiees, telles que la Section VI.C les imprime
PAPER = {
    "n_items": 158, "n_positive": 64,
    "B, schema": dict(precision=0.130, recall=0.047, mcc=-0.231, false_alarms=20,
                      ci_template=[-0.462, -0.015]),
    "C, consistency": dict(precision=0.639, recall=0.359, mcc=0.259, false_alarms=13,
                           ci_template=[-0.189, 0.624]),
    "B* or C": dict(precision=0.639, recall=0.359, mcc=0.259, false_alarms=13,
                    ci_template=[-0.189, 0.624]),
}

rows = {r["id"]: r for r in (json.loads(l) for l in
        io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"), encoding="utf-8")
        if l.strip())}
assert len(rows) == 200, len(rows)

G = {}
for w in ("A", "B"):
    q = os.path.join(ROOT, "annotation", "interview", "grounding_%s.jsonl" % w)
    assert os.path.exists(q), "lecture absente : %s" % q
    G[w] = {json.loads(l)["id"]: json.loads(l)
            for l in io.open(q, encoding="utf-8") if l.strip()}

# la portee est celle de grounding_agreement.py, a la ligne pres
off = {i for i in G["B"] if G["B"][i]["outcome"] in OUT_OF_AXIS}
judged = sorted(i for i in G["A"] if i not in off
                and G["A"][i]["outcome"] not in OUT_OF_AXIS)
items = [i for i in judged if G["A"][i]["outcome"] == G["B"][i]["outcome"]]
disagree = [i for i in judged if i not in items]
assert not any(G[w][i]["outcome"] == "unsure" for w in ("A", "B") for i in items), (
    "un item incertain entrerait dans la cible")

y = {i: G["A"][i]["outcome"] == "ungrounded" for i in items}
print()
print("  %d items juges par les deux lecteurs, %d desaccords exclus sans arbitrage, "
      "%d retenus" % (len(judged), len(disagree), len(items)))
print("  cible : %d non ancres contre %d ancres" % (sum(y.values()),
                                                    len(items) - sum(y.values())))

flags = {"B, schema": {}, "B*, exempted": {}, "C, consistency": {}}
for i in items:
    tr = rows[i]["trajectory"]
    flags["B, schema"][i] = tier1(tr)[0]
    flags["B*, exempted"][i] = tier1_exempt(tr)[0]
    flags["C, consistency"][i] = tier2(tr, None)[0]
flags["B* or C"] = {i: flags["B*, exempted"][i] or flags["C, consistency"][i]
                    for i in items}

# le test de doublon, lu dans le fichier publie plutot que recalcule avec un modele
fp = os.path.join(ROOT, "results", "flag_position.json")
assert os.path.exists(fp), "results/flag_position.json est requis pour ce controle"
pos = {r["id"]: r for r in json.load(io.open(fp, encoding="utf-8"))["per_trajectory"]}
dup = sorted(i for i, r in pos.items() if r["C"].get("duplicate"))
inside = [i for i in dup if i in y]
missed = [i for i in inside if not flags["C, consistency"][i]]
print()
print("  test de doublon : %d trajectoires signalees dans le corpus, %s ; %d dans la "
      "cible" % (len(dup), " et ".join(dup), len(inside)))
assert not missed, (
    "l'encodeur changerait le resultat sur %s : le test de doublon y signale une "
    "trajectoire que le test de contradiction ne signale pas, donc ces chiffres "
    "dependraient du modele de phrases" % missed)
print("  aucune n'est hors de ce que le test de contradiction signale deja, donc les "
      "chiffres ne dependent pas de l'encodeur")

clusters = {}
for i in items:
    clusters.setdefault(rows[i]["template"], []).append(i)
keys = sorted(clusters)


def score(sig, subset):
    f, tp = flags[sig], 0
    fp_ = fn = 0
    for i in subset:
        if f[i] and y[i]:
            tp += 1
        elif f[i]:
            fp_ += 1
        elif y[i]:
            fn += 1
    tn = len(subset) - tp - fp_ - fn
    return tp, fp_, fn, tn


def point(sig):
    tp, fp_, fn, tn = score(sig, items)
    pre = tp / (tp + fp_) if tp + fp_ else None
    rec = tp / (tp + fn) if tp + fn else None
    return dict(precision=round(pre, 3) if pre is not None else None,
                recall=round(rec, 3) if rec is not None else None,
                mcc=round(mcc(tp, fp_, fn, tn), 3), false_alarms=fp_)


def interval(sig):
    """Bootstrap par grappes de gabarits. Un tirage dont le MCC est indefini, faute de
    signalement ou faute de positif, est compte et non remplace : le nombre de tirages
    valides est publie avec l'intervalle."""
    rng = random.Random(SEED)
    vals = []
    for _ in range(B_REP):
        draw = []
        for _ in range(len(keys)):
            draw.extend(clusters[rng.choice(keys)])
        v = mcc(*score(sig, draw))
        if v == v:
            vals.append(v)
    if not vals:
        return [None, None], 0
    vals.sort()
    return ([round(vals[int(0.025 * (len(vals) - 1))], 3),
             round(vals[int(0.975 * (len(vals) - 1))], 3)], len(vals))


out = dict(
    what_this_is=(
        "The paper's signals scored against the source-grounding axis as a target, the "
        "axis being the agreed verdict of two independent human readers. Items the axis "
        "does not apply to are excluded, and items the readers disagree on are excluded "
        "rather than adjudicated. No language model takes part in the target."),
    n_items=len(items), n_positive=sum(y.values()),
    bootstrap={"replicates": B_REP, "seed": SEED, "clusters": "task templates"},
    signals={})

print()
print("  %-16s %9s %7s %8s %7s %18s %7s"
      % ("signal", "precision", "recall", "MCC", "FA", "IC95 du MCC", "tirages"))
for sig in ("B, schema", "B*, exempted", "C, consistency", "B* or C"):
    p = point(sig)
    ci, nb = interval(sig)
    p["ci_template"] = ci
    p["n_bootstrap_valid"] = nb
    out["signals"][sig] = p
    print("  %-16s %9s %7s %8s %7d %18s %7d"
          % (sig,
             "-" if p["precision"] is None else "%.3f" % p["precision"],
             "-" if p["recall"] is None else "%.3f" % p["recall"],
             "indef." if p["mcc"] != p["mcc"] else "%+.3f" % p["mcc"],
             p["false_alarms"],
             "indefini" if ci[0] is None else "[%+.3f, %+.3f]" % (ci[0], ci[1]),
             nb))

print()
bad = []
if out["n_items"] != PAPER["n_items"] or out["n_positive"] != PAPER["n_positive"]:
    bad.append("la taille de la cible : %d items, %d positifs"
               % (out["n_items"], out["n_positive"]))
for sig, exp in PAPER.items():
    if not isinstance(exp, dict):
        continue
    got = out["signals"][sig]
    for k, v in exp.items():
        g = got[k]
        if isinstance(v, list):
            if [abs(a - b) <= 0.002 for a, b in zip(g, v)] != [True, True]:
                bad.append("%s, %s : %s contre %s publie" % (sig, k, g, v))
        elif isinstance(v, float):
            if abs(g - v) > 0.002:
                bad.append("%s, %s : %s contre %s publie" % (sig, k, g, v))
        elif g != v:
            bad.append("%s, %s : %s contre %s publie" % (sig, k, g, v))
ex = out["signals"]["B*, exempted"]
if ex["false_alarms"] != 0 or ex["recall"] != 0.0 or ex["n_bootstrap_valid"] != 0:
    bad.append("la variante exemptee devrait ne se declencher sur aucun item : %s" % ex)
for b in bad:
    print("  ECART %s" % b)
assert not bad, "les chiffres de la Section VI.C ne tiennent plus"
print("  les chiffres de la Section VI.C sont reproduits, intervalles compris")

res = os.path.join(ROOT, "results", "grounding_target.json")
old = json.load(io.open(res, encoding="utf-8")) if os.path.exists(res) else None
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print()
if old is not None:
    same = json.dumps(old, sort_keys=True) == json.dumps(out, sort_keys=True)
    print("  %s : %s" % (res, "identique au fichier publie" if same
                         else "DIFFERENT du fichier publie, voir ci-dessus"))
else:
    print("  ecrit : %s" % res)
