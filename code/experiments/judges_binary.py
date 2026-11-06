# -*- coding: utf-8 -*-
"""Les juges en binaire, sur la metrique d'ICV, pour que la comparaison soit possible.

CE QUE LE COMMENTAIRE 5 DEMANDE

"Please also report binary success/failure metrics for the LLM judges to enable
comparison with ICV." Le papier rapporte les juges en accord par categorie, kappa de
0,115 pour le 7B et 0,238 pour la meilleure configuration, ce qui ne se compare pas aux
chiffres d'ICV, donnes en precision, rappel et correlation de Matthews sur la decision
binaire echec contre succes.

Ce script reduit chaque juge a cette meme decision et le note sur la meme metrique, le
meme corpus et la meme cible. Un juge dit echec quand son code n'est pas S.

CE QUE LA COMPARAISON COUTE AU PAPIER, ET QU'IL FAUT DIRE

Un juge lit la trajectoire entiere et produit une categorie. ICV lit la meme trajectoire
et produit un drapeau. Sur la decision binaire, le juge n'est plus desavantage par la
granularite de sa tache, donc cette comparaison lui est plus favorable que l'accord par
categorie. Le script la donne telle quelle.

L'intervalle est un bootstrap par grappes de gabarits, parce que chaque categorie de
faute vient d'un gabarit ou deux.

Sortie : results/judges_binary.json

    python experiments/judges_binary.py
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
import signals                      # noqa: E402
from metrics import mcc             # noqa: E402

ROWS = [json.loads(l) for l in
        io.open(os.path.join(ART, "data", "trajectories_200.jsonl"), encoding="utf-8")
        if l.strip()]
BY = {r["id"]: r for r in ROWS}
FAIL = {r["id"]: r["label_human"] != "S" for r in ROWS}
B = 10000
SEED = 20261105


def load(name):
    q = os.path.join(ART, "results", name)
    assert os.path.exists(q), "fichier absent : %s" % q
    return json.load(io.open(q, encoding="utf-8"))


def norm(code):
    return (code or "").strip().upper()


J32FR, J32EN = load("judge_32b_fr.json"), load("judge_32b_en.json")
FAL = load("judge_falcon3_7b.json")


# Falcon rend une liste de predictions dans l'ordre du corpus, et non un dictionnaire
# par identifiant : l'index est etabli une fois, sur l'ordre du fichier de trajectoires.
_FAL_ORDER = [r["id"] for r in ROWS]
assert len(FAL["preds"]) == len(_FAL_ORDER), (len(FAL["preds"]), len(_FAL_ORDER))
_FAL = dict(zip(_FAL_ORDER, FAL["preds"]))


def falcon(i):
    return norm(_FAL[i])


JUDGES = [
    ("7B judge, Qwen", lambda i: norm(BY[i]["label_judge_7b"])),
    ("32B judge, French", lambda i: norm(J32FR[i]["code"])),
    ("32B judge, English", lambda i: norm(J32EN[i]["code"])),
    ("7B judge, Falcon3", falcon),
]
SIGNALS = [
    ("ICV B, schema", lambda i: signals.tier1(BY[i]["trajectory"])[0]),
    ("ICV B*, exempted", lambda i: signals.tier1_exempt(BY[i]["trajectory"])[0]),
    ("ICV C, consistency", lambda i: signals.tier2(BY[i]["trajectory"])[0]),
    ("ICV B* or C", lambda i: (signals.tier1_exempt(BY[i]["trajectory"])[0]
                               or signals.tier2(BY[i]["trajectory"])[0])),
]

ids = sorted(BY)
missing = {n: [i for i in ids if fn(i) == ""] for n, fn in JUDGES}
for n, m in missing.items():
    assert not m, "%s : %d items sans code" % (n, len(m))
clusters = {}
for r in ROWS:
    clusters.setdefault(r["template"], []).append(r["id"])


def score(flag, sub):
    tp = fp = fn_ = tn = 0
    for i in sub:
        f, bad = bool(flag(i)), FAIL[i]
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
    return p, r, mcc(tp, fp, fn_, tn), fp, tp


def ci(flag):
    rng = random.Random(SEED)
    keys = sorted(clusters)
    vals = []
    for _ in range(B):
        s = []
        for _ in range(len(keys)):
            s.extend(clusters[rng.choice(keys)])
        v = score(flag, s)[2]
        if v == v:
            vals.append(v)
    if len(vals) < 100:
        return [None, None]
    vals.sort()
    return [round(vals[int(0.025 * (len(vals) - 1))], 3),
            round(vals[int(0.975 * (len(vals) - 1))], 3)]


print()
print("%d trajectoires, %d echecs, taux de base %.3f"
      % (len(ids), sum(FAIL.values()), sum(FAIL.values()) / len(ids)))
print()
print("%-22s %9s %8s %8s %6s %6s   %s"
      % ("decision binaire", "precision", "rappel", "MCC", "FA", "VP", "IC du MCC"))
OUT = {}
for group, rows in (("judges", JUDGES), ("ICV signals", SIGNALS)):
    for name, fn in rows:
        if group == "judges":
            flag = (lambda i, fn=fn: fn(i) != "S")
        else:
            flag = fn
        p, r, m, fa, tp = score(flag, ids)
        c = ci(flag)
        OUT[name] = dict(group=group, precision=None if p is None else round(p, 3),
                         recall=None if r is None else round(r, 3), mcc=round(m, 3),
                         false_alarms=fa, true_positives=tp, ci_template=c)
        print("%-22s %9.3f %8.3f %+8.3f %6d %6d   [%+0.3f, %+0.3f]"
              % (name, p, r, m, fa, tp, c[0], c[1]))
    print()

best_j = max((n for n in OUT if OUT[n]["group"] == "judges"),
             key=lambda n: OUT[n]["mcc"])
best_i = max((n for n in OUT if OUT[n]["group"] == "ICV signals"),
             key=lambda n: OUT[n]["mcc"])
print("meilleur juge : %s, MCC %+0.3f" % (best_j, OUT[best_j]["mcc"]))
print("meilleur signal ICV : %s, MCC %+0.3f" % (best_i, OUT[best_i]["mcc"]))

# l'ecart entre les deux, apparie sur les memes grappes
rng = random.Random(SEED)
keys = sorted(clusters)
fj = (lambda i: dict(JUDGES)[best_j](i) != "S")
fi = dict(SIGNALS)[best_i]
diffs = []
for _ in range(B):
    s = []
    for _ in range(len(keys)):
        s.extend(clusters[rng.choice(keys)])
    a, b = score(fj, s)[2], score(fi, s)[2]
    if a == a and b == b:
        diffs.append(a - b)
diffs.sort()
d_ci = [round(diffs[int(0.025 * (len(diffs) - 1))], 3),
        round(diffs[int(0.975 * (len(diffs) - 1))], 3)]
point = round(OUT[best_j]["mcc"] - OUT[best_i]["mcc"], 3)
print("ecart du meilleur juge au meilleur signal : %+0.3f, IC apparie [%+0.3f, %+0.3f]%s"
      % (point, d_ci[0], d_ci[1],
         "   contient zero" if d_ci[0] <= 0 <= d_ci[1] else ""))

res = os.path.join(ART, "results", "judges_binary.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(
    what_this_is=(
        "Every judge and every ICV signal reduced to the same binary decision, failure "
        "against success, and scored on the same metric, corpus and target. A judge says "
        "failure when its code is not S. On the binary decision a judge is no longer "
        "penalised by the granularity of its own task, so this comparison is more "
        "favourable to the judges than the per-category agreement the paper reports."),
    n_items=len(ids), n_failures=sum(FAIL.values()),
    base_rate=round(sum(FAIL.values()) / len(ids), 3),
    bootstrap={"replicates": B, "seed": SEED, "clusters": "task templates"},
    rows=OUT, best_judge=best_j, best_icv=best_i,
    best_judge_minus_best_icv={"point": point, "ci_template_paired": d_ci,
                               "includes_zero": d_ci[0] <= 0 <= d_ci[1]}),
    indent=1, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
