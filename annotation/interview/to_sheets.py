# -*- coding: utf-8 -*-
"""Des reponses de l'entretien vers les formats que la chaine existante lit deja.

L'entretien produit un fichier par annotateur, une ligne par trajectoire. Ce script en
tire ce dont les scripts d'accord ont besoin, sans rien decider a la place de personne.

Deux jeux d'etiquettes sortent, et les deux comptent.

  computed : l'etiquette calculee des reponses aux predicats par la regle du codebook.
             C'est la mesure du codebook lui-meme.
  free     : l'etiquette que l'annotateur a donnee de lui-meme, apres les questions mais
             sans y etre tenu. C'est la grandeur comparable a la premiere ronde, qui
             s'etait faite sur une feuille Excel sans questions.

Les comparer repond d'avance a l'objection evidente : si l'accord monte, vient-il des
conventions ecrites ou de l'instrument qui impose l'ordre des regles ?

Un item que les questions ne tranchent pas, parce que la justesse de la reponse est
restee incertaine, sort du jeu computed et y est compte, jamais rempli en douce.

    python -I to_sheets.py

Sorties, sous human_round/ :
  computed/annotations_<X>.csv, computed/labels_<X>.json
  free/annotations_<X>.csv,     free/labels_<X>.json
  localisation.txt, localisation.json
"""
import glob
import io
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "human_round")
QKEYS = ("correct", "fault", "f1a", "f1b", "f2", "f4", "f5", "f6", "f7")


ROSTER = ("A", "B", "C", "D", "E", "K")


def load():
    """Seules les quatre lettres du roster comptent comme annotateurs de la ronde.

    Un fichier porte par un autre identifiant, par exemple la passe de l'auteur ou un
    essai, est lu et signale, jamais melange au roster : il ne doit pas entrer dans un
    chiffre d'accord presente comme une reference humaine independante.
    """
    recs, aside = defaultdict(dict), defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(HERE, "responses_*.jsonl"))):
        who = os.path.basename(path)[len("responses_"):-len(".jsonl")]
        target = recs if who in ROSTER else aside
        for line in io.open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                target[who][r["id"]] = r
    for who, items in sorted(aside.items()):
        print("  hors roster, mis de cote : %s, %d items. Non compte dans la ronde."
              % (who, len(items)))
    return recs


def write_set(which, recs):
    d = os.path.join(OUT, which)
    os.makedirs(d, exist_ok=True)
    dropped = {}
    for who, items in sorted(recs.items()):
        rows, skipped = [], []
        for tid, r in items.items():
            lab = r["computed_label"] if which == "computed" else r["free_label"]
            if not lab:
                skipped.append(tid)
                continue
            rows.append((tid, lab, r["confidence"], r.get("note") or ""))
        rows.sort()
        with io.open(os.path.join(d, "annotations_%s.csv" % who), "w",
                     encoding="utf-8", newline="\n") as fh:
            fh.write("id,label,confidence,notes\n")
            for tid, lab, conf, note in rows:
                note = note.replace('"', "''")
                fh.write('%s,%s,%s,"%s"\n' % (tid, lab, conf, note))
        labels = {tid: dict(label=lab,
                            f3_subcode=items[tid].get("f3_subcode"),
                            note=note)
                  for tid, lab, conf, note in rows}
        io.open(os.path.join(d, "labels_%s.json" % who), "w",
                encoding="utf-8", newline="\n").write(
            json.dumps(labels, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        dropped[who] = skipped
        print("  %-10s %s : %d etiquettes%s"
              % (which, who, len(rows),
                 "" if not skipped else ", %d indetermine(s) : %s"
                 % (len(skipped), " ".join(skipped))))
    return dropped


def localise(recs):
    """Sur quelle question le desaccord nait-il ?"""
    who = sorted(recs)
    shared = set(recs[who[0]]) if who else set()
    for w in who[1:]:
        shared &= set(recs[w])
    first_q = Counter()
    per_item = {}
    for tid in sorted(shared):
        answers = {w: recs[w][tid]["answers"] for w in who}
        labs = {w: recs[w][tid]["computed_label"] for w in who}
        if len(set(labs.values())) == 1:
            continue
        culprit = None
        for q in QKEYS:
            vals = {a.get(q) for a in answers.values() if q in a}
            asked = sum(1 for a in answers.values() if q in a)
            if asked and (len(vals) > 1 or asked != len(who)):
                culprit = q
                break
        first_q[culprit or "aucune: le desaccord vient de l'etiquette libre"] += 1
        per_item[tid] = dict(labels=labs, first_divergent_question=culprit,
                             answers=answers)
    lines = ["LOCALISATION DU DESACCORD", "",
             "  %d annotateurs, %d trajectoires communes" % (len(who), len(shared)),
             "  %d trajectoires ou l'etiquette calculee differe" % len(per_item), ""]
    if per_item:
        lines.append("  premiere question divergente :")
        for q, n in first_q.most_common():
            lines.append("    %-56s %d" % (q, n))
        lines.append("")
        lines.append("  Cette colonne est ce que la feuille Excel ne pouvait pas donner :")
        lines.append("  un desaccord se rapporte a la question qui l'a cause, donc a la")
        lines.append("  phrase du codebook a reecrire, et non seulement a deux codes.")
    else:
        lines.append("  aucun desaccord sur l'etiquette calculee")
    report = "\n".join(lines) + "\n"
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "localisation.txt"), "w",
            encoding="utf-8", newline="\n").write(report)
    io.open(os.path.join(OUT, "localisation.json"), "w",
            encoding="utf-8", newline="\n").write(
        json.dumps(dict(annotators=who, n_shared=len(shared),
                        first_divergent_question=dict(first_q),
                        items=per_item), indent=2, ensure_ascii=False) + "\n")
    print()
    print(report)


def main():
    recs = load()
    if not recs:
        print("aucun fichier responses_*.jsonl dans %s" % HERE)
        return 1
    print("annotateurs : %s" % ", ".join("%s (%d items)" % (w, len(v))
                                         for w, v in sorted(recs.items())))
    print()
    write_set("computed", recs)
    write_set("free", recs)
    localise(recs)
    print("ecrit sous %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
