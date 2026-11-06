# -*- coding: utf-8 -*-
"""L'alignement de l'alarme sur la faute, contre un index humain et non contre un modele.

CE QUE LE COMMENTAIRE 4 DEMANDE, ET CE QUI MANQUAIT

Le relecteur 7 demande les emplacements d'alarme, le delai de detection, la couverture
avant la reponse finale, et si l'alarme designe la premiere erreur ou une anomalie
concomitante. Les deux premieres et la troisieme sont deja dans le manuscrit et ne
demandent aucune annotation. La quatrieme exige l'index de la premiere etape fautive, qui
n'existait que sous la forme d'une annotation produite par des modeles de langue.

La ronde humaine fournit cet index sans modele, mais seulement sur les echecs qu'elle
couvre. Ce script le releve, l'arbitre, et mesure l'alignement sur ce sous-ensemble.

DEUX CHOSES QUI DOIVENT PARAITRE AVEC LE CHIFFRE

La taille. La ronde porte sur cinquante trajectoires, dont une partie seulement sont des
echecs : le chiffre est donc petit et le script l'affiche au lieu de le diluer.

La reproductibilite de la cible elle-meme. Les quatre lecteurs ne s'accordent pas toujours
sur l'etape fautive, et une phrase de la forme "l'alarme tombe exactement sur la faute
dans tant de cas" se mesure contre une cible dont la propre reproductibilite doit etre
donnee. Le script la calcule et refuse de rapporter l'alignement sans elle.

L'etape retenue par item est l'etape unanime quand les quatre lecteurs s'accordent, sinon
celle que l'arbitrage a retenue, et sinon l'item sort du calcul sans etre comble.

Sortie : results/alarm_alignment_human.json

    python experiments/alarm_alignment_human.py
"""
import io
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ART = os.path.dirname(CODE)
IV = os.path.join(ART, "annotation", "interview")
READERS = ("A", "C", "E", "K")

ROWS = {r["id"]: r for r in (json.loads(l) for l in
        io.open(os.path.join(ART, "data", "trajectories_200.jsonl"), encoding="utf-8")
        if l.strip())}
POS = json.load(io.open(os.path.join(ART, "results", "flag_position.json"),
                        encoding="utf-8"))
BYID = {r["id"]: r for r in POS["per_trajectory"]}

recs = {}
for w in READERS:
    q = os.path.join(IV, "responses_%s.jsonl" % w)
    assert os.path.exists(q), "fichier absent : %s" % q
    recs[w] = {json.loads(l)["id"]: json.loads(l)
               for l in io.open(q, encoding="utf-8") if l.strip()}
adj = {}
for name in sorted(os.listdir(IV)):
    if name.startswith("adjudication_") and name.endswith("_computed.jsonl"):
        who = name[len("adjudication_"):-len("_computed.jsonl")]
        for line in io.open(os.path.join(IV, name), encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                adj.setdefault(r["id"], {})[who] = r

shared = sorted(set.intersection(*[set(d) for d in recs.values()]))
fails = [i for i in shared if ROWS[i]["label_human"] != "S"]

# --------------------------------------------- la reproductibilite de la cible
def steps(i):
    return [recs[w][i]["fault_step"] for w in READERS]


exact = sum(1 for i in fails if len(set(steps(i))) == 1)
within = sum(1 for i in fails if max(steps(i)) - min(steps(i)) <= 1)
print()
print("la cible : index de la premiere etape fautive, quatre lecteurs humains")
print("  %d echecs couverts par la ronde sur les %d du corpus"
      % (len(fails), sum(1 for r in ROWS.values() if r["label_human"] != "S")))
print("  accord exact des quatre lecteurs %d/%d, a une etape pres %d/%d"
      % (exact, len(fails), within, len(fails)))
assert len(fails) >= 20, "trop peu d'echecs couverts pour rapporter quoi que ce soit"

# --------------------------------------------- l'etape retenue, sans rien combler
TARGET, undecided = {}, []
for i in fails:
    st = set(steps(i))
    if len(st) == 1:
        TARGET[i] = st.pop()
    elif i in adj:
        # un arbitre non auteur garde la main la ou il a tranche
        who = sorted(adj[i], key=lambda w: (w == "AC", w))
        lab = None
        for w in who:
            if adj[i][w].get("adjudicated_label"):
                lab = w
        if lab is None:
            undecided.append(i)
            continue
        # l'arbitrage porte sur l'etiquette, pas sur l'etape : on retient l'etape du
        # lecteur dont l'etiquette a ete retenue, et l'item sort si elle est ambigue
        chosen = adj[i][lab]["adjudicated_label"]
        cand = {recs[w][i]["fault_step"] for w in READERS
                if recs[w][i]["computed_label"] == chosen}
        if len(cand) == 1:
            TARGET[i] = cand.pop()
        else:
            undecided.append(i)
    else:
        undecided.append(i)

print("  %d items retenus, %d laisses de cote et non combles" % (len(TARGET),
                                                                 len(undecided)))
if undecided:
    print("     %s" % " ".join(undecided))

# --------------------------------------------- l'alignement
SIG = (("B, schema validation", "B"), ("B*, schema with exemption", "Bx"),
       ("C, consistency", "C"))
print()
print("%-26s %6s %7s %7s %9s %s" % ("signal", "TP", "exact", "<=faute", "mediane",
                                    "decalages"))
OUT = {}
for label, key in SIG:
    rows = [(i, BYID[i][key]) for i in sorted(TARGET) if i in BYID]
    tp = [(i, v["at"]) for i, v in rows if v["flag"] and v["at"] is not None]
    if not tp:
        print("%-26s %6d" % (label, 0))
        OUT[label] = {"true_positives": 0}
        continue
    # flag_position indexe les etapes a partir de zero, l'entretien a partir de un
    off = [(at + 1) - TARGET[i] for i, at in tp]
    ex = sum(1 for o in off if o == 0)
    before = sum(1 for o in off if o <= 0)
    med = sorted(off)[len(off) // 2]
    OUT[label] = {"true_positives": len(tp), "exact": ex, "at_or_before": before,
                  "median_offset": med,
                  "offsets": dict(Counter(off)),
                  "items": {i: {"alarm_step": at + 1, "fault_step": TARGET[i],
                                "offset": (at + 1) - TARGET[i]} for i, at in tp}}
    print("%-26s %6d %7d %7d %9d  %s"
          % (label, len(tp), ex, before, med,
             " ".join("%+d:%d" % (k, v) for k, v in sorted(Counter(off).items()))))

res = os.path.join(ART, "results", "alarm_alignment_human.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(
    what_this_is=(
        "Alarm-to-fault alignment measured against a human index of the first faulty "
        "step, taken from the independent round of four readers, on the failures that "
        "round covers. No language model takes part in the target. The figure is small by "
        "construction and the target's own reproducibility is reported beside it, because "
        "a statement of the form 'the alarm lands exactly on the fault in n cases' is "
        "measured against a target that four readers do not always agree on."),
    n_failures_in_corpus=sum(1 for r in ROWS.values() if r["label_human"] != "S"),
    n_failures_covered=len(fails), n_used=len(TARGET),
    excluded_not_settled=undecided,
    target_reproducibility={"readers": list(READERS), "exact": exact,
                            "within_one_step": within, "n": len(fails)},
    alignment=OUT), indent=1, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
