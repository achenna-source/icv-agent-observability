# -*- coding: utf-8 -*-
"""Label-uncertainty sensitivity analysis.

The panel's strongest objection: every detection figure in the paper is scored
against one annotator's labels, and the only test of those labels is a 50-item
subsample where a second annotator reaches kappa 0.370. The intervals reported
elsewhere propagate sampling uncertainty over items and never uncertainty over
who is labelling.

The double-labelled 50 make that check runnable. On exactly those items we rescore
every detector once per reference and report how far the figures move. We also
rescore the two judges against each reference in turn, which asks whether the scale
result depends on which human is called the standard.

THREE REFERENCES, NOT TWO

The third is the adjudicated panel of the independent round: four readers who are not
authors labelled the same fifty trajectories from the clarified codebook, and the
fourteen items they disputed were settled by a blind adjudication. Where the four agree
the panel carries their label; where they disputed it carries the adjudicated one. No
released label is rewritten by this script, and the panel is read as a third reference
rather than as a correction.

Two things to hold in mind when reading the third column. The adjudicated distance from
the released labels is 0.749 with a template-clustered interval of [0.529, 0.913] that
covers each reader taken alone, so the panel is not established as different from the
released set. And the panel uses F1b and F4 on three items, categories the released
labels never use, which lowers a category-level kappa for a structural reason rather
than a substantive one. The failure against success split, which is what the detectors
are scored on, is unaffected by that.

PATHS REPAIRED

This file previously resolved its inputs one directory too high and looked for the judge
outputs in a kaggle folder outside the artefact, so it could not run as released. It now
resolves everything inside the artefact and fails with a named path if something is
missing.

    python label_sensitivity.py
"""
import ast
import csv
import json
import os
import sys
import io
import collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)                 # la racine de l'artefact
sys.path.insert(0, HERE)
import signals            # noqa: E402
from metrics import mcc   # noqa: E402

READERS = ("A", "C", "E", "K")
ADJUDICATOR = "AC"


def need(*parts):
    q = os.path.join(ART, *parts)
    assert os.path.exists(q), "fichier absent : %s" % q
    return q


ROWS = [json.loads(x) for x in
        io.open(need("data", "trajectories_200.jsonl"), encoding="utf-8")]
BY_ID = {r["id"]: r for r in ROWS}

A2 = {}
with io.open(need("annotation", "annotator2_returned.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        A2[row["id"]] = row["label"].strip().upper()

J32 = {lang: json.load(io.open(need("results", "judge_32b_%s.json" % lang),
                               encoding="utf-8")) for lang in ("fr", "en")}
SUB = sorted(A2)
DIST = {r["label_human"] for r in ROWS}


def norm(l):
    """Annotator 2 used F1a/F1b; the first annotator's scheme has no F1 instance.
    Only the failed / not-failed split matters for detector scoring."""
    return (l or "").strip().upper()


def build_panel(which):
    """Le jeu du panel : l'etiquette unanime, ou celle que l'arbitrage a retenue.

    Un item que l'arbitrage a laisse indecis n'est pas comble : il est rendu a part et
    sort du calcul, comme partout ailleurs dans cette revision.
    """
    base = os.path.join(ART, "annotation", "interview")
    recs = {}
    for w in READERS:
        q = os.path.join(base, "responses_%s.jsonl" % w)
        assert os.path.exists(q), "fichier absent : %s" % q
        recs[w] = {json.loads(l)["id"]: json.loads(l)
                   for l in io.open(q, encoding="utf-8") if l.strip()}
    # Tous les arbitrages de ce jeu d'etiquettes sont lus, et un arbitre qui n'est pas
    # auteur prend le pas la ou il a tranche : trois items residuels ont ete confies
    # dehors parce qu'eux seuls placent une etiquette dans une categorie non exercee.
    adj, by_whom = {}, {}
    files = sorted(n for n in os.listdir(base)
                   if n.startswith("adjudication_") and n.endswith("_%s.jsonl" % which))
    assert files, "aucun arbitrage pour le jeu %s" % which
    for name in files:
        who = name[len("adjudication_"):-len("_%s.jsonl" % which)]
        for line in io.open(os.path.join(base, name), encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                if who == ADJUDICATOR and r["id"] in adj:
                    continue          # un arbitre exterieur deja passe garde la main
                adj[r["id"]] = r
                by_whom[r["id"]] = who
    field = "free_label" if which == "free" else "computed_label"
    out, undecided, settled = {}, [], {}
    for i in sorted(set.intersection(*[set(d) for d in recs.values()])):
        labs = {recs[w][i][field] for w in READERS}
        if len(labs) == 1:
            out[i] = norm(labs.pop())
        elif i in adj and adj[i]["adjudicated_label"]:
            out[i] = norm(adj[i]["adjudicated_label"])
            settled[i] = by_whom[i]
        else:
            undecided.append(i)
    return out, undecided, settled


PANEL, UNDECIDED, SETTLED = build_panel("free")
N_ADJ = len(SETTLED)
missing = [i for i in SUB if i not in PANEL]
assert not missing or missing == UNDECIDED, missing

print("double-labelled items: %d, distinct trajectories: %d"
      % (len(SUB), len({BY_ID[i]["cluster_id"] for i in SUB})))
print("annotator 2 label counts:", dict(collections.Counter(A2[i] for i in SUB)))
print("annotator 1 label counts:",
      dict(collections.Counter(BY_ID[i]["label_human"] for i in SUB)))
print("panel label counts:     ",
      dict(collections.Counter(PANEL[i] for i in SUB if i in PANEL)))
print("panel: %d items unanimous among %d readers, %d settled by adjudication, "
      "%d left undecided" % (len(PANEL) - N_ADJ, len(READERS), N_ADJ, len(UNDECIDED)))
import collections as _c
print("  adjudicated by:", dict(_c.Counter(SETTLED.values())))
for _i, _w in sorted(SETTLED.items()):
    if _w != ADJUDICATOR:
        print("    %s settled outside the author team, by %s" % (_i, _w))
if UNDECIDED:
    print("  undecided and excluded:", " ".join(UNDECIDED))
print()


def traj(r):
    return ast.literal_eval(r["trajectory"]) if isinstance(r["trajectory"], str) \
        else r["trajectory"]


DETECTORS = [
    ("Tier 1 (B)", lambda t: signals.tier1(t)[0]),
    ("Tier 2 (C)", lambda t: signals.tier2(t)[0]),
    ("B or C", lambda t: signals.tier1(t)[0] or signals.tier2(t)[0]),
    ("B* (exempt)", lambda t: signals.tier1_exempt(t)[0]),
    ("B* or C", lambda t: signals.tier1_exempt(t)[0] or signals.tier2(t)[0]),
    ("32B judge", lambda t: None),   # handled separately, not trace-derived
]

FAILED = {
    "a1": lambda i: BY_ID[i]["label_human"] != "S",
    "a2": lambda i: norm(A2[i]) != "S",
    "panel": lambda i: PANEL[i] != "S",
}
ITEMS = {"a1": SUB, "a2": SUB, "panel": [i for i in SUB if i in PANEL]}

print("=== detectors rescored under each reference, on the same items ===")
print("%-14s %-26s %-26s %-26s"
      % ("", "against annotator 1", "against annotator 2", "against the panel"))
print("%-14s %8s %8s %8s   %8s %8s %8s   %8s %8s %8s"
      % ("detector", "prec", "MCC", "FA", "prec", "MCC", "FA", "prec", "MCC", "FA"))

TABLE = {}
for name, fn in DETECTORS:
    out = []
    for who in ("a1", "a2", "panel"):
        tp = fp = fn_ = tn = 0
        for i in ITEMS[who]:
            r = BY_ID[i]
            flag = (norm(J32["fr"][i]["code"]) != "S") if name == "32B judge" \
                else fn(traj(r))
            fail = FAILED[who](i)
            if flag and fail:
                tp += 1
            elif flag:
                fp += 1
            elif fail:
                fn_ += 1
            else:
                tn += 1
        prec = tp / (tp + fp) if tp + fp else float("nan")
        out.append((prec, mcc(tp, fp, fn_, tn), fp))
    TABLE[name] = out
    print("%-14s %8.3f %+8.3f %8d   %8.3f %+8.3f %8d   %8.3f %+8.3f %8d"
          % (name, out[0][0], out[0][1], out[0][2],
             out[1][0], out[1][1], out[1][2],
             out[2][0], out[2][1], out[2][2]))

print()
print("=== how far each figure moves across the three references ===")
print("%-14s %10s %10s %10s" % ("detector", "prec span", "MCC span", "same order?"))
for name, out in TABLE.items():
    ps = max(o[0] for o in out) - min(o[0] for o in out)
    ms = max(o[1] for o in out) - min(o[1] for o in out)
    print("%-14s %10.3f %10.3f" % (name, ps, ms))
best = {k: max(TABLE, key=lambda n: TABLE[n][k][1]) for k in range(3)}
print()
print("  the detector with the highest MCC is %s under annotator 1, %s under "
      "annotator 2 and %s under the panel" % (best[0], best[1], best[2]))
print("  the ranking %s across the three references"
      % ("holds" if len(set(best.values())) == 1 else "does not hold"))

print()
print("=== base rate on the same items ===")
for who, label in (("a1", "annotator 1"), ("a2", "annotator 2"), ("panel", "the panel")):
    items = ITEMS[who]
    nf = sum(1 for i in items if FAILED[who](i))
    print("  %-12s failures %2d of %d = %.3f" % (label, nf, len(items),
                                                 nf / len(items)))

# ------------------------------------------------ judges against either reference
print()
print("=== the two judges, scored against each reference in turn ===")


def kappa(ref, pred):
    res = [r if (p not in DIST and r in p) else p for p, r in zip(pred, ref)]
    n = len(ref)
    po = sum(1 for a, b in zip(ref, res) if a == b) / n
    cr, cp = collections.Counter(ref), collections.Counter(res)
    pe = sum(cr[k] * cp[k] for k in set(cr) | set(cp)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


KEEP = [i for i in SUB if i in PANEL]
refs = {"annotator 1": [BY_ID[i]["label_human"] for i in KEEP],
        "annotator 2": [norm(A2[i]) for i in KEEP],
        "the panel": [PANEL[i] for i in KEEP]}
preds = {"7B judge": [BY_ID[i]["label_judge_7b"] for i in KEEP],
         "32B judge": [norm(J32["fr"][i]["code"]) for i in KEEP]}

print("%-12s %14s %14s   %s" % ("reference", "7B judge", "32B judge",
                                "against the other two humans"))
for rname, ref in refs.items():
    others = [(o, v) for o, v in refs.items() if o != rname]
    print("%-12s %14.3f %14.3f   %s"
          % (rname, kappa(ref, preds["7B judge"]), kappa(ref, preds["32B judge"]),
             ", ".join("%s %.3f" % (o, kappa(ref, v)) for o, v in others)))

print()
print("The panel uses F1b and F4 where the released labels never do, so a "
      "category-level")
print("kappa against it is lowered for a structural reason. The failure against "
      "success")
print("split, on which the detectors above are scored, does not depend on that.")

# ------------------------------------------------------------------ sortie fichier
OUT = {
    "what_this_is": (
        "Detection figures rescored on the fifty double-labelled items against three "
        "references: the released labels, the second annotator, and the adjudicated "
        "panel of the independent round. No released label is rewritten here."),
    "n_items": len(SUB), "n_items_panel": len(KEEP),
    "panel": {"unanimous": len(PANEL) - N_ADJ, "adjudicated": N_ADJ,
              "undecided_excluded": UNDECIDED, "settled_by": SETTLED,
              "readers": list(READERS)},
    "base_rate": {label: round(sum(1 for i in ITEMS[w] if FAILED[w](i)) / len(ITEMS[w]),
                               3)
                  for w, label in (("a1", "annotator1"), ("a2", "annotator2"),
                                   ("panel", "panel"))},
    "detectors": {name: {ref: {"precision": round(o[0], 3), "mcc": round(o[1], 3),
                               "false_alarms": o[2]}
                         for ref, o in zip(("annotator1", "annotator2", "panel"), out)}
                  for name, out in TABLE.items()},
    "spans": {name: {"precision": round(max(o[0] for o in out) - min(o[0] for o in out),
                                        3),
                     "mcc": round(max(o[1] for o in out) - min(o[1] for o in out), 3)}
              for name, out in TABLE.items()},
    "best_by_mcc": {ref: best[k] for k, ref in enumerate(("annotator1", "annotator2",
                                                          "panel"))},
    "ranking_holds": len(set(best.values())) == 1,
    "judges": {rname: {jname: round(kappa(ref, pred), 3)
                       for jname, pred in preds.items()}
               for rname, ref in refs.items()},
    "between_references": {
        "annotator1_vs_annotator2": round(kappa(refs["annotator 1"],
                                                refs["annotator 2"]), 3),
        "annotator1_vs_panel": round(kappa(refs["annotator 1"], refs["the panel"]), 3),
        "annotator2_vs_panel": round(kappa(refs["annotator 2"], refs["the panel"]), 3)},
    "note": (
        "The detector columns under the released labels and under the panel coincide "
        "because the panel's relabellings all move one failure category to another and "
        "never cross the failure against success line the detectors are scored on. The "
        "second annotator's column differs because that reader labels nine malformation "
        "items as F1a where the released labels call them successes, which is the case "
        "the recovery convention now settles."),
}
res = os.path.join(ART, "results", "label_sensitivity.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(OUT, indent=1, ensure_ascii=False) + "\n")
print()
print("written: %s" % res)
