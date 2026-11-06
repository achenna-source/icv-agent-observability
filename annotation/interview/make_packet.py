# -*- coding: utf-8 -*-
"""Le paquet autonome a remettre a chaque annotateur.

Un annotateur ne recoit pas l'artefact : il recoit un dossier qui se suffit a lui meme,
sans etiquette de reference, sans sortie de detecteur et sans le papier. Ce script le
construit et verifie qu'il ne contient rien de plus que ce qu'il doit contenir.

    python -I make_packet.py                   ecrit packet_annotateurs/, lettre a saisir
    python -I make_packet.py --letters A B C D  ecrit paquet_A/ ... paquet_D/

Pourquoi une variante par lettre. L'ordre de presentation est tire de la graine et de la
lettre, et le fichier de sortie porte la lettre. Une lettre mal saisie change donc l'ordre
et le nom du fichier, et le defaut ne se voit qu'a la reception. Dans un paquet nomme, la
lettre est inscrite dans le lanceur et l'annotateur n'a rien a saisir. Rien d'autre ne
change : le script verifie que tous les autres fichiers sont identiques octet pour octet a
ceux du paquet generique.
"""
import argparse
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)

FILES = (("interview.py", HERE), ("lancer_entretien.cmd", HERE),
         ("essai_3_items.cmd", HERE), ("INSTRUCTIONS_ANNOTATOR.md", HERE),
         ("sample_blind.jsonl", ANN), ("codebook_clarified_v3.md", ANN),
         ("knowledge_base_observed.json", os.path.join(ROOT, "data")))
FORBIDDEN = ("sample_key", "DO_NOT_SHARE", "label_annotator1", "label_human",
             "disagreements", "results", "reproduce")

# ce qui change dans un paquet nomme, et rien de plus
CMD_PROMPT = "set /p ANN=Votre lettre d'annotateur, A B C ou D, puis Entree :\necho.\n"
CMD_RUN = "python -I interview.py --annotator %ANN% --resume"
CMD_TAIL = ("echo Vous pouvez fermer cette fenetre. Pour reprendre plus tard, relancez "
            "ce fichier\necho avec la meme lettre.")
DOC_START = ("Double-click `lancer_entretien.cmd`, type\nthe letter you were given, and "
             "press Enter.")
DOC_RESUME = "Running the file again with the\nsame letter continues"
DOC_RETURN = "Return the single file `responses_<your letter>.jsonl`"


def empty(d):
    """Vide le dossier sans le supprimer.

    Une fenetre de commande ouverte dans le paquet verrouille le dossier lui meme sous
    Windows, et rmtree echoue alors sur le dernier rmdir. Vider le contenu suffit, et la
    reconstruction n'oblige pas l'annotateur a fermer sa fenetre.
    """
    held = [n for n in os.listdir(d) if n.startswith("responses_")]
    assert not held, (
        "%s contient les reponses d'un annotateur (%s) : reconstruction refusee, "
        "ces fichiers seraient perdus" % (d, " ".join(held)))
    for name in os.listdir(d):
        q = os.path.join(d, name)
        if os.path.isdir(q):
            shutil.rmtree(q)
        else:
            os.remove(q)


def named_launcher(letter):
    src = io.open(os.path.join(HERE, "lancer_entretien.cmd"), encoding="utf-8").read()
    for s in (CMD_PROMPT, CMD_RUN, CMD_TAIL):
        assert src.count(s) == 1, "le lanceur generique n'a plus la ligne %r" % s[:40]
    out = src.replace(CMD_PROMPT, "")
    out = out.replace(CMD_RUN, "python -I interview.py --annotator %s --resume" % letter)
    out = out.replace("title Annotation interview",
                      "title Annotation interview, annotateur %s" % letter)
    out = out.replace(CMD_TAIL,
                      "echo Vous pouvez fermer cette fenetre. Pour reprendre plus tard, "
                      "relancez ce\necho meme fichier : il repart ou vous en etiez.")
    assert "set /p" not in out, "le lanceur nomme demande encore une saisie"
    assert "--annotator %s --resume" % letter in out, out
    return out


def named_doc(letter):
    src = io.open(os.path.join(HERE, "INSTRUCTIONS_ANNOTATOR.md"),
                  encoding="utf-8").read()
    for s in (DOC_START, DOC_RESUME, DOC_RETURN):
        assert src.count(s) == 1, "les instructions n'ont plus la phrase attendue : %r" % s
    out = src.replace(
        DOC_START,
        "Double-click `lancer_entretien_%s.cmd`.\nYour letter, %s, is already set, so "
        "there is nothing to type." % (letter, letter))
    out = out.replace(DOC_RESUME, "Running the file again continues")
    out = out.replace(DOC_RETURN, "Return the single file `responses_%s.jsonl`" % letter)
    return out


def build(dst, letter=None):
    if os.path.exists(dst):
        empty(dst)
    os.makedirs(os.path.join(dst, "essai"), exist_ok=True)
    changed = set()
    for name, src in FILES:
        shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
    if letter:
        os.remove(os.path.join(dst, "lancer_entretien.cmd"))
        q = os.path.join(dst, "lancer_entretien_%s.cmd" % letter)
        io.open(q, "w", encoding="utf-8", newline="\r\n").write(named_launcher(letter))
        io.open(os.path.join(dst, "INSTRUCTIONS_ANNOTATOR.md"), "w",
                encoding="utf-8", newline="\n").write(named_doc(letter))
        changed = {"lancer_entretien.cmd", "lancer_entretien_%s.cmd" % letter,
                   "INSTRUCTIONS_ANNOTATOR.md"}
    shutil.copy2(os.path.join(HERE, "essai", "sample_essai.jsonl"),
                 os.path.join(dst, "essai", "sample_essai.jsonl"))

    # tout ce qui n'est pas la lettre est identique octet pour octet a la source
    same = 0
    for name, src in FILES:
        if name in changed:
            continue
        a = io.open(os.path.join(src, name), "rb").read()
        b = io.open(os.path.join(dst, name), "rb").read()
        assert a == b, "%s differe de sa source" % name
        same += 1

    rows = [json.loads(l) for l in
            io.open(os.path.join(dst, "sample_blind.jsonl"), encoding="utf-8")
            if l.strip()]
    keys = sorted({k for r in rows for k in r})
    assert keys == ["id", "task", "trajectory"], keys

    leaks = []
    for root, _, names in os.walk(dst):
        for n in names:
            q = os.path.join(root, n)
            if any(f in n for f in FORBIDDEN):
                leaks.append(n)
                continue
            if n.endswith((".md", ".jsonl", ".json", ".py", ".cmd")):
                txt = io.open(q, encoding="utf-8", errors="replace").read()
                for f in ("label_annotator1", "label_human", "DO_NOT_SHARE"):
                    if f in txt:
                        leaks.append("%s contient %s" % (n, f))
    assert not leaks, leaks

    n_files = sum(len(f) for _, _, f in os.walk(dst))
    print("  %-22s %d fichiers, %d identiques a la source, %d trajectoires, "
          "aucune etiquette" % (os.path.basename(dst), n_files, same, len(rows)))
    return dst


p = argparse.ArgumentParser()
p.add_argument("--letters", nargs="*", default=None,
               help="une lettre par annotateur, le lanceur la porte deja")
args = p.parse_args()

print()
if not args.letters:
    build(os.path.join(HERE, "packet_annotateurs"))
    print()
    print("Remettre ce dossier a chaque annotateur, avec sa lettre A, B, C ou D.")
else:
    for letter in args.letters:
        assert letter.isalnum() and len(letter) <= 4, letter
        build(os.path.join(HERE, "paquet_%s" % letter), letter)
    print()
    print("Un paquet par annotateur. La lettre est dans le lanceur, rien a saisir.")
