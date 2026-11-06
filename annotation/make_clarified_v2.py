# -*- coding: utf-8 -*-
"""codebook_clarified_v2.md : une seule clause ajoutee, celle qui manquait au test du pivot.

Pourquoi une version et non une correction sur place. codebook_clarified.md est
byte-identique au document deja remis au panel de modeles (../annotation/panel), a
l'agent profile de llm_annotators, et au paquet des annotateurs humains deja constitue.
verify_instrument.py verifie en plus chacune de ses conventions mot pour mot. Le modifier
sur place invaliderait des mesures deja prises. La version 2 laisse tout cela intact.

Ce qui manquait. La convention du pivot dit qu'une valeur fabriquee simplement rapportee,
et non calculee avec, est F2. Elle ne dit pas ou la valeur doit apparaitre. Or la
categorie visee est l'hallucination d'argument d'outil, et sur six trajectoires des
cinquante la fabrication est dans la reponse finale, ce que decrit le residuel F3c. Les
quatre lecteurs de la ronde 2 ont tous choisi F2 sur ces six, contre F3 pour la
reference. Le piege precis est que l'entree de finish est un argument au sens de la
trace, alors qu'elle est la reponse finale au sens de la tache : la clause le dit
maintenant.

Rien d'autre ne change. Les trois autres frontieres restees ouvertes, la tolerance
d'arrondi, le conflit entre premier defaut et test du pivot, et F6, sont laissees telles
quelles, pour que la ronde qui suit mesure cette clause seule.

    python -I -X utf8 make_clarified_v2.py
"""
import difflib
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "codebook_clarified.md")
DST = os.path.join(HERE, "codebook_clarified_v2.md")

OLD = """**The pivot test requires a computation.** `F7` applies when a fabricated value is used
as an input to a computation whose result is the final answer. A fabricated value that is
merely reported, and not computed with, is `F2`. Where no value is fabricated at all and
the answer is simply wrong or incomplete, the label is `F3`. A fabrication that stays
inside a thought, never entering an argument and never reaching the final answer, is not
a fabricated datum under either rule."""

NEW = """**The pivot test requires a computation.** `F7` applies when a fabricated value is used
as an input to a computation whose result is the final answer. A fabricated value that is
merely reported, and not computed with, is `F2` when it appears in the argument of a call
the agent made, and `F3`, with the sub-code `F3c`, when it appears only in the final
answer. What separates the two is where the invention enters the trajectory. `F2` is a
hallucinated argument, so the invented value has to sit in an argument the agent passed
to a tool, whereas an invented value that only ever reaches the final answer was passed
to nothing and leaves the answer ungrounded. The input of `finish` is the final answer
and not a tool argument, so a value invented there is `F3c` and not `F2`. Where no value
is fabricated at all and the answer is simply wrong or incomplete, the label is `F3`. A
fabrication that stays inside a thought, never entering an argument and never reaching
the final answer, is not a fabricated datum under either rule."""

src = io.open(SRC, encoding="utf-8").read()
assert src.count(OLD) == 1, "la convention du pivot ne se trouve pas une fois exactement"
dst = src.replace(OLD, NEW, 1)

# rien d'autre n'a bouge : hors ce paragraphe, les deux fichiers sont identiques
assert src.replace(OLD, "") == dst.replace(NEW, ""), "une autre partie du fichier a change"

io.open(DST, "w", encoding="utf-8", newline="\n").write(dst)

added = len(NEW.split()) - len(OLD.split())
print("ecrit : %s" % os.path.basename(DST))
print("  mots  : %d, soit %+d" % (len(dst.split()), added))
print("  sha256 v1 : %s" % hashlib.sha256(src.encode("utf-8")).hexdigest()[:16])
print("  sha256 v2 : %s" % hashlib.sha256(dst.encode("utf-8")).hexdigest()[:16])
print("  em dash   : %d" % (NEW.count("—")))
print()
print("la seule difference entre les deux versions :")
for line in difflib.unified_diff(src.splitlines(), dst.splitlines(),
                                 "codebook_clarified.md", "codebook_clarified_v2.md",
                                 lineterm="", n=1):
    print("  %s" % line)
