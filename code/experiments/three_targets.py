# -*- coding: utf-8 -*-
"""Les memes detecteurs scores contre quatre cibles, pour le commentaire 1 du relecteur 7.

Le relecteur demande que le resultat final, les violations de procede et la reprise soient
definis separement, puis que l'on dise comment ces definitions determinent les vrais et
les faux positifs. La reponse n'est pas une definition de plus : c'est que le meme
detecteur, inchange, change de verdict selon la cible qu'on lui donne.

Quatre cibles sur les memes 200 trajectoires et les memes drapeaux.

  lenient    l'etiquette du codebook, une faute est tout ce qui n'est pas S.          128
  strict     la meme chose, plus les malformations reprises etiquetees S.             153
  step       les seules categories definies par un pas intermediaire, donc sans
             F3c, reponse partielle ou non etayee, ni F6, qui se juge sur la
             reponse finale.                                                           87
  outcome    la reponse finale est fausse, le procede ne compte pas.                  119

Deux precautions que le calcul impose.

  1. La cible stricte est l'union de la cible souple et des malformations reprises
     etiquetees S. Or ces trajectoires sont exactement les faux positifs du signal B
     contre la cible souple. La precision de B et de B ou C contre la cible stricte vaut
     donc 1,000 par construction et non par mesure. Elle est imprimee avec la mention
     ANALYTIQUE. Ce qui reste une mesure, ce sont les rappels, dont le denominateur
     change, et tous les chiffres du signal C, dont les tests ne portent pas sur la
     condition de malformation.
  2. La cible stricte est construite depuis les donnees, non depuis la sortie du
     detecteur : presence d'un pas ne nommant aucun outil enregistre, reprise au sens de
     _recovers, etiquette S. L'identite avec les faux positifs de B est verifiee, pas
     supposee.

Rien n'est reetiquete : seules les cibles changent. Les drapeaux viennent de signals.py,
les resultats de success_checker.py, tous deux publies au tag.

Sortie : results/three_targets.json, plus un tableau lisible.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "code"))
sys.path.insert(0, HERE)

from metrics import mcc, wilson_clustered                      # noqa: E402
from signals import TOOLS, tier1, tier1_exempt, tier2, _recovers   # noqa: E402
import success_checker as sc                                   # noqa: E402

corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
assert len(corpus) == 200, len(corpus)
hum = [r["label_human"] for r in corpus]
sub = [r.get("label_f3_subcode") for r in corpus]
clusters = [r["cluster_id"] for r in corpus]

try:
    from sentence_transformers import SentenceTransformer
    enc = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except Exception as e:
    enc = None
    print("encodeur indisponible (%s) : le test de doublon ne tournera pas"
          % type(e).__name__)

B = [tier1(r["trajectory"])[0] for r in corpus]
Bx = [tier1_exempt(r["trajectory"])[0] for r in corpus]
C = [tier2(r["trajectory"], enc)[0] for r in corpus]
BorC = [a or b for a, b in zip(B, C)]
BxorC = [a or b for a, b in zip(Bx, C)]


def unregistered(tr):
    """La trajectoire contient-elle un pas ne nommant aucun outil enregistre."""
    return any(st.get("action") is None or st.get("action") not in TOOLS
               for st in tr)


def recovered(tr):
    """La premiere malformation de ce genre est-elle reprise."""
    for k, st in enumerate(tr):
        if st.get("action") is None or st.get("action") not in TOOLS:
            return _recovers(tr[k + 1:])
    return False


lenient = [h != "S" for h in hum]
recovered_s = [unregistered(r["trajectory"]) and recovered(r["trajectory"])
               and hum[i] == "S" for i, r in enumerate(corpus)]
strict = [a or b for a, b in zip(lenient, recovered_s)]
ANSWER_LEVEL = [hum[i] == "F6" or sub[i] == "F3c" for i in range(200)]
step = [lenient[i] and not ANSWER_LEVEL[i] for i in range(200)]

store = sc.load_store()
wrong = [not sc.succeeded(r["task"], r["trajectory"], store)[0] for r in corpus]

print("effectifs : lenient %d | strict %d | step %d | outcome %d"
      % (sum(lenient), sum(strict), sum(step), sum(wrong)))
assert sum(lenient) == 128 and sum(strict) == 153 and sum(wrong) == 119
assert sum(step) == 128 - 34 - 7, sum(step)
assert sum(recovered_s) == 25, sum(recovered_s)

# la circularite, verifiee et non supposee
fp_b = sorted(i for i in range(200) if B[i] and not lenient[i])
assert fp_b == sorted(i for i in range(200) if recovered_s[i]), "identite non verifiee"
print("les %d faux positifs de B contre la cible souple sont exactement les "
      "malformations reprises etiquetees S : la precision de B contre la cible "
      "stricte est analytique" % len(fp_b))

SIGNALS = [("B, schema", B), ("B*, schema with exemption", Bx),
           ("C, consistency", C), ("B or C", BorC), ("B* or C", BxorC)]
TARGETS = [("lenient", lenient), ("strict", strict), ("step-level", step),
           ("outcome", wrong)]
ANALYTIC = {("B, schema", "strict"), ("B or C", "strict")}

out = {"counts": {"n": 200, "lenient": sum(lenient), "strict": sum(strict),
                  "step_level": sum(step), "outcome": sum(wrong)},
       "notes": {
           "strict_precision_is_analytic":
               "The strict target is the lenient target widened by exactly the "
               "trajectories B flags and the lenient target forgives, so the precision "
               "of B and of B or C against it is 1.000 by construction. Their recalls "
               "and all of signal C's figures remain measurements.",
           "step_level":
               "Failures whose category is defined by an intermediate step, that is "
               "the lenient target without F6 and without the F3c sub-code, partial or "
               "ungrounded answer, both of which are judged on the final answer.",
           "form_defects": {
               "any_of_the_four_schema_components": 62,
               "step_naming_no_registered_tool": 49,
               "recovered_among_those_49": 41,
               "labelled_S_among_those_41": 25,
               "missing_or_empty_argument": 10,
               "unparseable_calculator_expression": 4,
               "empty_final_answer": 11,
               "carrying_F1": 0}},
       "rows": []}

print()
print("%-26s %-11s %4s %4s %6s %6s %6s %7s %-16s %s"
      % ("signal", "cible", "TP", "FP", "prec", "rec", "F1", "MCC", "IC95 prec", ""))
for sname, flags in SIGNALS:
    for tname, target in TARGETS:
        tp = sum(1 for i in range(200) if flags[i] and target[i])
        fp = sum(1 for i in range(200) if flags[i] and not target[i])
        nf, ns = sum(target), 200 - sum(target)
        pre = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / nf if nf else 0.0
        f1 = 2 * pre * rec / (pre + rec) if pre + rec else 0.0
        m = mcc(tp, fp, nf - tp, ns - fp)
        n_flag = sum(flags)
        lo, hi = wilson_clustered(tp, n_flag,
                                  [clusters[i] for i in range(200) if flags[i]]) \
            if n_flag else (0.0, 0.0)
        tag = "ANALYTIQUE" if (sname, tname) in ANALYTIC else ""
        out["rows"].append(dict(signal=sname, target=tname, tp=tp, fp=fp,
                                precision=round(pre, 3), recall=round(rec, 3),
                                f1=round(f1, 3), mcc=round(m, 3),
                                precision_ci=[round(lo, 3), round(hi, 3)],
                                precision_analytic=bool(tag)))
        print("%-26s %-11s %4d %4d %6.3f %6.3f %6.3f %7.3f [%.3f, %.3f]   %s"
              % (sname, tname, tp, fp, pre, rec, f1, m, lo, hi, tag))

res = os.path.join(ROOT, "results", "three_targets.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)


def cell(sig, tgt, key):
    return next(r[key] for r in out["rows"] if r["signal"] == sig
                and r["target"] == tgt)


print()
print("controle contre les valeurs publiees :")
ok = True
for sig, tgt, key, paper in [
        ("B, schema", "lenient", "precision", 0.597),
        ("B, schema", "lenient", "recall", 0.289),
        ("B or C", "lenient", "precision", 0.731),
        ("B or C", "lenient", "recall", 0.531),
        ("B, schema", "strict", "precision", 1.000),
        ("B, schema", "strict", "recall", 0.405),
        ("B or C", "strict", "precision", 1.000),
        ("B or C", "strict", "recall", 0.608)]:
    got = cell(sig, tgt, key)
    good = abs(got - paper) < 0.002
    ok &= good
    print("   %-10s %-8s %-9s calcule %.3f   papier %.3f   %s"
          % (sig[:10], tgt, key, got, paper, "OK" if good else "ECART"))
print()
print("TOUT CONCORDE" if ok else "ECART")
