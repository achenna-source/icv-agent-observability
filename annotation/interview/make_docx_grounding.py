# -*- coding: utf-8 -*-
"""Le formulaire Word de l'axe d'ancrage des sources, pour des lecteurs humains.

POURQUOI CET AXE, ET POURQUOI IL AVAIT DISPARU

Le papier distinguait l'ancrage des sources de la justesse de la reponse finale, et en
tirait une mesure. Cette mesure reposait sur des annotations produites par des modeles de
langue, et elle est sortie du manuscrit. L'axe lui meme reste utile : les etiquettes
publiees ne le separent qu'a l'interieur de F3, par le sous code F3c.

POURQUOI LES 200 ET NON LES 128 ECHECS

Un formulaire qui contient exactement les 128 echecs apprend au lecteur que ces
trajectoires sont celles que la reference appelle des echecs, et il suffit qu'il le
remarque pour que son jugement en soit informe. Sur les 200 il n'y a rien a inferer,
l'axe devient disponible pour tout le corpus, et les detecteurs peuvent y etre notes sans
restreindre le corpus aux echecs.

CE QUE LE LECTEUR RECOIT, ET CE QU'IL NE RECOIT PAS

Il recoit la tache, la trajectoire entiere avec ce que chaque etape a renvoye, la reponse
finale, et la lecture mecanique des valeurs numeriques que les observations de cette
trajectoire ont effectivement rendues. Cette derniere est mecanique et lui est donnee, de
meme que les etapes malformees le sont dans l'autre formulaire.

Il ne recoit ni etiquette de reference, ni sous code F3c, ni sortie de detecteur, ni le
papier. Le script le verifie avant d'enregistrer.

LA QUESTION, UNE SEULE

La reponse finale avance-t-elle une valeur numerique qu'aucune observation de cette
trajectoire n'a rendue ? L'absence de reponse finale est mecanique et le formulaire la
marque lui meme, sans rien demander.

    python -I make_docx_grounding.py --annotator A
"""
import argparse
import io
import json
import os
import random
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

import docx
from docx.shared import Pt, Cm, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)
sys.path.insert(0, HERE)
import interview as IVM            # noqa: E402

ROWS = [json.loads(l) for l in
        io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"), encoding="utf-8")
        if l.strip()]
LEAK = ("label_human", "label_judge", "label_f3_subcode", "F3c", "sample_key",
        "DO_NOT_SHARE", "precision", "recall", "detector")

ROWS_TAGS = (("G1", "The final answer asserts a numeric value that no observation in "
                    "this trajectory returned", "y / n / u"),
             ("G2", "If you answered y, which value. If not, leave empty",
              "a number, or empty"),
             ("NOTE", "One line, or empty: what made the call hard",
              "free text, may be left empty"))


def fold(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def numbers(text):
    t = fold(text)
    out = set()
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:millions?|m\b)", t):
        try:
            out.add(int(round(float(m.group(1).replace(",", ".")) * 1_000_000)))
        except ValueError:
            pass
    t = re.sub(r"(?<=\d)[   ](?=\d{3}(?!\d))", "", t)
    for m in re.finditer(r"\d+", t):
        out.add(int(m.group()))
    return out


def observed(row):
    out = set()
    for s in row["trajectory"]:
        ob = s.get("observation")
        if ob not in (None, "Information non trouvee", "Information non trouvée"):
            out |= numbers(ob)
    return sorted(v for v in out if v >= 1000)


def arith_only(row):
    """Une tache qui fournit ses propres operandes n'a rien a quoi etre ancree.

    Le premier lecteur a juge deux de ces taches non ancrees, et il avait raison au mot
    pres : la question admettait l'arithmetique sur les valeurs observees et se taisait
    sur celles que l'enonce fournit. L'axe ne s'y applique pas, et le formulaire le dit
    au lieu de demander un jugement qui n'a pas d'objet.
    """
    return re.search(r"combien font \d+\s+multipli", fold(row["task"])) is not None


def final(row):
    last = row["trajectory"][-1]
    if last.get("action") != IVM.TERMINATOR:
        return None
    s = str(last.get("input") or "").strip()
    return s if s and s != "None" else None


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


def answer_table(doc, tid, skip):
    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    c = t.rows[0].cells
    c[0].paragraphs[0].add_run("GROUNDING %s" % tid).bold = True
    c[1].paragraphs[0].add_run("question").bold = True
    c[2].paragraphs[0].add_run("your answer").bold = True
    for key, text, allowed in ROWS_TAGS:
        row = t.add_row().cells
        row[0].paragraphs[0].add_run("[%s]" % key).bold = True
        q = row[1].paragraphs[0]
        if skip and key == "G1":
            q.add_run(skip).italic = True
            allowed = "leave empty"
        else:
            q.add_run(text)
        q.add_run("    (%s)" % allowed).italic = True
        row[2].text = ""
    for row in t.rows:
        for k, cell in enumerate(row.cells):
            cell.width = (Cm(3.0), Cm(11.0), Cm(2.6))[k]
            for q in cell.paragraphs:
                q.paragraph_format.space_after = Pt(1)
                for r in q.runs:
                    r.font.size = Pt(9)
    return t


ap = argparse.ArgumentParser()
ap.add_argument("--annotator", required=True)
ap.add_argument("--out", default=None)
a = ap.parse_args()

order = list(range(len(ROWS)))
random.Random("%d:grounding:%s" % (IVM.BASE_SEED, a.annotator)).shuffle(order)
seq = [ROWS[i] for i in order]

doc = docx.Document()
n = doc.styles["Normal"]
n.font.name = "Calibri"
n.font.size = Pt(10)
for s in doc.sections:
    s.top_margin = s.bottom_margin = Cm(1.8)
    s.left_margin = s.right_margin = Cm(2.0)

head(doc, "Source grounding form, annotator %s" % a.annotator, 0)
p(doc, "One question per trajectory, on %d agent trajectories. You decide whether the "
       "final answer asserts a number that nothing the trajectory retrieved can account "
       "for." % len(seq), space=8)
p(doc, "Work alone, and do not discuss individual items with anyone until this file is "
       "returned. Do not search the web for the study or its results.", space=8)
p(doc, "About an hour. The first items take longer than the rest.", space=8)
p(doc, "What the question means", bold=True, space=2)
p(doc, "For each trajectory you see the task, every step with what it returned, the final "
       "answer, and the list of numeric values the observations of that trajectory "
       "actually returned. That list is read mechanically and is given to you. Your "
       "judgment is whether the final answer puts forward a number that nothing accounts "
       "for. A number is accounted for when it is in that list, when the arithmetic the "
       "task calls for produces it from that list, or when the task statement itself "
       "supplies it, a divisor or a multiplier named in the task included.",
  space=8)
p(doc, "Answer y when at least one number in the final answer is unaccounted for, n when "
       "every number in it is accounted for, and u when you cannot tell. A trajectory "
       "that emits no final answer is marked as such by the form and asks nothing: leave "
       "its row empty.", space=8)
p(doc, "The tasks and the trajectories are in French. This form is in English.", space=8)
p(doc, "How to fill this in", bold=True, space=2)
p(doc, "Type your answer in the right-hand column of the row tagged [G1]. Do not delete, "
       "reorder or add rows: the answers are read back by tag and by trajectory "
       "identifier. [G2] and [NOTE] may be left empty.", space=8)
p(doc, "Items are in your own order, drawn from the published seed %d and your letter, "
       "so two annotators never see them in the same order." % IVM.BASE_SEED,
  italic=True, space=8)
doc.add_page_break()

n_empty = n_arith = 0
for pos, row in enumerate(seq, 1):
    ans = final(row)
    obs = observed(row)
    if ans is None:
        n_empty += 1
    elif arith_only(row):
        n_arith += 1
    head(doc, "Item %d of %d        %s" % (pos, len(seq), row["id"]), 2)
    p(doc, "TASK", size=9, bold=True, space=1)
    p(doc, row["task"], size=10, space=6)
    p(doc, "TRAJECTORY", size=9, bold=True, space=1)
    for k, s in enumerate(row["trajectory"], 1):
        p(doc, "Step %d." % k, size=9, bold=True, space=0)
        for field in ("thought", "action", "input", "observation"):
            v = s.get(field)
            p(doc, "    %-12s %s" % (field, "None" if v is None else str(v)),
              size=9, mono=True, space=0)
    p(doc, "", size=6, space=0)
    p(doc, "FINAL ANSWER", size=9, bold=True, space=1)
    p(doc, ans if ans is not None else
      "none: this trajectory does not end with a %s step carrying an answer"
      % IVM.TERMINATOR, size=10, italic=(ans is None), space=6)
    p(doc, "NUMBERS THE OBSERVATIONS RETURNED", size=9, bold=True, space=1)
    p(doc, (", ".join(str(v) for v in obs) if obs else
            "none: no observation of this trajectory returned a number"),
      size=9, mono=True, space=6)
    skip = None
    if ans is None:
        skip = ("This trajectory emits no final answer, which is read mechanically. "
                "Leave this row empty.")
    elif arith_only(row):
        skip = ("This task supplies its own operands in its statement, so there is "
                "nothing retrieved for the answer to be grounded in. The axis does not "
                "apply here. Leave this row empty.")
    answer_table(doc, row["id"], skip)
    doc.add_page_break()

out = a.out or os.path.join(HERE, "formulaire_ancrage_%s.docx" % a.annotator)
doc.save(out)

d = docx.Document(out)
body = "\n".join(q.text for q in d.paragraphs)
for t in d.tables:
    for r in t.rows:
        body += "\n" + "\n".join(c.text for c in r.cells)
bad = [m for m in LEAK if m in body]
assert not bad, bad
anchors = sum(1 for t in d.tables if t.rows[0].cells[0].text.startswith("GROUNDING "))
assert anchors == len(seq), (anchors, len(seq))
print()
print("  %s" % out)
print("  %d trajectoires, %d tableaux, %d sans reponse finale, %d purement "
      "arithmetiques" % (len(seq), anchors, n_empty, n_arith))
print("  items soumis a un jugement : %d" % (len(seq) - n_empty - n_arith))
print("  aucune etiquette de reference, aucun sous code F3c, aucune sortie de detecteur")
print("  em dash dans le document : %d" % body.count("—"))
