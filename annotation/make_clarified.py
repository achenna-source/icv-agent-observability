# -*- coding: utf-8 -*-
"""Le codebook clarifie, pour la seconde manche du panel.

Le relecteur 7 demande de clarifier la convention de reprise et les frontieres entre F2,
F3, F6 et F7 AVANT de conduire une evaluation multi-annotateurs. La premiere manche est
donc la condition avant, et celle-ci la condition apres. La difference entre les deux est
exactement le texte ajoute ci-dessous, rien d'autre : memes 50 items, memes modeles, meme
consigne d'isolement.

Les quatre conventions ajoutees ne sont pas des reglages pour faire monter le kappa. Ce
sont les conventions que le premier annotateur a appliquees, que la Section III.A du
manuscrit revise enonce pour les deux premieres, et que le panel a identifiees comme
manquantes pour les deux autres. Le texte enonce des regles, jamais des reponses : aucun
effectif, aucune mention qu'une categorie serait vide, aucun identifiant d'item.

    python make_clarified.py
"""
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

SRC = r"C:\claude\panel_isolated"
DST = r"C:\claude\panel_isolated_clarified"
os.makedirs(DST, exist_ok=True)

ADDED = """

## Conventions that resolve the three recurring conflicts

The four rules below are part of the procedure. Apply them before the ordered checks
above, because they decide which fault the ordered checks are applied to.

**A malformed step never determines the label.** A step whose action names no registered
tool is a malformation: a defect in the form of the call, not a diagnosis of what the
agent was trying to do. It is *recovered* when some later step calls a registered tool
and some later step terminates with a non-empty final answer. Whether recovered or not,
a malformation never gives the trajectory its label. Set it aside and label the
trajectory on the first fault that is not a malformation. If no such fault exists and the
final answer is correct, the trajectory is `S`. If no such fault exists and the answer is
wrong, label it `F5` when the trajectory ends with sub-goals still open, and `F3`
otherwise.

**The first fault in time governs, not the first rule in the table.** Where two faults of
different kinds occur, the label comes from the one that occurs earliest in the
trajectory, and the ordered table then tells you which category that fault falls into.
The table orders the checks; it does not rank the faults.

**The pivot test requires a computation.** `F7` applies when a fabricated value is used
as an input to a computation whose result is the final answer. A fabricated value that is
merely reported, and not computed with, is `F2`. Where no value is fabricated at all and
the answer is simply wrong or incomplete, the label is `F3`. A fabrication that stays
inside a thought, never entering an argument and never reaching the final answer, is not
a fabricated datum under either rule.

**A truthful report of absence is a success.** Some tasks ask for information the
knowledge base does not hold. Where the store genuinely lacks it and the agent's final
answer says so without asserting any invented value, the trajectory is `S`. It is not
`F5`, because the sub-goal is closed rather than abandoned, and it is not `F3`, because
nothing was mishandled.
"""

src = os.path.join(SRC, "annotator2_instructions.md")
text = io.open(src, encoding="utf-8").read()
out = text.rstrip() + ADDED
io.open(os.path.join(DST, "annotator2_instructions.md"), "w", encoding="utf-8",
        newline="\n").write(out)
shutil.copy2(os.path.join(SRC, "sample_packet.md"),
             os.path.join(DST, "sample_packet.md"))

for bad in ("0.370", "0.477", "0.793", "kappa", "is empty", "F1 is", "t003", "t004",
            "49 ", "25 false"):
    assert bad not in ADDED, bad
print("dossier : %s" % DST)
print("instructions : %d mots avant, %d apres, ajout de %d mots"
      % (len(text.split()), len(out.split()), len(ADDED.split())))
print("quatre conventions ajoutees, aucune reponse, aucun effectif, aucun identifiant")
print("le paquet des 50 items est identique a la premiere manche : %s"
      % (io.open(os.path.join(DST, "sample_packet.md"), encoding="utf-8").read()
         == io.open(os.path.join(SRC, "sample_packet.md"), encoding="utf-8").read()))
