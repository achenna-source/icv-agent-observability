# -*- coding: utf-8 -*-
"""Relit un formulaire Word rempli et en tire le fichier de reponses de la ronde humaine.

Ce que le script ne fait pas. Il ne devine aucune reponse, il ne comble aucune cellule
vide, et il ne choisit aucune etiquette. L'etiquette est calculee par la regle publiee,
importee de interview.py, a partir des reponses ecrites dans le document. Un item
incomplet est signale et laisse de cote, jamais rempli.

Ce qu'il tolere, en le disant. Une reponse peut etre ecrite oui, non, yes, no, unsure, Y,
N, U ou dans une autre casse, et une etape peut etre ecrite 2, etape 2 ou step 2. Chaque
normalisation appliquee est comptee et affichee, pour qu'aucune lecture ne soit
silencieuse.

Ce qu'il refuse. Un document qui n'est pas un formulaire de cette ronde, un identifiant
inconnu, un ordre qui n'est pas celui de la lettre, une reponse hors du jeu, une etape
designee qui est malformee ou qui n'existe pas, et une ligne de tableau ajoutee,
supprimee ou renommee.

Pourquoi la duree est nulle. Un formulaire ne mesure pas le temps par item, et y ecrire
un nombre serait une invention. Le champ reste nul et chaque enregistrement porte
instrument = docx-form, que reception.py reconnait pour cette seule raison.

    python -I read_docx_form.py formulaire_annotateur_A.docx
    python -I read_docx_form.py formulaire_annotateur_A.docx --out responses_A.jsonl
"""
import argparse
import io
import json
import os
import random
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

import docx

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import interview as IVM            # noqa: E402

YN = {"y": "y", "yes": "y", "oui": "y", "o": "y",
      "n": "n", "no": "n", "non": "n",
      "u": "u", "unsure": "u", "incertain": "u", "?": "u"}
SUB = {"a": "F3a", "b": "F3b", "c": "F3c", "n": None, "none": None, "aucun": None}
KEYS7 = [r[0] for r in IVM.RULES]
TAGS = ["Q1", "Q2", "Q2b"] + KEYS7 + ["Q4", "Q5", "NOTE", "KB"]


def label_from(step, correct, opened, checks):
    """La regle publiee, pilotee par l'ordre des controles de interview.py."""
    if step == 0:
        if correct == "y":
            return "S", False
        if correct == "n":
            lab = {"y": "F5", "n": "F3"}.get(opened)
            return lab, lab is None
        return None, True
    for key, code, _, _ in IVM.RULES:
        if checks.get(key) == "y":
            return code, False
    return "F3", False


def published_order(letter, ids):
    order = list(range(len(ids)))
    random.Random("%d:%s" % (IVM.BASE_SEED, letter)).shuffle(order)
    return [ids[i] for i in order]


ap = argparse.ArgumentParser()
ap.add_argument("form")
ap.add_argument("--annotator", default=None,
                help="la lettre, deduite du titre du document si elle est omise")
ap.add_argument("--out", default=None)
ap.add_argument("--sample", default="sample_blind.jsonl",
                help="le jeu d'items du corpus que ce formulaire porte")
a = ap.parse_args()

path = a.form if os.path.isabs(a.form) else os.path.join(HERE, a.form)
doc = docx.Document(path)
title = "\n".join(q.text for q in doc.paragraphs[:4])
m = re.search(r"Annotation form, annotator (\S+)", title)
# La lettre du formulaire et celle du lecteur peuvent differer : un lecteur a pu recevoir
# le formulaire d'un autre. Les deux sont conservees, parce que l'ordre de presentation
# vient du formulaire et que la protection contre un effet d'ordre tombe alors pour la
# paire formee avec le lecteur dont le formulaire a servi.
form_letter = m.group(1) if m else None
letter = a.annotator or form_letter
if not letter:
    print("  ECHEC : ce document ne porte pas le titre d'un formulaire de cette ronde,")
    print("  et aucune lettre n'a ete donnee par --annotator.")
    sys.exit(1)

rows = IVM.load_sample(os.path.join(ANN, a.sample))
by_id = {r["id"]: r for r in rows}
want = published_order(form_letter or letter, [r["id"] for r in rows])
if form_letter and form_letter != letter:
    print("  le lecteur %s a rempli le formulaire de %s : l'ordre de presentation est "
          "celui de %s" % (letter, form_letter, form_letter))
    print("  la protection contre un effet d'ordre tombe pour la paire %s et %s"
          % (letter, form_letter))

tables = [t for t in doc.tables
          if t.rows and t.rows[0].cells[0].text.strip().startswith("ANSWERS ")]
if not tables:
    print("  ECHEC : aucun tableau de reponses dans %s" % os.path.basename(path))
    sys.exit(1)

# De quel corpus ce formulaire vient-il, et le corpus charge est-il le bon.
#
# Les deux dorsales portent les memes cinquante identifiants et les memes enonces, donc
# un formulaire de l'une lu contre le corpus de l'autre ne provoquerait aucune erreur
# d'identifiant. Il donnerait des enregistrements faux en silence, parce que le numero
# d'etape du lecteur et la liste des etapes malformees seraient rapportes a une autre
# trajectoire. Le formulaire porte de quoi s'en apercevoir : la ligne Q2 de chaque item
# enumere les etapes disponibles, et cette liste est une propriete de la trajectoire.
# On la relit et on exige l'egalite, plutot que de faire confiance au drapeau passe.
def available_in_form(table):
    for r in table.rows[1:]:
        if r.cells[0].text.strip().strip("[]") != "Q2":
            continue
        m = re.search(r"Available:\s*([^.]*?),?\s*or 0\.", r.cells[1].text)
        if not m:
            return None
        body = m.group(1).strip()
        if body in ("none", ""):
            return []
        return [int(x) for x in re.findall(r"\d+", body)]
    return None


mismatch = []
for t in tables:
    tid = t.rows[0].cells[0].text.strip()[len("ANSWERS "):].strip()
    if tid not in by_id:
        continue
    got_av = available_in_form(t)
    if got_av is None:
        continue
    n = len(by_id[tid]["trajectory"])
    mal_here = IVM.malformed_steps(by_id[tid])
    want_av = [k for k in range(1, n + 1) if k not in mal_here]
    if got_av != want_av:
        mismatch.append((tid, got_av, want_av))
if mismatch:
    print("  ECHEC : ce formulaire ne porte pas le corpus charge.")
    print("  %d items sur %d enumerent d'autres etapes que celles du corpus %s."
          % (len(mismatch), len(tables), a.sample))
    for tid, g, w in mismatch[:4]:
        print("     %s : le formulaire offre %s, ce corpus donne %s"
              % (tid, g or "aucune", w or "aucune"))
    print("  Les deux dorsales portent les memes identifiants, donc rien d'autre ne")
    print("  l'aurait signale. Relancez avec --sample sur le jeu d'items que ce")
    print("  formulaire porte, par exemple sample_blind_falcon3.jsonl.")
    sys.exit(1)

hard, soft, norm = [], [], []
recs, incomplete = [], []
seen = []

for pos, t in enumerate(tables, 1):
    tid = t.rows[0].cells[0].text.strip()[len("ANSWERS "):].strip()
    seen.append(tid)
    if tid not in by_id:
        hard.append("tableau %d : identifiant inconnu %r" % (pos, tid))
        continue
    got = {}
    for r in t.rows[1:]:
        tag = r.cells[0].text.strip().strip("[]")
        if tag:
            got[tag] = r.cells[2].text.strip()
    missing_tags = [k for k in TAGS if k not in got]
    extra = [k for k in got if k not in TAGS]
    if missing_tags or extra:
        hard.append("%s : lignes manquantes %s, lignes inconnues %s"
                    % (tid, missing_tags or "aucune", extra or "aucune"))
        continue

    nsteps = len(by_id[tid]["trajectory"])
    mal = IVM.malformed_steps(by_id[tid])
    # Q4 n'est pas dans cette liste : le sous code F3 ne se pose que si les questions
    # donnent F3, comme dans l'entretien en fenetre, et la verification vient donc
    # apres le calcul de l'etiquette. Une cellule vide est normale sur un succes.
    errs, blanks = [], [k for k in ("Q1", "Q2", "Q5") if not got[k]]

    def yn(tag):
        v = got[tag].strip().lower()
        if v in YN:
            if v != YN[v]:
                norm.append("%s %s : %r lu %r" % (tid, tag, got[tag], YN[v]))
            return YN[v]
        errs.append("%s %s=%r hors y n u" % (tid, tag, got[tag]))
        return None

    correct = yn("Q1") if got["Q1"] else None
    step = None
    if got["Q2"]:
        d = re.search(r"\d+", got["Q2"])
        if not d:
            errs.append("%s Q2=%r : aucun numero" % (tid, got["Q2"]))
        else:
            step = int(d.group(0))
            if got["Q2"].strip() != str(step):
                norm.append("%s Q2 : %r lu %d" % (tid, got["Q2"], step))
            if step > nsteps:
                errs.append("%s Q2=%d hors 0..%d" % (tid, step, nsteps))
                step = None
            elif step in mal:
                errs.append("%s Q2=%d designe une etape malformee" % (tid, step))
                step = None
    # Quand aucune faute n'est designee, les sept controles ne se posent pas : ils
    # portent sur une etape, et il n'y en a pas. Une cellule vide est alors normale.
    checks = {}
    for k in KEYS7:
        if got[k]:
            checks[k] = yn(k)
        elif step == 0:
            checks[k] = None
        else:
            blanks.append(k)
    opened = None
    if step == 0 and correct == "n":
        if got["Q2b"]:
            opened = yn("Q2b")
        else:
            blanks.append("Q2b")
    elif got["Q2b"]:
        soft.append("%s Q2b rempli alors que la question ne se posait pas" % tid)

    sub = got["Q4"].strip().lower()
    if got["Q4"] and sub not in SUB:
        errs.append("%s Q4=%r hors a b c n" % (tid, got["Q4"]))
    free = None
    if got["Q5"]:
        hit = [x for x in IVM.FREE_LABELS if x.lower() == got["Q5"].strip().lower()]
        if hit:
            free = hit[0]
            if got["Q5"].strip() != free:
                norm.append("%s Q5 : %r lu %s" % (tid, got["Q5"], free))
        else:
            errs.append("%s Q5=%r hors du jeu" % (tid, got["Q5"]))

    if blanks:
        incomplete.append((tid, sorted(set(blanks))))
        continue
    if errs:
        hard.extend(errs)
        continue

    lab, und = label_from(step, correct, opened, checks)
    if lab == "F3" and not got["Q4"]:
        incomplete.append((tid, ["Q4, puisque les questions donnent F3 sur cet item"]))
        continue
    if lab != "F3" and got["Q4"]:
        soft.append("%s Q4 rempli alors que l'etiquette calculee est %s, donc le sous "
                    "code ne se pose pas : il est ignore" % (tid, lab))
    answers = {"correct": correct, "first_fault_step": step}
    if step == 0 and correct == "n":
        answers["open_subgoals"] = opened
    if step != 0:
        for k, _, _, _ in IVM.RULES:
            answers[k] = checks[k]
            if checks[k] == "y":
                break
    unsure = [k for k, v in answers.items() if v == "u"]
    recs.append(dict(
        annotator=letter, position=pos, id=tid, malformed_steps=mal, answers=answers,
        computed_label=lab, computed_undetermined=und, free_label=free,
        f3_subcode=SUB.get(sub) if lab == "F3" else None, fault_step=step,
        confidence="low" if (unsure or und or free != lab) else "high",
        unsure_on=unsure, note=got["NOTE"][:400],
        kb_lookups=[x.strip() for x in re.split(r"[;\n]", got["KB"]) if x.strip()],
        seconds=None, finished_at=None, instrument="docx-form",
        form_letter=form_letter, corpus=a.sample,
        checks_all_seven={k: checks[k] for k in KEYS7}))

print()
print("  formulaire de l'annotateur %s, %d tableaux lus" % (letter, len(tables)))
unknown = [i for i in seen if i not in by_id]
dup = sorted({i for i in seen if seen.count(i) > 1})
missing = [i for i in want if i not in set(seen)]
if dup:
    hard.append("doublons : %s" % " ".join(dup[:5]))
if missing:
    hard.append("%d items absents du document : %s" % (len(missing),
                                                       " ".join(missing[:8])))
if not unknown and not dup and not missing and seen != want:
    k = next(j for j in range(len(seen)) if seen[j] != want[j])
    hard.append("l'ordre du document n'est pas celui de la lettre %s : tableau %d porte "
                "%s au lieu de %s" % (form_letter or letter, k + 1, seen[k], want[k]))

if norm:
    print("  %d reponse(s) normalisee(s) :" % len(norm))
    for s in norm[:10]:
        print("      %s" % s)
    if len(norm) > 10:
        print("      et %d autres" % (len(norm) - 10))
for s in soft:
    print("  a regarder : %s" % s)
if incomplete:
    print()
    print("  %d item(s) incomplet(s), laisse(s) de cote et jamais rempli(s) :"
          % len(incomplete))
    for tid, b in incomplete[:12]:
        print("      %s : %s a repondre" % (tid, " ".join(b)))
if hard:
    print()
    for h in hard[:15]:
        print("  ECHEC : %s" % h)
    print()
    print("  rien n'est ecrit : corrigez le document et relancez")
    sys.exit(1)
if incomplete:
    print()
    print("  rien n'est ecrit tant que le formulaire est incomplet. Les %d items ci-"
          "dessus" % len(incomplete))
    print("  sont a completer, puis relancez cette commande.")
    sys.exit(1)

out = a.out or os.path.join(HERE, "responses_%s.jsonl" % letter)
assert not os.path.exists(out), (
    "%s existe deja : deplacez-le avant d'ecrire, pour ne pas melanger deux sources"
    % out)
with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
    for r in recs:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
dist = {}
for r in recs:
    dist[r["computed_label"]] = dist.get(r["computed_label"], 0) + 1
print()
print("  %d items ecrits dans %s" % (len(recs), out))
print("  etiquettes calculees : %s"
      % " ".join("%s %d" % (k, dist[k]) for k in sorted(dist, key=str)))
print("  duree non mesuree par un formulaire, champ nul, instrument docx-form")
print("  ensuite : python -I reception.py")
print("  genere le %s" % time.strftime("%Y-%m-%d"))
