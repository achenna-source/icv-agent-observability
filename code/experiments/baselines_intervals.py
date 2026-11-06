# -*- coding: utf-8 -*-
"""Les intervalles des ecarts de la comparaison, sans lesquels les ecarts ne sont rien.

Le manuscrit affirme desormais +0,876 contre +0,485, et la section VI.C de la revision 2
ne dit pas si cet ecart se distingue du bruit. La lecon du commentaire 2 est que
l'intervalle change la conclusion : 0,749 contre 0,846 y paraissait un resultat et s'est
revele recouvert. Le meme controle est donc applique ici avant que le relecteur le
demande.

Le bootstrap est apparie par grappes de gabarits de tache. Chaque tirage recalcule tous
les validateurs sur les memes grappes, donc l'ecart entre deux d'entre eux n'herite pas
de la variance qui leur est commune. Huit grappes seulement, ce qui donne des intervalles
larges : c'est la realite de ce banc et non un defaut de la methode.

Quatre ecarts sont testes.

  recomputation contre la meilleure configuration du papier
  la composition contre la recomputation seule, qui doit contenir zero
  la trajectoire seule contre l'oracle prive du gabarit
  la trajectoire seule contre l'oracle prive du magasin

Sortie : results/baselines_intervals.json

    python experiments/baselines_intervals.py
"""
import io
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ART = os.path.dirname(CODE)
sys.path.insert(0, CODE)
sys.path.insert(0, HERE)
from metrics import mcc              # noqa: E402

# les predicats sont importes de leurs scripts, jamais recopies
import importlib.util


class Quiet(io.StringIO):
    """Le module importe reconfigure sa sortie : on lui en donne une qui l'accepte."""

    def reconfigure(self, **kw):
        return None


def load(name):
    spec = importlib.util.spec_from_file_location(
        "_x_" + name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    keep, sys.stdout = sys.stdout, Quiet()
    try:
        spec.loader.exec_module(m)
    finally:
        sys.stdout = keep
    return m


OD = load("oracle_degradation")
CBJ = json.load(io.open(os.path.join(ART, "results", "cheap_baselines.json"),
                        encoding="utf-8"))
ROWS = OD.ROWS
FAIL = OD.FAIL

PRED = {
    "recompute": OD.L3,
    "store only": OD.L2,
    "task only": OD.L1,
    "trace only": OD.L0,
    "recompute + trace only": lambda r: OD.L3(r) or OD.L0(r),
}
TPL = {r["id"]: r["template"] for r in ROWS}
CLUST = {}
for r in ROWS:
    CLUST.setdefault(r["template"], []).append(r["id"])
BY = {r["id"]: r for r in ROWS}
FLAG = {n: {r["id"]: bool(f(r)) for r in ROWS} for n, f in PRED.items()}

B = 10000
SEED = 20261105


def score(name, ids):
    tp = fp = fn = tn = 0
    for i in ids:
        f, bad = FLAG[name][i], FAIL[i]
        if f and bad:
            tp += 1
        elif f:
            fp += 1
        elif bad:
            fn += 1
        else:
            tn += 1
    return mcc(tp, fp, fn, tn)


def ci(vals):
    vals = sorted(vals)
    return [round(vals[int(0.025 * (len(vals) - 1))], 3),
            round(vals[int(0.975 * (len(vals) - 1))], 3)]


rng = random.Random(SEED)
keys = sorted(CLUST)
draws = []
for _ in range(B):
    s = []
    for _ in range(len(keys)):
        s.extend(CLUST[rng.choice(keys)])
    draws.append(s)

print()
print("%d trajectoires, %d grappes de gabarits, %d tirages apparies"
      % (len(ROWS), len(keys), B))
print()
POINT = {n: round(score(n, [r["id"] for r in ROWS]), 3) for n in PRED}
BOOT = {n: [] for n in PRED}
for s in draws:
    for n in PRED:
        v = score(n, s)
        BOOT[n].append(v if v == v else 0.0)

print("%-24s %8s   %s" % ("validateur", "MCC", "IC par grappes"))
OUT = {}
for n in ("recompute", "store only", "task only", "trace only",
          "recompute + trace only"):
    c = ci(BOOT[n])
    OUT[n] = {"mcc": POINT[n], "ci_template": c}
    print("%-24s %+8.3f   [%+0.3f, %+0.3f]" % (n, POINT[n], c[0], c[1]))

PAIRS = (("recompute", "trace only",
          "la recomputation contre la meilleure configuration du papier"),
         ("recompute + trace only", "recompute",
          "la composition contre la recomputation seule"),
         ("trace only", "store only",
          "la trajectoire seule contre l'oracle prive du gabarit"),
         ("trace only", "task only",
          "la trajectoire seule contre l'oracle prive du magasin"))

print()
print("ecarts apparies")
DIFFS = {}
for a, b, label in PAIRS:
    d = [BOOT[a][k] - BOOT[b][k] for k in range(len(draws))]
    c = ci(d)
    point = round(POINT[a] - POINT[b], 3)
    zero = c[0] <= 0 <= c[1]
    DIFFS["%s - %s" % (a, b)] = {"point": point, "ci_template": c,
                                 "includes_zero": zero, "what": label}
    print("  %-52s %+0.3f  [%+0.3f, %+0.3f]%s"
          % (label, point, c[0], c[1], "   contient zero" if zero else ""))

# controle : le point de depart doit etre celui des deux scripts deja publies
assert POINT["recompute"] == CBJ["validators"]["1 recompute"]["mcc"], POINT
assert POINT["trace only"] == CBJ["validators"]["B* or C"]["mcc"], POINT
print()
print("  controle : les deux points reproduisent cheap_baselines.py")

res = os.path.join(ART, "results", "baselines_intervals.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(
    what_this_is=(
        "Cluster-bootstrap intervals for the comparison of Section VI.C. Each replicate "
        "resamples the eight task templates and recomputes every validator on the same "
        "clusters, so a paired difference does not inherit the variance the validators "
        "share. Eight clusters give wide intervals, which is a property of this benchmark "
        "and not of the method."),
    n_items=len(ROWS), n_clusters=len(keys), replicates=B, seed=SEED,
    validators=OUT, paired_differences=DIFFS), indent=1, ensure_ascii=False) + "\n")
print("ecrit : %s" % res)
