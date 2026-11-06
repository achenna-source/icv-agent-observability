# -*- coding: utf-8 -*-
"""Le jeu de cinquante items de la seconde dorsale, et son annexe de base observee.

POURQUOI LES MEMES CINQUANTE TACHES

La premiere ronde a porte sur cinquante des deux cents enonces. Reprendre les memes
identifiants donne un plan apparie : memes enonces, memes gabarits, deux dorsales, un
etiquetage humain de chaque cote. On peut alors comparer la qualite de detection sur les
deux corpus sans qu'un ecart d'echantillon s'y melange. Un tirage neuf de cinquante
items aurait coute le meme travail de lecture pour une comparaison plus faible.

CE QUI NE PEUT PAS ETRE REPRIS TEL QUEL

L'annexe « base de connaissances observee » du formulaire liste chaque requete que le
magasin a reellement servie, et ce qu'elle a rendu. C'est elle qui tranche la question la
plus difficile, celle de savoir si une valeur etait retrouvable. Le second agent n'a pas
pose les memes requetes, donc cette annexe doit etre reconstruite sur son corpus. La
reprendre de la premiere dorsale aurait mis le lecteur devant des requetes qui n'existent
pas dans ce qu'il lit, et prive de celles qui y sont.

UN CONTROLE QUE CELA PERMET

Le magasin est deterministe. Une requete posee par les deux agents doit donc rendre la
meme chose des deux cotes, et le script l'exige. Un ecart signalerait que les deux
corpus n'ont pas ete produits contre le meme magasin, ce qui invaliderait la comparaison.

    python -I annotation/make_sample_falcon.py
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

ANN = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(ANN)
CORPUS = os.path.join(ART, "data", "trajectories_200_falcon3_7b.jsonl")
BLIND = os.path.join(ANN, "sample_blind.jsonl")

rows = [json.loads(l) for l in io.open(CORPUS, encoding="utf-8") if l.strip()]
by = {r["id"]: r for r in rows}
first = [json.loads(l) for l in io.open(BLIND, encoding="utf-8") if l.strip()]
ids = [r["id"] for r in first]
assert len(ids) == len(set(ids)) == 50, len(ids)
missing = [i for i in ids if i not in by]
assert not missing, missing

# l'enonce doit etre le meme des deux cotes, sinon ce n'est pas un plan apparie
for r in first:
    assert by[r["id"]]["task"] == r["task"], r["id"]

out = os.path.join(ANN, "sample_blind_falcon3.jsonl")
with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
    for i in ids:
        r = by[i]
        fh.write(json.dumps({"id": r["id"], "task": r["task"],
                             "trajectory": r["trajectory"]},
                            ensure_ascii=False) + "\n")

# l'annexe : toute requete que le magasin a servie sur ce corpus, sur les 200
sys.path.insert(0, os.path.join(ART, "code"))
from agent import NOT_FOUND_FORMS            # noqa: E402

served = {}
for r in rows:
    for st in r["trajectory"]:
        if st.get("action") != "knowledge_base":
            continue
        o = st.get("observation")
        if o is None or o in NOT_FOUND_FORMS:
            continue
        q = str(st.get("input"))
        if q in served:
            assert served[q] == o, ("le magasin a rendu deux choses pour %r" % q)
        served[q] = o

ref = json.load(io.open(os.path.join(ART, "data", "knowledge_base_observed.json"),
                        encoding="utf-8"))
shared = sorted(set(served) & set(ref))
clash = [q for q in shared if served[q] != ref[q]]
assert not clash, ("le meme magasin rend autre chose sur les deux corpus : %s" % clash)

kb_out = os.path.join(ART, "data", "knowledge_base_observed_falcon3.json")
io.open(kb_out, "w", encoding="utf-8", newline="\n").write(
    json.dumps(dict(sorted(served.items())), ensure_ascii=False, indent=1) + "\n")

print()
print("  %s" % out)
print("  %d items, les memes identifiants que la premiere ronde" % len(ids))
print("  %s" % kb_out)
print("  %d requetes servies sur ce corpus, %d sur le premier, %d communes"
      % (len(served), len(ref), len(shared)))
print("  les %d requetes communes rendent la meme chose des deux cotes" % len(shared))
print()
print("  requetes propres a ce corpus : %d" % len(set(served) - set(ref)))
print("  requetes du premier corpus absentes d'ici : %d" % len(set(ref) - set(served)))
