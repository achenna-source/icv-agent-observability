# -*- coding: utf-8 -*-
"""La coincidence drapeau-faute, et l'etayage comme axe independant.

Ce sont les deux mesures que le commentaire 1 du relecteur 7 exigeait et que la Section
VI.C declarait non mesurees. Elles reposent sur une annotation nouvelle des 128 fautes,
produite par trois annotateurs independants, un par modele, dans un dossier isole sans
les etiquettes de reference, sans les sorties des detecteurs et sans le papier. Ces
annotateurs sont des modeles de langue, ce qui est declare partout ou ces chiffres
paraissent.

Pourquoi des lecteurs et non une regle. Deriver l'indice du pas fautif par une regle
mecanique reviendrait a juger les detecteurs contre une cible qu'un detecteur a
fabriquee, exactement la circularite que la Section VI.C declare pour la convention
stricte. Un lecteur qui n'est pas l'instrument evalue n'a pas ce defaut.

Trois mesures.

  1. L'accord entre les trois annotateurs, sur chacun des deux jugements.
  2. La coincidence entre le pas ou le drapeau se leve et le pas fautif de consensus :
     identique, au plus tard, ou apres.
  3. L'etayage comme quatrieme cible de detection, et le controle de coherence contre le
     sous-code F3c du premier annotateur.

Sortie : results/flag_fault_alignment.json
"""
import io
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "code"))
sys.path.insert(0, os.path.join(ROOT, "annotation"))

from metrics import mcc, wilson_clustered                      # noqa: E402

ANN = os.path.join(ROOT, "annotation", "panel")
RATERS = {"A": "opus", "B": "sonnet", "C": "fable"}

ids = json.load(io.open(os.path.join(ANN, "ids_128.json"), encoding="utf-8"))
ann = {k: json.load(io.open(os.path.join(ANN, "faultstep_%s.json" % k),
                            encoding="utf-8")) for k in RATERS}
for k, d in ann.items():
    assert all(i in d for i in ids), k

corpus = {json.loads(l)["id"]: json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()}
pos = json.load(io.open(os.path.join(ROOT, "results", "flag_position.json"),
                        encoding="utf-8"))["per_trajectory"]
pos = {r["id"]: r for r in pos}

out = {"n": len(ids), "raters": RATERS, "notes": {
    "annotators_are_llms": "The three annotators are Claude models, not people. They "
                           "received an isolated packet with the task, the numbered "
                           "steps, the final answer and the complete store, and neither "
                           "the reference labels nor the detector outputs.",
    "why_not_a_rule": "Deriving the faulty step by a mechanical rule would score the "
                      "detectors against a target a detector produced.",
    "human_reference_pending": "The first annotator's own pass over the same 128 "
                               "failures is prepared and not yet returned; it will be "
                               "the human reference for both judgements."}}

print("=" * 78)
print("1. ACCORD ENTRE LES TROIS ANNOTATEURS, %d fautes" % len(ids))
print()
G = {k: [ann[k][i]["grounded"] for i in ids] for k in RATERS}
S = {k: [ann[k][i]["first_faulty_step"] for i in ids] for k in RATERS}
for k in RATERS:
    print("   %-8s etayage %s" % (RATERS[k], dict(Counter(G[k]))))
names = sorted(RATERS)
agree3 = sum(1 for n in range(len(ids))
             if len({G[k][n] for k in names}) == 1)
print()
print("   etayage, unanimite des trois : %d/%d (%.1f%%)"
      % (agree3, len(ids), 100 * agree3 / len(ids)))
for a in range(len(names)):
    for b in range(a + 1, len(names)):
        x, y = names[a], names[b]
        same = sum(1 for n in range(len(ids)) if G[x][n] == G[y][n])
        print("      %s vs %s : %d/%d" % (RATERS[x], RATERS[y], same, len(ids)))

ex3 = sum(1 for n in range(len(ids)) if len({S[k][n] for k in names}) == 1)
w13 = sum(1 for n in range(len(ids))
          if max(S[k][n] for k in names) - min(S[k][n] for k in names) <= 1)
print()
print("   pas fautif, unanimite des trois : %d/%d (%.1f%%), a un pas pres %d/%d (%.1f%%)"
      % (ex3, len(ids), 100 * ex3 / len(ids), w13, len(ids), 100 * w13 / len(ids)))
out["agreement"] = {
    "grounded_unanimous": agree3, "grounded_pairwise": {
        "%s|%s" % (RATERS[names[a]], RATERS[names[b]]):
            sum(1 for n in range(len(ids)) if G[names[a]][n] == G[names[b]][n])
        for a in range(len(names)) for b in range(a + 1, len(names))},
    "step_unanimous": ex3, "step_within_one": w13}

# consensus : majorite pour l'etayage, mediane pour le pas
cons_g, cons_s, ties = {}, {}, []
for n, i in enumerate(ids):
    c = Counter(G[k][n] for k in names).most_common()
    if len(c) > 1 and c[0][1] == c[1][1]:
        ties.append(i)
    cons_g[i] = c[0][0]
    cons_s[i] = int(statistics.median(S[k][n] for k in names))
print("   egalites non tranchees sur l'etayage : %d" % len(ties))
out["grounded_ties"] = ties

print()
print("=" * 78)
print("2. LE DRAPEAU TOMBE-T-IL SUR LA FAUTE")
print()
print("   %-28s %4s %8s %8s %8s %8s"
      % ("signal", "VP", "exact", "<= faute", "apres", "ecart med"))
out["alignment"] = {}
for sig, label in (("B", "B, schema"), ("Bx", "B*, schema with exemption"),
                   ("C", "C, consistency")):
    tp = [i for i in ids if pos[i][sig]["flag"] and pos[i][sig]["at"] is not None]
    if not tp:
        continue
    d = [pos[i][sig]["at"] - cons_s[i] for i in tp]
    exact = sum(1 for x in d if x == 0)
    before = sum(1 for x in d if x <= 0)
    after = sum(1 for x in d if x > 0)
    print("   %-28s %4d %8d %8d %8d %8d"
          % (label, len(tp), exact, before, after, int(statistics.median(d))))
    out["alignment"][label] = dict(true_positives=len(tp), exact=exact,
                                   at_or_before=before, after=after,
                                   median_offset=int(statistics.median(d)),
                                   offsets=dict(Counter(d)))
print()
print("   lecture : un ecart negatif veut dire que le drapeau se leve avant la faute,")
print("   donc sur autre chose. Un ecart positif veut dire qu'il la rate et se leve")
print("   plus tard, typiquement au pas terminal.")

print()
print("=" * 78)
print("3. L'ETAYAGE, AXE INDEPENDANT ET QUATRIEME CIBLE")
print()
t = defaultdict(Counter)
for i in ids:
    t[corpus[i]["label_human"]][cons_g[i]] += 1
for lab in sorted(t):
    print("   auteur %-3s n=%2d : %s" % (lab, sum(t[lab].values()), dict(t[lab])))
out["grounded_by_label"] = {k: dict(v) for k, v in t.items()}

f3c = [i for i in ids if corpus[i].get("label_f3_subcode") == "F3c"]
chk = Counter(cons_g[i] for i in f3c)
print()
print("   controle de coherence, les %d items que le premier annotateur a sous-codes"
      % len(f3c))
print("   F3c, reponse partielle ou non etayee : %s" % dict(chk))
print("   soit %d confirmes non etayes, %.0f%%"
      % (chk["no"], 100 * chk["no"] / len(f3c)))
out["f3c_check"] = dict(n=len(f3c), counts=dict(chk))

# l'etayage comme cible, sur les 200
sys.path.insert(0, os.path.join(ROOT, "code"))
from signals import tier1, tier1_exempt, tier2                   # noqa: E402
try:
    from sentence_transformers import SentenceTransformer
    enc = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except Exception:
    enc = None
all_ids = sorted(corpus)
flags = {"B": {}, "Bx": {}, "C": {}}
for i in all_ids:
    tr = corpus[i]["trajectory"]
    flags["B"][i] = tier1(tr)[0]
    flags["Bx"][i] = tier1_exempt(tr)[0]
    flags["C"][i] = tier2(tr, enc)[0]
# cible : non etaye, parmi les 128 annotees ; les 72 S sont hors annotation
target = {i: (cons_g.get(i) == "no") for i in all_ids}
n_t = sum(target.values())
print()
print("   la cible 'non etaye' compte %d trajectoires sur les 200" % n_t)
print("   %-28s %4s %4s %7s %7s %8s"
      % ("signal", "VP", "FP", "prec", "rapp", "MCC"))
out["grounding_target"] = {"size": n_t, "rows": {}}
for sig, label in (("B", "B, schema"), ("Bx", "B*, schema with exemption"),
                   ("C", "C, consistency")):
    f = flags[sig]
    tp = sum(1 for i in all_ids if f[i] and target[i])
    fp = sum(1 for i in all_ids if f[i] and not target[i])
    nf, ns = n_t, 200 - n_t
    pre = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / nf
    m = mcc(tp, fp, nf - tp, ns - fp)
    print("   %-28s %4d %4d %7.3f %7.3f %8.3f" % (label, tp, fp, pre, rec, m))
    out["grounding_target"]["rows"][label] = dict(tp=tp, fp=fp,
                                                  precision=round(pre, 3),
                                                  recall=round(rec, 3),
                                                  mcc=round(m, 3))
u = {i: flags["B"][i] or flags["C"][i] for i in all_ids}
tp = sum(1 for i in all_ids if u[i] and target[i])
fp = sum(1 for i in all_ids if u[i] and not target[i])
pre = tp / (tp + fp) if tp + fp else 0.0
print("   %-28s %4d %4d %7.3f %7.3f %8.3f"
      % ("B or C", tp, fp, pre, tp / n_t,
         mcc(tp, fp, n_t - tp, 200 - n_t - fp)))
out["grounding_target"]["rows"]["B or C"] = dict(
    tp=tp, fp=fp, precision=round(pre, 3), recall=round(tp / n_t, 3),
    mcc=round(mcc(tp, fp, n_t - tp, 200 - n_t - fp), 3))

res = os.path.join(ROOT, "results", "flag_fault_alignment.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
