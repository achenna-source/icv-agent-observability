# -*- coding: utf-8 -*-
"""Ou se leve chaque drapeau, et est-ce avant la reponse finale.

Le commentaire 1 du relecteur 7 demande comment les definitions determinent les vrais et
les faux positifs. Un compte au niveau de la trajectoire n'y suffit pas : un drapeau leve
au pas 3 compte comme vrai positif meme si la faute qui a valu l'etiquette est ailleurs.
Mesurer la coincidence avec le pas fautif exige d'annoter l'indice de ce pas, qui n'est
pas dans les donnees. Ce qui est objectif et disponible tout de suite, c'est la position
du drapeau lui-meme.

  - le signal B renvoie l'indice de son premier pas fautif ;
  - le test de doublon du signal C se leve au second element de la premiere paire ;
  - le test de contradiction se leve par construction au pas terminal.

Sortie : results/flag_position.json. Aucune annotation nouvelle, aucun reetiquetage.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "code"))

from signals import tier1, tier1_exempt, tier2, _numbers     # noqa: E402

corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
hum = [r["label_human"] for r in corpus]
fail = [h != "S" for h in hum]

try:
    from sentence_transformers import SentenceTransformer
    enc = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except Exception as e:
    enc = None
    print("encodeur indisponible (%s)" % type(e).__name__)


def dup_index(tr, threshold=0.92):
    """Second element de la premiere paire qui depasse le seuil, sinon None."""
    if enc is None or len(tr) < 2:
        return None
    import numpy as np
    texts = ["%s %s %s" % (s.get("thought", ""), s.get("action", ""),
                           s.get("input", "")) for s in tr]
    e = enc.encode([t.strip() for t in texts], normalize_embeddings=True)
    best = None
    for i in range(len(e)):
        for j in range(i + 1, len(e)):
            if float(np.dot(e[i], e[j])) > threshold:
                if best is None or j < best:
                    best = j
    return best


rows = []
for r in corpus:
    tr = r["trajectory"]
    last = len(tr) - 1
    b_flag, b_at = tier1(tr)
    bx_flag, bx_at = tier1_exempt(tr)
    c_flag, dup, contra = tier2(tr, enc)
    c_at = None
    if dup:
        c_at = dup_index(tr)
    if contra and (c_at is None or last < c_at):
        c_at = last
    rows.append(dict(id=r["id"], label=r["label_human"], n_steps=len(tr),
                     terminal=last,
                     B=dict(flag=bool(b_flag), at=b_at),
                     Bx=dict(flag=bool(bx_flag), at=bx_at),
                     C=dict(flag=bool(c_flag), at=c_at, duplicate=bool(dup),
                            contradiction=bool(contra))))


def summarise(key, name):
    sel = [x for x in rows if x[key]["flag"]]
    tp = [x for x in sel if x["label"] != "S"]
    pre = [x for x in tp if x[key]["at"] is not None
           and x[key]["at"] < x["terminal"]]
    at_last = [x for x in tp if x[key]["at"] == x["terminal"]]
    med = sorted(x[key]["at"] for x in tp if x[key]["at"] is not None)
    print("%-26s drapeaux %3d | vrais positifs %3d | avant le pas terminal %3d "
          "(%.0f%%) | au pas terminal %3d | indice median %s"
          % (name, len(sel), len(tp), len(pre),
             100 * len(pre) / len(tp) if tp else 0, len(at_last),
             med[len(med) // 2] if med else "n/a"))
    return dict(flags=len(sel), true_positives=len(tp), before_terminal=len(pre),
                at_terminal=len(at_last),
                median_index=med[len(med) // 2] if med else None)


print("corpus de %d trajectoires, %d fautes sous la cible souple"
      % (len(rows), sum(fail)))
print()
out = {"n": len(rows), "failures_lenient": sum(fail), "signals": {}}
out["signals"]["B"] = summarise("B", "B, schema")
out["signals"]["Bx"] = summarise("Bx", "B*, schema with exemption")
out["signals"]["C"] = summarise("C", "C, consistency")

n_dup = sum(1 for x in rows if x["C"]["duplicate"])
n_con = sum(1 for x in rows if x["C"]["contradiction"])
out["C_components"] = {"duplicate": n_dup, "contradiction": n_con}
print()
print("dans le signal C : test de doublon %d, test de contradiction %d, "
      "ce dernier toujours au pas terminal par construction" % (n_dup, n_con))

res = os.path.join(ROOT, "results", "flag_position.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps({"summary": out, "per_trajectory": rows}, indent=2,
               ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
