# -*- coding: utf-8 -*-
"""Les quatre conventions du codebook clarifie, verifiees contre les 200 etiquettes.

Le relecteur 7 demande de clarifier la convention de reprise et les frontieres entre F2,
F3, F6 et F7. Une clarification n'a de valeur que si elle enonce la procedure reellement
appliquee, et cela se teste : chaque convention doit etre vraie des etiquettes publiees,
sans exception, sinon ce n'est pas une clarification mais un changement de regle.

Les quatre conventions.

  C1  une malformation ne determine jamais l'etiquette.
  C2  la premiere faute dans le temps gouverne, et non le premier test de la table.
  C3  le test du pivot exige un calcul : une valeur fabriquee et seulement rapportee est
      F2, une valeur fabriquee et calculee avec est F7.
  C4  un rapport veridique d'absence est un succes.

Aucun annotateur n'intervient ici. Les predicats sont lus des trajectoires et des
etiquettes du depot, et chaque convention est acceptee ou refutee par comptage.

Sortie : results/conventions_check.json
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

from signals import TOOLS, _recovers                        # noqa: E402

corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
assert len(corpus) == 200
by = {r["id"]: r for r in corpus}

ABSENT = set(json.load(io.open(os.path.join(ROOT, "data", "knowledge_base.json"),
                               encoding="utf-8"))["populations_absent_by_design"])
REFUSAL = ("non trouve", "pas trouve", "pas pu trouver", "introuvab", "non trouv",
           "pas d'information", "aucune information", "insuffisante")

out = {"n": 200, "conventions": {}}
fail = 0


def verdict(name, claim, holds, counter, required=True):
    """required=False : la propriete est testee pour etre rapportee, non pour tenir.

    C3 est dans ce cas. Le manuscrit ne l'enonce pas comme convention, il rapporte son
    echec, donc un echec de C3 ne doit pas faire echouer le script.
    """
    global fail
    tag = ("OK" if holds else "REFUTE") if required else (
        "NOTE" if not holds else "NOTE")
    print("   %-4s %s" % (tag, claim))
    for k, v in counter.items():
        print("        %-46s %s" % (k, v))
    out["conventions"][name] = dict(claim=claim, holds=bool(holds),
                                    required=bool(required), evidence=dict(counter))
    if not holds and required:
        fail += 1


def malformed(tr):
    return [k for k, s in enumerate(tr)
            if s.get("action") is None or s.get("action") not in TOOLS]


def norm(s):
    s = (s or "").lower()
    return re.sub(r"[^a-z0-9 ]", "", s)


print("=" * 78)
print("C1. UNE MALFORMATION NE DETERMINE JAMAIS L'ETIQUETTE")
print()
with_mal = [r for r in corpus if malformed(r["trajectory"])]
labels = Counter(r["label_human"] for r in with_mal)
rec = [r for r in with_mal if _recovers(
    r["trajectory"][malformed(r["trajectory"])[0] + 1:])]
verdict("C1", "aucune trajectoire contenant une malformation ne porte F1",
        labels.get("F1", 0) == 0,
        {"trajectoires avec une malformation": len(with_mal),
         "dont la premiere est reprise": len(rec),
         "parmi les reprises, etiquetees S": sum(
             1 for r in rec if r["label_human"] == "S"),
         "etiquettes portees par ces trajectoires": dict(labels)})

print()
print("=" * 78)
print("C2. LA PREMIERE FAUTE DANS LE TEMPS GOUVERNE")
print()
# Testable sur un cas decidable : une malformation precede une faute de contenu. Si la
# table primait, l'etiquette serait F1 ; si le temps prime hors malformation, c'est la
# categorie de la faute de contenu. C1 ayant montre que F1 est vide, le temps gouverne
# deja hors malformation. Ce qui reste a verifier est que F4 n'est jamais attribue a une
# malformation repetee, que la table placerait avant.
rep_mal = [r for r in corpus if len(malformed(r["trajectory"])) > 1]
verdict("C2", "une malformation repetee n'est jamais etiquetee F4",
        all(r["label_human"] != "F4" for r in rep_mal),
        {"trajectoires avec au moins deux malformations": len(rep_mal),
         "leurs etiquettes": dict(Counter(r["label_human"] for r in rep_mal)),
         "F4 dans tout le corpus": sum(
             1 for r in corpus if r["label_human"] == "F4")})

print()
print("=" * 78)
print("C3. LE TEST DU PIVOT EXIGE UN CALCUL")
print()
# Deux lectures sont testees et les deux echouent, ce qui est le resultat.
#   lecture a : F7 passe par le calculateur, F2 non.
#   lecture b : la reponse de F7 porte un nombre derive, celle de F2 un nombre rapporte.
from signals import _numbers                                   # noqa: E402


def uses_calc(tr):
    return any(s.get("action") == "calculator" for s in tr)


def obs_nums(tr):
    s = set()
    for st in tr:
        o = st.get("observation")
        if o not in (None, "Information non trouvee", "Information non trouvée"):
            s |= _numbers(str(o))
    return s


def fin_nums(tr):
    last = tr[-1]
    return _numbers(str(last.get("input") or ""))         if last.get("action") == "finish" else set()


def shape(tr):
    o, f = obs_nums(tr), fin_nums(tr)
    if not f:
        return "no number in the answer"
    novel = [v for v in f if v not in o]
    if not novel:
        return "every number came from an observation"
    if any(any(abs(v - (a + b)) < 1000 or abs(v - abs(a - b)) < 1000
               or abs(v - (a + b) // 2) < 1000 for a in o for b in o) for v in novel):
        return "novel number, reconstructible from observations"
    return "novel number, not reconstructible"


f7 = [r for r in corpus if r["label_human"] == "F7"]
f2 = [r for r in corpus if r["label_human"] == "F2"]
calc_sep = (all(uses_calc(r["trajectory"]) for r in f7)
            and not any(uses_calc(r["trajectory"]) for r in f2))
sh7, sh2 = Counter(shape(r["trajectory"]) for r in f7),     Counter(shape(r["trajectory"]) for r in f2)
shape_sep = set(sh7) & set(sh2) == set()
verdict("C3", "une regle lue de la trace separe F2 de F7 (rapportee, non requise)",
        calc_sep or shape_sep, required=False, counter=
        {"F7, trajectoires": len(f7),
         "F7 avec un appel calculator": sum(1 for r in f7 if uses_calc(r["trajectory"])),
         "F2, trajectoires": len(f2),
         "F2 avec un appel calculator": sum(1 for r in f2 if uses_calc(r["trajectory"])),
         "lecture a, le calculateur separe": calc_sep,
         "forme numerique des reponses F7": dict(sh7),
         "forme numerique des reponses F2": dict(sh2),
         "lecture b, la forme numerique separe": shape_sep,
         "cause de fond": "F2 n'apparait que dans T2 et F7 que dans T7, donc le corpus "
                          "ne met jamais les deux categories en concurrence ; voir "
                          "boundary_map.py"})

print()
print("=" * 78)
print("C4. UN RAPPORT VERIDIQUE D'ABSENCE EST UN SUCCES")
print()
# Les taches portant une entite absente par construction, dont la reponse finale refuse
# sans avancer de valeur, doivent etre etiquetees S.
cand = []
for r in corpus:
    task = norm(r["task"])
    if not any(a in task for a in ABSENT):
        continue
    last = r["trajectory"][-1]
    if last.get("action") != "finish":
        continue
    ans = str(last.get("input") or "")
    if not any(w in norm(ans) for w in REFUSAL):
        continue
    if re.search(r"\d{5,}", ans.replace(" ", "")):
        continue
    cand.append(r)
lab = Counter(r["label_human"] for r in cand)
verdict("C4", "un refus veridique sans valeur avancee est etiquete S",
        set(lab) <= {"S"},
        {"trajectoires correspondantes": len(cand), "leurs etiquettes": dict(lab)})


print()
print("=" * 78)
print("C5. ENTRE F7 ET LE F3 RESIDUEL, UNE TRAJECTOIRE SANS VALEUR EXPLOITABLE EST F3")
print()
# Validee dans T7 seulement, le seul gabarit ou F3 et F7 apparaissent tous deux. Hors de
# T7 la regle n'est pas testable, et le manuscrit en limite la portee a cette decision.
ABSENCE_MARK = "Information non trouv"


def _usable(step):
    o = step.get("observation")
    if o is None:
        return False
    o = str(o).strip()
    return bool(o) and not o.startswith("Erreur") and ABSENCE_MARK not in o


t7 = [r for r in corpus if r["template"] == "T7" and r["label_human"] in ("F3", "F7")]
held_any = {r["id"]: any(_usable(s) for s in r["trajectory"]) for r in t7}
ok = sum(1 for r in t7
         if (r["label_human"] == "F3") == (not held_any[r["id"]]))
n_f3 = sum(1 for r in t7 if r["label_human"] == "F3")
base = max(n_f3, len(t7) - n_f3) / len(t7)
# C5 est rapportee, non requise, et deux faits la privent du statut de convention.
# D'abord la multiplicite : le predicat a ete choisi apres avoir vu les etiquettes, parmi
# six frontieres, donc le p intra-paire de 0,012 devient 0,072 corrige sur les six.
# Ensuite la portee : le predicat vaut pour 73 trajectoires du corpus, dont 30 succes et
# 21 F2, donc il ne signifie rien par lui-meme et ne sert que de depart entre F3 et F7.
n_pred = sum(1 for r in corpus if not any(_usable(st) for st in r["trajectory"]))
lab_pred = Counter(r["label_human"] for r in corpus
                   if not any(_usable(st) for st in r["trajectory"]))
verdict("C5", "dans T7, l'absence de toute valeur exploitable donne F3 et non F7 "
              "(exploratoire, non requise)",
        ok / len(t7) > base, required=False, counter=
        {"trajectoires de T7 etiquetees F3 ou F7": len(t7),
         "dont F3": n_f3,
         "trajectoires classees correctement par la regle": ok,
         "taux de la regle": round(ok / len(t7), 3),
         "base de la categorie majoritaire": round(base, 3),
         "p de permutation intra-paire, recherche de predicat incluse": 0.012,
         "p corrige sur les six frontieres examinees": round(min(1, 0.012 * 6), 3),
         "trajectoires du corpus ou le predicat vaut": n_pred,
         "leurs etiquettes": dict(lab_pred),
         "portee": "cette decision seulement. Le predicat vaut pour 73 trajectoires, "
                   "dont 30 succes et 21 F2, donc il ne porte aucun sens par lui-meme "
                   "et ne vaut que comme depart entre F3 et F7, apres que la decision "
                   "a ete reduite a ces deux categories"})

res = os.path.join(ROOT, "results", "conventions_check.json")
out["all_hold"] = fail == 0
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("=" * 78)
print("ecrit : %s" % res)
print("LES QUATRE CONVENTIONS REQUISES TIENNENT" if fail == 0
      else "%d CONVENTION(S) REFUTEE(S) : ne pas les ecrire telles quelles" % fail)
print("C3 est rapportee comme refutee et C5 comme exploratoire : aucune des deux")
print("n'est requise, et aucune ne compte comme un echec du script.")
sys.exit(1 if fail else 0)
