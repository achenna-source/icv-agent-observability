# -*- coding: utf-8 -*-
"""La fiabilite au grain que le corpus soutient, et non au grain que la table annonce.

Pourquoi ce calcul. Le corpus tire chaque categorie de faute d'un seul gabarit de tache,
donc un lecteur qui separe les gabarits separe les etiquettes sans rien dire des
frontieres internes. Le manuscrit le declare deja. La consequence qui n'avait pas ete
tiree est qu'une fiabilite rapportee au grain fin mesure en partie la separation des
gabarits, et qu'il faut donc rapporter aussi le grain que le corpus soutient.

Les deux regroupements, et ils ne sont pas choisis apres coup : ce sont exactement les
deux blocs ou les desaccords de la ronde humaine se concentrent.

  FAB  F2, F6, F7   les trois categories qui se disputent une valeur fabriquee
  INC  F3, F5       le residuel contre l'arret premature
  S    inchange,    F1a et F1b fondus en F1, F4 inchange

Ce que le script rapporte, pour le grain fin et pour le grain grossier : le kappa par
paires et le Fleiss entre les quatre lecteurs, le kappa de chaque lecteur contre les
etiquettes publiees avec un intervalle par grappes de gabarits, le nombre d'items
unanimes, et combien de litiges disparaissent en passant au grain grossier.

Aucune etiquette n'est reecrite par ce script. Il ne change pas le jeu de reference, il
change la granularite a laquelle on le lit.

    python -I coarse_grain.py

Sortie : coarse_grain.json et un rapport lisible.
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

READERS = ("A", "C", "E", "K")
KEY = os.path.join(ANN, "sample_key_DO_NOT_SHARE.jsonl")
TPL = os.path.join(ROOT, "data", "trajectories_200.jsonl")
B = 10000
SEED = 20261105

FAB = ("F2", "F6", "F7")
INC = ("F3", "F5")


def fine(l):
    if not l:
        return None
    return "F1" if l.startswith("F1") else ("F3" if l.startswith("F3") else l)


def coarse(l):
    l = fine(l)
    if l is None:
        return None
    if l in FAB:
        return "FAB"
    if l in INC:
        return "INC"
    return l


def kappa(pairs):
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(1 for x, y in pairs if x == y) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(ca[k] / n * cb.get(k, 0) / n for k in ca)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def fleiss(items):
    m, n = len(items[0]), len(items)
    cats = sorted({c for it in items for c in it})
    tot, pi = Counter(), []
    for it in items:
        c = Counter(it)
        tot.update(c)
        pi.append((sum(v * v for v in c.values()) - m) / (m * (m - 1)))
    pe = sum((tot[c] / (n * m)) ** 2 for c in cats)
    return (sum(pi) / n - pe) / (1 - pe) if pe < 1 else float("nan")


def ci(fn, clusters):
    rng = random.Random(SEED)
    keys = sorted(clusters)
    vals = []
    for _ in range(B):
        s = []
        for _ in range(len(keys)):
            s.extend(clusters[rng.choice(keys)])
        if len(s) < 5:
            continue
        v = fn(s)
        if v == v:
            vals.append(v)
    vals.sort()
    if not vals:
        return [None, None]
    return [round(vals[int(0.025 * (len(vals) - 1))], 3),
            round(vals[int(0.975 * (len(vals) - 1))], 3)]


recs = {}
for w in READERS:
    q = os.path.join(HERE, "responses_%s.jsonl" % w)
    assert os.path.exists(q), "%s manque" % q
    recs[w] = {json.loads(l)["id"]: json.loads(l)
               for l in io.open(q, encoding="utf-8") if l.strip()}
REF = {}
for line in io.open(KEY, encoding="utf-8"):
    if line.strip():
        r = json.loads(line)
        REF[r["id"]] = r["label_annotator1"]
meta = {}
for line in io.open(TPL, encoding="utf-8"):
    if line.strip():
        r = json.loads(line)
        meta[r["id"]] = r["template"]

ids = sorted(set.intersection(*[set(d) for d in recs.values()]))
clusters = {}
for i in ids:
    clusters.setdefault(meta.get(i, "?"), []).append(i)

out = {"readers": list(READERS), "n_items": len(ids),
       "groupings": {"FAB": list(FAB), "INC": list(INC),
                     "note": "F1a and F1b collapse to F1, F4 and S unchanged"},
       "why": ("The corpus draws each fault category from a single task template, so a "
               "reliability figure at the fine grain measures template separation in "
               "part. The coarse grain is the one this corpus supports. No reference "
               "label is rewritten by this analysis."),
       "bootstrap": {"replicates": B, "seed": SEED, "clusters": "task templates"},
       "grains": {}}

print()
for gname, g in (("fine", fine), ("coarse", coarse)):
    for which in ("computed_label", "free_label"):
        def lab(w, i):
            return g(recs[w][i][which])

        kept = [i for i in ids if all(lab(w, i) for w in READERS)]
        e = {"n_items": len(kept)}
        pw, vals = {}, []
        for a in range(len(READERS)):
            for b in range(a + 1, len(READERS)):
                x, y = READERS[a], READERS[b]
                k = kappa([(lab(x, i), lab(y, i)) for i in kept])
                pw["%s|%s" % (x, y)] = round(k, 3)
                vals.append(k)
        e["pairwise"] = pw
        e["mean_pairwise_kappa"] = round(sum(vals) / len(vals), 3)
        its = [[lab(w, i) for w in READERS] for i in kept]
        e["fleiss"] = round(fleiss(its), 3)
        e["unanimous"] = sum(1 for it in its if len(set(it)) == 1)
        e["disputed"] = [kept[k] for k, it in enumerate(its) if len(set(it)) > 1]
        e["vs_reference"] = {}
        for w in READERS:
            pr = [(g(REF[i]), lab(w, i)) for i in kept if i in REF]
            e["vs_reference"][w] = {
                "kappa": round(kappa(pr), 3),
                "ci_template": ci(lambda s, w=w: kappa(
                    [(g(REF[i]), lab(w, i)) for i in s
                     if i in REF and i in set(kept)]), clusters)}
        out["grains"].setdefault(gname, {})[which] = e

        print("%-7s %-15s %d items, kappa moyen %.3f, Fleiss %.3f, %d unanimes, "
              "%d en litige" % (gname, which, len(kept), e["mean_pairwise_kappa"],
                                e["fleiss"], e["unanimous"], len(e["disputed"])))
        for w in READERS:
            v = e["vs_reference"][w]
            print("        lecteur %s contre les etiquettes publiees  %6.3f  IC [%s, %s]"
                  % (w, v["kappa"], v["ci_template"][0], v["ci_template"][1]))
        print()

print("=" * 78)
for which in ("computed_label", "free_label"):
    f = set(out["grains"]["fine"][which]["disputed"])
    c = set(out["grains"]["coarse"][which]["disputed"])
    out["grains"]["coarse"][which]["disputes_resolved_by_grouping"] = sorted(f - c)
    out["grains"]["coarse"][which]["disputes_surviving"] = sorted(c)
    print("%s : %d litiges au grain fin, %d survivent au grain grossier"
          % (which, len(f), len(c)))
    print("  disparaissent : %s" % " ".join(sorted(f - c)))
    print("  survivent     : %s" % (" ".join(sorted(c)) or "aucun"))
    print()

res = os.path.join(HERE, "coarse_grain.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print("ecrit : %s" % res)
