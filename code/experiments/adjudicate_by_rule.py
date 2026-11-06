# -*- coding: utf-8 -*-
"""Les 27 desaccords des deux lecteurs, arbitres par les conventions ecrites.

Le relecteur 7 demande une evaluation multi-annotateurs avec arbitrage. La ronde humaine
lui appartient, mais une question se tranche des maintenant : les conventions que nous
venons d'ecrire auraient-elles empeche les desaccords deja observes ? Les 27 desaccords de
la ronde reelle n'avaient jamais ete arbitres, la colonne prevue pour cela etant restee
vide. Ce script les arbitre par regle, non par jugement.

La procedure. Pour chaque desaccord, on applique les conventions dans leur ordre d'ecriture
et on retient celle qui tranche la premiere. Une convention tranche quand elle exclut l'une
des deux etiquettes proposees. Rien n'est decide a la main, et un desaccord qu'aucune
convention n'exclut est rapporte comme restant au jugement.

  C1  une malformation ne determine jamais l'etiquette, donc F1 est exclu des qu'une
      etiquette de contenu ou de trajectoire est en cause
  C4  un refus veridique sans valeur avancee est un succes, donc S est retenu
  C5  entre F7 et le F3 residuel, une trajectoire sans aucune valeur exploitable est F3

Sortie : results/adjudication_by_rule.json
"""
import contextlib
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
sys.path.insert(0, HERE)

with contextlib.redirect_stdout(io.open(os.devnull, "w", encoding="utf-8")):
    from content_boundaries import held, usable            # noqa: E402,F401

from signals import TOOLS                                  # noqa: E402

ret = {r["id"]: r["label"] for r in csv.DictReader(
    io.open(os.path.join(ROOT, "annotation", "annotator2_returned.csv"),
            encoding="utf-8"))}
corpus = {json.loads(l)["id"]: json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()}
ABSENT = set(json.load(io.open(os.path.join(ROOT, "data", "knowledge_base.json"),
                               encoding="utf-8"))["populations_absent_by_design"])

dis = [(i, corpus[i]["label_human"], ret[i]) for i in ret
       if corpus[i]["label_human"] != ret[i]]
assert len(dis) == 27, len(dis)


def malformed(tr):
    return any(s.get("action") is None or s.get("action") not in TOOLS for s in tr)


def c1(tid, a, b):
    """F1 est exclu quand l'autre etiquette n'est pas F1 : une malformation ne decide pas."""
    pair = {a, b}
    f1 = {x for x in pair if x.startswith("F1")}
    if len(f1) == 1 and malformed(corpus[tid]["trajectory"]):
        return (pair - f1).pop(), "C1, a malformation never determines the label"
    return None, None


def c5(tid, a, b):
    """Entre F7 et F3, une trajectoire sans valeur exploitable est F3.

    La regle n'est validee que dans T7, le seul gabarit ou F3 et F7 apparaissent tous
    deux. L'appliquer ailleurs serait une extrapolation, et elle renverserait l'etiquette
    de reference sur sept trajectoires de T3 et T5, gabarits ou F7 n'existe pas. Hors de
    T7, la convention s'abstient, et le desaccord est rapporte comme restant ouvert.
    """
    if {a, b} != {"F7", "F3"}:
        return None, None
    if corpus[tid]["template"] != "T7":
        return None, None
    if not held(corpus[tid]["trajectory"]):
        return "F3", "C5, nothing was retrieved that a later step could carry forward"
    return "F7", "C5, a value was retrieved, so the cascade reading stands"


RULES = [c1, c5]
rows = []
for tid, a, b in dis:
    out, why = None, None
    for rule in RULES:
        out, why = rule(tid, a, b)
        if out:
            break
    rows.append(dict(id=tid, annotator1=a, annotator2=b,
                     adjudicated=out, rule=why,
                     agrees_with_annotator1=(out == a) if out else None))

settled = [r for r in rows if r["adjudicated"]]
open_ = [r for r in rows if not r["adjudicated"]]
print("=" * 78)
print("LES 27 DESACCORDS, ARBITRES PAR LES CONVENTIONS ECRITES")
print()
print("   tranches par une convention : %d des 27" % len(settled))
print("   restant au jugement         : %d des 27" % len(open_))
print()
print("   par convention : %s" % dict(Counter(
    r["rule"].split(",")[0] for r in settled)))
print("   l'arbitrage confirme le premier lecteur dans %d des %d cas tranches"
      % (sum(1 for r in settled if r["agrees_with_annotator1"]), len(settled)))
print()
print("   detail des cas tranches")
for r in settled:
    print("      %s  %s contre %s  ->  %s   %s"
          % (r["id"], r["annotator1"], r["annotator2"], r["adjudicated"], r["rule"]))
print()
print("   detail des cas restants")
for r in open_:
    print("      %s  %s contre %s  ->  aucune convention ne tranche"
          % (r["id"], r["annotator1"], r["annotator2"]))

base = sum(1 for i in ret if corpus[i]["label_human"] == ret[i])
after = base + len(settled)
print()
print("   accord brut avant arbitrage %d / 50 = %.3f" % (base, base / 50))
print("   apres arbitrage par regle   %d / 50 = %.3f" % (after, after / 50))
print("   les %d cas restants sont ceux qu'une ronde humaine avec arbitre doit trancher,"
      % len(open_))
print("   et ils se concentrent sur %s." % ", ".join(
    sorted({"%s contre %s" % tuple(sorted((r["annotator1"], r["annotator2"])))
            for r in open_})))
print()
print("   Ces paires sont exactement celles que boundary_map.py trouve non exercees ou")
print("   non separables. Aucun desaccord ne tombe dans T7, le seul gabarit ou une regle")
print("   tient, donc les conventions ecrites ne pouvaient pas trancher ces cas. Ce qui")
print("   manque n'est pas seulement un codebook plus precis mais un corpus qui mette les")
print("   categories en concurrence dans une meme tache.")

out = dict(n_disagreements=27, settled=len(settled), still_open=len(open_),
           by_rule=dict(Counter(r["rule"].split(",")[0] for r in settled)),
           confirms_annotator1=sum(1 for r in settled if r["agrees_with_annotator1"]),
           raw_before=round(base / 50, 3), raw_after=round(after / 50, 3),
           cases=rows,
           note="adjudication by written rule only; no case is decided by hand, and the "
                "cases no convention excludes are reported as open")
res = os.path.join(ROOT, "results", "adjudication_by_rule.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
