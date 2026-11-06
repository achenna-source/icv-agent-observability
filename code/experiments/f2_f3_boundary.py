# -*- coding: utf-8 -*-
"""Qu'est-ce qui separe F2 de F3 dans les etiquettes de reference ?

D'ou vient la question. Une clause a ete ajoutee a la convention du pivot : une valeur
fabriquee est F2 quand elle figure dans l'argument d'un appel, et F3c quand elle ne
figure que dans la reponse finale. Quatre lecteurs independants l'ont appliquee. Elle
repare les six trajectoires que la reference appelle F3 et casse les six qu'elle appelle
F2, l'accord par categorie passant de 0,467 a 0,733 sur F3 et de 1,000 a 0,000 sur F2.

Or les douze trajectoires se ressemblent : la valeur inventee est dans l'entree de finish
dans les douze, et dans aucune elle n'entre dans un argument de recherche. Le critere de
l'argument ne peut donc pas les separer. Ce script cherche ce qui les separe reellement,
sur les 200 trajectoires et non sur douze.

Deux predicats mecaniques, calcules de la trace seule :

  invente   la reponse finale affirme un nombre qu'aucune observation n'a rendu.
  ancre     la reponse finale reprend au moins une valeur qu'une observation a rendue.

Le tableau croise ces deux predicats avec l'etiquette de reference. Si une regle separe
F2 de F3, elle apparait la.

Sortie : results/f2_f3_boundary.json
"""
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
assert len(corpus) == 200

ABSENT = ("information non trouv", "none", "")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def numbers(s):
    """Les nombres d'un texte, y compris la forme 'N millions', en entiers.

    Les milliers ecrits avec une espace, 500 000, sont recolles avant extraction : sans
    cela 500 000 se lit 500 puis 000, et les deux tombent sous le seuil.
    """
    t = norm(s).replace(",", ".")
    t = re.sub(r"(?<=\d)[   ](?=\d{3}(?!\d))", "", t)
    out = set()
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(millions?|milliers?)?", t):
        v, unit = m.group(1), m.group(2)
        try:
            x = float(v)
        except ValueError:
            continue
        if unit and unit.startswith("million"):
            x *= 1e6
        elif unit and unit.startswith("milli"):
            x *= 1e3
        out.add(int(round(x)))
    return {n for n in out if n >= 1000}          # les annees et petits indices ecartes


def observed(tr):
    """Ce que le magasin a reellement rendu dans cette trajectoire."""
    vals = []
    for s in tr:
        o = s.get("observation")
        if o is None:
            continue
        if any(norm(o).startswith(a) for a in ABSENT if a):
            continue
        if norm(o) in ("", "none"):
            continue
        vals.append(str(o))
    return vals


def final_answer(tr):
    for s in tr:
        if s.get("action") == "finish":
            return str(s.get("input") or "")
    return ""


def tool_args(tr):
    """Les arguments des appels autres que finish."""
    return [str(s.get("input") or "") for s in tr
            if s.get("action") not in (None, "finish", "None", "")]


rows = {}
for r in corpus:
    tr = r["trajectory"]
    ans = final_answer(tr)
    obs = observed(tr)
    obs_nums = set()
    for o in obs:
        obs_nums |= numbers(o)
    ans_nums = numbers(ans)
    invented = sorted(ans_nums - obs_nums)
    anchored = [o for o in obs if norm(o) and norm(o) in norm(ans)]
    arg_nums = set()
    for a in tool_args(tr):
        arg_nums |= numbers(a)
    rows[r["id"]] = dict(
        label=r["label_human"], subcode=r["label_f3_subcode"],
        invented_in_answer=bool(invented), invented_values=invented,
        anchored_in_answer=bool(anchored), anchored_values=anchored[:3],
        invented_in_a_tool_argument=bool(arg_nums - obs_nums),
        answer=ans[:120])

out = {"question": ("What separates F2 from F3 in the reference labels, given that the "
                    "argument criterion cannot?")}

print("=" * 78)
print("1. LE CRITERE DE L'ARGUMENT, SUR LES 200")
print()
n_arg = sum(1 for v in rows.values() if v["invented_in_a_tool_argument"])
print("   trajectoires ou un nombre inexistant entre dans un argument autre que finish")
print("   : %d sur 200" % n_arg)
by = Counter(v["label"] for v in rows.values() if v["invented_in_a_tool_argument"])
print("   leurs etiquettes de reference : %s"
      % (", ".join("%s %d" % kv for kv in sorted(by.items())) or "aucune"))
print()
print("   La categorie F2 s'appelle hallucination d'argument d'outil. Si le critere de")
print("   l'argument la decrivait, les trajectoires F2 seraient ici.")
f2_ids = [i for i, v in rows.items() if v["label"] == "F2"]
f2_arg = [i for i in f2_ids if rows[i]["invented_in_a_tool_argument"]]
print("   trajectoires F2 de la reference : %d, dont %d avec un nombre inexistant dans"
      % (len(f2_ids), len(f2_arg)))
print("   un argument de recherche.")
out["argument_criterion"] = dict(
    trajectories_with_an_invented_number_in_a_retrieval_argument=n_arg,
    their_reference_labels=dict(by), reference_F2_total=len(f2_ids),
    reference_F2_matching_the_argument_criterion=len(f2_arg))

print()
print("=" * 78)
print("2. CE QUI SEPARE REELLEMENT F2 DE F3")
print()
print("   invente = la reponse finale affirme un nombre qu'aucune observation n'a rendu")
print("   ancre   = la reponse finale reprend une valeur qu'une observation a rendue")
print()
tab = defaultdict(Counter)
for i, v in rows.items():
    tab[(v["invented_in_answer"], v["anchored_in_answer"])][v["label"]] += 1
print("   invente  ancre   n    etiquettes de reference")
for k in sorted(tab, key=lambda k: (-sum(tab[k].values()))):
    inv, anc = k
    print("   %-8s %-6s %-4d %s"
          % ("oui" if inv else "non", "oui" if anc else "non", sum(tab[k].values()),
             ", ".join("%s %d" % kv for kv in sorted(tab[k].items()))))
out["cross_tabulation"] = {
    "invented_%s__anchored_%s" % (k[0], k[1]): dict(v) for k, v in tab.items()}

print()
cell_f2 = tab[(True, False)]
cell_f3 = tab[(True, True)]
print("   Lecture. Parmi les trajectoires dont la reponse finale affirme un nombre")
print("   inexistant, celles dont la reponse n'est ancree sur rien se repartissent en")
print("   %s, et celles dont une partie est ancree en %s."
      % (", ".join("%s %d" % kv for kv in sorted(cell_f2.items())),
         ", ".join("%s %d" % kv for kv in sorted(cell_f3.items()))))
print()
print("   Le critere de la reference n'est donc pas la position de la valeur inventee,")
print("   mais la presence ou l'absence d'une partie ancree dans la reponse finale.")

tot_f2 = sum(cell_f2.values())
tot_f3 = sum(cell_f3.values())
out["the_rule_the_reference_actually_applied"] = {
    "wholly_invented_answer": {"n": tot_f2, "labels": dict(cell_f2),
                               "share_F2": round(cell_f2.get("F2", 0) / tot_f2, 3)
                               if tot_f2 else None},
    "partly_grounded_answer_with_an_invented_part": {
        "n": tot_f3, "labels": dict(cell_f3),
        "share_F3": round(cell_f3.get("F3", 0) / tot_f3, 3) if tot_f3 else None},
    "statement": ("On the trajectories whose final answer asserts a number no "
                  "observation returned, the reference uses F2 when nothing in the "
                  "answer is grounded and F3 when part of it is. Neither the pivot test "
                  "nor the position of the invented value distinguishes them, and the "
                  "name of F2, tool argument hallucination, does not describe them."),
}

print()
print("=" * 78)
print("3. LES DOUZE TRAJECTOIRES DU LOT DE 50 QUI ONT FAIT APPARAITRE LA QUESTION")
print()
ids50 = [json.loads(l)["id"] for l in
         io.open(os.path.join(ROOT, "annotation", "sample_blind.jsonl"),
                 encoding="utf-8") if l.strip()]
key = {json.loads(l)["id"]: json.loads(l)["label_annotator1"] for l in
       io.open(os.path.join(ROOT, "annotation", "sample_key_DO_NOT_SHARE.jsonl"),
               encoding="utf-8") if l.strip()}
twelve = [i for i in ids50 if key[i] in ("F2", "F3")
          and rows[i]["invented_in_answer"]]
print("   id     ref  invente  ancre  argument  reponse")
for i in twelve:
    v = rows[i]
    print("   %-6s %-4s %-8s %-6s %-9s %s"
          % (i, key[i], "oui" if v["invented_in_answer"] else "non",
             "oui" if v["anchored_in_answer"] else "non",
             "oui" if v["invented_in_a_tool_argument"] else "non", v["answer"][:46]))
out["the_twelve_in_the_sample"] = {
    i: dict(reference=key[i], invented_in_answer=rows[i]["invented_in_answer"],
            anchored_in_answer=rows[i]["anchored_in_answer"],
            invented_in_a_tool_argument=rows[i]["invented_in_a_tool_argument"])
    for i in twelve}

agree = sum(1 for i in twelve
            if (key[i] == "F2") == (not rows[i]["anchored_in_answer"]))
print()
print("   La regle ancre-ou-non reproduit l'etiquette de reference sur %d de ces %d."
      % (agree, len(twelve)))
out["the_twelve_in_the_sample"]["rule_reproduces"] = "%d of %d" % (agree, len(twelve))

print()
print("=" * 78)
print("4. LE CONFOND DE GABARIT, QUI DECIDE CE QUE LA REGLE VAUT")
print()
print("   Une regle lue des etiquettes ne vaut comme frontiere que si le corpus la met")
print("   en concurrence a l'interieur d'un gabarit. Voici d'ou viennent les deux")
print("   cellules.")
print()
tpl = defaultdict(Counter)
for r in corpus:
    v = rows[r["id"]]
    if v["invented_in_answer"]:
        tpl[(r["template"], v["anchored_in_answer"])][v["label"]] += 1
print("   gabarit  ancre   etiquettes de reference")
for k in sorted(tpl):
    print("   %-8s %-7s %s"
          % (k[0], "oui" if k[1] else "non",
             ", ".join("%s %d" % kv for kv in sorted(tpl[k].items()))))
anch_t = sorted({r["template"] for r in corpus
                 if rows[r["id"]]["invented_in_answer"]
                 and rows[r["id"]]["anchored_in_answer"]})
f2_t = sorted({r["template"] for r in corpus if r["label_human"] == "F2"})
f7_t = sorted({r["template"] for r in corpus if r["label_human"] == "F7"})
print()
print("   les trajectoires inventees et ancrees viennent de : %s" % " ".join(anch_t))
print("   les trajectoires F2 de la reference viennent de    : %s" % " ".join(f2_t))
print("   les trajectoires F7 de la reference viennent de    : %s" % " ".join(f7_t))
print()
print("   La regle de l'ancrage separe donc %s de %s. C'est le confond decrit en VI.B :"
      % (" ".join(anch_t), " ".join(f2_t)))
print("   un predicat qui separe ces gabarits separe les etiquettes parfaitement sans")
print("   rien dire de la frontiere. La clause est une reparation de documentation, qui")
print("   permet de reproduire les etiquettes, et non une frontiere etablie.")
out["template_confound"] = {
    "by_template": {"%s|%s" % (k[0], "anchored" if k[1] else "unanchored"): dict(v)
                    for k, v in tpl.items()},
    "invented_and_anchored_templates": anch_t,
    "reference_F2_templates": f2_t,
    "reference_F7_templates": f7_t,
    "statement": ("The anchoring rule separates the templates the two cells come from, "
                  "so it reproduces the labels without putting the categories in "
                  "competition. It is a documentation fix, not an established "
                  "boundary."),
}

print()
print("=" * 78)
print("5. LES COMPTES CITES DANS LE MANUSCRIT ET DANS LA LETTRE")
print()
anch = tab[(True, True)]
unanch = tab[(True, False)]
checks = [
    ("inventees et ancrees, total", sum(anch.values()), 25),
    ("inventees et ancrees, etiquetees F3", anch.get("F3", 0), 25),
    ("inventees non ancrees, total", sum(unanch.values()), 38),
    ("inventees non ancrees, F2", unanch.get("F2", 0), 17),
    ("inventees non ancrees, F7", unanch.get("F7", 0), 13),
    ("inventees non ancrees, F3", unanch.get("F3", 0), 6),
    ("inventees non ancrees, S", unanch.get("S", 0), 2),
    ("F2 de la reference", len(f2_ids), 21),
    ("F2 avec un nombre inexistant dans un argument", len(f2_arg), 0),
    ("trajectoires avec un nombre inexistant dans un argument", n_arg, 15),
]
bad = []
for name, got, want in checks:
    ok = got == want
    print("   %-4s %-46s %3d, attendu %3d" % ("ok" if ok else "ECART", name, got, want))
    if not ok:
        bad.append(name)
assert sum(anch.values()) == anch.get("F3", 0), (
    "la cellule ancree n'est plus homogene : la clause ne tient plus")
assert anch_t == ["T3"] and f2_t == ["T2"], (anch_t, f2_t)
assert not bad, "comptes cites qui ne tiennent plus : %s" % ", ".join(bad)
out["quoted_counts_hold"] = {name: got for name, got, _ in checks}
print()
print("   Les comptes cites dans le manuscrit et dans la lettre tiennent tous.")

res = os.path.join(ROOT, "results", "f2_f3_boundary.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
