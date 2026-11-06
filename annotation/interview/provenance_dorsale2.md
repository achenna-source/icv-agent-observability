# La ronde d'étiquetage de la seconde dorsale

## Ce qu'elle mesure, et ce qu'elle ne mesure pas

La campagne Falcon3-7B-Instruct régénère les 200 énoncés de l'étude avec un autre
modèle, tout le reste tenu fixe. Elle valide les signaux sur un second corpus, puisque
leur taux de déclenchement et leur mécanisme s'y calculent sans étiquette. Elle ne valide
pas le transfert de la taxonomie, parce qu'un corpus sans étiquette ne permet ni
précision ni rappel, et parce qu'un signal qui se déclenche au même taux sur deux corpus
peut y attraper des fautes différentes. Cette ronde existe pour cette seule raison.

## Le plan apparié, et pourquoi il vaut mieux qu'un tirage neuf

Les cinquante items sont **les mêmes identifiants** que la ronde de la Section VI.B.
Mêmes énoncés, mêmes gabarits, deux dorsales, un étiquetage humain de chaque côté. La
qualité de détection se compare alors sans qu'un écart d'échantillon s'y mêle. Un tirage
neuf de cinquante items aurait coûté le même travail de lecture pour une comparaison plus
faible.

Conséquence utile: la question 1, qui demande si la réponse finale est correcte, porte
sur la même vérité de terrain qu'à la première ronde. Le codebook, les sept contrôles,
les quatre conventions et la règle d'étiquette s'appliquent donc **sans adaptation**.
C'est la différence avec la ronde ToolBench, où l'absence de clé de vérité oblige à
reformuler la question 1.

## Ce qui a dû changer, et ce qui n'a pas changé

Deux choses seulement changent, et elles devaient changer.

Les trajectoires sont celles du second agent. Et l'annexe « base de connaissances
observée » est reconstruite sur son corpus: 17 requêtes servies ici contre 57 sur le
premier, 7 seulement en commun. Reprendre l'annexe du premier corpus aurait mis le
lecteur devant des requêtes absentes de ce qu'il lit, et l'aurait privé de celles qui y
sont. Or c'est cette annexe qui tranche la question la plus difficile, celle de savoir si
une valeur était retrouvable.

Le reste est identique au bit près. `make_docx_form.py` régénère le formulaire B de la
première ronde avec un `word/document.xml` de hachage identique à celui que la version
d'avant la paramétrisation produisait. L'instrument n'a donc pas dérivé.

## Un contrôle que le plan apparié permet

Le magasin est déterministe, donc une requête posée par les deux agents doit rendre la
même chose des deux côtés. `make_sample_falcon.py` l'exige sur les 7 requêtes communes et
refuse d'écrire si une seule diverge. Un écart aurait signalé que les deux corpus n'ont
pas été produits contre le même magasin, ce qui aurait invalidé toute la comparaison.

## Le garde-fou qui compte le plus

Les deux dorsales portent les **mêmes cinquante identifiants**. Un formulaire de l'une lu
contre le corpus de l'autre ne provoquerait donc aucune erreur d'identifiant: il
produirait des enregistrements faux en silence, le numéro d'étape du lecteur et la liste
des étapes malformées étant rapportés à une autre trajectoire.

`read_docx_form.py` le détecte tout seul, sans dépendre du drapeau passé en ligne de
commande. La ligne Q2 de chaque item énumère les étapes disponibles, et cette liste est
une propriété de la trajectoire. L'extracteur la relit dans le document et exige
l'égalité avec le corpus chargé. Sur le formulaire F lu contre le corpus d'origine, le
refus porte sur 45 items des 50. Les 5 restants coïncident, ce qui montre qu'un contrôle
portant sur le seul nombre d'items n'aurait pas suffi.

## Les fichiers

| fichier | rôle |
|---|---|
| `annotation/sample_blind_falcon3.jsonl` | les 50 items, sans étiquette |
| `data/knowledge_base_observed_falcon3.json` | l'annexe, 17 requêtes servies |
| `annotation/make_sample_falcon.py` | construit les deux, avec le contrôle du magasin |
| `formulaire_annotateur_F_dorsale2.docx` | premier lecteur |
| `formulaire_annotateur_G_dorsale2.docx` | second lecteur, autre ordre |

Les deux formulaires portent 50 items, 700 lignes à remplir, aucun tiret cadratin, et le
contrôle vérifie avant enregistrement qu'aucune étiquette de référence et aucune sortie
de détecteur n'y figure. L'ordre de présentation vient de la graine publiée et de la
lettre, donc les deux lecteurs ne voient jamais les items dans le même ordre.

## La lecture, quand les formulaires reviennent

```
python -I read_docx_form.py formulaire_annotateur_F_dorsale2_rempli.docx --sample sample_blind_falcon3.jsonl
```

Le drapeau `--sample` est obligatoire ici. Sans lui, le garde-fou ci-dessus refuse le
fichier et nomme la commande à relancer.

## Ce que le manuscrit dit déjà, et ce qu'il dira

La Section VI.E rapporte la campagne et sa limite: le corpus ne porte pas d'étiquette,
donc la taxonomie n'y est pas testée. Elle annonce cette ronde comme préparée sur les
mêmes cinquante identifiants, sans en annoncer le résultat. La lettre dit de même qu'elle
ne demande pas au relecteur de prendre ce résultat sur parole. Rien n'est à corriger si
la ronde n'a pas lieu.
