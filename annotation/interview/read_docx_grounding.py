# -*- coding: utf-8 -*-
"""Relit un formulaire d'ancrage rempli et en tire le fichier de l'axe.

Il ne devine rien. Une cellule vide la ou la trajectoire porte une reponse finale est
signalee et rien n'est ecrit tant qu'il en reste une. Une reponse hors du jeu est refusee.
Une cellule remplie la ou la trajectoire n'a pas de reponse finale est signalee et
ignoree, puisque la question ne se posait pas.

L'issue par item est a quatre valeurs et aucune n'est comblee : ungrounded quand le
lecteur repond oui, grounded quand il repond non, unsure quand il hesite, et no_answer
quand la trajectoire n'emet pas de reponse finale, ce qui est une lecture mecanique et
non un jugement.

    python -I read_docx_grounding.py formulaire_ancrage_A_rempli.docx

Sortie : grounding_<annotateur>.jsonl
"""
import argparse
import io
import json
import os
import random
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

import docx

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)
sys.path.insert(0, HERE)
import interview as IVM            # noqa: E402

YN = {"y": "y", "yes": "y", "oui": "y", "o": "y",
      "n": "n", "no": "n", "non": "n",
      "u": "u", "unsure": "u", "incertain": "u", "?": "u"}
OUTCOME = {"y": "ungrounded", "n": "grounded", "u": "unsure"}

ROWS = [json.loads(l) for l in
        io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"), encoding="utf-8")
        if l.strip()]
BY = {r["id"]: r for r in ROWS}


def final(row):
    last = row["trajectory"][-1]
    if last.get("action") != IVM.TERMINATOR:
        return None
    s = str(last.get("input") or "").strip()
    return s if s and s != "None" else None


HAS = {r["id"]: final(r) is not None for r in ROWS}


def arith_only(row):
    """Une tache qui fournit ses propres operandes : l'axe ne s'y applique pas."""
    import unicodedata
    t = unicodedata.normalize("NFD", row["task"])
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    return re.search(r"combien font \d+\s+multipli", t) is not None


ARITH = {r["id"]: arith_only(r) for r in ROWS}

ap = argparse.ArgumentParser()
ap.add_argument("form")
ap.add_argument("--annotator", default=None)
ap.add_argument("--out", default=None)
a = ap.parse_args()

path = a.form if os.path.isabs(a.form) else os.path.join(HERE, a.form)
doc = docx.Document(path)
title = "\n".join(q.text for q in doc.paragraphs[:3])
m = re.search(r"Source grounding form, annotator (\S+)", title)
who = a.annotator or (m.group(1) if m else None)
if not who:
    print("  ECHEC : ce document ne porte pas le titre d'un formulaire d'ancrage.")
    sys.exit(1)

order = list(range(len(ROWS)))
random.Random("%d:grounding:%s" % (IVM.BASE_SEED, who)).shuffle(order)
want = [ROWS[i]["id"] for i in order]

tables = [t for t in doc.tables
          if t.rows and t.rows[0].cells[0].text.strip().startswith("GROUNDING ")]
if not tables:
    print("  ECHEC : aucun tableau de reponses dans %s" % os.path.basename(path))
    sys.exit(1)

hard, blank, soft, norm, recs, seen = [], [], [], [], [], []
for pos, t in enumerate(tables, 1):
    tid = t.rows[0].cells[0].text.strip()[len("GROUNDING "):].strip()
    seen.append(tid)
    if tid not in BY:
        hard.append("tableau %d : identifiant inconnu %r" % (pos, tid))
        continue
    got = {}
    for r in t.rows[1:]:
        tag = r.cells[0].text.strip().strip("[]")
        if tag:
            got[tag] = r.cells[2].text.strip()
    missing = [k for k in ("G1", "G2", "NOTE") if k not in got]
    if missing:
        hard.append("%s : lignes manquantes %s" % (tid, " ".join(missing)))
        continue
    v = got["G1"].strip().lower()
    if not HAS[tid] or ARITH[tid]:
        if v:
            soft.append("%s : G1 rempli alors que la question ne se posait pas, ignore"
                        % tid)
        out = "no_answer" if not HAS[tid] else "not_applicable"
        ans = None
    elif not v:
        blank.append(tid)
        continue
    elif v in YN:
        if v != YN[v]:
            norm.append("%s : %r lu %r" % (tid, got["G1"], YN[v]))
        ans = YN[v]
        out = OUTCOME[ans]
    else:
        hard.append("%s : G1=%r hors y n u" % (tid, got["G1"]))
        continue
    recs.append(dict(annotator=who, position=pos, id=tid, answer=ans, outcome=out,
                     value=got["G2"][:80] or None, note=got["NOTE"][:300],
                     instrument="docx-form", seconds=None))

print()
print("  formulaire d'ancrage de %s, %d tableaux lus" % (who, len(tables)))
dup = sorted({i for i in seen if seen.count(i) > 1})
absent = [i for i in want if i not in set(seen)]
if dup:
    hard.append("doublons : %s" % " ".join(dup[:5]))
if absent:
    hard.append("%d items absents : %s" % (len(absent), " ".join(absent[:8])))
if not dup and not absent and seen != want:
    k = next(j for j in range(len(seen)) if seen[j] != want[j])
    hard.append("l'ordre n'est pas celui de %s : tableau %d porte %s au lieu de %s"
                % (who, k + 1, seen[k], want[k]))
if norm:
    print("  %d reponse(s) normalisee(s)" % len(norm))
    for s in norm[:8]:
        print("      %s" % s)
for s in soft[:8]:
    print("  a regarder : %s" % s)
if blank:
    print()
    print("  %d item(s) sans reponse, rien n'est ecrit : %s"
          % (len(blank), " ".join(blank[:12])))
if hard:
    print()
    for h in hard[:12]:
        print("  ECHEC : %s" % h)
if blank or hard:
    print()
    print("  completez ou corrigez le document, puis relancez")
    sys.exit(1)

out = a.out or os.path.join(HERE, "grounding_%s.jsonl" % who)
assert not os.path.exists(out), "%s existe deja : deplacez-le avant d'ecrire" % out
with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
    for r in recs:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
c = Counter(r["outcome"] for r in recs)
print()
print("  %d items ecrits dans %s" % (len(recs), out))
print("  issues : %s" % "  ".join("%s %d" % (k, c[k]) for k in sorted(c)))
print("  lecture mecanique : %d sans reponse finale, %d purement arithmetiques"
      % (sum(1 for v in HAS.values() if not v),
         sum(1 for i, v in ARITH.items() if v and HAS[i])))
print("  items soumis a un jugement : %d"
      % sum(1 for r in recs if r["outcome"] not in ("no_answer", "not_applicable")))
print("  ensuite : un second lecteur, puis l'accord sur l'axe")
