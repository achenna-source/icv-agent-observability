# -*- coding: utf-8 -*-
"""Les six frontieres du bloc F2, F3, F6, F7, chacune contre sa base.

Le relecteur 7 demande les distinctions entre F2, F3, F6 et F7. Quatre categories font six
frontieres, et il faut les traiter toutes, y compris F3 contre F7 qui est la plus grosse
case de desaccord des deux lecteurs. Le protocole est celui de la Section III.A : une
frontiere n'est retenue que si une regle lue de la trace reproduit les etiquettes.

Le test est volontairement genereux envers la taxonomie. Pour chaque frontiere on essaie
tous les predicats ci-dessous, dans les deux sens, et on garde le meilleur, choisi apres
avoir vu les etiquettes. Un tel choix surestime ce qu'une regle ecrite d'avance obtiendrait.
Si meme ce maximum n'atteint pas la base de la categorie majoritaire, la frontiere n'est pas
une procedure.

Sortie : results/boundary_map.json
"""
import io
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "code"))
sys.path.insert(0, HERE)

from signals import TOOLS                                       # noqa: E402
# content_boundaries imprime son propre rapport a l'import ; on le tait sans toucher a
# sys.stdout, que ce module reconfigure.
import contextlib                                              # noqa: E402
import os as _os                                               # noqa: E402
with contextlib.redirect_stdout(io.open(_os.devnull, "w", encoding="utf-8")):
    from content_boundaries import (answer, asserts, declines, held, complete, names,
                                    terms, values, usable)

corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
assert len(corpus) == 200
BLOCK = ["F2", "F3", "F6", "F7"]
sub = [r for r in corpus if r["label_human"] in BLOCK]


def obs_values(tr):
    v = set()
    for s in tr:
        u = usable(s)
        if u:
            v |= values(u)
    return v


def novel(tr):
    ans = answer(tr)
    return values(ans or "") - obs_values(tr)


def reconstructible(tr):
    o = list(obs_values(tr))
    out = set()
    for v in novel(tr):
        for a in o:
            for b in o:
                if min(abs(v - (a + b)), abs(v - abs(a - b)),
                       abs(v - (a + b) // 2)) < 1000:
                    out.add(v)
    return out


def arg_novel(r):
    known = terms(r["task"])
    for s in r["trajectory"]:
        if s.get("action") in ("knowledge_base", "calculator"):
            if terms(s.get("input")) - known:
                return True
        u = usable(s)
        if u:
            known |= terms(u)
    return False


def contradicts(r):
    tr = r["trajectory"]
    ans = answer(tr)
    if ans is None:
        return False
    nums, nms = set(), set()
    for v in held(tr):
        nums |= values(v)
        nms |= names(v)
    a_nums, a_nms = values(ans), names(ans)
    if a_nums and nums and not (a_nums & nums):
        return True
    return bool(a_nms and nms and not (a_nms & nms))


PREDICATES = {
    "the calculator is called":
        lambda r: any(s.get("action") == "calculator" for s in r["trajectory"]),
    "a retrieval came back on an absence":
        lambda r: not complete(r["trajectory"]),
    "no usable value was ever obtained":
        lambda r: not held(r["trajectory"]),
    "the final answer declines":
        lambda r: declines(answer(r["trajectory"])),
    "the final answer asserts a value":
        lambda r: asserts(answer(r["trajectory"]), r["task"]),
    "the final answer is empty or absent":
        lambda r: not (answer(r["trajectory"]) or "").strip(),
    "the answer carries a quantity no observation supplied":
        lambda r: bool(novel(r["trajectory"])),
    "that quantity is not reconstructible from the retrieved values":
        lambda r: bool(novel(r["trajectory"]) - reconstructible(r["trajectory"])),
    "the answer conflicts with a value the agent held": contradicts,
    "a tool argument introduces a term from nowhere": arg_novel,
    "the trajectory contains a malformed step":
        lambda r: any(s.get("action") not in TOOLS for s in r["trajectory"]),
    "the trajectory runs more than three steps":
        lambda r: len(r["trajectory"]) > 3,
    "two or more retrievals succeeded":
        lambda r: len(held(r["trajectory"])) >= 2,
}

print("=" * 78)
print("LES SIX FRONTIERES DU BLOC, %d TRAJECTOIRES" % len(sub))
print()
print("Un prealable decide la lecture du reste. Une frontiere n'est mise a l'epreuve par")
print("le corpus que si les deux categories apparaissent dans un meme gabarit de tache.")
print("Sinon, n'importe quel predicat qui distingue les gabarits les separe parfaitement,")
print("sans rien dire de la frontiere elle-meme.")
print()
tmpl = {}
for lab in BLOCK:
    tmpl[lab] = {r["template"] for r in sub if r["label_human"] == lab}
    print("  %s : gabarits %s" % (lab, " ".join(sorted(tmpl[lab]))))
print()

rows = []
for i, a in enumerate(BLOCK):
    for b in BLOCK[i + 1:]:
        shared = sorted(tmpl[a] & tmpl[b])
        two = [r for r in sub if r["label_human"] in (a, b)
               and r["template"] in shared]
        name = "%s/%s" % (a, b)
        if not shared:
            all_two = [r for r in sub if r["label_human"] in (a, b)]
            rows.append(dict(pair=name, shared_templates=[], n_shared=0,
                             n_all=len(all_two), testable=False,
                             note="the two categories never occur in the same template, "
                                  "so this corpus never forces a choice between them"))
            print("  %-7s AUCUN GABARIT COMMUN. %d trajectoires au total, mais la"
                  % (name, len(all_two)))
            print("          frontiere n'est jamais exercee : %s contre %s."
                  % (" ".join(sorted(tmpl[a])), " ".join(sorted(tmpl[b]))))
            continue
        na = sum(1 for r in two if r["label_human"] == a)
        baseline = max(na, len(two) - na) / len(two)
        best = (0.0, None, None)
        for pname, fn in PREDICATES.items():
            for sense in (True, False):
                ok = sum(1 for r in two
                         if (bool(fn(r)) == sense) == (r["label_human"] == a))
                if ok / len(two) > best[0]:
                    best = (ok / len(two), pname,
                            "%s when it %s" % (a, "holds" if sense else "does not hold"))
        rows.append(dict(pair=name, shared_templates=shared, n_shared=len(two),
                         n_first=na, testable=True,
                         best_rate=round(best[0], 3), baseline=round(baseline, 3),
                         gain=round(best[0] - baseline, 3),
                         predicate=best[1], direction=best[2],
                         reproduces=bool(best[0] > baseline)))
        print("  %-7s gabarits communs %s, n=%d (%d %s, %d %s)"
              % (name, " ".join(shared), len(two), na, a, len(two) - na, b))
        print("          meilleur %.3f   base %.3f   %s"
              % (best[0], baseline, "gain %+.3f" % (best[0] - baseline)
                 if best[0] > baseline else "aucun gain"))
        print("          %s, %s" % (best[1], best[2]))
print()
testable = [r for r in rows if r["testable"]]
beats = [r for r in testable if r["reproduces"]]
print("  frontieres que le corpus exerce : %d des 6" % len(testable))
print("  parmi elles, celles ou le meilleur predicat depasse sa base : %d" % len(beats))
for r in beats:
    print("     %s, %+0.3f, avec %s" % (r["pair"], r["gain"], r["predicate"]))
print()
print("  MULTIPLICITE. Six frontieres ont ete examinees, et pour chacune le predicat a ete")
print("  choisi apres avoir vu les etiquettes. Le p intra-paire de 0,012 de F3 contre F7")
print("  devient %.3f corrige sur les six, donc aucune des six frontieres n'est etablie."
      % min(1, 0.012 * 6))
print("  La frontiere F3 contre F7 reste la seule candidate, et elle est rapportee comme")
print("  exploratoire et non comme une convention.")
print()
print("  Les quatre frontieres impliquant F2 ou F6 contre F7 ne sont pas exercees : F2")
print("  n'apparait que dans T2 et F7 que dans T7. La separation parfaite obtenue sans")
print("  ce prealable est un artefact du gabarit, non une regle de decision.")

out = dict(n=len(sub), counts=dict(Counter(r["label_human"] for r in sub)),
           templates_by_label={k: sorted(v) for k, v in tmpl.items()},
           pairs=rows, n_testable=len(testable), n_reproducing=len(beats),
           protocol="for each pair, every predicate is tried in both directions and the "
                    "best is kept after seeing the labels, which overstates what a rule "
                    "written in advance would achieve",
           predicates=sorted(PREDICATES),
           multiplicity=dict(pairs_examined=6, best_within_pair_p=0.012,
                             family_wise_p=round(min(1, 0.012 * 6), 3),
                             consequence="no boundary in the block is established once "
                                         "the search over six pairs is accounted for"),
           verdict="of the six boundaries inside the block the reviewer names, this "
                   "corpus exercises only %d, because F2 occurs in one template and F7 "
                   "in another; of those exercised, %d exceed the majority baseline even "
                   "under a post hoc choice of rule" % (len(testable), len(beats)))
res = os.path.join(ROOT, "results", "boundary_map.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
