# -*- coding: utf-8 -*-
"""Le formulaire Word de la ronde humaine, et rien d'autre dedans.

Pourquoi un formulaire a cote de l'entretien en fenetre. Il se remplit hors ligne, il se
partage, il se reprend sans crainte de fermer une fenetre, et certains lecteurs vont plus
vite sur un document que dans un terminal. Les deux instruments posent les memes
questions dans le meme ordre, et l'etiquette est calculee de la meme facon.

Ce qui est garanti par construction, et non par relecture.

  Les sept controles, les quatre conventions et l'ordre de la table ne sont pas recopies
  ici : ils sont importes de interview.py, donc le formulaire ne peut pas deriver du
  codebook clarifie.

  Les etapes malformees de chaque trajectoire sont calculees par la fonction publiee et
  donnees au lecteur, parce que cette lecture est mecanique et que la convention dit
  qu'elles ne determinent jamais l'etiquette.

  L'ordre de presentation vient de la graine publiee et de la lettre, comme dans
  l'entretien, donc deux lecteurs ne voient jamais les items dans le meme ordre.

  La base de connaissances tient en 57 entrees : elle figure en entier dans le document,
  puisqu'il n'y a pas de commande kb sur un formulaire. C'est elle qui tranche la
  question la plus difficile, celle de savoir si une valeur etait retrouvable.

  Aucune etiquette de reference, aucune sortie de detecteur et aucun resultat anterieur
  n'entre dans le document, ce que le script verifie avant d'enregistrer.

Une difference assumee avec l'entretien. Sur un formulaire, l'ordre des controles ne peut
pas etre impose : les sept sont donc tous poses, et la regle publiee prend le premier oui
dans l'ordre de la table, ce qui donne exactement la meme etiquette. Les reponses aux
controles suivants sont conservees a part plutot que jetees.

    python -I make_docx_form.py --annotator A
"""
import argparse
import io
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)
sys.path.insert(0, HERE)
import interview as IVM            # noqa: E402

CATEGORIES = (
    ("S", "Success. The task is answered correctly, or the store genuinely lacks what "
          "the task asks for and the answer says so without asserting any invented "
          "value."),
    ("F1a", "Called a tool that does not exist in the registered tool set."),
    ("F1b", "Called an existing tool that does not fit the sub-goal."),
    ("F2", "A fabricated value reported but not computed with, in an answer grounded in "
           "nothing the store returned."),
    ("F3", "The residual category, defined by exclusion: a fault that none of the other "
           "checks describes. Sub-codes a, b and c below."),
    ("F4", "An equivalent step repeated without progress until the budget runs out."),
    ("F5", "Stopped, or an empty or None final answer, before finishing."),
    ("F6", "The final answer contradicts a value the agent itself produced earlier."),
    ("F7", "A fabricated value used as an input to a computation whose result is the "
           "final answer."),
)

JUDGMENT = (
    ("Tool fitness",
     "Unfit means a competent solver would not have chosen that tool for that sub-goal, "
     "not merely that a different tool would also have worked."),
    ("Semantic repetition",
     "Two steps are equivalent if they pursue the same sub-goal by the same means, even "
     "when the wording differs. A genuine follow-up query on the same entity is not a "
     "repetition."),
    ("The pivot test",
     "Would removing the invented value change the final answer, and did a computation "
     "carry it there?"),
)

ROWS = ([("Q1", "The final answer is correct with respect to the ground truth",
          "y / n / u")]
        + [("Q2", "The earliest step at which something went wrong, leaving aside the "
                  "malformed steps", "a step number, or 0 for none")]
        + [("Q2b", "Only if Q2 is 0 and Q1 is n: the trajectory ends with sub-goals "
                   "still open", "y / n / u")]
        + [(r[0], r[2], "y / n / u") for r in IVM.RULES]
        + [("Q4", "Only if the questions above give F3: a sub-code, if one is clear. "
                  "a = wrong calculation over correctly retrieved values, b = failed or "
                  "misdirected retrieval of a fact that was present, c = partial or "
                  "ungrounded answer, n = none of the three. On any other label this "
                  "question does not arise and the cell stays empty",
            "a / b / c / n, or empty"),
           ("Q5", "Independently of the questions, the single code you would assign on "
                  "your own", " ".join(IVM.FREE_LABELS)),
           ("NOTE", "One line: which step held the fault, or which two categories you "
                    "were torn between", "free text, may be left empty"),
           ("KB", "The knowledge base entries you looked up for this trajectory",
            "free text, may be left empty")])

LEAK = ("label_annotator1", "label_human", "label_judge", "DO_NOT_SHARE", "sample_key",
        "kappa", "0.370", "0.477", "0.601", "Fleiss", "detector", "confusion",
        "precision", "recall")


def style(doc):
    n = doc.styles["Normal"]
    n.font.name = "Calibri"
    n.font.size = Pt(10)
    n.paragraph_format.space_after = Pt(4)
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(1.8)
        s.left_margin = s.right_margin = Cm(2.0)


def p(doc, text="", size=10, bold=False, italic=False, mono=False, space=4,
      colour=None):
    q = doc.add_paragraph()
    q.paragraph_format.space_after = Pt(space)
    r = q.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if mono:
        r.font.name = "Consolas"
    if colour is not None:
        r.font.color.rgb = colour
    return q


def head(doc, text, level):
    h = doc.add_heading(text, level=level)
    for r in h.runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    return h


def kb_table(doc, kb):
    t = doc.add_table(rows=1, cols=2)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    c = t.rows[0].cells
    c[0].paragraphs[0].add_run("Query the store answered").bold = True
    c[1].paragraphs[0].add_run("What it returned").bold = True
    for k in sorted(kb):
        row = t.add_row().cells
        row[0].text = str(k)
        row[1].text = str(kb[k])
    for row in t.rows:
        for cell in row.cells:
            for q in cell.paragraphs:
                for r in q.runs:
                    r.font.size = Pt(9)
    return t


def answer_table(doc, tid, candidates):
    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    c = t.rows[0].cells
    c[0].paragraphs[0].add_run("ANSWERS %s" % tid).bold = True
    c[1].paragraphs[0].add_run("question").bold = True
    c[2].paragraphs[0].add_run("your answer").bold = True
    for key, text, allowed in ROWS:
        row = t.add_row().cells
        row[0].paragraphs[0].add_run("[%s]" % key).bold = True
        body = text
        if key == "Q2":
            body = ("%s. Available: %s, or 0. If you answer 0, the seven checks below "
                    "do not arise and their cells stay empty."
                    % (text, ", ".join(str(n) for n in candidates) or "none"))
        q = row[1].paragraphs[0]
        q.add_run(body)
        q.add_run("    (%s)" % allowed).italic = True
        row[2].text = ""
    for row in t.rows:
        for k, cell in enumerate(row.cells):
            cell.width = (Cm(1.6), Cm(12.4), Cm(2.6))[k]
            for q in cell.paragraphs:
                q.paragraph_format.space_after = Pt(1)
                for r in q.runs:
                    r.font.size = Pt(9)
    return t


def render_item(doc, row, pos, total, letter):
    mal = IVM.malformed_steps(row)
    nsteps = len(row["trajectory"])
    head(doc, "Item %d of %d        %s" % (pos, total, row["id"]), 2)
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
    if mal:
        p(doc, "MALFORMED STEPS: %s" % ", ".join("step %d" % n for n in mal),
          size=9, bold=True, space=1)
        p(doc, IVM.MALFORMED_NOTE.replace("\n", " ").replace("  ", " ").strip(),
          size=9, italic=True, space=6)
    else:
        p(doc, "No step fails to name a registered tool.", size=9, italic=True, space=6)
    answer_table(doc, row["id"], [n for n in range(1, nsteps + 1) if n not in mal])
    doc.add_page_break()


def build(letter, out, sample="sample_blind.jsonl",
          kb_name="knowledge_base_observed.json", corpus=None):
    """corpus : le nom de la dorsale, quand ce n'est pas celle de l'etude.

    Le second corpus se lit avec le meme codebook, les memes sept controles et la meme
    regle d'etiquette, puisqu'il porte les memes enonces : la verite de terrain de la
    question 1 est donc la meme. Seules deux choses changent, et elles doivent changer.
    Les trajectoires sont celles du second agent, et l'annexe de base observee est
    reconstruite sur son corpus, parce que cet agent n'a pas pose les memes requetes.
    """
    rows = IVM.load_sample(os.path.join(ANN, sample))
    kb = json.load(io.open(os.path.join(ROOT, "data", kb_name), encoding="utf-8"))
    order = list(range(len(rows)))
    random.Random("%d:%s" % (IVM.BASE_SEED, letter)).shuffle(order)
    seq = [rows[i] for i in order]

    doc = docx.Document()
    style(doc)
    head(doc, "Annotation form, annotator %s" % letter, 0)
    p(doc, "Fifty agent trajectories, to be labelled against the published codebook, "
           "for a study on how such agents fail. Your labels measure whether the "
           "labelling scheme is reproducible by someone other than its author.",
      space=8)
    p(doc, "Work alone. Do not discuss individual items with anyone until this file is "
           "returned, and do not try to guess what another annotator decided: a "
           "disagreement is informative, a forced match is not. Do not search the web "
           "for the study or its results.", space=8)
    p(doc, "About an hour and a half to two hours. The first items take much longer "
           "than the rest, so do not judge the pace by them. Split the work over two "
           "sittings if you prefer.", space=8)
    p(doc, "How to fill this in", bold=True, space=2)
    p(doc, "Each item ends with a table. Type your answer in the right-hand column, on "
           "the row whose left cell carries the matching tag. Write nothing else in "
           "that column, and do not delete, reorder or add rows: the answers are read "
           "back from those cells by tag and by trajectory identifier.", space=8)
    p(doc, "u for unsure is a real answer and a useful one. Use it whenever you "
           "hesitate rather than forcing a choice. An item left unsettled by the "
           "questions is recorded as unsettled and never filled in with a guess.",
      space=8)
    p(doc, "The seven checks of question 3 are asked in the order of the table below. "
           "A reader working in the terminal version is asked them one at a time and "
           "stops at the first yes. Here you answer all seven, and the label is "
           "computed from your answers by the published rule, which takes the first "
           "yes in that order. The label is therefore the same, and your answers to "
           "the later checks are kept as extra information.", space=8)
    p(doc, "The tasks and the trajectories are in French. The codebook and this form "
           "are in English.", space=8)
    if corpus:
        p(doc, "About these trajectories", bold=True, space=2)
        p(doc, "They come from a second agent, %s, run on the same fifty tasks as an "
               "earlier round. The tasks, the tool set, the step budget and the store "
               "are the same, so question 1 asks about the same correct answers and the "
               "codebook applies unchanged. The agent is not the same, and it behaves "
               "differently: it takes more steps, and it more often reaches the step "
               "budget without giving a final answer. Nothing follows from that for your "
               "reading. Label what you see, item by item, exactly as the rules below "
               "say." % corpus, space=8)
    doc.add_page_break()

    head(doc, "The nine categories", 1)
    for code, text in CATEGORIES:
        q = doc.add_paragraph()
        q.paragraph_format.space_after = Pt(3)
        q.add_run("%-4s " % code).bold = True
        q.add_run(text)
    doc.add_page_break()

    head(doc, "The ordered checks, in the codebook's own words", 1)
    p(doc, "This is the order question 3 follows, and the order the label rule uses.",
      italic=True, space=6)
    for k, (key, code, text, _) in enumerate(IVM.RULES, 1):
        q = doc.add_paragraph()
        q.paragraph_format.space_after = Pt(3)
        q.add_run("%d. [%s] %s   " % (k, key, code)).bold = True
        q.add_run(text)
    p(doc, "", space=6)
    p(doc, "If no check fires on the step you named, the label is the residual F3, "
           "which is defined by exclusion.", space=8)

    head(doc, "The four conventions", 1)
    for k in ("pivot", "absence", "earliest", "open"):
        p(doc, k.upper(), size=10, bold=True, space=1)
        p(doc, " ".join(IVM.HELP[k].split()), space=6)

    head(doc, "The three questions that need judgment", 1)
    p(doc, "Most checks are mechanical. These three need your judgment, and they are "
           "exactly the ones the study wants measured.", italic=True, space=6)
    for name, text in JUDGMENT:
        p(doc, name, bold=True, space=1)
        p(doc, text, space=6)
    doc.add_page_break()

    head(doc, "The knowledge base, in full", 1)
    p(doc, "Every query the agent's store ever answered, and what it returned. Any "
           "query not listed here returned nothing. This is what settles whether a "
           "value the agent asserted was retrieved or invented, which is the commonest "
           "hard call. The registered tool set is %s, and the step that ends a "
           "trajectory uses %s, which is the terminator and not a tool."
      % (" and ".join(IVM.REGISTERED), IVM.TERMINATOR), space=6)
    kb_table(doc, kb)
    doc.add_page_break()

    head(doc, "The fifty trajectories", 1)
    p(doc, "In your own presentation order, drawn from the published seed %d and your "
           "letter, so that two annotators never see the items in the same order."
      % IVM.BASE_SEED, italic=True, space=8)
    for pos, row in enumerate(seq, 1):
        render_item(doc, row, pos, len(seq), letter)

    doc.save(out)

    # rien du document ne doit porter une etiquette ni un resultat anterieur
    d = docx.Document(out)
    body = "\n".join(q.text for q in d.paragraphs)
    for t in d.tables:
        for r in t.rows:
            body += "\n" + "\n".join(c.text for c in r.cells)
    bad = [m for m in LEAK if m in body]
    assert not bad, bad
    tags = sum(1 for t in d.tables for r in t.rows
               if r.cells[0].text.strip().startswith("["))
    anchors = sum(1 for t in d.tables if t.rows[0].cells[0].text.startswith("ANSWERS "))
    print()
    print("  %s" % out)
    print("  %d items, %d tableaux de reponses, %d lignes a remplir, %d entrees de base"
          % (len(seq), anchors, tags, len(kb)))
    print("  aucune etiquette de reference, aucun resultat anterieur")
    print("  em dash dans le document : %d" % body.count("—"))
    assert anchors == len(seq), anchors
    assert tags == len(seq) * len(ROWS), tags


ap = argparse.ArgumentParser()
ap.add_argument("--annotator", required=True)
ap.add_argument("--out", default=None)
ap.add_argument("--sample", default="sample_blind.jsonl",
                help="le jeu d'items, dans annotation/")
ap.add_argument("--kb", default="knowledge_base_observed.json",
                help="l'annexe de base observee, dans data/")
ap.add_argument("--corpus", default=None,
                help="le nom de la dorsale, quand ce n'est pas celle de l'etude")
a = ap.parse_args()
assert (a.sample == "sample_blind.jsonl") == (a.kb == "knowledge_base_observed.json"), (
    "un corpus doit venir avec son annexe de base observee : le lecteur ne peut pas "
    "trancher ce qui etait retrouvable avec les requetes d'un autre agent")
assert (a.corpus is None) == (a.sample == "sample_blind.jsonl"), (
    "un second corpus doit etre nomme au lecteur, et le premier ne doit pas l'etre")
build(a.annotator, a.out or os.path.join(
    HERE, "formulaire_annotateur_%s.docx" % a.annotator),
    sample=a.sample, kb_name=a.kb, corpus=a.corpus)
