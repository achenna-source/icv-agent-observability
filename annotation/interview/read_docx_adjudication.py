# -*- coding: utf-8 -*-
"""Relit le formulaire d'arbitrage rempli et ecrit les fichiers que l'analyse attend.

Il ne devine rien. Un choix hors des etiquettes que les lecteurs ont ecrites est refuse,
parce qu'un arbitrage qui cree une categorie neuve est une troisieme annotation. Une
cellule vide est signalee et rien n'est ecrit tant qu'il en reste une. Un item repondu u
reste indecis, et son etiquette arbitree est nulle : il n'est jamais comble.

Les etiquettes vues sont relues du tableau des lecteurs de chaque item, dans l'ordre
anonyme du document, donc le fichier produit garde ce que l'arbitre a reellement eu sous
les yeux. La correspondance avec les lettres reste dans
mapping_adjudication_DO_NOT_SHARE.json, que ce script ne lit pas.

    python -I read_docx_adjudication.py formulaire_arbitrage_AC.docx

Sorties : adjudication_<arbitre>_computed.jsonl et adjudication_<arbitre>_free.jsonl
"""
import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

import docx

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("form")
ap.add_argument("--adjudicator", default=None)
a = ap.parse_args()

path = a.form if os.path.isabs(a.form) else os.path.join(HERE, a.form)
doc = docx.Document(path)
title = "\n".join(q.text for q in doc.paragraphs[:3])
m = re.search(r"Adjudication form, adjudicator (\S+)", title)
who = a.adjudicator or (m.group(1) if m else None)
if not who:
    print("  ECHEC : ce document ne porte pas le titre d'un formulaire d'arbitrage,")
    print("  et aucun arbitre n'a ete donne par --adjudicator.")
    sys.exit(1)

out, hard, blank = {}, [], []
seen_labels, n_tables = None, 0
for t in doc.tables:
    first = t.rows[0].cells[0].text.strip()
    if first.lower() == "reader":
        seen_labels = [r.cells[1].text.strip() for r in t.rows[1:]]
        continue
    if not first.startswith("ADJUDICATION "):
        continue
    n_tables += 1
    parts = first.split()
    if len(parts) != 3:
        hard.append("en-tete de tableau illisible : %r" % first)
        continue
    which, tid = parts[1], parts[2]
    if seen_labels is None:
        hard.append("%s %s : aucun tableau de lecteurs avant ce tableau"
                    % (which, tid))
        continue
    got = {}
    for r in t.rows[1:]:
        tag = r.cells[0].text.strip().strip("[]")
        if tag:
            got[tag] = r.cells[2].text.strip()
    if sorted(got) != ["CHOICE", "WHY"]:
        hard.append("%s %s : lignes attendues CHOICE et WHY, trouvees %s"
                    % (which, tid, " ".join(sorted(got)) or "aucune"))
        continue
    choices = sorted({l for l in seen_labels if l and l != "undetermined"})
    v = got["CHOICE"].strip()
    if not v:
        blank.append("%s %s" % (which, tid))
        continue
    hit = [c for c in choices if c.lower() == v.lower()]
    if v.lower() == "u":
        lab, und = None, True
    elif hit:
        lab, und = hit[0], False
        if hit[0] != v:
            print("  %s %s : %r lu %s" % (which, tid, v, hit[0]))
    else:
        hard.append("%s %s : %r n'est pas une etiquette que les lecteurs ont ecrite "
                    "(%s) ni u" % (which, tid, v, " ".join(choices)))
        continue
    out.setdefault(which, []).append(dict(
        id=tid, which=which, adjudicator=who, labels_seen=seen_labels,
        adjudicated_label=lab, undecided=und, rationale=got["WHY"][:400],
        seconds=None, instrument="docx-form"))

print()
print("  formulaire d'arbitrage de %s, %d tableaux lus" % (who, n_tables))
if blank:
    print()
    print("  %d item(s) sans reponse, rien n'est ecrit :" % len(blank))
    for b in blank[:15]:
        print("      %s" % b)
if hard:
    print()
    for h in hard[:15]:
        print("  ECHEC : %s" % h)
if blank or hard:
    print()
    print("  completez ou corrigez le document, puis relancez")
    sys.exit(1)

for which, recs in sorted(out.items()):
    q = os.path.join(HERE, "adjudication_%s_%s.jsonl" % (who, which))
    assert not os.path.exists(q), (
        "%s existe deja : deplacez-le avant d'ecrire, pour ne pas melanger deux "
        "arbitrages" % q)
    with io.open(q, "w", encoding="utf-8", newline="\n") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    und = [r["id"] for r in recs if r["undecided"]]
    print("  %-9s %d items ecrits dans %s" % (which, len(recs), os.path.basename(q)))
    if und:
        print("            %d laisse(s) indecis, jamais comble(s) : %s"
              % (len(und), " ".join(und)))
print()
print("  ensuite : python -I adjudication_agreement.py")
