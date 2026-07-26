"""
Human-human agreement, once the second annotator returns their sheet.

    python compute_agreement.py annotations_annotator2.csv

Reads the returned sheet and the held-back key, and reports raw agreement, Cohen's
kappa with a bootstrap interval, agreement per category, the confusion matrix, and the
list of disagreements for adjudication.

Two conventions are applied and both are reported, because the choice moves the figure:
F1a and F1b collapse to F1 (the first annotator's scheme did not split them at labelling
time), and an F3 sub-code in the notes column is read as F3.
"""
import argparse
import csv
import json
import math
import os
import random
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
VALID = {"S", "F1", "F1a", "F1b", "F2", "F3", "F3a", "F3b", "F3c", "F4", "F5", "F6", "F7"}


def normalise(label):
    l = (label or "").strip().upper().replace(" ", "")
    if l.startswith("F1"):
        return "F1"
    if l.startswith("F3"):
        return "F3"
    return l


def kappa(a, b):
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return (po - pe) / (1 - pe) if pe != 1 else float("nan"), po, pe


def bootstrap(a, b, n_boot=5000, seed=42):
    rng = random.Random(seed)
    n = len(a)
    out = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        k, _, _ = kappa([a[i] for i in idx], [b[i] for i in idx])
        if not math.isnan(k):
            out.append(k)
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def main(sheet):
    key = {}
    with open(os.path.join(HERE, "sample_key_DO_NOT_SHARE.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                key[r["id"]] = r["label_annotator1"]

    if sheet.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        ws = load_workbook(sheet, data_only=True)["annotations"]
        head = [str(c.value or "").strip().lower() for c in next(ws.iter_rows(max_row=1))]
        returned = [dict(zip(head, [c.value for c in row]))
                    for row in ws.iter_rows(min_row=2) if row[0].value]
    elif sheet.lower().endswith((".csv", ".txt")):
        with open(sheet, encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            # Excel in some locales writes semicolons
            delim = ";" if sample.count(";") > sample.count(",") else ","
            returned = list(csv.DictReader(f, delimiter=delim))
    else:
        raise SystemExit(f"unrecognised sheet format: {sheet}")

    rows, bad, blank = [], [], 0
    if True:
        for r in returned:
            tid = str(r.get("id") or "").strip()
            raw = str(r.get("label") or "").strip()
            if not tid:
                continue
            if tid not in key:
                bad.append((tid, "id not in the sample"))
                continue
            if not raw:
                blank += 1
                continue
            if raw.upper().replace(" ", "") not in {v.upper() for v in VALID}:
                bad.append((tid, raw))
                continue
            rows.append((tid, normalise(raw), normalise(key[tid])))

    print(f"returned {len(rows)} labels of {len(key)}; {blank} blank, {len(bad)} unrecognised")
    for tid, raw in bad:
        print(f"   unrecognised: {tid} -> {raw!r}")
    if len(rows) < 20:
        print("too few labels to report agreement")
        return

    a2 = [r[1] for r in rows]
    a1 = [r[2] for r in rows]
    k, po, pe = kappa(a1, a2)
    lo, hi = bootstrap(a1, a2)
    print(f"\nraw agreement  {po:.3f}   ({sum(1 for x, y in zip(a1, a2) if x == y)}/{len(rows)})")
    print(f"expected       {pe:.3f}")
    print(f"Cohen's kappa  {k:.3f}   bootstrap 95% CI [{lo:.3f}, {hi:.3f}]")
    print("  Landis and Koch: <0 poor, 0-.20 slight, .21-.40 fair, .41-.60 moderate, "
          ".61-.80 substantial, >.80 almost perfect")

    print("\nper category (annotator 1's label as the reference)")
    by = defaultdict(lambda: [0, 0])
    for _, x, y in rows:
        by[y][1] += 1
        if x == y:
            by[y][0] += 1
    for lab in sorted(by):
        m, n = by[lab]
        print(f"  {lab:4s} {m:3d}/{n:3d} = {m/n:.3f}")

    labels = sorted(set(a1) | set(a2))
    print("\nconfusion (rows annotator 1, columns annotator 2)")
    print("      " + "".join(f"{l:>6s}" for l in labels))
    conf = defaultdict(Counter)
    for _, x, y in rows:
        conf[y][x] += 1
    for l in labels:
        print(f"  {l:4s}" + "".join(f"{conf[l].get(c, 0):6d}" for c in labels))

    dis = [(t, y, x) for t, x, y in rows if x != y]
    out = os.path.join(HERE, "disagreements.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "annotator1", "annotator2", "adjudicated", "rule_applied", "notes"])
        for t, one, two in dis:
            w.writerow([t, one, two, "", "", ""])
    print(f"\n{len(dis)} disagreements written to {os.path.basename(out)} for adjudication")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", nargs="?", default=os.path.join(HERE, "annotations_annotator2.csv"))
    main(ap.parse_args().sheet)
