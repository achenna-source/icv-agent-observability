# -*- coding: utf-8 -*-
"""Label-uncertainty sensitivity analysis.

The panel's strongest objection: every detection figure in the paper is scored
against one annotator's labels, and the only test of those labels is a 50-item
subsample where a second annotator reaches kappa 0.370. The intervals reported
elsewhere propagate sampling uncertainty over items and never uncertainty over
who is labelling.

The double-labelled 50 make that check runnable. On exactly those items we rescore
every detector twice, once against each annotator, and report how far the figures
move. We also rescore the two judges against the second annotator as reference,
which asks whether the scale result depends on which human is called the standard.
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
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "artifact", "code"))
import signals            # noqa: E402
from metrics import mcc   # noqa: E402

ROWS = [json.loads(x) for x in
        open(os.path.join(ROOT, "artifact/data/trajectories_200.jsonl"), encoding="utf-8")]
BY_ID = {r["id"]: r for r in ROWS}

A2 = {}
with open(os.path.join(ROOT, "artifact/annotation/annotator2_returned.csv"),
          encoding="utf-8") as f:
    for row in csv.DictReader(f):
        A2[row["id"]] = row["label"].strip().upper()

J32 = {lang: json.load(open(os.path.join(ROOT, "kaggle/out/judge_32b_%s.json" % lang),
                            encoding="utf-8")) for lang in ("fr", "en")}
SUB = sorted(A2)
DIST = {r["label_human"] for r in ROWS}


def traj(r):
    return ast.literal_eval(r["trajectory"]) if isinstance(r["trajectory"], str) \
        else r["trajectory"]


def norm(l):
    """Annotator 2 used F1a/F1b; the first annotator's scheme has no F1 instance.
    Only the failed / not-failed split matters for detector scoring."""
    return (l or "").strip().upper()


print("double-labelled items: %d, distinct trajectories: %d"
      % (len(SUB), len({BY_ID[i]["cluster_id"] for i in SUB})))
print("annotator 2 label counts:", dict(collections.Counter(A2[i] for i in SUB)))
print("annotator 1 label counts:",
      dict(collections.Counter(BY_ID[i]["label_human"] for i in SUB)))
print()

DETECTORS = [
    ("Tier 1 (B)", lambda t: signals.tier1(t)[0]),
    ("Tier 2 (C)", lambda t: signals.tier2(t)[0]),
    ("B or C", lambda t: signals.tier1(t)[0] or signals.tier2(t)[0]),
    ("B* (exempt)", lambda t: signals.tier1_exempt(t)[0]),
    ("B* or C", lambda t: signals.tier1_exempt(t)[0] or signals.tier2(t)[0]),
    ("32B judge", lambda t: None),   # handled separately, not trace-derived
]

print("=== detectors rescored under each annotator, on the same 50 items ===")
print("%-14s %-26s %-26s" % ("", "against annotator 1", "against annotator 2"))
print("%-14s %8s %8s %8s   %8s %8s %8s"
      % ("detector", "prec", "MCC", "FA", "prec", "MCC", "FA"))

for name, fn in DETECTORS:
    out = []
    for who in ("a1", "a2"):
        tp = fp = fn_ = tn = 0
        for i in SUB:
            r = BY_ID[i]
            flag = (norm(J32["fr"][i]["code"]) != "S") if name == "32B judge" \
                else fn(traj(r))
            fail = (norm(A2[i]) != "S") if who == "a2" else (r["label_human"] != "S")
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
    print("%-14s %8.3f %+8.3f %8d   %8.3f %+8.3f %8d"
          % (name, out[0][0], out[0][1], out[0][2],
             out[1][0], out[1][1], out[1][2]))

print()
print("=== base rate on the 50 ===")
for who, get in (("annotator 1", lambda i: BY_ID[i]["label_human"]),
                 ("annotator 2", lambda i: A2[i])):
    nf = sum(1 for i in SUB if norm(get(i)) != "S")
    print("  %-12s failures %2d of %d = %.3f" % (who, nf, len(SUB), nf / len(SUB)))

# ------------------------------------------------ judges against either reference
print()
print("=== the two judges, scored against each annotator in turn ===")


def kappa(ref, pred):
    res = [r if (p not in DIST and r in p) else p for p, r in zip(pred, ref)]
    n = len(ref)
    po = sum(1 for a, b in zip(ref, res) if a == b) / n
    cr, cp = collections.Counter(ref), collections.Counter(res)
    pe = sum(cr[k] * cp[k] for k in set(cr) | set(cp)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


refs = {"annotator 1": [BY_ID[i]["label_human"] for i in SUB],
        "annotator 2": [norm(A2[i]) for i in SUB]}
preds = {"7B judge": [BY_ID[i]["label_judge_7b"] for i in SUB],
         "32B judge": [norm(J32["fr"][i]["code"]) for i in SUB],
         "the other annotator": None}

print("%-12s %14s %14s" % ("reference", "7B judge", "32B judge"))
for rname, ref in refs.items():
    other = refs["annotator 2"] if rname == "annotator 1" else refs["annotator 1"]
    print("%-12s %14.3f %14.3f   (other human: %.3f)"
          % (rname, kappa(ref, preds["7B judge"]), kappa(ref, preds["32B judge"]),
             kappa(ref, other)))
