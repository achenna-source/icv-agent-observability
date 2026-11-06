# -*- coding: utf-8 -*-
# L'INSTRUMENT DE LA TABLE SEULE, GARDE POUR QUE LE CONSTAT SOIT REPRODUCTIBLE.
#
# Cette version pose les sept controles de annotator2_instructions.md dans l'ordre de la
# table, sans les quatre conventions. Un essai sur trois items l'a opposee aux etiquettes
# de reference et elle a diverge sur les trois : t154 F1a contre S, t063 F7 contre F2,
# t183 F1a contre F7. interview.py, qui pose le codebook clarifie, reproduit les trois.
# La table seule, lue a la lettre, ne decrit donc pas la procedure reellement appliquee,
# et c'est ce que les conventions corrigent. Ne pas utiliser pour annoter.
#
"""Entretien d'annotation : l'instrument pose les questions, l'humain juge.

Pourquoi un script et non un agent LLM. Les etiquettes de cette ronde servent de
reference humaine. Si un modele de langue formule les questions, il peut orienter la
reponse, et un relecteur pourra dire que l'etiquette est en partie celle du modele.
Ici rien n'est genere. Les sept predicats sont recopies mot pour mot de
annotator2_instructions.md, ils sont poses dans l'ordre du codebook, l'entretien
s'arrete au premier qui se declenche, et l'etiquette est calculee des reponses par la
regle publiee. Le jugement reste celui de l'annotateur, l'etiquette est une fonction de
ce jugement, et le fichier garde les deux.

Ce que l'entretien apporte sur la feuille Excel de la premiere ronde.

  1. L'ordre des regles est impose. La feuille laissait choisir une etiquette
     directement, donc on ne sait pas quelle regle a decide.
  2. Chaque predicat est enregistre separement, donc un desaccord se localise sur la
     question qui l'a cause et non seulement sur l'etiquette.
  3. L'annotateur donne aussi son etiquette libre, sans passer par les questions. Les
     deux chiffres d'accord se calculent : celui de l'etiquette calculee, qui mesure le
     codebook, et celui de l'etiquette libre, comparable a la ronde a la feuille.
  4. L'incertitude est une reponse admise sur chaque predicat, au lieu d'une colonne de
     confiance remplie apres coup.
  5. L'ordre de presentation est melange par annotateur, avec une graine publiee
     d'avance, donc un effet d'ordre ne peut pas se correler entre annotateurs.
  6. Chaque reponse est ecrite sur le disque des qu'elle est donnee.

L'entretien ne dit jamais ce qu'une autre personne a repondu, ne montre aucune sortie
de detecteur et ne donne aucun avis.

    python -I interview.py --annotator A
    python -I interview.py --annotator A --resume

Sortie : responses_<annotateur>.jsonl, une ligne par trajectoire.
"""
import argparse
import io
import json
import os
import random
import sys
import time
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)

BASE_SEED = 20261105          # publie avant la ronde, ne change jamais
REGISTERED = ("knowledge_base", "calculator")
TERMINATOR = "finish"
FREE_LABELS = ("S", "F1a", "F1b", "F2", "F3", "F4", "F5", "F6", "F7")

# Les sept predicats, dans l'ordre du codebook. Le texte est celui du codebook publie.
RULES = (
    ("f1a", "F1a",
     "The agent called a tool that does not exist in the registered tool set.",
     "tools"),
    ("f1b", "F1b",
     "The agent called an existing tool that does not fit the sub-goal, when a better "
     "one was available.",
     "fitness"),
    ("f2", "F2",
     "Arguments are well formed but contain a value absent from the knowledge base, "
     "AND that value is not later used as the pivot of the final result.",
     "pivot"),
    ("f4", "F4",
     "The agent repeats an equivalent step without progress until the budget runs out "
     "(verbatim, or rephrased but functionally the same).",
     "repetition"),
    ("f5", "F5",
     "The agent stops, or emits an empty or None final answer, before finishing.",
     None),
    ("f6", "F6",
     "The final answer contradicts a value the agent itself produced earlier.",
     None),
    ("f7", "F7",
     "The agent fabricates a value absent from the sources and uses it as the PIVOT of "
     "the final computation (shown in a calculation, or reconstructible from the final "
     "number).",
     "pivot"),
)

HELP = {
    "tools":
        "The registered tool set is knowledge_base and calculator. The step that ends a\n"
        "  trajectory uses finish, which is the terminator and not a tool. A step naming\n"
        "  anything else names no registered tool.",
    "fitness":
        "Tool fitness, rule 2 of the codebook. \"Unfit\" means a competent solver would not\n"
        "  have chosen it for that sub-goal, not merely that a different tool would also\n"
        "  have worked.",
    "repetition":
        "Semantic repetition, rule 4 of the codebook. Two steps are equivalent if they\n"
        "  pursue the same sub-goal by the same means, even when the wording differs. A\n"
        "  genuine follow-up query on the same entity is not a repetition.",
    "pivot":
        "The pivot test, rules 3 against 7 of the codebook. Ask whether the fabricated\n"
        "  value carries through into the final result. If the agent invents a population\n"
        "  figure and then divides it by something to produce its answer, that is F7. If it\n"
        "  invents a value, gets an error or ignores it, and reaches its answer another way,\n"
        "  that is F2. Equivalently: would removing the invented value change the final\n"
        "  answer? If yes, it is a pivot.",
}

ORDER_RULE = (
    "The label is the category of the FIRST observable fault, not the state the\n"
    "  trajectory ends in. A trajectory that mishandles a retrieved value and then also\n"
    "  returns nothing is a reasoning error F3, not a termination error F5. The questions\n"
    "  are asked in the codebook's order and stop at the first that fires, so answer each\n"
    "  one on its own and do not try to reach a label you have in mind.")

BANNER = """
================================================================================
 ANNOTATION INTERVIEW
 Annotator %s          item %d of %d          %s
================================================================================
"""

PROMPT_HELP = """
  y / n / u  yes, no, unsure            ?        explain this question
  kb <text>  search the knowledge base  tools    list the registered tools
  order      the first-fault rule       steps    show the trajectory again
  back       re-answer the previous question of this item
  save       save and stop, resume later with --resume
"""


# ----------------------------------------------------------------------------- donnees
def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def load_sample(path):
    rows = [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
    for r in rows:
        assert "id" in r and "task" in r and "trajectory" in r, r.get("id")
        assert "label_human" not in r and "label_annotator1" not in r, \
            "l'echantillon contient des etiquettes : il n'est pas aveugle"
    return rows


def load_kb(path):
    return json.load(io.open(path, encoding="utf-8"))


# ----------------------------------------------------------------------------- affichage
def render(row):
    out = []
    out.append("TASK")
    out.append("  %s" % row["task"])
    out.append("")
    out.append("TRAJECTORY")
    for i, s in enumerate(row["trajectory"], 1):
        th = (s.get("thought") or "").strip()
        out.append("  Step %d." % i)
        if th:
            out.append("    thought      %s" % th)
        out.append("    action       %s" % s.get("action"))
        out.append("    input        %s" % s.get("input"))
        out.append("    observation  %s" % s.get("observation"))
    out.append("")
    last = row["trajectory"][-1] if row["trajectory"] else {}
    if last.get("action") == TERMINATOR:
        out.append("FINAL ANSWER")
        out.append("  %s" % last.get("input"))
    else:
        out.append("FINAL ANSWER")
        out.append("  none: the trajectory does not end with a %s step" % TERMINATOR)
    return "\n".join(out)


def kb_search(kb, query, limit=12):
    q = strip_accents(query.strip())
    if not q:
        return ["  type some text after kb, for example: kb population lisbonne"]
    hits = [(k, v) for k, v in kb.items() if q in strip_accents(k)]
    if not hits:
        words = [w for w in q.split() if len(w) > 2]
        hits = [(k, v) for k, v in kb.items()
                if words and any(w in strip_accents(k) for w in words)]
    if not hits:
        return ["  no query matching %r was ever answered by the knowledge base,"
                % query, "  so a value of that kind was not retrievable."]
    lines = ["  %d query/queries the knowledge base answered:" % len(hits)]
    for k, v in sorted(hits)[:limit]:
        lines.append("    %-46s -> %s" % (k, v))
    if len(hits) > limit:
        lines.append("    ... %d more, narrow the search" % (len(hits) - limit))
    return lines


# ----------------------------------------------------------------------------- entretien
class Stop(Exception):
    pass


class Back(Exception):
    pass


def ask(question, allowed, row, kb, helpkey, lookups, extra=None, allow_back=True):
    """Pose une question et rend la reponse. Ne suggere jamais de reponse."""
    print()
    print(question)
    if extra:
        print(extra)
    while True:
        try:
            raw = input("  > ").strip()
        except EOFError:
            raise Stop
        low = raw.lower()
        if low in ("save", "quit", "exit"):
            raise Stop
        if low == "back":
            if allow_back:
                raise Back
            print("  the earlier answers of this item are already fixed")
            continue
        if low in ("?", "help", "h"):
            print()
            print("  %s" % (HELP.get(helpkey) or
                            "No separate guidance: answer the question as written."))
            print(PROMPT_HELP)
            continue
        if low == "order":
            print()
            print("  %s" % ORDER_RULE)
            continue
        if low == "tools":
            print()
            print("  %s" % HELP["tools"])
            continue
        if low == "steps":
            print()
            print(render(row))
            continue
        if low.startswith("kb"):
            arg = raw[2:].strip()
            lookups.append(arg)
            print()
            for line in kb_search(kb, arg):
                print(line)
            continue
        if low in allowed:
            return low
        print("  answer one of: %s   (? for help)" % ", ".join(allowed))


def interview_item(row, kb, idx, total, elapsed):
    """Un item. Rend l'enregistrement, ou leve Stop."""
    print(BANNER % (ARGS.annotator, idx, total, elapsed))
    print(render(row))
    print()
    print("-" * 80)
    print("  y = yes, n = no, u = unsure. Type ? at any prompt for guidance on that")
    print("  question, kb <text> to search the knowledge base, steps to see the")
    print("  trajectory again, save to stop and resume later.")
    print("-" * 80)

    lookups = []
    t0 = time.time()
    answers = {}
    seq = ["correct", "fault"] + [r[0] for r in RULES]
    pos = 0
    label = None

    while pos < len(seq):
        key = seq[pos]
        try:
            if key == "correct":
                answers[key] = ask(
                    "Q. Is the final answer correct with respect to the ground truth?",
                    ("y", "n", "u"), row, kb, None, lookups,
                    "   Use kb <text> to check what the knowledge base could return.")
            elif key == "fault":
                # La question ne se pose que si la reponse finale a ete jugee juste :
                # le codebook ne permet S que dans ce cas. Si la justesse est restee
                # incertaine, les regles sont parcourues et l'item peut rester
                # indetermine, ce qui vaut mieux qu'un S fabrique.
                if answers["correct"] != "y":
                    pos += 1
                    continue
                answers[key] = ask(
                    "Q. Did any observable fault occur along the way?",
                    ("y", "n", "u"), row, kb, "order", lookups)
                if answers[key] == "n":
                    label = "S"
                    break
            else:
                rule = [r for r in RULES if r[0] == key][0]
                _, code, text, helpkey = rule
                answers[key] = ask("Q. %s" % text, ("y", "n", "u"),
                                   row, kb, helpkey, lookups)
                if answers[key] == "y":
                    label = code
                    break
        except Back:
            if pos == 0:
                print("\n  this is the first question of the item")
                continue
            pos -= 1
            answers.pop(seq[pos], None)
            continue
        pos += 1

    undetermined = False
    if label is None:
        residual_valid = (answers.get("correct") == "n"
                          or (answers.get("correct") == "y"
                              and answers.get("fault") == "y"))
        if residual_valid:
            label = "F3"
            print()
            print("  No rule fired, so the computed label is the residual F3.")
        else:
            undetermined = True
            print()
            print("  No rule fired, and you left the earlier question unsure, so the")
            print("  questions do not settle this item between S and F3. That is")
            print("  recorded as it stands, and your own code below is kept separately.")

    subcode = None
    if label == "F3":
        subcode = ask(
            "Q. An F3 sub-code, if one is clear. a = wrong calculation over correctly\n"
            "   retrieved values, b = failed or misdirected retrieval of a fact that was\n"
            "   present, c = partial or ungrounded answer, n = none of the three.",
            ("a", "b", "c", "n"), row, kb, None, lookups, allow_back=False)
        subcode = {"a": "F3a", "b": "F3b", "c": "F3c", "n": None}[subcode]

    nsteps = len(row["trajectory"])
    step = ask("Q. Which step number holds the first fault? 1 to %d, or 0 if none."
               % nsteps,
               tuple(str(i) for i in range(0, nsteps + 1)), row, kb, "order", lookups,
               allow_back=False)

    print()
    if undetermined:
        print("  The questions leave this item undetermined.")
    else:
        print("  The questions give the computed label %s." % label)
    free = ask("Q. Independently of the questions, which single code would you assign?\n"
               "   %s" % ", ".join(FREE_LABELS),
               tuple(x.lower() for x in FREE_LABELS), row, kb, None, lookups,
               allow_back=False)
    free = [x for x in FREE_LABELS if x.lower() == free][0]

    print()
    print("Q. One line of note, or Enter for none. Which step held the fault, or which")
    print("   two categories you were torn between.")
    try:
        note = input("  > ").strip()
    except EOFError:
        raise Stop
    if note.lower() in ("save", "quit", "exit"):
        raise Stop

    unsure = [k for k, v in answers.items() if v == "u"]
    conf = "low" if (unsure or undetermined or free != label) else "high"
    rec = dict(annotator=ARGS.annotator, position=idx, id=row["id"],
               answers=answers, computed_label=label,
               computed_undetermined=undetermined, free_label=free,
               f3_subcode=subcode, fault_step=int(step), confidence=conf,
               unsure_on=unsure, note=note, kb_lookups=lookups,
               seconds=round(time.time() - t0, 1),
               finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    print()
    if undetermined:
        print("  Recorded: undetermined by the questions, your own code %s." % free)
    elif free != label:
        print("  Recorded: computed %s, your own %s. Both are kept, and the difference is"
              % (label, free))
        print("  itself a finding about the codebook. Nothing is overridden.")
    else:
        print("  Recorded: %s, confidence %s." % (label, conf))
    return rec


# ----------------------------------------------------------------------------- pilotage
def main():
    sample = load_sample(ARGS.sample)
    kb = load_kb(ARGS.kb)
    order = list(range(len(sample)))
    random.Random("%d:%s" % (ARGS.seed, ARGS.annotator)).shuffle(order)
    rows = [sample[i] for i in order]

    out = ARGS.out or os.path.join(HERE, "responses_%s.jsonl" % ARGS.annotator)
    done = {}
    if os.path.exists(out):
        for l in io.open(out, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                done[r["id"]] = r
        if not ARGS.resume and done:
            print("%s holds %d answered items. Relaunch with --resume to continue."
                  % (out, len(done)))
            return 1

    todo = [r for r in rows if r["id"] not in done]
    print()
    print("  Annotator %s, sample of %d, seed %d, %d already answered, %d to go."
          % (ARGS.annotator, len(rows), ARGS.seed, len(done), len(todo)))
    print("  Presentation order is shuffled from the seed and the annotator letter, so")
    print("  two annotators never see the items in the same order.")
    print(PROMPT_HELP)
    input("  Enter to begin. ")

    t_start = time.time()
    fh = io.open(out, "a", encoding="utf-8", newline="\n")
    n = len(done)
    for row in todo:
        n += 1
        mins = (time.time() - t_start) / 60.0
        elapsed = "%d min elapsed" % mins if n > len(done) + 1 else "starting"
        try:
            rec = interview_item(row, kb, n, len(rows), elapsed)
        except Stop:
            fh.close()
            print()
            print("  Stopped. %d of %d answered, saved in %s" % (n - 1, len(rows), out))
            print("  Resume with:  python -I interview.py --annotator %s --resume"
                  % ARGS.annotator)
            return 0
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
        if n % 15 == 0 and n < len(rows):
            print()
            print("  %d of %d done. Take a break: annotation quality drops when tired."
                  % (n, len(rows)))
            print("  Type save to stop here, or Enter to carry on.")
            if input("  > ").strip().lower() in ("save", "quit", "exit"):
                fh.close()
                print("  Saved in %s, resume with --resume" % out)
                return 0
    fh.close()
    print()
    print("  All %d items answered. File: %s" % (len(rows), out))
    print("  Return that one file. Nothing else is needed.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--annotator", required=True,
                   help="une lettre ou un identifiant court, A B C D")
    p.add_argument("--sample", default=os.path.join(ANN, "sample_blind.jsonl"))
    p.add_argument("--kb", default=os.path.join(ROOT, "data",
                                                "knowledge_base_observed.json"))
    p.add_argument("--out", default=None)
    p.add_argument("--seed", type=int, default=BASE_SEED)
    p.add_argument("--resume", action="store_true")
    ARGS = p.parse_args()
    sys.exit(main())
