# -*- coding: utf-8 -*-
"""Entretien d'annotation : l'instrument pose les questions, l'humain juge.

Pourquoi un script et non un agent LLM. Les etiquettes de cette ronde servent de
reference humaine. Si un modele de langue formule les questions, il peut orienter la
reponse, et un relecteur pourra dire que l'etiquette est en partie celle du modele. Ici
rien n'est genere. Les predicats sont recopies mot pour mot de codebook_clarified.md, ils
sont poses dans l'ordre de ce document, l'entretien s'arrete au premier qui se declenche,
et l'etiquette est calculee des reponses par la regle publiee. Le jugement reste celui de
l'annotateur, l'etiquette est une fonction de ce jugement, et le fichier garde les deux.

Le document de reference est le codebook CLARIFIE, celui des quatre conventions, et non
la table seule. Un essai sur trois items a montre pourquoi : la table seule, lue a la
lettre et dans son ordre, contredit les etiquettes de reference des que la trajectoire
porte une etape malformee, et les trois divergences de l'essai sont exactement les trois
que les conventions tranchent. L'ordre des questions suit donc les conventions.

  1. Les etapes malformees sont mises de cote d'emblee, puisqu'une malformation ne donne
     jamais son etiquette a la trajectoire, reprise ou non.
  2. L'annotateur designe la premiere faute dans le temps, et la table ne sert ensuite
     qu'a classer cette faute. La table ordonne les controles, elle ne hierarchise pas
     les fautes.
  3. Le test du pivot demande un calcul, ce que les deux questions concernees enoncent.
  4. Un constat d'absence veridique est un succes, ce que la question sur la justesse de
     la reponse rappelle.

Ce que l'entretien apporte sur la feuille Excel de la premiere ronde. Chaque predicat est
enregistre separement, donc un desaccord se localise sur la question qui l'a cause et non
seulement sur l'etiquette. L'annotateur donne aussi son etiquette libre, sans passer par
les questions, donc deux chiffres d'accord se calculent : celui de l'etiquette calculee,
qui mesure le codebook, et celui de l'etiquette libre, comparable a la ronde a la feuille.
L'incertitude est une reponse admise sur chaque predicat. L'ordre de presentation est
melange par annotateur, avec une graine publiee d'avance. Chaque reponse est ecrite sur le
disque des qu'elle est donnee.

L'entretien ne dit jamais ce qu'une autre personne a repondu, ne montre aucune sortie de
detecteur et ne donne aucun avis.

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

# Les controles, dans l'ordre de la table. Chaque phrase est celle du codebook clarifie.
RULES = (
    ("f1a", "F1a",
     "The agent called a tool that does not exist in the registered tool set.",
     "tools"),
    ("f1b", "F1b",
     "The agent called an existing tool that does not fit the sub-goal, when a better "
     "one was available.",
     "fitness"),
    ("f2", "F2",
     "A fabricated value that is merely reported, and not computed with, is F2 when "
     "nothing else in the final answer is grounded in a value the store returned.",
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
     "F7 applies when a fabricated value is used as an input to a computation whose "
     "result is the final answer.",
     "pivot"),
)

HELP = {
    "tools":
        "The registered tool set is knowledge_base and calculator. The step that ends a\n"
        "  trajectory uses finish, which is the terminator and not a tool. A step whose\n"
        "  action names no registered tool is a malformation, and those steps were set\n"
        "  aside before this question: this question is about a step naming some other\n"
        "  tool, one that simply does not exist.",
    "fitness":
        "Tool fitness. \"Unfit\" means a competent solver would not have chosen it for\n"
        "  that sub-goal, not merely that a different tool would also have worked.",
    "repetition":
        "Semantic repetition. Two steps are equivalent if they pursue the same sub-goal\n"
        "  by the same means, even when the wording differs. A genuine follow-up query on\n"
        "  the same entity is not a repetition.",
    "pivot":
        "The pivot test requires a computation. F7 applies when a fabricated value is\n"
        "  used as an input to a computation whose result is the final answer. A\n"
        "  fabricated value that is merely reported, and not computed with, is F2 when\n"
        "  nothing else in the final answer is grounded in a value the store returned,\n"
        "  and F3, with the sub-code F3c, when the answer also reports a value the store\n"
        "  did return. What separates the two is how much of the answer is invented. An\n"
        "  answer built on nothing the store returned is a fabricated answer. An answer\n"
        "  that reports a retrieved fact and pads it with an invented one is a partial\n"
        "  answer, which is what F3c describes, and it stays F3 however plausible the\n"
        "  invented part looks. Where no value is fabricated at all and the answer is\n"
        "  simply wrong or incomplete, the label is F3. A fabrication that stays inside a\n"
        "  thought, never entering an argument and never reaching the final answer, is\n"
        "  not a fabricated datum under either rule.",
    "absence":
        "A truthful report of absence is a success. Some tasks ask for information the\n"
        "  knowledge base does not hold. Where the store genuinely lacks it and the\n"
        "  agent's final answer says so without asserting any invented value, the\n"
        "  trajectory is S. It is not F5, because the sub-goal is closed rather than\n"
        "  abandoned, and it is not F3, because nothing was mishandled.",
    "earliest":
        "The first fault in time governs, not the first rule in the table. Where two\n"
        "  faults of different kinds occur, the label comes from the one that occurs\n"
        "  earliest in the trajectory, and the ordered table then tells you which\n"
        "  category that fault falls into. The table orders the checks; it does not rank\n"
        "  the faults. The malformed steps listed above are not candidates, since a\n"
        "  malformation never gives the trajectory its label, whether recovered or not.",
    "open":
        "Sub-goals still open means the trajectory stopped with part of the task\n"
        "  unanswered. If no fault other than a malformation exists and the answer is\n"
        "  wrong, the label is F5 when the trajectory ends with sub-goals still open, and\n"
        "  F3 otherwise.",
}

MALFORMED_NOTE = """  CONVENTION. A step whose action names no registered tool is a malformation: a defect
  in the form of the call, not a diagnosis of what the agent was trying to do. Whether
  recovered or not, a malformation never gives the trajectory its label. The step or
  steps above are therefore set aside, and the trajectory is labelled on the first fault
  that is not a malformation."""

BANNER = """
================================================================================
 ANNOTATION INTERVIEW
 Annotator %s          item %d of %d          %s
================================================================================
"""

PROMPT_HELP = """
  y / n / u  yes, no, unsure            ?        explain this question
  kb <text>  search the knowledge base  tools    list the registered tools
  rules      the four conventions       steps    show the trajectory again
  back       re-answer the previous check of this item
  save       save and stop, resume later
"""


# ----------------------------------------------------------------------------- donnees
def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def load_sample(path):
    rows = [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
    for r in rows:
        assert "id" in r and "task" in r and "trajectory" in r, r.get("id")
        bad = [k for k in r if "label" in k.lower() or "gold" in k.lower()]
        assert not bad, "l'echantillon porte des etiquettes : %s" % bad
    return rows


def malformed_steps(row):
    """Mecanique, et lue de la definition publiee du jeu d'outils enregistres."""
    out = []
    for n, s in enumerate(row["trajectory"], 1):
        a = s.get("action")
        name = a.strip() if isinstance(a, str) else ""
        if name.lower() in ("", "none") or name not in REGISTERED + (TERMINATOR,):
            out.append(n)
    return out


# ----------------------------------------------------------------------------- affichage
def render(row):
    out = ["TASK", "  %s" % row["task"], "", "TRAJECTORY"]
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
    out.append("FINAL ANSWER")
    if last.get("action") == TERMINATOR:
        out.append("  %s" % last.get("input"))
    else:
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


def conventions():
    return "\n\n".join(("  THE FOUR CONVENTIONS", MALFORMED_NOTE,
                        "  " + HELP["earliest"], "  " + HELP["pivot"],
                        "  " + HELP["absence"]))


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
        if low in ("rules", "order", "conventions"):
            print()
            print(conventions())
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


def classify_step(step, row, kb, lookups, answers):
    """La table, appliquee a la faute que l'annotateur a designee."""
    pos, label = 0, None
    keys = [r[0] for r in RULES]
    while pos < len(keys):
        key = keys[pos]
        _, code, text, helpkey = [r for r in RULES if r[0] == key][0]
        try:
            answers[key] = ask("Q. At step %d: %s" % (step, text),
                               ("y", "n", "u"), row, kb, helpkey, lookups)
        except Back:
            if pos == 0:
                print("\n  this is the first check of the table")
                continue
            pos -= 1
            answers.pop(keys[pos], None)
            continue
        if answers[key] == "y":
            label = code
            break
        pos += 1
    return label


def interview_item(row, kb, idx, total, elapsed):
    """Un item. Rend l'enregistrement, ou leve Stop."""
    print(BANNER % (ARGS.annotator, idx, total, elapsed))
    print(render(row))
    mal = malformed_steps(row)
    nsteps = len(row["trajectory"])
    print()
    print("-" * 80)
    if mal:
        print("  MALFORMED STEPS: %s" % ", ".join("step %d" % n for n in mal))
        print(MALFORMED_NOTE)
    else:
        print("  No step fails to name a registered tool.")
    print("-" * 80)
    print("  y = yes, n = no, u = unsure. ? explains the question in the codebook's own")
    print("  words, rules shows the four conventions, kb <text> searches the knowledge")
    print("  base, steps redisplays the trajectory, save stops and resumes later.")
    print("-" * 80)

    lookups, answers = [], {}
    t0 = time.time()

    correct = ask("Q. Is the final answer correct with respect to the ground truth?",
                  ("y", "n", "u"), row, kb, "absence", lookups,
                  "   Use kb <text> to check what the knowledge base could return.",
                  allow_back=False)
    answers["correct"] = correct

    candidates = [n for n in range(1, nsteps + 1) if n not in mal]
    allowed = tuple(str(n) for n in candidates) + ("0",)
    first = ask("Q. Which is the earliest step at which something went wrong, leaving\n"
                "   aside the malformed steps? Answer 0 if nothing went wrong.\n"
                "   Available: %s, or 0."
                % (", ".join(str(n) for n in candidates) or "none"),
                allowed, row, kb, "earliest", lookups, allow_back=False)
    answers["first_fault_step"] = int(first)

    label, undetermined, step = None, False, int(first)
    if step == 0:
        if correct == "y":
            label = "S"
        elif correct == "n":
            opened = ask("Q. Does the trajectory end with sub-goals still open?",
                         ("y", "n", "u"), row, kb, "open", lookups, allow_back=False)
            answers["open_subgoals"] = opened
            label = {"y": "F5", "n": "F3"}.get(opened)
            undetermined = label is None
        else:
            undetermined = True
            print()
            print("  No fault located, and the correctness of the answer was left")
            print("  unsure, so the questions do not settle this item between S and a")
            print("  failure. That is recorded as it stands.")
    else:
        label = classify_step(step, row, kb, lookups, answers)
        if label is None:
            label = "F3"
            print()
            print("  No check fired on that step, so the computed label is the residual")
            print("  F3, which is defined by exclusion.")

    subcode = None
    if label == "F3":
        subcode = ask(
            "Q. An F3 sub-code, if one is clear. a = wrong calculation over correctly\n"
            "   retrieved values, b = failed or misdirected retrieval of a fact that was\n"
            "   present, c = partial or ungrounded answer, n = none of the three.",
            ("a", "b", "c", "n"), row, kb, None, lookups, allow_back=False)
        subcode = {"a": "F3a", "b": "F3b", "c": "F3c", "n": None}[subcode]

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
               malformed_steps=mal, answers=answers, computed_label=label,
               computed_undetermined=undetermined, free_label=free,
               f3_subcode=subcode, fault_step=step, confidence=conf,
               unsure_on=unsure, note=note, kb_lookups=lookups,
               seconds=round(time.time() - t0, 1),
               finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    print()
    if undetermined:
        print("  Recorded: undetermined by the questions, your own code %s." % free)
    elif free != label:
        print("  Recorded: computed %s, your own %s. Both are kept, and the difference"
              % (label, free))
        print("  is itself a finding about the codebook. Nothing is overridden.")
    else:
        print("  Recorded: %s, confidence %s." % (label, conf))
    return rec


# ----------------------------------------------------------------------------- pilotage
def main():
    sample = load_sample(ARGS.sample)
    kb = json.load(io.open(ARGS.kb, encoding="utf-8"))
    order = list(range(len(sample)))
    random.Random("%d:%s" % (ARGS.seed, ARGS.annotator)).shuffle(order)
    rows = [sample[i] for i in order]

    out = ARGS.out or os.path.join(HERE, "responses_%s.jsonl" % ARGS.annotator)
    done = {}
    if os.path.exists(out):
        for l in io.open(out, encoding="utf-8"):
            if l.strip():
                done[json.loads(l)["id"]] = 1
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
        try:
            rec = interview_item(row, kb, n, len(rows), "%d min elapsed" % mins)
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
    # Un paquet autonome porte ses deux fichiers a cote du script. Hors paquet, ils
    # sont a leur place dans l'artefact.
    def first(*paths):
        for q in paths:
            if os.path.exists(q):
                return q
        return paths[-1]

    p.add_argument("--sample", default=first(
        os.path.join(HERE, "sample_blind.jsonl"),
        os.path.join(ANN, "sample_blind.jsonl")))
    p.add_argument("--kb", default=first(
        os.path.join(HERE, "knowledge_base_observed.json"),
        os.path.join(ROOT, "data", "knowledge_base_observed.json")))
    p.add_argument("--out", default=None)
    p.add_argument("--seed", type=int, default=BASE_SEED)
    p.add_argument("--resume", action="store_true")
    ARGS = p.parse_args()
    sys.exit(main())
