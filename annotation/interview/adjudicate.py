# -*- coding: utf-8 -*-
"""L'arbitrage de la ronde humaine, aveugle a qui a produit quelle etiquette.

Ce que le relecteur demande. Une evaluation multi-annotateurs "with adjudication". Sans
arbitrage, la ronde rend un desaccord et s'arrete la. Avec lui, elle rend deux chiffres :
ce que le codebook obtient seul, avant arbitrage, et ce qu'un panel obtient, apres. La
lettre promet les deux, et promet aussi que l'arbitre "sees the label sets without knowing
which annotator produced which". Ce fichier tient cette promesse par construction et non
par discipline.

Comment l'aveuglement est obtenu.

  Pour chaque item en litige, les lecteurs sont presentes comme Reader 1, Reader 2, dans
  un ordre tire du hasard du systeme et non d'une graine. Une graine fixe figurant dans un
  script publie laisserait l'arbitre recalculer la correspondance, et l'aveuglement ne
  tiendrait plus qu'a ce qu'il ne lise pas le script. Un ordre neuf a chaque item empeche
  en outre de suivre un lecteur d'un item au suivant, ce qu'un ordre fixe permettrait meme
  sans les lettres.

  La correspondance entre les positions affichees et les lettres A a D est ecrite dans un
  fichier a part, marque DO_NOT_SHARE, pour que l'aveuglement soit auditable apres coup
  sans etre visible pendant. L'ecran ne la contient jamais, et le script le verifie.

  Les notes des lecteurs sont montrees, parce qu'elles portent le motif du desaccord,
  mais elles sont anonymisees avec les etiquettes et affichees dans le meme ordre tire.

Ce que l'arbitre decide, et ce qu'il ne decide pas. Il choisit une etiquette parmi celles
que les lecteurs ont proposees, ou None s'il juge que le codebook ne tranche pas. Il ne
peut pas inventer une categorie qu'aucun lecteur n'a ecrite : un arbitrage qui cree une
etiquette nouvelle est une troisieme annotation, pas un arbitrage.

L'arbitre ne voit a aucun moment les etiquettes de reference, qui ne sont pas dans ce
dossier.

    python -I -X utf8 adjudicate.py --adjudicator X
    python -I -X utf8 adjudicate.py --adjudicator X --free      arbitre les etiquettes libres

Sorties : adjudication_<X>.jsonl, et mapping_adjudication_DO_NOT_SHARE.json
"""
import argparse
import io
import json
import os
import random
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)

# L'ordre d'affichage des lecteurs n'est pas tire d'une graine fixe. Une graine ecrite
# dans un script publie laisserait l'arbitre recalculer la correspondance, donc
# l'aveuglement ne tiendrait qu'a ce qu'il ne lise pas ce fichier. Le tirage est pris du
# systeme et n'est reconstituable que par le fichier DO_NOT_SHARE, ou il est consigne.
SHUFFLE = random.SystemRandom()
ROSTER = ("A", "B", "C", "D", "E", "K")
FREE_LABELS = ("S", "F1a", "F1b", "F2", "F3", "F4", "F5", "F6", "F7")
WIDTH = 78


def first(*paths):
    for q in paths:
        if os.path.exists(q):
            return q
    return paths[-1]


def load_sample(path):
    return [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]


def load_responses():
    """Les passes du roster seules. Toute autre lettre est lue, signalee, ecartee."""
    recs, aside = {}, {}
    for who in sorted(os.listdir(HERE)):
        if not (who.startswith("responses_") and who.endswith(".jsonl")):
            continue
        name = who[len("responses_"):-len(".jsonl")]
        d = {}
        for line in io.open(os.path.join(HERE, who), encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                d[r["id"]] = r
        if name in ROSTER:
            recs[name] = d
        else:
            aside[name] = d
    for name, d in sorted(aside.items()):
        print("  hors roster, ecarte de l'arbitrage : %s, %d items" % (name, len(d)))
    return recs


def label_of(rec, which):
    return rec["free_label"] if which == "free" else rec["computed_label"]


def disputed(recs, which):
    """Les items ou les lecteurs qui ont repondu ne donnent pas la meme etiquette."""
    shared = None
    for d in recs.values():
        s = set(d)
        shared = s if shared is None else (shared & s)
    out = []
    for tid in sorted(shared or ()):
        labs = {w: label_of(recs[w][tid], which) for w in recs}
        if len({v for v in labs.values() if v} ) > 1:
            out.append(tid)
    return out


def render_trajectory(row):
    out = ["", "TASK", "  %s" % row["task"], "", "TRAJECTORY"]
    for k, s in enumerate(row["trajectory"], 1):
        out.append("  Step %d." % k)
        for field in ("thought", "action", "input", "observation"):
            v = s.get(field)
            out.append("    %-12s %s" % (field, "None" if v is None else str(v)))
    return "\n".join(out)


def ask(prompt, allowed, row, conv):
    while True:
        try:
            a = input("%s " % prompt).strip()
        except EOFError:
            return "save"
        if not a:
            continue
        low = a.lower()
        if low == "steps":
            print(render_trajectory(row))
            continue
        if low in ("?", "rules"):
            print(conv)
            continue
        if low in ("save", "skip"):
            return low
        for x in allowed:
            if a == x or low == x.lower():
                return x
        print("  reponses possibles : %s, ou skip, save, steps, ?"
              % ", ".join(allowed))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--adjudicator", required=True)
    p.add_argument("--free", action="store_true",
                   help="arbitrer les etiquettes libres au lieu des calculees")
    p.add_argument("--sample", default=first(
        os.path.join(HERE, "sample_blind.jsonl"),
        os.path.join(ANN, "sample_blind.jsonl")))
    args = p.parse_args()
    which = "free" if args.free else "computed"

    recs = load_responses()
    if len(recs) < 2:
        print()
        print("  %d passe(s) du roster dans %s." % (len(recs), HERE))
        print("  L'arbitrage demande au moins deux lecteurs. Il n'y a rien a arbitrer")
        print("  tant que les annotateurs n'ont pas rendu.")
        return 1

    sample = {r["id"]: r for r in load_sample(args.sample)}
    conv = ("\n  The adjudicator applies the same codebook as the readers. Choose among "
            "the\n  labels the readers wrote. Choose u only if the codebook does not "
            "settle it.\n")

    out_path = os.path.join(HERE, "adjudication_%s_%s.jsonl" % (args.adjudicator, which))
    done = set()
    if os.path.exists(out_path):
        for line in io.open(out_path, encoding="utf-8"):
            if line.strip():
                done.add(json.loads(line)["id"])

    items = [t for t in disputed(recs, which) if t not in done]
    print()
    print("  Adjudicator %s, %s labels, %d readers, %d disputed items, %d already done."
          % (args.adjudicator, which, len(recs), len(disputed(recs, which)), len(done)))
    print("  You never see which reader is which. The display order is drawn afresh")
    print("  for every item, so a reader cannot be followed from one item to the next.")
    print("  Commands: a label, u for undecided, steps, ?, skip, save.")
    if not items:
        print()
        print("  rien a arbitrer.")
        return 0
    try:
        input("\n  Enter to begin. ")
    except EOFError:
        return 0

    mapping_path = os.path.join(HERE, "mapping_adjudication_DO_NOT_SHARE.json")
    mapping = {}
    if os.path.exists(mapping_path):
        mapping = json.load(io.open(mapping_path, encoding="utf-8"))

    fh = io.open(out_path, "a", encoding="utf-8", newline="\n")
    for n, tid in enumerate(items, 1):
        row = sample[tid]
        order = list(recs)
        SHUFFLE.shuffle(order)
        mapping.setdefault(which, {})[tid] = {"Reader %d" % (k + 1): w
                                              for k, w in enumerate(order)}
        shown = []
        print()
        print("=" * WIDTH)
        print(" ADJUDICATION   item %d of %d   %s" % (n, len(items), tid))
        print("=" * WIDTH)
        print(render_trajectory(row))
        print()
        print("THE READERS DISAGREE")
        for k, w in enumerate(order, 1):
            r = recs[w][tid]
            lab = label_of(r, which) or "undetermined"
            shown.append(lab)
            print("  Reader %d : %-12s confidence %-6s" % (k, lab, r.get("confidence")))
            note = (r.get("note") or "").strip()
            if note:
                print("             note: %s" % note)
        choices = sorted({l for l in shown if l and l != "undetermined"})
        print()
        t0 = time.time()
        a = ask("  Q. Which label does the codebook give? [%s / u]"
                % " / ".join(choices), tuple(choices) + ("u",), row, conv)
        if a == "save":
            break
        if a == "skip":
            continue
        why = ""
        try:
            why = input("  One line on why, for the record: ").strip()
        except EOFError:
            pass
        fh.write(json.dumps(
            dict(id=tid, which=which, adjudicator=args.adjudicator,
                 labels_seen=shown, adjudicated_label=None if a == "u" else a,
                 undecided=(a == "u"), rationale=why,
                 seconds=round(time.time() - t0, 1)),
            ensure_ascii=False) + "\n")
        fh.flush()
    fh.close()
    io.open(mapping_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(mapping, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print()
    print("  ecrit : %s" % out_path)
    print("  la correspondance des positions est dans %s, jamais affichee"
          % os.path.basename(mapping_path))
    print("  ensuite : python -I -X utf8 adjudication_agreement.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
