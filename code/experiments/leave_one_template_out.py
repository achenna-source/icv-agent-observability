# -*- coding: utf-8 -*-
"""Les signaux separent-ils des fautes, ou seulement des gabarits ?

La question vient du confondu trouve en repondant au relecteur 7 : chaque categorie de
faute n'apparait que dans un gabarit ou deux. Si l'etiquette est predictible depuis le
gabarit, un detecteur peut sembler marcher en ne lisant que le gabarit. Le papier doit
repondre avant qu'on le lui demande.

Deux mesures, toutes deux lues des 200 trajectoires publiees.

  1. Un temoin de gabarit. On attribue a chaque trajectoire l'etiquette binaire majoritaire
     de son gabarit, apres avoir retire la trajectoire elle-meme. C'est le detecteur qui ne
     lit que le gabarit. Son score borne ce que l'identite du gabarit explique a elle seule.

  2. Le detecteur, gabarit par gabarit, en laissant un gabarit dehors. Les signaux de ce
     papier n'ont aucun parametre appris, donc il n'y a rien a reentrainer : la mesure
     consiste a rapporter la precision et le rappel dans chaque gabarit pris a part. Si le
     detecteur ne marchait que par le gabarit, ses scores a l'interieur d'un gabarit
     tomberaient au niveau du hasard, l'identite du gabarit y etant constante.

Sortie : results/leave_one_template_out.json
"""
import io
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "code"))

from signals import tier1, tier1_exempt, tier2                 # noqa: E402

corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
assert len(corpus) == 200
for r in corpus:
    r["failed"] = r["label_human"] != "S"


def mcc(tp, fp, fn, tn):
    num = tp * tn - fp * fn
    den = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    return num / den if den else 0.0


def score(rows, fire):
    tp = sum(1 for r in rows if fire(r) and r["failed"])
    fp = sum(1 for r in rows if fire(r) and not r["failed"])
    fn = sum(1 for r in rows if not fire(r) and r["failed"])
    tn = sum(1 for r in rows if not fire(r) and not r["failed"])
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return dict(tp=tp, fp=fp, fn=fn, tn=tn,
                precision=round(prec, 3) if tp + fp else None,
                recall=round(rec, 3) if tp + fn else None,
                mcc=round(mcc(tp, fp, fn, tn), 3))


print("=" * 78)
print("1. LE TEMOIN DE GABARIT : CE QUE L'IDENTITE DU GABARIT EXPLIQUE A ELLE SEULE")
print()
by_t = {}
for r in corpus:
    by_t.setdefault(r["template"], []).append(r)
hit = 0
for r in corpus:
    others = [o for o in by_t[r["template"]] if o is not r]
    maj = Counter(o["failed"] for o in others).most_common(1)[0][0]
    hit += (maj == r["failed"])
base = max(sum(1 for r in corpus if r["failed"]),
           sum(1 for r in corpus if not r["failed"])) / 200
print("   le gabarit seul, en laissant chaque trajectoire dehors : %d / 200 = %.3f"
      % (hit, hit / 200))
print("   la classe majoritaire du corpus entier                 : %.3f" % base)
print("   l'identite du gabarit explique donc une grande part de l'etiquette binaire,")
print("   ce qui est la raison de mesurer les signaux a l'interieur des gabarits.")

print()
print("=" * 78)
print("2. LES SIGNAUX A L'INTERIEUR DE CHAQUE GABARIT")
print()
print("   Les signaux n'ont aucun parametre appris : rien n'est reentraine, et le gabarit")
print("   est constant dans chaque bloc, donc il ne peut pas porter la decision.")
print()
# tier1 et tier2 rendent un tuple dont le premier element est le drapeau. Les appeler
# sans l'indice rend un tuple toujours vrai, ce qui ferait croire que les signaux se
# declenchent partout.
try:
    from sentence_transformers import SentenceTransformer
    ENC = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except Exception as e:                                          # noqa: BLE001
    ENC = None
    print("   encodeur indisponible (%s) : le signal C tourne sans le test de doublon,"
          % type(e).__name__)
    print("   comme reproduce.py le fait dans le meme cas.")
    print()

DET = {"B, schema validation": lambda r: tier1(r["trajectory"])[0],
       "B*, schema with the recovery exemption":
           lambda r: tier1_exempt(r["trajectory"])[0],
       "C, consistency": lambda r: tier2(r["trajectory"], ENC)[0],
       "B or C": lambda r: tier1(r["trajectory"])[0] or tier2(r["trajectory"], ENC)[0],
       "B* or C": lambda r: (tier1_exempt(r["trajectory"])[0]
                            or tier2(r["trajectory"], ENC)[0])}
out = {"template_only_control": dict(accuracy=round(hit / 200, 3),
                                     corpus_majority=round(base, 3)),
       "within_template": {}, "pooled": {}}
for name, fire in DET.items():
    print("   %s" % name)
    pooled = score(corpus, fire)
    out["pooled"][name] = pooled
    print("      tout le corpus : precision %s  rappel %s  MCC %s"
          % (pooled["precision"], pooled["recall"], pooled["mcc"]))
    per = {}
    for t in sorted(by_t):
        s = score(by_t[t], fire)
        per[t] = s
        nf = sum(1 for r in by_t[t] if r["failed"])
        print("      %s  n=25 echecs=%-2d  precision %-6s rappel %-6s MCC %-7s"
              % (t, nf, s["precision"], s["recall"], s["mcc"]))
    out["within_template"][name] = per
    usable = [s for s in per.values() if s["precision"] is not None]
    if usable:
        mean_p = sum(s["precision"] for s in usable) / len(usable)
        print("      precision moyenne sur les %d gabarits ou le signal se declenche : %.3f"
              % (len(usable), mean_p))
        out["within_template"][name + " :: mean_precision_where_firing"] = round(mean_p, 3)
    print()

res = os.path.join(ROOT, "results", "leave_one_template_out.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("ecrit : %s" % res)
