# -*- coding: utf-8 -*-
"""Le formulaire Word de la ronde ToolBench, pour tester le transfert de la taxonomie.

CE QUE LE RELECTEUR 7 DEMANDE, ET CE QUE CETTE RONDE REPOND

« The external API audit supports aspects of schema checking, but does not validate
transfer of the taxonomy or task-level failure detection. » Il a raison : les trajectoires
ToolBench de la section VI.E n'ont jamais ete etiquetees. Cette ronde les etiquette, ce
qui teste la taxonomie sur un autre agent, un autre modele, un autre espace d'outils et
un autre environnement, sans aucun calcul.

L'echantillon de soixante existe deja, tire et stratifie par la campagne
icv-toolbench-sample, avec un sous-ensemble de vingt-cinq pour un second lecteur en
aveugle.

CE QUE LE CODEBOOK TOOLBENCH CHANGE, ET LE SEUL ENDROIT OU IL CHANGE

ToolBench ne porte aucune cle de verite : son evaluation propre passe par un juge modele
et non par une reponse de reference. La premiere question ne peut donc pas etre « la
reponse finale est-elle juste ». Elle devient « la reponse finale est-elle coherente avec
les observations que la trajectoire a obtenues », et S signifie ici aucune faute
observable a l'interface des actions et une reponse coherente avec ces observations. S ne
signifie pas que la reponse est correcte, et le formulaire le dit en tete.

Toutes les autres categories sont jugees comme avant, chacune etant definie par quelque
chose de visible dans la trace.

CE QUI EST DONNE AU LECTEUR PARCE QUE C'EST MECANIQUE

Le jeu d'outils enregistres de chaque tache, qui varie de deux a seize dans ToolBench,
et les etapes dont l'action ne nomme aucun de ces outils ni le terminateur. Sans cette
liste F1a ne serait pas jugeable, le jeu n'etant pas constant d'une tache a l'autre.

LA LIGNE AJOUTEE LE 6 NOVEMBRE 2026, AVANT QU'UN LECTEUR AIT COMMENCE

La regle publiee tranche le cas « aucune faute d'etape et reponse fautive » par la
convention des sous-buts ouverts : F5 si la trajectoire s'arrete en laissant une part de
la tache sans reponse, F3 sinon. Le formulaire enoncait cette convention dans sa page des
conventions sans porter la ligne pour y repondre, donc un item ou le lecteur ecrit Q2=0
et Q1=n n'etait pas calculable. La ligne Q2b est ajoutee, avec le meme libelle que le
formulaire de l'etude. Aucun lecteur n'avait commence, les identifiants, l'ordre et la
graine ne changent pas, et read_docx_toolbench.py lit les deux formes : sans la ligne, il
declare l'item indetermine plutot que de le combler.

CE QUI EST RETIRE

La strate d'echantillonnage. Elle porte des mentions du type « A gives up » ou « B schema
flag », qui nommeraient presque l'etiquette. Le fichier des vingt-cinq en aveugle l'avait
deja retiree, celui des soixante non, et le script la retire des deux.

    python -I make_docx_toolbench.py --annotator A
    python -I make_docx_toolbench.py --annotator B --blind
"""
import argparse
import io
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

import docx
from docx.shared import Pt, Cm, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)
REPO = os.path.dirname(ROOT)
SAMPLE = os.path.join(REPO, "kaggle", "icv-toolbench-sample", "out")
sys.path.insert(0, HERE)
import interview as IVM            # noqa: E402

TERMINATOR = "Finish"
SEED = 20261105
# Les valeurs de strate sont lues du fichier source et verifiees telles quelles. Les
# chercher par mots isoles serait faux : « gives up » et « repeats » sont les termes du
# codebook pour F5 et F4, donc ils doivent figurer dans les questions.
LEAK = ("stratum", "pool_index", "label_human", "DO_NOT_SHARE", "precision",
        "recall", "detector")

CATEGORIES = (
    ("S", "No observable fault at the action interface, and a final answer consistent "
          "with the observations this trajectory obtained. It does not mean the answer "
          "is correct: this corpus carries no reference answer."),
    ("F1a", "Called a tool that is not in this task's registered tool set."),
    ("F1b", "Called a registered tool that does not fit the sub-goal, when a better one "
            "was available in the same set."),
    ("F2", "A fabricated value reported but not computed with, in a final answer "
           "grounded in nothing the tools returned."),
    ("F3", "The residual category, defined by exclusion: a fault none of the other "
           "checks describes."),
    ("F4", "An equivalent step repeated without progress until the budget runs out."),
    ("F5", "Stopped, or gave up, or emitted an empty final answer, before finishing."),
    ("F6", "The final answer contradicts a value the agent itself obtained earlier."),
    ("F7", "A fabricated value used as an input to a computation whose result is the "
           "final answer."),
)

TAGS = (("Q1", "The final answer is consistent with the observations this trajectory "
               "obtained", "y / n / u"),
        ("Q2", "The earliest step at which something went wrong, leaving aside the "
               "malformed steps. Answer 0 for none", "a step number, or 0"),
        ("Q2b", "Only if Q2 is 0 and Q1 is n: the trajectory ends with sub-goals "
                 "still open", "y / n / u"),
        ("f1a", "The agent called a tool that is not in this task's registered set",
         "y / n / u"),
        ("f1b", "The agent called a registered tool that does not fit the sub-goal, when "
                "a better one was available", "y / n / u"),
        ("f2", "A fabricated value is merely reported, and nothing else in the final "
               "answer is grounded in a value a tool returned", "y / n / u"),
        ("f4", "The agent repeats an equivalent step without progress until the budget "
               "runs out", "y / n / u"),
        ("f5", "The agent stops, gives up, or emits an empty final answer, before "
               "finishing", "y / n / u"),
        ("f6", "The final answer contradicts a value the agent itself obtained earlier",
         "y / n / u"),
        ("f7", "A fabricated value is used as an input to a computation whose result is "
               "the final answer", "y / n / u"),
        ("Q4", "An F3 sub-code, only if the questions above give F3. a = wrong "
               "calculation over correctly obtained values, b = failed or misdirected "
               "retrieval of something the tools could return, c = partial or ungrounded "
               "answer, n = none of the three",
         "a / b / c / n, or empty"),
        ("Q5", "Independently of the questions, the single code you would assign on your "
               "own", "S F1a F1b F2 F3 F4 F5 F6 F7"),
        ("NOTE", "One line, or empty: which step held the fault, or which two categories "
                 "you were torn between", "free text"))


def load(blind):
    name = "toolbench_blind_25.jsonl" if blind else "toolbench_60.jsonl"
    q = os.path.join(SAMPLE, name)
    assert os.path.exists(q), "echantillon absent : %s" % q
    rows = [json.loads(l) for l in io.open(q, encoding="utf-8") if l.strip()]
    for r in rows:
        r.pop("stratum", None)
        r.pop("pool_index", None)
    return rows


def malformed(row):
    """Mecanique : une action qui ne nomme ni un outil enregistre de cette tache ni le
    terminateur."""
    ok = set(row["tools"]) | {TERMINATOR}
    return [k for k, s in enumerate(row["steps"], 1) if s.get("action") not in ok]


def final(row):
    last = row["steps"][-1]
    if last.get("action") != TERMINATOR:
        return None, "no Finish step"
    raw = str(last.get("input") or "")
    try:
        d = json.loads(raw)
    except ValueError:
        return raw.strip() or None, "unparsed Finish input"
    if d.get("return_type") == "give_up_and_restart":
        return None, "gave up"
    return (d.get("final_answer") or "").strip() or None, "gave answer"


def p(doc, text="", size=10, bold=False, italic=False, mono=False, space=4):
    q = doc.add_paragraph()
    q.paragraph_format.space_after = Pt(space)
    r = q.add_run(text)
    r.font.size = Pt(size)
    r.bold, r.italic = bold, italic
    if mono:
        r.font.name = "Consolas"
    return q


def head(doc, text, level):
    h = doc.add_heading(text, level=level)
    for r in h.runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    return h


def answer_table(doc, aid, cands):
    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    c = t.rows[0].cells
    c[0].paragraphs[0].add_run("ANSWERS %s" % aid).bold = True
    c[1].paragraphs[0].add_run("question").bold = True
    c[2].paragraphs[0].add_run("your answer").bold = True
    for key, text, allowed in TAGS:
        row = t.add_row().cells
        row[0].paragraphs[0].add_run("[%s]" % key).bold = True
        body = text
        if key == "Q2":
            body = "%s. Available: %s, or 0. If you answer 0, the seven checks below do " \
                   "not arise and their cells stay empty." % (
                       text, ", ".join(str(n) for n in cands) or "none")
        q = row[1].paragraphs[0]
        q.add_run(body)
        q.add_run("    (%s)" % allowed).italic = True
        row[2].text = ""
    for row in t.rows:
        for k, cell in enumerate(row.cells):
            cell.width = (Cm(1.8), Cm(12.2), Cm(2.6))[k]
            for q in cell.paragraphs:
                q.paragraph_format.space_after = Pt(1)
                for r in q.runs:
                    r.font.size = Pt(9)
    return t


ap = argparse.ArgumentParser()
ap.add_argument("--annotator", required=True)
ap.add_argument("--blind", action="store_true",
                help="le sous-ensemble de 25 pour un second lecteur")
ap.add_argument("--out", default=None)
a = ap.parse_args()

rows = load(a.blind)
order = list(range(len(rows)))
random.Random("%d:toolbench:%s" % (SEED, a.annotator)).shuffle(order)
seq = [rows[i] for i in order]

doc = docx.Document()
n = doc.styles["Normal"]
n.font.name = "Calibri"
n.font.size = Pt(10)
for s in doc.sections:
    s.top_margin = s.bottom_margin = Cm(1.8)
    s.left_margin = s.right_margin = Cm(2.0)

head(doc, "ToolBench annotation form, annotator %s" % a.annotator, 0)
p(doc, "%d agent trajectories from a corpus we did not build, to be labelled with the "
       "same taxonomy as the study's own corpus. Your labels test whether the taxonomy "
       "transfers to another agent, another model and another tool surface." % len(seq),
  space=8)
p(doc, "Work alone, and do not discuss individual items with anyone until this file is "
       "returned. Do not search the web for the study or for this corpus.", space=8)
p(doc, "About two hours for sixty items, less for twenty-five. The first items take far "
       "longer than the rest.", space=8)
p(doc, "One thing differs from the study's own corpus, and it changes one category",
  bold=True, space=2)
p(doc, "This corpus carries no reference answer: its own evaluation uses a model judge "
       "rather than a key. So the first question is not whether the final answer is "
       "correct, which nobody here can check, but whether it is consistent with the "
       "observations this trajectory obtained. S therefore means no observable fault at "
       "the action interface and an answer consistent with those observations. It does "
       "not mean the answer is right. A trajectory that retrieves nothing useful, invents "
       "nothing, contradicts nothing and then answers plausibly from memory is S here.",
  space=8)
p(doc, "Every other category is judged exactly as in the study's codebook, because each "
       "is defined by something visible in the trace.", space=8)
p(doc, "What is given to you mechanically", bold=True, space=2)
p(doc, "The registered tool set of each task, which varies from one task to the next in "
       "this corpus, and the steps whose action names none of those tools and is not the "
       "terminator. Without that list the first check would not be answerable, since the "
       "tool set is not constant here. The terminator is %s, and it may either give an "
       "answer or give up." % TERMINATOR, space=8)
p(doc, "One category has no instance in this corpus, and you should know it now",
  bold=True, space=2)
p(doc, "Every action in all %d trajectories names a tool that is in its own task's "
       "registered set, and none is empty. We checked this mechanically. So the first "
       "check, a call to a tool that does not exist, is answered no everywhere, and the "
       "convention that a malformed step never determines the label never applies here. "
       "You are still asked the check, because its being empty on this corpus is itself "
       "a measurement, but do not spend time hunting for a case. F1b, a registered tool "
       "that does not fit the sub-goal, remains available and is a judgment call."
  % len(seq), space=8)
p(doc, "How to fill this in", bold=True, space=2)
p(doc, "Type your answer in the right-hand column of the row carrying the matching tag. "
       "Do not delete, reorder or add rows: the answers are read back by tag and by "
       "trajectory identifier. u for unsure is a real answer, and the seven checks are "
       "asked about the step you name in Q2.", space=8)
p(doc, "Items are in your own order, drawn from the published seed %d and your letter."
  % SEED, italic=True, space=8)
doc.add_page_break()

head(doc, "The nine categories", 1)
for code, text in CATEGORIES:
    q = doc.add_paragraph()
    q.paragraph_format.space_after = Pt(3)
    q.add_run("%-4s " % code).bold = True
    q.add_run(text)
doc.add_page_break()

head(doc, "The four conventions", 1)
for k in ("pivot", "absence", "earliest", "open"):
    p(doc, k.upper(), size=10, bold=True, space=1)
    p(doc, " ".join(IVM.HELP[k].split()), space=6)
p(doc, "Read ABSENCE with the change above in mind: here a truthful report that the tools "
       "returned nothing usable is S, and correctness of the answer is not at issue.",
  italic=True, space=8)
doc.add_page_break()

n_mal = n_gaveup = n_noans = 0
for pos, row in enumerate(seq, 1):
    mal = malformed(row)
    ans, how = final(row)
    n_mal += 1 if mal else 0
    n_gaveup += 1 if how == "gave up" else 0
    n_noans += 1 if ans is None else 0
    head(doc, "Item %d of %d        %s" % (pos, len(seq), row["aid"]), 2)
    p(doc, "TASK", size=9, bold=True, space=1)
    p(doc, row["task"], size=10, space=6)
    p(doc, "REGISTERED TOOLS FOR THIS TASK (%d)" % len(row["tools"]), size=9, bold=True,
      space=1)
    p(doc, ", ".join(row["tools"]), size=9, mono=True, space=6)
    p(doc, "TRAJECTORY", size=9, bold=True, space=1)
    for k, s in enumerate(row["steps"], 1):
        p(doc, "Step %d." % k, size=9, bold=True, space=0)
        for field in ("thought", "action", "input", "observation"):
            v = s.get(field)
            p(doc, "    %-12s %s" % (field, "None" if v is None else
                                     " ".join(str(v).split())[:700]),
              size=9, mono=True, space=0)
    p(doc, "", size=6, space=0)
    p(doc, "FINAL ANSWER", size=9, bold=True, space=1)
    p(doc, ans if ans is not None else "none: the trajectory %s" % how,
      size=10, italic=(ans is None), space=6)
    if mal:
        p(doc, "MALFORMED STEPS: %s" % ", ".join("step %d" % x for x in mal),
          size=9, bold=True, space=1)
        p(doc, " ".join(IVM.MALFORMED_NOTE.split()), size=9, italic=True, space=6)
    else:
        p(doc, "No step names anything outside this task's tool set.", size=9,
          italic=True, space=6)
    answer_table(doc, row["aid"], [x for x in range(1, len(row["steps"]) + 1)
                                   if x not in mal])
    doc.add_page_break()

out = a.out or os.path.join(
    HERE, "formulaire_toolbench_%s%s.docx" % (a.annotator, "_blind25" if a.blind else ""))
doc.save(out)

d = docx.Document(out)
body = "\n".join(q.text for q in d.paragraphs)
for t in d.tables:
    for r in t.rows:
        body += "\n" + "\n".join(c.text for c in r.cells)
bad = [m for m in LEAK if m.lower() in body.lower()]
STRATA = sorted({r.get("stratum") for r in
                 (json.loads(l) for l in
                  io.open(os.path.join(SAMPLE, "toolbench_60.jsonl"), encoding="utf-8")
                  if l.strip())} - {None})
bad += [t for t in STRATA if t in body]
assert not bad, bad
print("  strates du corpus, absentes du document : %s" % " ; ".join(STRATA))
anchors = sum(1 for t in d.tables if t.rows[0].cells[0].text.startswith("ANSWERS "))
assert anchors == len(seq), (anchors, len(seq))
print()
print("  %s" % out)
print("  %d trajectoires, %d tableaux, %d avec au moins une etape malformee"
      % (len(seq), anchors, n_mal))
print("  %d abandonnent, %d sans reponse finale exploitable" % (n_gaveup, n_noans))
print("  strate et index de tirage retires, aucune etiquette, aucune sortie de detecteur")
print("  em dash dans le document : %d" % body.count("—"))
