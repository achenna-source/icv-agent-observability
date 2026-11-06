# -*- coding: utf-8 -*-
"""Ou se trouve le desaccord des deux lecteurs, et ce que chaque clarification rachete.

Le relecteur 7 lit le kappa de 0,370 comme une incertitude sur les frontieres de
categories, et demande de clarifier la convention de reprise puis les distinctions entre
F2, F3, F6 et F7. Les 50 doubles annotations disent ou le desaccord se trouve, et ce
script le decompose. Aucune etiquette n'est modifiee.

  1. la part du desaccord qui tombe a l'interieur du bloc F2, F3, F6, F7
  2. la part qui tombe sur F1, c'est-a-dire sur la convention de reprise
  3. l'echelle des kappas obtenus en appliquant la convention de reprise, puis en fondant
     des categories, pour voir ce que chaque clarification rachete reellement

Un controle est inclus parce qu'il a trouve une erreur. La version soumise annonce que
fondre F2 et F7 apres la convention de reprise porte le kappa a 0,793. Ce chiffre ne se
reproduit pas : le calcul correct donne 0,601. Les valeurs proches de 0,793 ne s'obtiennent
qu'en gardant au denominateur l'accord attendu du schema a sept categories alors que le
numerateur est deja fondu, ce qui gonfle le resultat. Le script recalcule les deux termes
ensemble et refuse de passer si l'ecart reapparait.

Sortie : results/boundary_localisation.json
"""
import csv
import io
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

ret = {r["id"]: r["label"] for r in csv.DictReader(
    io.open(os.path.join(ROOT, "annotation", "annotator2_returned.csv"),
            encoding="utf-8"))}
corpus = {json.loads(l)["id"]: json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()}
pairs = [(corpus[i]["label_human"], ret[i]) for i in ret]
assert len(pairs) == 50, len(pairs)


def kappa(ps, pe_override=None):
    n = len(ps)
    po = sum(1 for a, b in ps if a == b) / n
    ca, cb = Counter(a for a, _ in ps), Counter(b for _, b in ps)
    pe = pe_override if pe_override is not None else sum(
        ca[k] / n * cb[k] / n for k in set(ca) | set(cb))
    return (po - pe) / (1 - pe), po, pe


BLOCK = {"F2", "F3", "F6", "F7"}


def is_f1(x):
    return x.startswith("F1")


dis = [(a, b) for a, b in pairs if a != b]
inside = [p for p in dis if p[0] in BLOCK and p[1] in BLOCK]
on_f1 = [p for p in dis if is_f1(p[0]) or is_f1(p[1])]
other = [p for p in dis if p not in inside and p not in on_f1]
k0, po0, pe0 = kappa(pairs)

print("=" * 78)
print("1. OU SE TROUVE LE DESACCORD")
print()
print("   accord brut %.3f, kappa %.3f, accord attendu %.3f, %d trajectoires, %d desaccords"
      % (po0, k0, pe0, len(pairs), len(dis)))
print("   dans le bloc F2, F3, F6, F7 : %d des %d, soit %.0f pour cent"
      % (len(inside), len(dis), 100 * len(inside) / len(dis)))
print("   sur F1, donc la convention de reprise : %d des %d, soit %.0f pour cent"
      % (len(on_f1), len(dis), 100 * len(on_f1) / len(dis)))
print("   ailleurs : %d" % len(other))
print("   bloc : %s" % dict(Counter("%s vers %s" % p for p in inside)))
print("   F1   : %s" % dict(Counter("%s vers %s" % p for p in on_f1)))
assert len(inside) + len(on_f1) + len(other) == len(dis)

RECOVERY = [(a, ("S" if is_f1(b) else b)) for a, b in pairs]


def fold(ps, group):
    g = set(group)
    return [("|".join(sorted(g)) if a in g else a,
             "|".join(sorted(g)) if b in g else b) for a, b in ps]


print()
print("=" * 78)
print("2. CE QUE CHAQUE CLARIFICATION RACHETE")
print()
ladder = []


def step(name, ps):
    k, po, pe = kappa(ps)
    ladder.append(dict(step=name, kappa=round(k, 3), raw=round(po, 3),
                       expected=round(pe, 3)))
    print("   %-52s kappa %.3f  accord %.3f  attendu %.3f" % (name, k, po, pe))
    return k


step("as submitted, seven categories", pairs)
step("recovery convention, a recovered malformation is not F1", RECOVERY)
k_f27 = step("  and F2 against F7 taken as one decision", fold(RECOVERY, ("F2", "F7")))
step("  and the whole block F2, F3, F6, F7 taken as one", fold(RECOVERY, BLOCK))
print()
step("F2 against F7 as one decision, without the recovery convention",
     fold(pairs, ("F2", "F7")))
step("the block as one, without the recovery convention", fold(pairs, BLOCK))

print()
print("=" * 78)
print("3. CONTROLE DU CHIFFRE DE 0,793 ANNONCE DANS LA VERSION SOUMISE")
print()
stale, po_stale, _ = kappa(fold(RECOVERY, ("F2", "F7")), pe_override=pe0)
stale_blk, po_blk, _ = kappa(fold(pairs, BLOCK), pe_override=pe0)
print("   valeur correcte, convention puis fusion F2 et F7      %.3f" % k_f27)
print("   meme fusion avec l'accord attendu du schema a sept    %.3f  (numerateur %.3f)"
      % (stale, po_stale))
print("   bloc entier fondu avec cet accord attendu conserve    %.3f  (numerateur %.3f)"
      % (stale_blk, po_blk))
print()
print("   0,793 ne se reproduit par aucun calcul coherent des deux termes.")
print("   Il s'approche seulement en gardant l'accord attendu de %.3f, celui du schema" % pe0)
print("   a sept categories, sous un numerateur deja fondu. La valeur a publier est %.3f."
      % k_f27)
assert abs(k_f27 - 0.793) > 0.05, "le chiffre soumis se reproduirait, revoir la conclusion"

out = dict(n=50, kappa=round(k0, 3), raw=round(po0, 3), expected=round(pe0, 3),
           disagreements=len(dis), inside_block=len(inside), on_F1=len(on_f1),
           elsewhere=len(other),
           block_detail=dict(Counter("%s->%s" % p for p in inside)),
           f1_detail=dict(Counter("%s->%s" % p for p in on_f1)),
           ladder=ladder,
           submitted_figure_check=dict(
               claimed=0.793, correct=round(k_f27, 3),
               with_stale_expected_agreement=round(stale, 3),
               block_with_stale_expected_agreement=round(stale_blk, 3),
               verdict="the 0.793 reported in the submitted version does not reproduce; "
                       "it is approached only by keeping the seven-category expected "
                       "agreement in the denominator of a collapsed numerator"))
res = os.path.join(ROOT, "results", "boundary_localisation.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
