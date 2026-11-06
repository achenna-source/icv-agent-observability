# -*- coding: utf-8 -*-
"""La sentinelle de la base de connaissances, et pourquoi son orthographe ne change rien.

LE DEFAUT, TEL QU'IL ETAIT

Le corpus publie porte « Information non trouvee » sous sa forme accentuee, produite par
la version du code qui l'a genere. Le agent.py publie ecrit la forme sans accent, et le
signals.py publie comparait a la forme accentuee seule. Trois consequences :

  une regeneration avec le code publie ne redonnait pas le corpus publie octet pour octet
  le test de coherence ne reconnaissait la sentinelle sur aucun corpus regenere
  le second corpus, produit ici, portait la forme sans accent

LA CORRECTION, ET CE QU'ELLE NE REPARE PAS

agent.py expose maintenant la chaine et ses deux orthographes, et signals.py les importe
au lieu d'en coder une. L'ecart d'octets entre le corpus publie et une regeneration reste,
et il reste declare : il porte sur cette seule chaine.

CE QUE CE SCRIPT ETABLIT

Qu'aucun chiffre du papier n'en depend. La sentinelle ne contient aucun chiffre, donc
l'inclure ou non dans l'ensemble des valeurs retrouvees ne peut pas changer le test de
contradiction. Le script le verifie en calculant le signal des deux facons, sur les deux
corpus, et en exigeant l'egalite trajectoire par trajectoire.

    python -I experiments/sentinel_check.py
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ART = os.path.dirname(CODE)
sys.path.insert(0, CODE)
import signals                                        # noqa: E402
from agent import NOT_FOUND, NOT_FOUND_FORMS          # noqa: E402
from signals import _numbers                          # noqa: E402

ACCENTED = "Information non trouvée"
assert NOT_FOUND in NOT_FOUND_FORMS and ACCENTED in NOT_FOUND_FORMS

print()
print("la sentinelle porte-t-elle un chiffre")
for s in NOT_FOUND_FORMS:
    print("  %-28r %s" % (s, _numbers(s) or "aucun"))
assert all(not _numbers(s) for s in NOT_FOUND_FORMS)


def tier2_one_spelling(trajectory, sentinel):
    """Le test de coherence tel qu'il etait, avec une seule orthographe reconnue."""
    retrieved = set()
    for st in trajectory:
        if st.get("action") == "knowledge_base" and st.get("observation") not in (
                None, sentinel):
            retrieved |= _numbers(st.get("observation"))
    last = trajectory[-1]
    if last.get("action") == "finish" and last.get("input"):
        for v in _numbers(last.get("input")):
            if v > 50000 and v not in retrieved:
                if not any(abs(v - (a + b)) < 1000 or abs(v - (a - b)) < 1000
                           or abs(v - (a + b) // 2) < 1000
                           for a in retrieved for b in retrieved):
                    return True
    return False


print()
print("%-38s %8s %8s %8s %8s" % ("corpus", "publie", "accent", "sans", "orthogr."))
ok = True
for name in ("trajectories_200.jsonl", "trajectories_200_falcon3_7b.jsonl"):
    q = os.path.join(ART, "data", name)
    if not os.path.exists(q):
        print("%-38s absent" % name)
        continue
    rows = [json.loads(l) for l in io.open(q, encoding="utf-8") if l.strip()]
    cur = [signals.tier2(r["trajectory"])[0] for r in rows]
    acc = [tier2_one_spelling(r["trajectory"], ACCENTED) for r in rows]
    pla = [tier2_one_spelling(r["trajectory"], NOT_FOUND) for r in rows]
    seen = {st.get("observation") for r in rows for st in r["trajectory"]
            if st.get("observation") in NOT_FOUND_FORMS}
    same = cur == acc == pla
    ok = ok and same
    print("%-38s %8d %8d %8d %8s"
          % (name, sum(cur), sum(acc), sum(pla),
             "accentuee" if seen == {ACCENTED} else
             "sans" if seen == {NOT_FOUND} else "melange"))
    assert same, (
        "l'orthographe de la sentinelle change le signal sur %s, ce qui contredit "
        "l'argument ci-dessus" % name)

print()
print("Les trois colonnes de comptes sont egales sur chaque corpus, et l'egalite est")
print("exigee trajectoire par trajectoire et non sur le total. Aucun chiffre du papier")
print("ne depend donc de l'orthographe de la sentinelle.")
print()
print("resultat : %s" % ("conforme" if ok else "NON CONFORME"))
sys.exit(0 if ok else 1)
