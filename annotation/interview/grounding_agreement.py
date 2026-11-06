# -*- coding: utf-8 -*-
"""L'accord des deux lecteurs sur l'axe d'ancrage, et ce que l'axe ajoute a l'etiquette.

Pourquoi deux lecteurs et pas un. Une cible dont la reproductibilite est inconnue ne peut
pas servir a noter un detecteur : c'est le defaut qui a fait sortir la version precedente
de cet axe du manuscrit. Ce script mesure donc l'accord avant de rapporter quoi que ce
soit d'autre.

Le calcul porte sur les items soumis a un jugement dans les deux lectures. Les
trajectoires sans reponse finale sont une lecture mecanique et n'entrent pas. Les taches
purement arithmetiques sont hors de l'axe : elles fournissent leurs propres operandes, et
le premier lecteur les a jugees sous une formulation qui ne le disait pas encore, donc
elles sortent des deux lectures et non d'une seule.

L'intervalle est un bootstrap par grappes de gabarits de tache, parce que chaque categorie
de faute vient d'un gabarit ou deux : un intervalle par item serait trop etroit.

    python -I grounding_agreement.py

Sortie : grounding_agreement.json
"""
import io
import json
import os
import random
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)
READERS = ("A", "B")
B_REP = 10000
SEED = 20261105

ROWS = {r["id"]: r for r in (json.loads(l) for l in
        io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"), encoding="utf-8")
        if l.strip())}

G = {}
for w in READERS:
    q = os.path.join(HERE, "grounding_%s.jsonl" % w)
    assert os.path.exists(q), "fichier absent : %s" % q
    G[w] = {json.loads(l)["id"]: json.loads(l)
            for l in io.open(q, encoding="utf-8") if l.strip()}

# les items hors axe, determines par la lecture de B qui porte la formulation corrigee
OUT = {i for i in G["B"] if G["B"][i]["outcome"] in ("no_answer", "not_applicable")}
ids = sorted(i for i in G["A"] if i not in OUT
             and G["A"][i]["outcome"] not in ("no_answer", "not_applicable"))
print()
print("  %d items au total, %d hors axe, %d soumis a un jugement dans les deux lectures"
      % (len(ROWS), len(OUT), len(ids)))
assert len(ids) >= 100, len(ids)


def lab(w, i):
    return G[w][i]["outcome"]


def raw(pairs):
    return sum(1 for x, y in pairs if x == y) / len(pairs)


def kappa(pairs):
    n = len(pairs)
    po = raw(pairs)
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(ca[k] / n * cb.get(k, 0) / n for k in ca)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


clusters = {}
for i in ids:
    clusters.setdefault(ROWS[i]["template"], []).append(i)
rng = random.Random(SEED)
keys = sorted(clusters)
vals = []
for _ in range(B_REP):
    s = []
    for _ in range(len(keys)):
        s.extend(clusters[rng.choice(keys)])
    v = kappa([(lab("A", i), lab("B", i)) for i in s])
    if v == v:
        vals.append(v)
vals.sort()
ci = [round(vals[int(0.025 * (len(vals) - 1))], 3),
      round(vals[int(0.975 * (len(vals) - 1))], 3)]

pairs = [(lab("A", i), lab("B", i)) for i in ids]
k = kappa(pairs)
print()
print("  accord brut %.3f, kappa de Cohen %.3f, intervalle par grappes [%s, %s]"
      % (raw(pairs), k, ci[0], ci[1]))
tab = Counter(pairs)
print("  croisement : %s" % "  ".join("A=%s B=%s %d" % (a, b, n)
                                      for (a, b), n in sorted(tab.items())))
disagree = sorted(i for i in ids if lab("A", i) != lab("B", i))
print("  %d desaccords : %s" % (len(disagree), " ".join(disagree[:14])))

# ---------------------------------------------- ce que l'axe ajoute a l'etiquette
print()
print("  l'axe contre l'etiquette de reference, sur les items ou les deux s'accordent")
agree = [i for i in ids if lab("A", i) == lab("B", i)]
byl = {}
for i in agree:
    byl.setdefault(ROWS[i]["label_human"], Counter())[lab("A", i)] += 1
for lb in sorted(byl):
    print("    %-4s %s" % (lb, dict(byl[lb])))
f3 = byl.get("F3", Counter())
print()
print("  dans F3, l'axe partage %d non ancres contre %d ancres, la ou l'etiquette ne dit"
      % (f3.get("ungrounded", 0), f3.get("grounded", 0)))
print("  rien de l'ancrage")

sub = Counter()
for i in agree:
    if ROWS[i]["label_human"] == "F3":
        sub[(ROWS[i].get("label_f3_subcode") or "aucun", lab("A", i))] += 1
print("  croisement avec le sous-code publie : %s"
      % "  ".join("%s/%s %d" % (a, b, n) for (a, b), n in sorted(sub.items(), key=str)))

# ---------------------------------------------- independance des deux lectures
notes = sum(1 for i in ids
            if (G["A"][i]["note"] or "").strip()
            and (G["A"][i]["note"] or "").strip() == (G["B"][i]["note"] or "").strip())
print()
print("  notes non vides identiques entre les deux lecteurs : %d" % notes)
print("  reponses incertaines : A %d, B %d"
      % (sum(1 for i in ids if lab("A", i) == "unsure"),
         sum(1 for i in ids if lab("B", i) == "unsure")))

out = dict(
    what_this_is=(
        "Agreement between two human readers on the source-grounding axis, on the items "
        "the axis applies to. Trajectories with no final answer are a mechanical reading "
        "and are excluded; arithmetic-only tasks supply their own operands and are "
        "outside the axis, excluded from both readers rather than from one. The interval "
        "is a cluster bootstrap over task templates."),
    readers=list(READERS), n_total=len(ROWS), n_out_of_scope=len(OUT), n_judged=len(ids),
    raw_agreement=round(raw(pairs), 3), cohen_kappa=round(k, 3), ci_template=ci,
    bootstrap={"replicates": B_REP, "seed": SEED, "clusters": "task templates"},
    cross_tab={"A=%s|B=%s" % kk: v for kk, v in sorted(tab.items())},
    disagreements=disagree,
    by_reference_label_where_both_agree={lb: dict(c) for lb, c in sorted(byl.items())},
    f3_split_where_both_agree={"ungrounded": f3.get("ungrounded", 0),
                               "grounded": f3.get("grounded", 0)},
    f3_subcode_cross={"%s/%s" % kk: v for kk, v in sorted(sub.items(), key=str)},
    identical_notes=notes,
    unsure={"A": sum(1 for i in ids if lab("A", i) == "unsure"),
            "B": sum(1 for i in ids if lab("B", i) == "unsure")})
res = os.path.join(HERE, "grounding_agreement.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
