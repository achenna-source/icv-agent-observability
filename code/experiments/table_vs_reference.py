# -*- coding: utf-8 -*-
"""La table de decision publiee, lue a la lettre, contre les etiquettes de reference.

D'ou vient la question. En construisant l'instrument d'entretien de la ronde humaine, les
sept controles ont ete recopies de annotator2_instructions.md et poses dans l'ordre de la
table, sans les conventions. Sur trois trajectoires d'essai, l'instrument a diverge de la
reference trois fois sur trois. L'instrument etait fidele au document ; le document ne
decrit pas la procedure qui a produit les etiquettes. Ce script mesure l'ecart sur tout le
corpus, au lieu de le laisser a trois cas.

Quatre mesures, toutes lues des 200 trajectoires publiees et de la table telle qu'elle est
ecrite.

  1. La premiere regle de la table, prise au mot, ne peut se declencher que sur une etape
     malformee : aucune etape du corpus ne nomme un outil inexistant non vide. F1a n'est
     donc pas atteignable comme diagnostic de choix d'outil.
  2. Les trajectoires qui portent une malformation, ce que la reference leur donne, et
     combien d'entre elles sont reprises.
  3. La table lue a la lettre declenche sa regle 1 sur chacune de ces trajectoires, donc
     elle les etiquette toutes F1a, alors que la reference n'en etiquette aucune F1.
  4. Sur le lot de 50 de la ronde a deux lecteurs, ce que cette lecture coute en accord,
     et le sens des desaccords F1 reellement observes.

Sortie : results/table_vs_reference.json
"""
import csv
import io
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "code"))

from signals import TOOLS, _recovers                           # noqa: E402

corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
assert len(corpus) == 200
by_id = {r["id"]: r for r in corpus}


def malformed(tr):
    """La definition de la table : une etape qui ne nomme aucun outil enregistre."""
    return [k for k, s in enumerate(tr)
            if s.get("action") is None or s.get("action") not in TOOLS]


def kappa(a, b):
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] / n * cb.get(k, 0) / n for k in ca)
    return (po - pe) / (1 - pe) if pe != 1 else float("nan"), po, pe


out = {}

print("=" * 78)
print("1. LA PREMIERE REGLE DE LA TABLE NE PEUT SE DECLENCHER QUE SUR UNE MALFORMATION")
print()
steps = sum(len(r["trajectory"]) for r in corpus)
mal_steps = sum(len(malformed(r["trajectory"])) for r in corpus)
named = [(r["id"], k + 1, s["action"]) for r in corpus
         for k, s in enumerate(r["trajectory"])
         if isinstance(s.get("action"), str) and s["action"].strip()
         and s["action"].strip().lower() != "none" and s["action"].strip() not in TOOLS]
print("   etapes du corpus                                        : %d" % steps)
print("   etapes ne nommant aucun outil enregistre                : %d" % mal_steps)
print("   dont nommant un outil inexistant, non vide              : %d" % len(named))
print()
print("   La regle 1 dit : l'agent a appele un outil qui n'existe pas. Aucune etape du")
print("   corpus ne nomme un tel outil : les %d sont une action vide ou None, c'est a"
      % mal_steps)
print("   dire une malformation de la forme de l'appel. F1a n'est donc pas atteignable")
print("   comme diagnostic de choix d'outil, et le document ne le dit pas.")
out["rule1_reachability"] = dict(steps=steps, malformed_steps=mal_steps,
                                 steps_naming_a_nonexistent_tool=len(named))
assert not named, "une etape nomme un outil inexistant non vide : revoir la conclusion"

print()
print("=" * 78)
print("2. LES TRAJECTOIRES QUI PORTENT UNE MALFORMATION")
print()
with_mal = [r for r in corpus if malformed(r["trajectory"])]
rec = [r for r in with_mal
       if _recovers(r["trajectory"][malformed(r["trajectory"])[0] + 1:])]
labels = Counter(r["label_human"] for r in with_mal)
print("   trajectoires portant au moins une malformation          : %d" % len(with_mal))
print("   dont la premiere malformation est reprise               : %d" % len(rec))
print("   etiquetees F1 par la reference                          : %d"
      % sum(v for k, v in labels.items() if str(k).startswith("F1")))
print("   etiquettes que la reference leur donne                  : %s"
      % ", ".join("%s %d" % (k, v) for k, v in sorted(labels.items())))
out["trajectories_with_a_malformation"] = dict(
    n=len(with_mal), recovered=len(rec), labelled_F1=0, reference_labels=dict(labels))
assert len(with_mal) == 49 and len(rec) == 41, (len(with_mal), len(rec))
assert not any(str(k).startswith("F1") for k in labels)

print()
print("=" * 78)
print("3. CE QUE LA TABLE LUE A LA LETTRE DONNE SUR CES MEMES TRAJECTOIRES")
print()
print("   La regle 1 se declenche sur les %d, donc la table les etiquette toutes F1a."
      % len(with_mal))
print("   La reference n'en etiquette aucune F1. La contradiction porte donc sur")
print("   %d trajectoires sur %d, soit %d pour cent du corpus."
      % (len(with_mal), len(with_mal), round(100 * len(with_mal) / 200)))
print()
print("   Ce n'est pas une ambiguite de categorie, c'est un defaut de documentation : la")
print("   convention appliquee, qu'une malformation ne determine jamais l'etiquette,")
print("   n'etait ecrite nulle part dans la table remise au second lecteur.")
out["literal_table_contradiction"] = dict(
    trajectories=len(with_mal), share_of_corpus=round(len(with_mal) / 200, 3),
    table_label="F1a", reference_labels_F1=0)

print()
print("=" * 78)
print("4. CE QUE CETTE LECTURE COUTE SUR LE LOT DE 50, ET LE SENS DES DESACCORDS F1")
print()
key = {json.loads(l)["id"]: json.loads(l)["label_annotator1"] for l in
       io.open(os.path.join(ROOT, "annotation", "sample_key_DO_NOT_SHARE.jsonl"),
               encoding="utf-8") if l.strip()}
ref, lit = [], []
for tid, lab in key.items():
    ref.append(lab)
    lit.append("F1" if malformed(by_id[tid]["trajectory"]) else lab)
k, po, pe = kappa(ref, lit)
n_mal_50 = sum(1 for tid in key if malformed(by_id[tid]["trajectory"]))
print("   trajectoires du lot de 50 portant une malformation      : %d" % n_mal_50)
print("   plafond de la lecture litterale contre la reference, tout le reste etant")
print("   suppose en accord : accord brut %.3f, kappa %.3f" % (po, k))
out["literal_reading_ceiling_on_the_50"] = dict(
    with_a_malformation=n_mal_50, raw_agreement=round(po, 3), kappa=round(k, 3))

rows = list(csv.DictReader(io.open(os.path.join(ROOT, "annotation",
                                                "disagreements.csv"), encoding="utf-8")))
assert len(rows) == 27
f1 = [r for r in rows
      if r["annotator1"].startswith("F1") or r["annotator2"].startswith("F1")]
by2 = sum(1 for r in f1 if r["annotator2"].startswith("F1"))
by1 = sum(1 for r in f1 if r["annotator1"].startswith("F1"))
pairs = Counter("%s/%s" % (r["annotator1"], r["annotator2"]) for r in f1)
print()
print("   desaccords de la ronde reelle impliquant F1             : %d sur 27" % len(f1))
print("   F1 ecrit par le second lecteur                          : %d" % by2)
print("   F1 ecrit par le premier lecteur                         : %d" % by1)
print("   paires observees                                        : %s"
      % ", ".join("%s %d" % (k2, v) for k2, v in sorted(pairs.items())))
print()
print("   Les neuf sont donc a sens unique. Ce n'est pas du bruit symetrique entre deux")
print("   lecteurs hesitants : c'est un lecteur qui applique la table telle qu'elle est")
print("   ecrite et un autre qui applique la convention, sur chacun des neuf cas.")
out["F1_disagreements"] = dict(n=len(f1), written_by_annotator2=by2,
                              written_by_annotator1=by1, pairs=dict(pairs))
assert by2 == 9 and by1 == 0, (by2, by1)

res = os.path.join(ROOT, "results", "table_vs_reference.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
