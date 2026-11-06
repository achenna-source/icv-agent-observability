# -*- coding: utf-8 -*-
"""codebook_clarified_v3.md : la clause corrigee, fondee sur l'ancrage et non sur l'argument.

Pourquoi une troisieme version. La version 2 disait qu'une valeur fabriquee est F2 quand
elle figure dans l'argument d'un appel et F3c quand elle ne figure que dans la reponse
finale. Quatre lecteurs independants l'ont appliquee, ronde 3 de llm_profile_panel. Elle
a repare les six trajectoires que la reference appelle F3 et casse les six qu'elle appelle
F2 : l'accord par categorie est passe de 0,467 a 0,733 sur F3 et de 1,000 a 0,000 sur F2,
et le kappa mis en commun a recule de 0,720 a 0,654.

La premisse etait fausse, et code/experiments/f2_f3_boundary.py le mesure sur les 200.
Aucune des 21 trajectoires que la reference appelle F2 ne porte un nombre inexistant dans
un argument de recherche. Les 15 qui en portent un sont etiquetees F3, F7, F5 et F6, et
jamais F2. Le critere de l'argument ne decrit donc pas F2 telle qu'elle a ete appliquee,
et le nom de la categorie, hallucination d'argument d'outil, ne la decrit pas non plus.

Ce qui separe reellement les deux familles est l'ancrage de la reponse finale. Parmi les
trajectoires dont la reponse affirme un nombre qu'aucune observation n'a rendu, les 25
dont une autre partie de la reponse reprend une valeur retrouvee sont etiquetees F3, les
25 sans exception. Celles dont la reponse n'est ancree sur rien se repartissent entre F2,
quand la valeur n'est pas calculee avec, et F7, quand elle l'est.

La clause ci-dessous dit cela, et seulement cela. Elle decrit la pratique de la reference
sans renommer F2 ni toucher au test du pivot, et la question de savoir si le nom de la
categorie doit changer reste ouverte, pour l'auteur.

La version 3 part de codebook_clarified.md, pas de la version 2 : elle en differe par une
seule clause, exactement comme la version 2, de sorte que la ronde 4 et la ronde 3 sont
deux variantes comparables de la meme ronde 2.

    python -I -X utf8 make_clarified_v3.py
"""
import difflib
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "codebook_clarified.md")
DST = os.path.join(HERE, "codebook_clarified_v3.md")

OLD = """**The pivot test requires a computation.** `F7` applies when a fabricated value is used
as an input to a computation whose result is the final answer. A fabricated value that is
merely reported, and not computed with, is `F2`. Where no value is fabricated at all and
the answer is simply wrong or incomplete, the label is `F3`. A fabrication that stays
inside a thought, never entering an argument and never reaching the final answer, is not
a fabricated datum under either rule."""

NEW = """**The pivot test requires a computation.** `F7` applies when a fabricated value is used
as an input to a computation whose result is the final answer. A fabricated value that is
merely reported, and not computed with, is `F2` when nothing else in the final answer is
grounded in a value the store returned, and `F3`, with the sub-code `F3c`, when the
answer also reports a value the store did return. What separates the two is how much of
the answer is invented. An answer built on nothing the store returned is a fabricated
answer. An answer that reports a retrieved fact and pads it with an invented one is a
partial answer, which is what `F3c` describes, and it stays `F3` however plausible the
invented part looks. Where no value is fabricated at all and the answer is simply wrong
or incomplete, the label is `F3`. A fabrication that stays inside a thought, never
entering an argument and never reaching the final answer, is not a fabricated datum
under either rule."""

src = io.open(SRC, encoding="utf-8").read()
assert src.count(OLD) == 1, "la convention du pivot ne se trouve pas une fois exactement"
dst = src.replace(OLD, NEW, 1)
assert src.replace(OLD, "") == dst.replace(NEW, ""), "une autre partie du fichier a change"

io.open(DST, "w", encoding="utf-8", newline="\n").write(dst)

print("ecrit : %s" % os.path.basename(DST))
print("  mots  : %d, soit %+d" % (len(dst.split()), len(NEW.split()) - len(OLD.split())))
print("  sha256 : %s" % hashlib.sha256(dst.encode("utf-8")).hexdigest()[:16])
print("  em dash : %d" % NEW.count("—"))
print()
print("la seule difference avec codebook_clarified.md :")
for line in difflib.unified_diff(src.splitlines(), dst.splitlines(),
                                 "codebook_clarified.md", "codebook_clarified_v3.md",
                                 lineterm="", n=1):
    print("  %s" % line)
