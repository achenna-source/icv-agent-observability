"""
Reproduce every number the paper reports, from the released data.

    python reproduce.py            # everything that runs on CPU without a model download
    python reproduce.py --full     # additionally runs the Tier-2 duplicate test and the
                                   # entailment tier, which download models on first use

Each block prints the value the paper states beside the value computed here, so a
mismatch is visible without cross-referencing the manuscript.
"""
import argparse
import csv
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "code"))
from signals import tier1, tier1_exempt, tier2                      # noqa: E402
from metrics import (wilson, wilson_clustered, design_effect, mcc, balanced_accuracy,
                     kappa_lenient, cluster_bootstrap)                     # noqa: E402

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
    by_id = {r["id"]: r for r in corpus}
    ok_all = True

    print("\n=== Table 1, failure-mode distribution ===")
    dist = Counter(hum)
    for m, exp in [("S", 72), ("F2", 21), ("F3", 69), ("F5", 13), ("F6", 7), ("F7", 18)]:
        ok_all &= check(m, dist.get(m, 0), exp)
    ok_all &= check("distinct trajectories", len(set(clusters)), 130)
    ok_all &= check("design effect", round(design_effect(clusters), 2), 2.34)

    print("\n=== Section VI.B, the 7B judge ===")
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

    print("\n=== Revision R1: Table 3, trajectory-level, with the encoder ===")
    try:
        from sentence_transformers import SentenceTransformer
        enc_r1 = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        enc_r1 = None
        print("     encoder unavailable (%s); Signal C runs without the duplicate test"
              % type(e).__name__)
    Br1 = [tier1(r["trajectory"])[0] for r in corpus]
    Bxr1 = [tier1_exempt(r["trajectory"])[0] for r in corpus]
    Cr1 = [tier2(r["trajectory"], enc_r1)[0] for r in corpus]

    def conf(flags):
        t = sum(1 for i in range(200) if flags[i] and fail[i])
        f = sum(1 for i in range(200) if flags[i] and not fail[i])
        return t, f

    for name, flags, p_tp, p_fp, p_pre, p_mcc in [
            ("B (schema)", Br1, 37, 25, 0.597, -0.060),
            ("C (consistency)", Cr1, 39, 0, 1.000, 0.369),
            ("B or C", [a or b for a, b in zip(Br1, Cr1)], 68, 25, 0.731, 0.177),
            ("B* (exempt)", Bxr1, 21, 0, 1.000, 0.257),
            ("B* or C", [a or b for a, b in zip(Bxr1, Cr1)], 59, 0, 1.000, 0.485)]:
        t, f = conf(flags)
        ok_all &= check("%s: TP" % name, t, p_tp)
        ok_all &= check("%s: FP" % name, f, p_fp)
        ok_all &= check("%s: precision" % name,
                        round(t / (t + f), 3) if t + f else 0.0, p_pre)
        ok_all &= check("%s: MCC" % name,
                        round(mcc(t, f, NF - t, NS - f), 3), p_mcc)

    print("\n=== Revision R1: Table 4 and Figure 6, per mode and per signal ===")
    for m, pb, pc, pu in [("F2", 0, 12, 12), ("F3", 11, 12, 22), ("F5", 13, 1, 13),
                          ("F6", 6, 1, 6), ("F7", 7, 13, 15)]:
        sel = [i for i in range(200) if hum[i] == m]
        ok_all &= check("  %s: B only" % m, sum(1 for i in sel if Br1[i]), pb)
        ok_all &= check("  %s: C only" % m, sum(1 for i in sel if Cr1[i]), pc)
        ok_all &= check("  %s: union" % m,
                        sum(1 for i in sel if Br1[i] or Cr1[i]), pu)

    print("\n=== Revision R1: Section VI.A, the naive success count ===")
    naive = 0
    for r in corpus:
        last = r["trajectory"][-1]
        if last.get("action") == "finish" and                 str(last.get("input") or "").strip() not in ("", "None"):
            naive += 1
    ok_all &= check("naive end-of-run successes", naive, 179)
    ok_all &= check("inspected successes", NS, 72)

    print("\n=== Revision R1: Section IV.B, Signal A on the pilot ===")
    with open(os.path.join(HERE, "results", "signal_a_and_pilot_icv.json"),
              encoding="utf-8") as f:
        icv = json.load(f)
    sa = icv["signal_A"]
    ok_all &= check("Signal A, a priori threshold", sa["threshold_apriori"], 0.9)
    ok_all &= check("Signal A, F1-optimal threshold", sa["threshold_f1opt"], 0.55)

    # Recomputed from the stored per-step entropies through signal_a(), not read back
    # out of the summary. Comparing the summary with the paper compares the same
    # numbers twice and cannot detect a wrong decision rule, which is how an earlier
    # draft came to describe the cross-step aggregation as a mean when it is a maximum.
    from signal_a import signal_a as flag_a                             # noqa: E402
    ent = sa["entropy_stats"]
    pk = sorted(ent, key=lambda k: int(k))
    pfail = {k: ent[k]["annotation"] != "S" for k in pk}
    NFP = sum(pfail.values())
    # the summary stores the per-step maximum, which is the decision variable; passing
    # it as a one-element list makes signal_a apply the same rule it applies in full
    score = {k: [ent[k]["max"]] for k in pk}

    def pilot_prf(th, keys=None):
        keys = pk if keys is None else keys
        hit = {k: flag_a(score[k], th)[0] for k in keys}
        tp = sum(1 for k in keys if hit[k] and pfail[k])
        fp = sum(1 for k in keys if hit[k] and not pfail[k])
        fn = sum(1 for k in keys if not hit[k] and pfail[k])
        if tp == 0:
            return 0.0, 0.0, 0.0
        p, r = tp / (tp + fp), tp / (tp + fn)
        return p, r, 2 * p * r / (p + r)

    p90, r90, f90 = pilot_prf(0.90)
    ok_all &= check("Signal A, a priori precision", round(p90, 2), 0.53)
    ok_all &= check("Signal A, a priori recall", round(r90, 2), 0.47)
    ok_all &= check("Signal A, a priori F1", round(f90, 2), 0.50)
    p55, r55, f55 = pilot_prf(0.55)
    ok_all &= check("Signal A, F1-optimal precision", round(p55, 2), 0.59)
    ok_all &= check("Signal A, F1-optimal recall", round(r55, 2), 1.0)
    ok_all &= check("Signal A, F1-optimal F1", round(f55, 2), 0.74)

    def pilot_ci(th, n_boot=5000, seed=42):
        rng = random.Random(seed)
        vals = []
        for _ in range(n_boot):
            draw = [pk[rng.randrange(len(pk))] for _ in range(len(pk))]
            vals.append(pilot_prf(th, draw)[2])
        vals.sort()
        return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]

    lo90, hi90 = pilot_ci(0.90)
    # wider tolerance: the original resampling order is not preserved in the artifact
    ok_all &= check("Signal A, a priori F1 CI low", round(lo90, 2), 0.26, tol=0.011)
    ok_all &= check("Signal A, a priori F1 CI high", round(hi90, 2), 0.69)
    lo55, hi55 = pilot_ci(0.55)
    ok_all &= check("Signal A, F1-optimal CI low", round(lo55, 2), 0.57)
    ok_all &= check("Signal A, F1-optimal CI high", round(hi55, 2), 0.86)
    for stack, pf1 in [("B", 0.69), ("B+C", 0.79), ("A+B+C", 0.77)]:
        ok_all &= check("pilot F1, %s" % stack,
                        icv["bootstrap_ci"]["results"][stack]["f1"], pf1)
    print("     bootstrap: %d resamples, seed %s"
          % (icv["bootstrap_ci"]["n_boot"], icv["bootstrap_ci"]["seed"]))

    print("\n=== Revision R1: Section VI.B, the two annotators ===")
    import csv as _csv
    import subprocess as _sub
    sys.path.insert(0, os.path.join(HERE, "annotation"))
    import compute_agreement as _ca
    _rows = []
    with open(os.path.join(HERE, "annotation", "annotator2_returned.csv"),
              encoding="utf-8") as _f:
        for _r in _csv.DictReader(_f):
            _tid = _r["id"].strip()
            _rows.append((_tid, _ca.normalise(_r["label"]),
                          _ca.normalise(by_id[_tid]["label_human"])))
    _a2 = [r[1] for r in _rows]
    _a1 = [r[2] for r in _rows]
    _cl = [by_id[r[0]]["cluster_id"] for r in _rows]
    _k, _po, _pe = _ca.kappa(_a1, _a2)
    ok_all &= check("second annotator, items", len(_rows), 50)
    ok_all &= check("second annotator, distinct trajectories", len(set(_cl)), 44)
    ok_all &= check("second annotator, raw agreement", round(_po, 3), 0.460)
    ok_all &= check("second annotator, kappa", round(_k, 3), 0.370)
    _lo, _hi = _ca.bootstrap(_a1, _a2, _cl)
    ok_all &= check("  cluster CI, low", round(_lo, 3), 0.225)
    ok_all &= check("  cluster CI, high", round(_hi, 3), 0.531)
    _judge = [_ca.normalise(by_id[r[0]]["label_judge_7b"]) for r in _rows]
    _kj, _, _ = _ca.kappa(_a1, _judge)
    ok_all &= check("7B judge on the same 50, kappa", round(_kj, 3), 0.129)
    _jlo, _jhi = _ca.bootstrap(_a1, _judge, _cl)
    ok_all &= check("  cluster CI, low", round(_jlo, 3), -0.030)
    ok_all &= check("  cluster CI, high", round(_jhi, 3), 0.293)
    _obs, _dlo, _dhi, _pv = _ca.paired_bootstrap(_a1, _a2, _judge, _cl)
    ok_all &= check("paired difference, annotator minus judge", round(_obs, 3), 0.241)
    ok_all &= check("  paired CI, low", round(_dlo, 3), 0.078)
    ok_all &= check("  paired CI, high", round(_dhi, 3), 0.426)

    print("\n=== Revision R1: Section VI.D, composition standardisation ===")
    pilot_bc = {"F1": (3, 3), "F2": (3, 5), "F3": (0, 1),
                "F4": (0, 2), "F5": (5, 5), "F7": (0, 1)}
    NFp = sum(n for _, n in pilot_bc.values())
    ok_all &= check("pilot failures", NFp, 17)
    ok_all &= check("pilot detected by B or C", sum(d for d, _ in pilot_bc.values()), 11)
    main_rate, w_pilot, common = {}, {}, []
    for m in ("F2", "F3", "F5", "F7"):
        sel = [i for i in range(200) if hum[i] == m]
        main_rate[m] = sum(1 for i in sel if Br1[i] or Cr1[i]) / len(sel)
        w_pilot[m] = pilot_bc[m][1] / NFp
        common.append(m)
    std = (sum(w_pilot[m] * main_rate[m] for m in common)
           / sum(w_pilot[m] for m in common))
    ok_all &= check("main coverage standardised to pilot mix", round(std, 3), 0.751)
    ok_all &= check("main coverage observed", round(68 / NF, 3), 0.531)


    # The 32B scale and language control belongs to a companion manuscript. Its
    # result files are outside the scope of the Neurocomputing submission tag, so the
    # section is skipped there instead of aborting the whole script.
    j32_files = [os.path.join(HERE, "results", f"judge_32b_{lang}.json")
                 for lang in ("fr", "en")]
    if not all(os.path.exists(p) for p in j32_files):
        print("\n=== Section VII.B, the 32B scale and language control ===")
        print("     skipped; this control belongs to a companion manuscript and its")
        print("     result files are not part of this tag.")
    else:
        print("\n=== Section VII.B, the 32B scale and language control ===")
        valid = set(dist)
        j32 = {}
        for lang in ("fr", "en"):
            with open(os.path.join(HERE, "results", f"judge_32b_{lang}.json"),
                      encoding="utf-8") as f:
                j32[lang] = json.load(f)
        a2 = {}
        with open(os.path.join(HERE, "annotation", "annotator2_returned.csv"),
                  encoding="utf-8") as f:
            for line in list(csv.DictReader(f)):
                a2[line["id"]] = line["label"].strip()
        sub = [i for i, r in enumerate(corpus) if r["id"] in a2]

        def kap(idx, get):
            return kappa_lenient([hum[i] for i in idx], [get(i) for i in idx], valid)

        def boot(idx, get):
            items = [(clusters[i], (get(i), hum[i])) for i in idx]
            lo, hi, _ = cluster_bootstrap(
                items, lambda d: kappa_lenient([r for _, r in d], [p for p, _ in d], valid))
            return lo, hi

        getters = {
            "second annotator": lambda i: a2[corpus[i]["id"]],
            "7B judge":         lambda i: jm[i],
            "32B judge, fr":    lambda i: j32["fr"][corpus[i]["id"]]["code"],
            "32B judge, en":    lambda i: j32["en"][corpus[i]["id"]]["code"],
        }
        for name, paper in [("second annotator", 0.370), ("7B judge", 0.129),
                            ("32B judge, fr", 0.421), ("32B judge, en", 0.341)]:
            k = kap(sub, getters[name])
            ok_all &= check(f"kappa on the 50, {name}", round(k, 3), paper)
            print(f"       cluster 95%% CI [%.3f, %.3f]" % boot(sub, getters[name]))

        def paired(idx, a, b):
            items = [(clusters[i], (getters[a](i), getters[b](i), hum[i])) for i in idx]

            def d(draw):
                ref = [r for _, _, r in draw]
                return (kappa_lenient(ref, [x for x, _, _ in draw], valid) -
                        kappa_lenient(ref, [y for _, y, _ in draw], valid))
            lo, hi, vals = cluster_bootstrap(items, d)
            p_le = sum(1 for v in vals if v <= 0) / len(vals)
            return kap(idx, getters[a]) - kap(idx, getters[b]), lo, hi, \
                min(1.0, 2 * min(p_le, 1 - p_le))

        for a, b, paper in [("second annotator", "32B judge, fr", -0.051),
                            ("32B judge, fr", "7B judge", 0.292)]:
            obs, lo, hi, p = paired(sub, a, b)
            ok_all &= check(f"d.kappa, {a} - {b}", round(obs, 3), paper)
            print(f"       cluster 95%% CI [%+.3f, %+.3f], P = %.3f" % (lo, hi, p))

        everything = list(range(200))
        for name, paper in [("32B judge, fr", 0.401), ("32B judge, en", 0.383)]:
            ok_all &= check(f"kappa on the 200, {name}",
                            round(kap(everything, getters[name]), 3), paper)
        obs, lo, hi, p = paired(everything, "32B judge, fr", "32B judge, en")
        ok_all &= check("d.kappa, French - English on the 200", round(obs, 3), 0.018)
        print(f"       cluster 95%% CI [%+.3f, %+.3f], P = %.3f" % (lo, hi, p))

        g32 = getters["32B judge, fr"]
        tp = sum(1 for i in everything if g32(i) != "S" and fail[i])
        fp = sum(1 for i in everything if g32(i) != "S" and not fail[i])
        ok_all &= check("32B as binary detector, precision",
                        round(tp / (tp + fp), 3), 0.906)
        ok_all &= check("32B as binary detector, recall", round(tp / NF, 3), 0.977)
        ok_all &= check("32B as binary detector, MCC",
                        round(mcc(tp, fp, NF - tp, NS - fp), 3), 0.826)
        ok_all &= check("32B as binary detector, false alarms", fp, 13)

        resid = [i for i, r in enumerate(corpus)
                 if hum[i] == "F3" and not (tier1(r["trajectory"])[0]
                                            or tier2(r["trajectory"])[0])]
        ok_all &= check("residual F3 the free tiers leave", len(resid), 47)
        ok_all &= check("32B flags on the residual",
                        sum(1 for i in resid if g32(i) != "S"), 44)
        ok_all &= check("7B flags on the residual",
                        sum(1 for i in resid if jm[i] != "S"), 16)

        print("\n     per mode, matched against the first annotator (Table V)")
        for m, p7, p32 in [("S", 30, 59), ("F2", 0, 21), ("F3", 11, 12),
                           ("F5", 4, 11), ("F6", 0, 0), ("F7", 15, 0)]:
            sel = [i for i in everything if hum[i] == m]

            def matched(get):
                return sum(1 for i in sel
                           if get(i) == m or (get(i) not in valid and m in get(i)))
            ok_all &= check(f"  {m}: matched by 7B", matched(lambda i: jm[i]), p7)
            ok_all &= check(f"  {m}: matched by 32B", matched(g32), p32)

    print("\n=== Additional: the same detectors, scored as in the companion manuscript ===")
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

    print("\n=== Additional, companion manuscript: observability classes ===")
    BC = [B[i] or C[i] for i in range(200)]
    FORM, MEAN = {"F5", "F6", "F7"}, {"F2", "F3"}
    for name, modes, paper in [("c_F", FORM, 0.895), ("c_M", MEAN, 0.378)]:
        idx = [i for i in range(200) if hum[i] in modes]
        d = sum(1 for i in idx if BC[i])
        lo, hi = wilson_clustered(d, len(idx), [clusters[i] for i in idx])
        ok_all &= check(name, round(d / len(idx), 3), paper)
        print(f"       cluster-corrected 95% CI [{lo:.3f}, {hi:.3f}]")

    print("\n=== Additional, companion manuscript: detection lead time ===")
    tp_rows = [(len(r["trajectory"]), tier1(r["trajectory"])[1])
               for i, r in enumerate(corpus) if B[i] and fail[i]]
    early = sum(1 for L, k in tp_rows if L - 1 - k > 0)
    ok_all &= check("Tier 1, true positives firing early", early, 25)
    ok_all &= check("of true positives", len(tp_rows), 37)

    print("\n=== Additional, companion manuscript: entailment tier ===")
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
