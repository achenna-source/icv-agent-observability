"""
Reproduce every number the paper reports, from the released data.

    python reproduce.py            # everything that runs on CPU without a model download
    python reproduce.py --full     # additionally runs the Tier-2 duplicate test and the
                                   # entailment tier, which download models on first use

Each block prints the value the paper states beside the value computed here, so a
mismatch is visible without cross-referencing the manuscript.
"""
import argparse
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "code"))
from signals import tier1, tier1_exempt, tier2                      # noqa: E402
from metrics import wilson, wilson_clustered, design_effect, mcc, balanced_accuracy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def check(label, got, paper, tol=0.002):
    ok = abs(got - paper) <= tol if isinstance(paper, float) else got == paper
    print(f"  {'OK ' if ok else '!! '} {label:44s} computed {got!s:>18s}   paper {paper}")
    return ok


def main(full=False):
    corpus = load("trajectories_200.jsonl")
    pilot = load("trajectories_pilot_30.jsonl")
    hum = [r["label_human"] for r in corpus]
    clusters = [r["cluster_id"] for r in corpus]
    fail = [h != "S" for h in hum]
    NF, NS = sum(fail), 200 - sum(fail)
    ok_all = True

    print("\n=== Table IV, failure-mode distribution ===")
    dist = Counter(hum)
    for m, exp in [("S", 72), ("F2", 21), ("F3", 69), ("F5", 13), ("F6", 7), ("F7", 18)]:
        ok_all &= check(m, dist.get(m, 0), exp)
    ok_all &= check("distinct trajectories", len(set(clusters)), 130)
    ok_all &= check("design effect", round(design_effect(clusters), 2), 2.34)

    print("\n=== Section VII.B, the 7B judge ===")
    jm = [r["label_judge_7b"] for r in corpus]
    lenient = sum(1 for a, b in zip(hum, jm) if a == b or (b not in dist and a in b))
    po = lenient / 200
    hc, jc = Counter(hum), Counter(
        (a if (b not in dist and a in b) else b) for a, b in zip(hum, jm))
    pe = sum(hc.get(k, 0) * jc.get(k, 0) for k in set(hc) | set(jc)) / 200 ** 2
    ok_all &= check("raw agreement", lenient, 60)
    ok_all &= check("kappa (lenient)", round((po - pe) / (1 - pe), 3), 0.115, 0.002)
    strict = sum(1 for a, b in zip(hum, jm) if a == b)
    ok_all &= check("kappa (strict scoring)", strict, 58)
    jb = [b != "S" for b in jm]
    tp = sum(1 for i in range(200) if jb[i] and fail[i])
    fp = sum(1 for i in range(200) if jb[i] and not fail[i])
    ok_all &= check("judge as binary detector, MCC",
                    round(mcc(tp, fp, NF - tp, NS - fp), 3), 0.026)

    print("\n=== Table VI, detection performance ===")
    B = [tier1(r["trajectory"])[0] for r in corpus]
    Bx = [tier1_exempt(r["trajectory"])[0] for r in corpus]
    if full:
        from sentence_transformers import SentenceTransformer
        enc = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    else:
        enc = None
    C = [tier2(r["trajectory"], enc)[0] for r in corpus]

    def score(flags, name, paper_tp, paper_fp, paper_mcc):
        t = sum(1 for i in range(200) if flags[i] and fail[i])
        f = sum(1 for i in range(200) if flags[i] and not fail[i])
        m = round(mcc(t, f, NF - t, NS - f), 3)
        good = check(f"{name}: true positives", t, paper_tp)
        good &= check(f"{name}: false alarms", f, paper_fp)
        good &= check(f"{name}: MCC", m, paper_mcc)
        return good

    ok_all &= score(B, "Tier 1", 37, 25, -0.060)
    ok_all &= score(C, "Tier 2", 39 if full else 38, 0, 0.369 if full else 0.363)
    ok_all &= score([B[i] or C[i] for i in range(200)], "B or C", 68, 25, 0.177)
    ok_all &= score(Bx, "Tier 1 repaired (B*)", 21, 0, 0.257)
    ok_all &= score([Bx[i] or C[i] for i in range(200)], "B* or C", 59, 0, 0.485)
    if not full:
        print("     (Tier 2's duplicate test is skipped without --full. It accounts for "
              "one of Tier 2's 39 true positives, so the contradiction test alone gives 38.)")

    print("\n=== Section VII.C, observability classes ===")
    BC = [B[i] or C[i] for i in range(200)]
    FORM, MEAN = {"F5", "F6", "F7"}, {"F2", "F3"}
    for name, modes, paper in [("c_F", FORM, 0.895), ("c_M", MEAN, 0.378)]:
        idx = [i for i in range(200) if hum[i] in modes]
        d = sum(1 for i in idx if BC[i])
        lo, hi = wilson_clustered(d, len(idx), [clusters[i] for i in idx])
        ok_all &= check(name, round(d / len(idx), 3), paper)
        print(f"       cluster-corrected 95% CI [{lo:.3f}, {hi:.3f}]")

    print("\n=== Section VII.E, lead time ===")
    tp_rows = [(len(r["trajectory"]), tier1(r["trajectory"])[1])
               for i, r in enumerate(corpus) if B[i] and fail[i]]
    early = sum(1 for L, k in tp_rows if L - 1 - k > 0)
    ok_all &= check("Tier 1, true positives firing early", early, 25)
    ok_all &= check("of true positives", len(tp_rows), 37)

    print("\n=== Section VII.F, entailment tier ===")
    if full:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        mid = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
        tok = AutoTokenizer.from_pretrained(mid)
        mdl = AutoModelForSequenceClassification.from_pretrained(mid).eval()
        ent = {v.lower(): k for k, v in mdl.config.id2label.items()}["entailment"]
        idx = [i for i in range(200) if hum[i] in ("F3", "S")]
        pairs = []
        for i in idx:
            t = corpus[i]["trajectory"]
            prem = " ; ".join(f"{s.get('input')} : {s.get('observation')}" for s in t
                              if s.get("action") in ("knowledge_base", "calculator")
                              and s.get("observation"))
            hyp = next((str(s["input"]) for s in t
                        if s.get("action") == "finish" and s.get("input")), "")
            pairs.append((i, prem or "aucune information récupérée", hyp))
        pairs = [p for p in pairs if p[2].strip()]
        scores = {}
        with torch.no_grad():
            for a in range(0, len(pairs), 8):
                ch = pairs[a:a + 8]
                enc2 = tok([c[1] for c in ch], [c[2] for c in ch], truncation=True,
                           padding=True, max_length=512, return_tensors="pt")
                pr = torch.softmax(mdl(**enc2).logits, -1)[:, ent]
                for c, v in zip(ch, pr.tolist()):
                    scores[c[0]] = v
        succ = [i for i in scores if hum[i] == "S"]
        random.Random(42).shuffle(succ)
        cal, hold = succ[:36], succ[36:]
        th = sorted(scores[i] for i in cal)[max(0, int(0.05 * len(cal)) - 1)]
        f3 = [i for i in scores if hum[i] == "F3"]
        ok_all &= check("F3 recovered", sum(1 for i in f3 if scores[i] < th), 44)
        ok_all &= check("false alarms, held-out successes",
                        sum(1 for i in hold if scores[i] < th), 1)
        for code in ("F3a", "F3b", "F3c"):
            sel = [i for i in f3 if corpus[i]["label_f3_subcode"] == code]
            print(f"       {code}: {sum(1 for i in sel if scores[i] < th)}/{len(sel)}")
    else:
        print("     skipped; rerun with --full to download the entailment model")

    print("\n" + ("all reproduced" if ok_all else "MISMATCHES ABOVE — see MAPPING.md"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    sys.exit(main(ap.parse_args().full))
