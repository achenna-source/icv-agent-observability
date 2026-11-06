# -*- coding: utf-8 -*-
"""Relit un formulaire ToolBench rempli et en tire le fichier de reponses de la ronde.

Ce que le script ne fait pas. Il ne devine aucune reponse, il ne comble aucune cellule
vide, et il ne choisit aucune etiquette. L'etiquette est calculee par la regle publiee,
dans l'ordre des controles de interview.py, a partir des reponses ecrites dans le
document. Un item incomplet est signale et laisse de cote, jamais rempli.

CE QUE CE CORPUS CHANGE, ET LA SEULE QUESTION QU'IL CHANGE

ToolBench ne porte aucune cle de verite. La premiere question n'est donc pas la
correction de la reponse finale mais sa coherence avec les observations obtenues, et S
signifie ici aucune faute observable a l'interface des actions et une reponse coherente
avec ces observations. Le formulaire le dit en tete, et ce script enregistre la reponse
sous le nom consistent plutot que correct, pour qu'aucune analyse ne les confonde.

UN TROU DE L'INSTRUMENT, TROUVE EN ECRIVANT CE LECTEUR PUIS COMBLE

La regle publiee tranche le cas « aucune faute d'etape et reponse fautive » par la
convention des sous-buts ouverts : F5 si la trajectoire s'arrete en laissant une part de
la tache sans reponse, F3 sinon. Le formulaire ToolBench enoncait cette convention sans
porter la ligne pour y repondre, donc un item ou le lecteur ecrit Q2=0 et Q1=n n'etait
pas calculable. La ligne Q2b a ete ajoutee au constructeur le 6 novembre 2026, avant
qu'aucun lecteur ait commence, et les formulaires ont ete reemis sans changer les
identifiants, l'ordre ni la graine.

Ce lecteur lit les deux formes. Avec la ligne, il applique la convention. Sans elle, il
declare l'item indetermine, le compte, et garde l'etiquette libre du lecteur sans la
promouvoir : il n'invente pas la reponse manquante.

CE QU'IL VERIFIE EN PLUS

Le formulaire annonce au lecteur que le premier controle est vide sur ce corpus : aucune
action n'y nomme un outil hors du jeu enregistre de sa tache. Ce script le recalcule, et
si un lecteur repond oui a f1a quelque part, il le signale comme desaccord avec une
affirmation mecanique plutot que de l'ecraser.

    python -I read_docx_toolbench.py formulaire_toolbench_A_rempli.docx
    python -I read_docx_toolbench.py formulaire_toolbench_B_blind25_rempli.docx --blind
"""
import argparse
import io
import json
import os
import random
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

import docx

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, HERE)
import interview as IVM            # noqa: E402

SAMPLE_DIR = os.path.join(REPO, "kaggle", "icv-toolbench-sample", "out")
TERMINATOR = "Finish"
SEED = 20261105
YN = {"y": "y", "yes": "y", "oui": "y", "o": "y",
      "n": "n", "no": "n", "non": "n",
      "u": "u", "unsure": "u", "incertain": "u", "?": "u"}
SUB = {"a": "F3a", "b": "F3b", "c": "F3c", "n": None, "none": None, "aucun": None}
KEYS7 = [r[0] for r in IVM.RULES]
TAGS = ["Q1", "Q2"] + KEYS7 + ["Q4", "Q5", "NOTE"]
TAG_OPEN = "Q2b"       # present depuis la reemission du 6 novembre 2026


def malformed(row):
    """La meme definition que le constructeur : une action qui ne nomme ni un outil
    enregistre de cette tache ni le terminateur."""
    ok = set(row["tools"]) | {TERMINATOR}
    return [k for k, s in enumerate(row["steps"], 1) if s.get("action") not in ok]


def label_from(step, consistent, opened, checks):
    """La regle publiee, pilotee par l'ordre des controles de interview.py. Sur un
    formulaire sans la ligne des sous-buts ouverts, le cas step 0 avec une reponse
    incoherente reste indetermine plutot que comble."""
    if step == 0:
        if consistent == "y":
            return "S", False
        lab = {"y": "F5", "n": "F3"}.get(opened)
        return lab, lab is None
    for key, code, _, _ in IVM.RULES:
        if checks.get(key) == "y":
            return code, False
    return "F3", False


def published_order(letter, aids):
    order = list(range(len(aids)))
    random.Random("%d:toolbench:%s" % (SEED, letter)).shuffle(order)
    return [aids[i] for i in order]


ap = argparse.ArgumentParser()
ap.add_argument("form")
ap.add_argument("--annotator", default=None,
                help="la lettre, deduite du titre du document si elle est omise")
ap.add_argument("--blind", action="store_true",
                help="le sous-ensemble de 25, au lieu des 60")
ap.add_argument("--sample", default=None, help="le fichier d'echantillon a charger")
ap.add_argument("--out", default=None)
a = ap.parse_args()

path = a.form if os.path.isabs(a.form) else os.path.join(HERE, a.form)
doc = docx.Document(path)
title = "\n".join(q.text for q in doc.paragraphs[:4])
m = re.search(r"ToolBench annotation form, annotator (\S+)", title)
form_letter = m.group(1) if m else None
letter = a.annotator or form_letter
if not letter:
    print("  ECHEC : ce document ne porte pas le titre d'un formulaire ToolBench de "
          "cette ronde,")
    print("  et aucune lettre n'a ete donnee par --annotator.")
    sys.exit(1)

sample = a.sample or os.path.join(
    SAMPLE_DIR, "toolbench_blind_25.jsonl" if a.blind else "toolbench_60.jsonl")
if not os.path.exists(sample):
    print("  ECHEC : echantillon absent : %s" % sample)
    print("  Ce corpus n'est pas redistribue dans l'artefact. Donnez --sample.")
    sys.exit(1)
rows = [json.loads(l) for l in io.open(sample, encoding="utf-8") if l.strip()]
by_id = {r["aid"]: r for r in rows}
want = published_order(form_letter or letter, [r["aid"] for r in rows])
if form_letter and form_letter != letter:
    print("  le lecteur %s a rempli le formulaire de %s : l'ordre de presentation est "
          "celui de %s" % (letter, form_letter, form_letter))

tables = [t for t in doc.tables
          if t.rows and t.rows[0].cells[0].text.strip().startswith("ANSWERS ")]
if not tables:
    print("  ECHEC : aucun tableau de reponses dans %s" % os.path.basename(path))
    sys.exit(1)


def available_in_form(table):
    """La liste des etapes offertes par la ligne Q2 : une propriete de la trajectoire,
    donc de quoi s'apercevoir qu'un formulaire est lu contre le mauvais echantillon."""
    for r in table.rows[1:]:
        if r.cells[0].text.strip().strip("[]") != "Q2":
            continue
        mm = re.search(r"Available:\s*([^.]*?),?\s*or 0\.", r.cells[1].text)
        if not mm:
            return None
        body = mm.group(1).strip()
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
    n = len(by_id[tid]["steps"])
    mal_here = malformed(by_id[tid])
    want_av = [k for k in range(1, n + 1) if k not in mal_here]
    if got_av != want_av:
        mismatch.append((tid, got_av, want_av))
if mismatch:
    print("  ECHEC : ce formulaire ne porte pas l'echantillon charge.")
    print("  %d items sur %d enumerent d'autres etapes que celles de %s."
          % (len(mismatch), len(tables), os.path.basename(sample)))
    for tid, g, w in mismatch[:4]:
        print("     %s : le formulaire offre %s, cet echantillon donne %s"
              % (tid, g or "aucune", w or "aucune"))
    print("  Relancez avec ou sans --blind, ou avec --sample sur le bon fichier.")
    sys.exit(1)

# l'affirmation mecanique du formulaire, recalculee avant de lire une seule reponse
vacuous = all(not malformed(r) for r in rows)
print()
print("  formulaire ToolBench de l'annotateur %s, %d tableaux, echantillon %s"
      % (letter, len(tables), os.path.basename(sample)))
print("  premier controle vide sur ce corpus : %s" % ("oui" if vacuous else "NON"))

hard, soft, norm = [], [], []
recs, incomplete, undet = [], [], []
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
    extra = [k for k in got if k not in TAGS + [TAG_OPEN]]
    has_open = TAG_OPEN in got
    if missing_tags or extra:
        hard.append("%s : lignes manquantes %s, lignes inconnues %s"
                    % (tid, missing_tags or "aucune", extra or "aucune"))
        continue

    row = by_id[tid]
    nsteps = len(row["steps"])
    mal = malformed(row)
    errs, blanks = [], [k for k in ("Q1", "Q2", "Q5") if not got[k]]

    def yn(tag):
        v = got[tag].strip().lower()
        if v in YN:
            if v != YN[v]:
                norm.append("%s %s : %r lu %r" % (tid, tag, got[tag], YN[v]))
            return YN[v]
        errs.append("%s %s=%r hors y n u" % (tid, tag, got[tag]))
        return None

    consistent = yn("Q1") if got["Q1"] else None
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

    checks = {}
    for k in KEYS7:
        if got[k]:
            checks[k] = yn(k)
        elif step == 0:
            checks[k] = None
        else:
            blanks.append(k)
    if checks.get("f1a") == "y" and vacuous and not mal:
        soft.append("%s f1a=y alors qu'aucune action de cette trajectoire ne sort du jeu "
                    "enregistre : desaccord avec une affirmation mecanique, conserve tel "
                    "quel" % tid)

    opened = None
    if step == 0 and consistent == "n":
        if has_open and got[TAG_OPEN]:
            opened = yn(TAG_OPEN)
        elif has_open:
            blanks.append(TAG_OPEN)
    elif has_open and got[TAG_OPEN]:
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

    lab, und = label_from(step, consistent, opened, checks)
    if und:
        undet.append((tid, consistent, free))
    if lab == "F3" and not got["Q4"]:
        incomplete.append((tid, ["Q4, puisque les questions donnent F3 sur cet item"]))
        continue
    if lab not in (None, "F3") and got["Q4"]:
        soft.append("%s Q4 rempli alors que l'etiquette calculee est %s : ignore"
                    % (tid, lab))
    answers = {"consistent": consistent, "first_fault_step": step}
    if step == 0 and consistent == "n":
        answers["open_subgoals"] = opened
    if step != 0:
        for k, _, _, _ in IVM.RULES:
            answers[k] = checks[k]
            if checks[k] == "y":
                break
    unsure = [k for k, v in answers.items() if v == "u"]
    recs.append(dict(
        annotator=letter, position=pos, id=tid, corpus="toolbench",
        malformed_steps=mal, answers=answers, computed_label=lab,
        computed_undetermined=und, free_label=free,
        f3_subcode=SUB.get(sub) if lab == "F3" else None, fault_step=step,
        confidence="low" if (unsure or und or free != lab) else "high",
        unsure_on=unsure, note=got["NOTE"][:400], seconds=None, finished_at=None,
        instrument="docx-toolbench", form_letter=form_letter,
        checks_all_seven={k: checks[k] for k in KEYS7}))

unknown = [i for i in seen if i not in by_id]
dup = sorted({i for i in seen if seen.count(i) > 1})
missing = [i for i in want if i not in set(seen)]
if dup:
    hard.append("doublons : %s" % " ".join(dup[:5]))
if missing:
    hard.append("%d items absents du document : %s"
                % (len(missing), " ".join(missing[:8])))
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
    print("  rien n'est ecrit tant que le formulaire est incomplet.")
    sys.exit(1)

if undet:
    print()
    print("  %d item(s) que la regle ne tranche pas, faute de la ligne des sous-buts "
          "ouverts" % len(undet))
    print("  dans ce formulaire. L'etiquette calculee reste nulle et l'etiquette libre "
          "du lecteur")
    print("  est conservee sans etre promue :")
    for tid, c, free in undet[:10]:
        print("      %s : Q1=%s, etiquette libre %s" % (tid, c, free))

out = a.out or os.path.join(HERE, "responses_toolbench_%s.jsonl" % letter)
io.open(out, "w", encoding="utf-8", newline="\n").write(
    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
print()
print("  %d enregistrement(s) ecrit(s) dans %s" % (len(recs), os.path.basename(out)))
agree = sum(1 for r in recs if r["free_label"] == r["computed_label"])
print("  etiquette libre et etiquette calculee d'accord sur %d des %d items"
      % (agree, len(recs)))
dist = {}
for r in recs:
    dist[r["computed_label"]] = dist.get(r["computed_label"], 0) + 1
print("  repartition calculee : %s" % dist)
