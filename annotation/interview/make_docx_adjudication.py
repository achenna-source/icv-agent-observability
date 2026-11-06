# -*- coding: utf-8 -*-
"""Le formulaire Word de l'arbitrage, aveugle a qui a produit quelle etiquette.

Ce que ce document doit garantir, et qu'il garantit par construction.

  Les lecteurs y figurent en positions Reader 1, Reader 2, et ainsi de suite, dans un
  ordre tire du hasard du systeme a chaque item. Un ordre fixe permettrait de suivre un
  lecteur d'un item au suivant meme sans les lettres, et une graine ecrite dans un script
  publie laisserait recalculer la correspondance.

  La correspondance entre positions et lettres est ecrite au moment ou le document est
  engendre, dans mapping_adjudication_DO_NOT_SHARE.json, et ne figure nulle part dans le
  document. Le script le verifie avant d'enregistrer.

  Les choix proposes sont exactement les etiquettes que les lecteurs ont ecrites sur cet
  item, plus u. Un arbitrage qui cree une categorie neuve est une troisieme annotation et
  non un arbitrage.

  Les etiquettes de reference n'entrent pas dans le document.

Les deux jeux d'etiquettes sont arbitres separement, le calcule et le libre, parce qu'ils
ne mesurent pas la meme chose : le calcule mesure le codebook, le libre est la grandeur
comparable a la ronde a la feuille.

    python -I make_docx_adjudication.py --adjudicator AC
"""
import argparse
import io
import json
import os
import random
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

import docx
from docx.shared import Pt, Cm, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import interview as IVM            # noqa: E402

ROSTER = ("A", "B", "C", "D", "E", "K")
SHUFFLE = random.SystemRandom()
SETS = (("computed", "computed_label", "the label the questions give"),
        ("free", "free_label", "the label the reader would assign on their own"))
MAPPING = os.path.join(HERE, "mapping_adjudication_DO_NOT_SHARE.json")


def p(doc, text="", size=10, bold=False, italic=False, mono=False, space=4):
    q = doc.add_paragraph()
    q.paragraph_format.space_after = Pt(space)
    r = q.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if mono:
        r.font.name = "Consolas"
    return q


def head(doc, text, level):
    h = doc.add_heading(text, level=level)
    for r in h.runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    return h


def load_roster():
    recs, aside = {}, []
    for name in sorted(os.listdir(HERE)):
        if not (name.startswith("responses_") and name.endswith(".jsonl")):
            continue
        w = name[len("responses_"):-len(".jsonl")]
        d = {}
        for line in io.open(os.path.join(HERE, name), encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                d[r["id"]] = r
        if w in ROSTER:
            recs[w] = d
        else:
            aside.append(w)
    for w in aside:
        print("  hors roster, ecarte de l'arbitrage : %s" % w)
    return recs


def render_trajectory(doc, row):
    p(doc, "TASK", size=9, bold=True, space=1)
    p(doc, row["task"], size=10, space=6)
    p(doc, "TRAJECTORY", size=9, bold=True, space=1)
    for k, s in enumerate(row["trajectory"], 1):
        p(doc, "Step %d." % k, size=9, bold=True, space=0)
        for field in ("thought", "action", "input", "observation"):
            v = s.get(field)
            p(doc, "    %-12s %s" % (field, "None" if v is None else str(v)),
              size=9, mono=True, space=0)
    last = row["trajectory"][-1]
    p(doc, "", size=6, space=0)
    p(doc, "FINAL ANSWER", size=9, bold=True, space=1)
    if last.get("action") == IVM.TERMINATOR:
        p(doc, "%s" % last.get("input"), size=10, space=6)
    else:
        p(doc, "none: the trajectory does not end with a %s step" % IVM.TERMINATOR,
          size=10, italic=True, space=6)


def readers_table(doc, shown):
    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    c = t.rows[0].cells
    for k, txt in enumerate(("reader", "label", "what they wrote")):
        c[k].paragraphs[0].add_run(txt).bold = True
    for k, (lab, note, conf) in enumerate(shown, 1):
        row = t.add_row().cells
        row[0].text = "Reader %d" % k
        row[1].text = lab
        row[2].text = note or ""
    for row in t.rows:
        for k, cell in enumerate(row.cells):
            cell.width = (Cm(2.2), Cm(2.0), Cm(12.4))[k]
            for q in cell.paragraphs:
                q.paragraph_format.space_after = Pt(1)
                for r in q.runs:
                    r.font.size = Pt(9)
    return t


def answer_table(doc, which, tid, choices):
    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    c = t.rows[0].cells
    c[0].paragraphs[0].add_run("ADJUDICATION %s %s" % (which, tid)).bold = True
    c[1].paragraphs[0].add_run("question").bold = True
    c[2].paragraphs[0].add_run("your answer").bold = True
    for key, text, allowed in (
            ("CHOICE", "Which label does the codebook give for this trajectory? Choose "
                       "one of the labels the readers wrote, or u if the codebook does "
                       "not settle it. An item left u stays at the readers' "
                       "disagreement and is never filled in",
             " / ".join(choices) + " / u"),
            ("WHY", "One line on why, for the record", "free text")):
        row = t.add_row().cells
        row[0].paragraphs[0].add_run("[%s]" % key).bold = True
        q = row[1].paragraphs[0]
        q.add_run(text)
        q.add_run("    (%s)" % allowed).italic = True
        row[2].text = ""
    for row in t.rows:
        for k, cell in enumerate(row.cells):
            cell.width = (Cm(3.4), Cm(10.6), Cm(2.6))[k]
            for q in cell.paragraphs:
                q.paragraph_format.space_after = Pt(1)
                for r in q.runs:
                    r.font.size = Pt(9)
    return t


ap = argparse.ArgumentParser()
ap.add_argument("--adjudicator", required=True)
ap.add_argument("--items", nargs="*", default=None,
                help="restreindre a ces trajectoires, par exemple les cas residuels "
                     "qu'un arbitre exterieur doit trancher")
ap.add_argument("--out", default=None)
a = ap.parse_args()

recs = load_roster()
assert len(recs) >= 2, "l'arbitrage demande au moins deux lecteurs, %d trouve(s)" % len(recs)
rows = {r["id"]: r for r in IVM.load_sample(os.path.join(ANN, "sample_blind.jsonl"))}
shared = sorted(set.intersection(*[set(d) for d in recs.values()]))

# La correspondance est nichee par arbitre : un second formulaire sur les memes items ne
# doit pas ecraser la trace d'aveuglement du premier. L'ancienne forme plate est migree
# une fois sous son arbitre, apres sauvegarde.
mapping = {}
if os.path.exists(MAPPING):
    mapping = json.load(io.open(MAPPING, encoding="utf-8"))
    if any(k in mapping for k in ("computed", "free")):
        shutil.copy2(MAPPING, MAPPING.replace(".json", "_avant_migration.json"))
        flat = {k: mapping.pop(k) for k in ("computed", "free") if k in mapping}
        prior = sorted(n[len("adjudication_"):].rsplit("_", 1)[0]
                       for n in os.listdir(HERE)
                       if n.startswith("adjudication_") and n.endswith(".jsonl"))
        owner = prior[0] if prior else "unknown"
        mapping[owner] = flat
        print("  correspondance migree sous l'arbitre %s" % owner)
mine = mapping.setdefault(a.adjudicator, {})

doc = docx.Document()
n = doc.styles["Normal"]
n.font.name = "Calibri"
n.font.size = Pt(10)
for s in doc.sections:
    s.top_margin = s.bottom_margin = Cm(1.8)
    s.left_margin = s.right_margin = Cm(2.0)

head(doc, "Adjudication form, adjudicator %s" % a.adjudicator, 0)
p(doc, "The readers below disagreed. You apply the same codebook they did and decide "
       "which label it gives. You are not told which reader is which, and the display "
       "order is drawn afresh for every item, so a reader cannot be followed from one "
       "item to the next.", space=8)
p(doc, "Choose among the labels the readers wrote. You cannot introduce a label none of "
       "them wrote: an adjudication that creates a new category is a third annotation, "
       "not an adjudication. Answer u when the codebook does not settle the item. An "
       "item left u stays at the readers' disagreement and is never filled in, which is "
       "a legitimate and informative outcome.", space=8)
p(doc, "You never see the reference labels. They are not in this document.", space=8)
p(doc, "Type your answer in the right-hand column of the row tagged [CHOICE], and a "
       "line of reasoning in [WHY]. Do not delete, reorder or add rows: the answers are "
       "read back by tag, by label set and by trajectory identifier.", space=8)

head(doc, "The ordered checks, in the codebook's own words", 1)
for k, (key, code, text, _) in enumerate(IVM.RULES, 1):
    q = doc.add_paragraph()
    q.paragraph_format.space_after = Pt(3)
    q.add_run("%d. %s   " % (k, code)).bold = True
    q.add_run(text)
p(doc, "", space=6)
p(doc, "If no check fires on the step in question, the label is the residual F3.",
  space=8)
head(doc, "The four conventions", 1)
for k in ("pivot", "absence", "earliest", "open"):
    p(doc, k.upper(), size=10, bold=True, space=1)
    p(doc, " ".join(IVM.HELP[k].split()), space=6)
doc.add_page_break()

total = 0
for which, field, desc in SETS:
    disputed = []
    for tid in shared:
        if a.items and tid not in a.items:
            continue
        labs = {w: recs[w][tid].get(field) for w in recs}
        if len({v for v in labs.values() if v}) > 1:
            disputed.append(tid)
    head(doc, "Part %s: %s" % (which.upper(), desc), 1)
    p(doc, "%d items on which the readers disagree." % len(disputed), italic=True,
      space=8)
    for pos, tid in enumerate(disputed, 1):
        order = list(recs)
        SHUFFLE.shuffle(order)
        mine.setdefault(which, {})[tid] = {"Reader %d" % (k + 1): w
                                              for k, w in enumerate(order)}
        shown = []
        for w in order:
            r = recs[w][tid]
            shown.append((r.get(field) or "undetermined",
                          (r.get("note") or "").strip(), r.get("confidence")))
        head(doc, "%s item %d of %d        %s" % (which, pos, len(disputed), tid), 2)
        render_trajectory(doc, rows[tid])
        p(doc, "THE READERS DISAGREE", size=9, bold=True, space=2)
        readers_table(doc, shown)
        p(doc, "", size=6, space=2)
        choices = sorted({l for l, _, _ in shown if l and l != "undetermined"})
        answer_table(doc, which, tid, choices)
        doc.add_page_break()
        total += 1
    print("  %-9s %d items en litige" % (which, len(disputed)))

out = a.out or os.path.join(HERE, "formulaire_arbitrage_%s.docx" % a.adjudicator)
doc.save(out)
io.open(MAPPING, "w", encoding="utf-8", newline="\n").write(
    json.dumps(mapping, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

# rien du document ne doit nommer un lecteur ni porter une etiquette de reference
d = docx.Document(out)
body = "\n".join(q.text for q in d.paragraphs)
for t in d.tables:
    for r in t.rows:
        body += "\n" + "\n".join(c.text for c in r.cells)
bad = [m for m in ("label_annotator1", "label_human", "DO_NOT_SHARE", "sample_key",
                   "kappa", "0.370") if m in body]
for w in recs:
    for pat in ("Reader 1 = %s" % w, "annotator %s" % w, "reader %s" % w,
                "lecteur %s" % w):
        if pat in body:
            bad.append(pat)
assert not bad, bad
anchors = sum(1 for t in d.tables
              if t.rows[0].cells[0].text.startswith("ADJUDICATION "))
assert anchors == total, (anchors, total)
print()
print("  %s" % out)
print("  %d items a arbitrer, %d tableaux de reponses" % (total, anchors))
print("  aucun lecteur nomme, aucune etiquette de reference, aucun resultat anterieur")
print("  la correspondance des positions est dans %s, jamais dans le document"
      % os.path.basename(MAPPING))
print("  em dash dans le document : %d" % body.count("—"))
