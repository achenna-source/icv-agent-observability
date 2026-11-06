# -*- coding: utf-8 -*-
"""L'accord avant et apres arbitrage, les deux chiffres que la lettre promet.

Pourquoi les deux comptent, et pourquoi l'un seul tromperait. Avant arbitrage, l'accord
dit ce que le codebook obtient de lecteurs qui l'appliquent seuls : c'est la grandeur
comparable au 0,370 et la seule qui mesure le document. Apres arbitrage, il dit ce qu'un
panel obtient quand un arbitre tranche les litiges : c'est plus haut par construction,
puisque les desaccords ont ete resolus, et ce chiffre ne mesure plus le codebook. Publier
le second seul donnerait une fiabilite que le schema n'a pas.

Ce qui est calcule.

  avant   kappa de chaque lecteur contre la reference, kappa par paires entre lecteurs,
          Fleiss sur les lecteurs, sur les items que tous ont rendus.
  apres   la meme chose, les items arbitres portant l'etiquette de l'arbitre pour chaque
          lecteur, les autres restant inchanges.
  reste   les items que l'arbitre a laisses indecis, comptes et nommes, jamais remplis.

Les deux jeux d'etiquettes de l'entretien sont traites separement, le calcule et le libre,
parce qu'ils ne mesurent pas la meme chose.

    python -I -X utf8 adjudication_agreement.py

Sortie : adjudication_agreement.json et un rapport lisible.
"""
import glob
import io
import json
import os
import random
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)

ROSTER = ("A", "B", "C", "D", "E", "K")
KEY = os.path.join(ANN, "sample_key_DO_NOT_SHARE.jsonl")
B = 10000
SEED = 20261105


def collapse(l):
    if not l:
        return None
    return "F1" if l.startswith("F1") else ("F3" if l.startswith("F3") else l)


def raw(pairs):
    return sum(1 for x, y in pairs if x == y) / len(pairs)


def kappa(pairs):
    n = len(pairs)
    po = raw(pairs)
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(ca[k] / n * cb.get(k, 0) / n for k in ca)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def fleiss(items):
    m = len(items[0])
    cats = sorted({c for it in items for c in it})
    n = len(items)
    tot, pi = Counter(), []
    for it in items:
        c = Counter(it)
        tot.update(c)
        pi.append((sum(v * v for v in c.values()) - m) / (m * (m - 1)))
    pe = sum((tot[c] / (n * m)) ** 2 for c in cats)
    return (sum(pi) / n - pe) / (1 - pe) if pe < 1 else float("nan")


def ci(fn, ids, clusters):
    rng = random.Random(SEED)
    keys = sorted(clusters)
    vals = []
    for _ in range(B):
        s = []
        for _ in range(len(keys)):
            s.extend(clusters[rng.choice(keys)])
        s = [i for i in s if i in ids]
        if len(s) < 5:
            continue
        v = fn(s)
        if v == v:
            vals.append(v)
    if not vals:
        return [None, None]
    vals.sort()
    return [round(vals[int(0.025 * (len(vals) - 1))], 3),
            round(vals[int(0.975 * (len(vals) - 1))], 3)]


# ------------------------------------------------------------------- lecture
recs = {}
for p in sorted(glob.glob(os.path.join(HERE, "responses_*.jsonl"))):
    who = os.path.basename(p)[len("responses_"):-len(".jsonl")]
    if who not in ROSTER:
        print("  hors roster, ecarte : %s" % who)
        continue
    recs[who] = {json.loads(l)["id"]: json.loads(l)
                 for l in io.open(p, encoding="utf-8") if l.strip()}
if len(recs) < 2:
    print()
    print("  %d passe(s) du roster. Il faut au moins deux lecteurs." % len(recs))
    sys.exit(1)

adj = {}
for p in sorted(glob.glob(os.path.join(HERE, "adjudication_*.jsonl"))):
    for line in io.open(p, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            adj.setdefault(r["which"], {})[r["id"]] = r

REF = {}
if os.path.exists(KEY):
    for line in io.open(KEY, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            REF[r["id"]] = collapse(r["label_annotator1"])

# les gabarits servent au bootstrap par grappes. Hors de l'arborescence de l'artefact
# ils sont absents, et chaque item devient alors sa propre grappe, ce qui donne un
# intervalle plus etroit a tort : le fichier le dit plutot que de le taire.
meta, by_template = {}, True
tpath = os.path.join(os.path.dirname(ANN), "data", "trajectories_200.jsonl")
if os.path.exists(tpath):
    for line in io.open(tpath, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            meta[r["id"]] = r["template"]
else:
    by_template = False
    print("  trajectories_200.jsonl absent : bootstrap par item, intervalle trop etroit")

out = {"readers": sorted(recs), "n_readers": len(recs),
       "bootstrap": {"replicates": B, "seed": SEED,
                     "clusters": "task templates" if by_template
                                 else "items, templates unavailable"},
       "what_this_is": (
           "Human inter-annotator agreement on the fifty, before and after a blind "
           "adjudication. The pre-adjudication figure is the one comparable to the "
           "published 0.370 and the only one that measures the codebook. The "
           "post-adjudication figure measures what a panel achieves and is higher by "
           "construction."),
       "sets": {}}

print()
for which in ("computed", "free"):
    shared = None
    for d in recs.values():
        s = {i for i in d if (d[i]["free_label"] if which == "free"
                              else d[i]["computed_label"])}
        shared = s if shared is None else (shared & s)
    shared = sorted(shared or ())
    if not shared:
        print("=" * 78)
        print("%s : aucun item rendu par tous les lecteurs" % which.upper())
        print()
        continue

    def lab(w, i, after):
        r = recs[w][i]
        v = collapse(r["free_label"] if which == "free" else r["computed_label"])
        if after and i in adj.get(which, {}):
            a = adj[which][i]
            if a["adjudicated_label"]:
                return collapse(a["adjudicated_label"])
        return v

    clusters = {}
    for i in shared:
        clusters.setdefault(meta.get(i, "?"), []).append(i)

    e = {"n_items": len(shared),
         "n_adjudicated": sum(1 for i in shared if i in adj.get(which, {})),
         "n_left_undecided": [i for i in shared
                              if i in adj.get(which, {})
                              and adj[which][i].get("undecided")]}
    for stage, after in (("before", False), ("after", True)):
        st = {}
        if REF:
            st["vs_reference"] = {}
            for w in sorted(recs):
                pr = [(REF[i], lab(w, i, after)) for i in shared if i in REF]
                if pr:
                    st["vs_reference"][w] = {
                        "raw": round(raw(pr), 3), "kappa": round(kappa(pr), 3),
                        "ci_template": ci(
                            lambda s, w=w, after=after: kappa(
                                [(REF[i], lab(w, i, after)) for i in s if i in REF]),
                            set(shared), clusters)}
        pw, vals = {}, []
        ws = sorted(recs)
        for a in range(len(ws)):
            for b in range(a + 1, len(ws)):
                pr = [(lab(ws[a], i, after), lab(ws[b], i, after)) for i in shared]
                k = kappa(pr)
                pw["%s|%s" % (ws[a], ws[b])] = {"raw": round(raw(pr), 3),
                                                "kappa": round(k, 3)}
                vals.append(k)
        st["pairwise"] = pw
        st["mean_pairwise_kappa"] = round(sum(vals) / len(vals), 3)
        if len(ws) > 2:
            its = [[lab(w, i, after) for w in ws] for i in shared]
            st["fleiss"] = round(fleiss(its), 3)
            st["unanimous"] = sum(1 for it in its if len(set(it)) == 1)
        e[stage] = st
    out["sets"][which] = e

    print("=" * 78)
    print("%s : %d items, %d arbitres, %d laisses indecis"
          % (which.upper(), e["n_items"], e["n_adjudicated"],
             len(e["n_left_undecided"])))
    print()
    print("  entre lecteurs          avant     apres")
    print("  kappa moyen par paires %7.3f   %7.3f"
          % (e["before"]["mean_pairwise_kappa"], e["after"]["mean_pairwise_kappa"]))
    if "fleiss" in e["before"]:
        print("  kappa de Fleiss        %7.3f   %7.3f"
              % (e["before"]["fleiss"], e["after"]["fleiss"]))
        print("  items unanimes         %7d   %7d"
              % (e["before"]["unanimous"], e["after"]["unanimous"]))
    if REF and "vs_reference" in e["before"]:
        print()
        print("  contre la reference     avant     apres")
        for w in sorted(e["before"]["vs_reference"]):
            print("  lecteur %-14s %7.3f   %7.3f"
                  % (w, e["before"]["vs_reference"][w]["kappa"],
                     e["after"]["vs_reference"][w]["kappa"]))
    if e["n_left_undecided"]:
        print()
        print("  l'arbitre a laisse indecis : %s" % " ".join(e["n_left_undecided"]))
        print("  ces items restent au desaccord des lecteurs, ils ne sont pas remplis")
    print()

if not out["sets"]:
    print("rien a rapporter : aucun item commun")
    sys.exit(1)

res = os.path.join(HERE, "adjudication_agreement.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("ecrit : %s" % res)
print()
print("Le chiffre a citer a cote du 0,370 est celui d'avant arbitrage, sur les "
      "etiquettes")
print("libres. Celui d'apres arbitrage mesure un panel, pas le codebook, et les deux")
print("doivent paraitre ensemble.")
