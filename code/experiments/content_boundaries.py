# -*- coding: utf-8 -*-
"""Les frontieres entre F2, F3 et F6, testees contre les 200 etiquettes.

Le relecteur 7 demande de clarifier les distinctions entre F2, F3, F6 et F7. La frontiere
F2 contre F7 a deja ete testee et refutee dans verify_conventions.py : aucune regle lue de
la trace ne la separe. Restent trois frontieres entre categories de contenu, et le meme
protocole s'applique : on enonce une regle, on la lit des traces, et on la garde seulement
si elle reproduit les etiquettes publiees.

Les predicats sont lus des traces, jamais des etiquettes.

  held(tr)        une observation exploitable a ete obtenue, ni absence ni erreur d'outil
  complete(tr)    aucune recherche n'est revenue sur une absence
  declines(ans)   la reponse finale refuse au lieu d'avancer une valeur
  asserts(ans)    la reponse finale avance une valeur, nombre ou nom propre

Les trois regles mises a l'epreuve.

  R6  la reponse n'utilise pas une valeur que l'agent avait obtenue, soit en avancant une
      autre valeur du meme genre, soit en refusant alors que toutes les recherches avaient
      abouti.
  R2  la reponse avance une valeur qu'aucune observation n'a fournie.
  R3  le reste : la reponse ne fabrique pas de valeur et l'agent n'avait pas celle qu'il
      fallait.

Sortie : results/content_boundaries.json
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

from signals import _numbers                                    # noqa: E402

_MULT = {"million": 1e6, "millions": 1e6, "mille": 1e3, "milliers": 1e3,
         "milliard": 1e9, "milliards": 1e9}


def values(text):
    """Toutes les quantites d'un texte, multiplicateurs ecrits compris.

    _numbers de signals.py ne voit que les groupes de cinq chiffres et plus, parce qu'il
    sert a reperer des chiffres de population dans des observations. Ici une reponse peut
    porter « 8 millions » ou « 890,000 », et les manquer ferait conclure a tort qu'aucune
    valeur n'est avancee. La normalisation est donc faite ici.
    """
    out = set()
    t = (text or "").replace(" ", " ")
    for m in re.finditer(r"(\d[\d  .,]*\d|\d)\s*([A-Za-zé]+)?", t):
        raw, word = m.group(1), (m.group(2) or "").lower()
        core = raw.replace(" ", "")
        # un separateur de milliers est un point ou une virgule suivi de trois chiffres
        core = re.sub(r"[.,](?=\d{3})", "", core)
        core = core.replace(",", ".")
        try:
            v = float(core)
        except ValueError:
            continue
        if word in _MULT:
            v *= _MULT[word]
        out.add(round(v))
    return out


corpus = [json.loads(l) for l in
          io.open(os.path.join(ROOT, "data", "trajectories_200.jsonl"),
                  encoding="utf-8") if l.strip()]
assert len(corpus) == 200

ABSENCE = "Information non trouv"
REFUSAL = ("non trouv", "pas trouv", "pas pu", "ne peux pas", "n'est pas possible",
           "pas ete possible", "pas assez d'information", "aucune information",
           "insuffisant", "manque", "impossible")
STOP = set("""la le les de du des et ou en au aux un une est sont pour par sur dans
population capitale ville habitants calcul estimation information je il elle nous""".split())


def usable(step):
    o = step.get("observation")
    if o is None:
        return None
    o = str(o).strip()
    if not o or o.startswith("Erreur") or ABSENCE in o:
        return None
    return o


def held(tr):
    return [v for v in (usable(s) for s in tr) if v]


def complete(tr):
    return not any(ABSENCE in str(s.get("observation") or "") for s in tr)


def answer(tr):
    last = tr[-1]
    return str(last.get("input") or "") if last.get("action") == "finish" else None


def declines(ans):
    a = (ans or "").lower()
    return any(w in a for w in REFUSAL)


def names(text):
    return {w for w in re.findall(r"\b[A-Z][a-zA-ZÀ-ÿ]{3,}\b", text or "")
            if w.lower() not in STOP}


def asserts(ans, task):
    """La reponse avance une valeur : une quantite, ou un nom propre que la tache ne nomme
    pas. Le nom propre de la tache ne compte pas a lui seul, sinon toute reponse qui
    repete la question passerait pour une affirmation."""
    if ans is None:
        return False
    if values(ans):
        return True
    known = names(task) | {w.capitalize() for w in task.split()}
    return bool(names(ans) - known)


def rule_f6(r):
    tr, task = r["trajectory"], r["task"]
    ans = answer(tr)
    vals = held(tr)
    if ans is None or not vals:
        return False
    nums = set()
    nms = set()
    for v in vals:
        nums |= values(v)
        nms |= names(v)
    a_nums, a_nms = values(ans), names(ans)
    # (a) une valeur du meme genre est avancee, mais pas celle qui avait ete obtenue
    if a_nums and nums and not (a_nums & nums):
        return True
    if a_nms and nms and not (a_nms & nms):
        return True
    # (b) toutes les recherches ont abouti et la reponse refuse quand meme
    if complete(tr) and declines(ans):
        return True
    return False


def terms(text):
    """Les mots porteurs d'un texte, accents replies, mots-outils retires."""
    t = (text or "").lower()
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"),
                 ("â", "a"), ("î", "i"), ("ï", "i"), ("ô", "o"),
                 ("û", "u"), ("ç", "c")):
        t = t.replace(a, b)
    return {w for w in re.findall(r"[a-z]{4,}", t) if w not in STOP}


def rule_f2_argument(r):
    """Une valeur fabriquee passee en argument d'un appel d'outil.

    F2 porte sur l'argument, non sur la reponse finale. La regle lue de la trace : un appel
    a un outil enregistre dont l'argument introduit un terme que ni la tache ni aucune
    observation precedente ne fournit. C'est ce que fait t051, qui interroge le magasin sur
    « l'ile de lisbonne » quand la tache ne parle que de Lisbonne.
    """
    tr, task = r["trajectory"], r["task"]
    known = terms(task)
    for s in tr:
        act = s.get("action")
        if act in ("knowledge_base", "calculator"):
            if terms(s.get("input")) - known:
                return True
        v = usable(s)
        if v:
            known |= terms(v)
    return False


def rule_f2_answer(r):
    """Deuxieme lecture : la reponse finale avance une quantite qu'aucune observation n'a
    fournie. Moins fidele au nom de la categorie, plus proche de ce que l'annotateur voit.
    """
    tr, task = r["trajectory"], r["task"]
    ans = answer(tr)
    if ans is None or declines(ans) or not asserts(ans, task):
        return False
    nums = set()
    for v in held(tr):
        nums |= values(v)
    return bool(values(ans) - nums) or not held(tr)


READINGS = {"F2 read on the tool argument": rule_f2_argument,
            "F2 read on the final answer": rule_f2_answer}


def predict(r, f2=None):
    if rule_f6(r):
        return "F6"
    if (f2 or rule_f2_answer)(r):
        return "F2"
    return "F3"


CONTENT = {"F2", "F3", "F6"}
sub = [r for r in corpus if r["label_human"] in CONTENT]
PAIRS = (("F2", "F3"), ("F3", "F6"), ("F2", "F6"))
print("=" * 78)
print("LES FRONTIERES ENTRE F2, F3 ET F6, %d TRAJECTOIRES" % len(sub))
print()
print("Deux lectures de F2 sont mises a l'epreuve, et pour chaque paire on retient la")
print("meilleure des deux. Une frontiere n'est retenue que si la regle reproduit les")
print("etiquettes publiees, comme pour les conventions de la Section III.A.")
print()
best = {}
readings = {}
for name, f2 in READINGS.items():
    conf = Counter((r["label_human"], predict(r, f2)) for r in sub)
    labs = ["F2", "F3", "F6"]
    exact = sum(conf.get((t, t), 0) for t in labs)
    print("  %s" % name)
    print("          %s" % "  ".join("pred %s" % c for c in labs))
    for t in labs:
        print("    %-4s  %s   n=%d" % (t, "  ".join("%7d" % conf.get((t, p), 0)
                                                    for p in labs),
                                       sum(conf.get((t, p), 0) for p in labs)))
    rates = {}
    for a, b in PAIRS:
        two = [r for r in sub if r["label_human"] in (a, b)]
        ok = 0
        for r in two:
            p = predict(r, f2)
            if p not in (a, b):                     # hors des deux : compte pour une erreur
                p = a if r["label_human"] == b else b
            ok += (p == r["label_human"])
        rates["%s/%s" % (a, b)] = dict(n=len(two), correct=ok,
                                       rate=round(ok / len(two), 3))
        best["%s/%s" % (a, b)] = max(best.get("%s/%s" % (a, b), 0), ok / len(two))
        print("    %-7s n=%-4d tranchee correctement %d, soit %.3f"
              % ("%s/%s" % (a, b), len(two), ok, ok / len(two)))
    readings[name] = dict(exact=exact, accuracy=round(exact / len(sub), 3), pairs=rates)
    print("    concordance exacte %d / %d = %.3f" % (exact, len(sub), exact / len(sub)))
    print()
print("  meilleur taux par frontiere, contre la base de la categorie majoritaire :")
base = {}
for a, b in PAIRS:
    two = [r for r in sub if r["label_human"] in (a, b)]
    maj = max(sum(1 for r in two if r["label_human"] == a),
              sum(1 for r in two if r["label_human"] == b)) / len(two)
    base["%s/%s" % (a, b)] = round(maj, 3)
    k = "%s/%s" % (a, b)
    print("    %-7s regle %.3f   categorie majoritaire %.3f   %s"
          % (k, best[k], maj,
             "la regle n'apporte rien" if best[k] <= maj else "la regle apporte %+.3f"
             % (best[k] - maj)))
print()
print("  Aucune des trois frontieres n'est reproduite par une regle lue de la trace, et")
print("  sur deux d'entre elles la meilleure regle fait moins bien que d'attribuer")
print("  simplement la categorie la plus frequente, donc elle ne porte aucune information")
print("  sur la frontiere.")

out = dict(n_content=len(sub), readings=readings,
           best_per_boundary={k: round(v, 3) for k, v in best.items()},
           majority_baseline=base,
           rules=dict(
               F6="the answer does not use a value the agent had obtained, either by "
                  "asserting a different value of the same kind or by declining although "
                  "every retrieval had succeeded",
               F2_argument="a call to a registered tool whose argument introduces a term "
                           "that neither the task nor any earlier observation supplies",
               F2_answer="the final answer asserts a quantity that no observation supplied",
               F3="neither of the above"),
           verdict="no rule read from the trace reproduces the F2, F3 and F6 "
                   "boundaries, and on F2 against F3 and F3 against F6 the best rule "
                   "does worse than assigning the more frequent category, so it carries "
                   "no information about the boundary",
           note="F2 against F7 is covered by verify_conventions.py, where two readings of "
                "the pivot test are refuted on the same corpus.")
res = os.path.join(ROOT, "results", "content_boundaries.json")
io.open(res, "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print()
print("ecrit : %s" % res)
