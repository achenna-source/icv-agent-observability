# La ronde ToolBench

## Ce qu'elle mesure, et pourquoi elle ne ressemble pas aux autres

La Section VI.E applique les signaux à 19 738 trajectoires ToolBench sans aucune
étiquette, donc elle valide les détecteurs et pas la taxonomie. Cette ronde étiquette
soixante de ces trajectoires, et vingt-cinq en aveugle pour un second lecteur. C'est le
seul dispositif de ce travail qui teste le transfert de la taxonomie vers un autre agent,
un autre modèle, un autre espace d'outils et un autre environnement.

## La seule question qui change, et pourquoi elle devait changer

ToolBench ne porte pas de clé de vérité: son évaluation propre passe par un juge modèle.
La première question ne peut donc pas être « la réponse finale est-elle juste », que
personne ici ne peut vérifier. Elle devient « la réponse finale est-elle cohérente avec
les observations que la trajectoire a obtenues », et **S** signifie ici aucune faute
observable à l'interface des actions et une réponse cohérente avec ces observations. S ne
signifie pas que la réponse est correcte, et le formulaire le dit en tête.

`read_docx_toolbench.py` enregistre cette réponse sous le nom `consistent` et non
`correct`, pour qu'aucune analyse ne confonde les deux.

## La ligne ajoutée le 6 novembre 2026, avant qu'un lecteur ait commencé

La règle publiée tranche le cas « aucune faute d'étape et réponse fautive » par la
convention des sous-buts ouverts: F5 si la trajectoire s'arrête en laissant une part de la
tâche sans réponse, F3 sinon. Le formulaire énonçait cette convention dans sa page des
conventions **sans porter la ligne pour y répondre**. Un lecteur qui écrivait Q2=0 et Q1=n
produisait donc un item que la règle ne calculait pas.

Le trou est apparu en écrivant l'extracteur, qui a dû décider quoi faire de ce cas. La
ligne `Q2b` est maintenant dans le formulaire, avec le libellé du formulaire de l'étude.
Les identifiants, l'ordre de présentation et la graine n'ont pas changé.

L'extracteur lit les deux formes. Avec la ligne, il applique la convention. Sans elle, il
déclare l'item indéterminé, le compte, et garde l'étiquette libre du lecteur sans la
promouvoir: il n'invente pas la réponse manquante.

## Une catégorie est vide sur ce corpus, et le lecteur le sait d'avance

Aucune action des soixante trajectoires ne nomme un outil hors du jeu enregistré de sa
tâche, et aucune n'est vide. Le formulaire le dit, parce qu'un lecteur qui chercherait ce
cas perdrait son temps, et l'extracteur le recalcule plutôt que de le croire. F1a est donc
vide ici par construction, ce qui est en soi une mesure: la convention selon laquelle une
étape malformée ne détermine jamais l'étiquette ne s'applique nulle part sur ce corpus.

Si un lecteur répond tout de même oui à f1a, l'extracteur le signale comme un désaccord
avec une affirmation mécanique et conserve la réponse telle quelle.

## Les garde-fous de la lecture

Quatre refus, chacun essayé sur un formulaire rempli par automate avant toute distribution:
une ligne supprimée du tableau, une valeur hors du jeu `y n u`, un ordre de présentation
qui n'est pas celui de la lettre, et un formulaire lu contre le mauvais échantillon. Ce
dernier contrôle relit la liste des étapes offertes par la ligne Q2, qui est une propriété
de la trajectoire, au lieu de faire confiance au drapeau passé en ligne de commande.

## Les fichiers

| fichier | rôle |
|---|---|
| `formulaire_toolbench_A.docx` | les 60 items, premier lecteur |
| `formulaire_toolbench_B_blind25.docx` | les 25 en aveugle, second lecteur |
| `make_docx_toolbench.py` | construit les deux, sans strate ni étiquette |
| `read_docx_toolbench.py` | relit un formulaire rempli, calcule par la règle publiée |

L'échantillon lui-même, `toolbench_60.jsonl` et `toolbench_blind_25.jsonl`, vient de la
campagne `icv-toolbench-sample` et n'est pas redistribué dans l'artefact: la licence de
ToolBench reste à vérifier. L'extracteur prend donc `--sample` et dit où il cherche.

## La lecture, quand les formulaires reviennent

```
python -I read_docx_toolbench.py formulaire_toolbench_A_rempli.docx
python -I read_docx_toolbench.py formulaire_toolbench_B_blind25_rempli.docx --blind
```

La sortie est `responses_toolbench_A.jsonl` et `responses_toolbench_B.jsonl`.
`reception.py` ne contrôle pas ces fichiers: il porte sur la ronde de l'étude, et il les
reconnaît pour les écarter plutôt que de les juger sur un échantillon qui n'est pas le
leur.

## Ce que le manuscrit dit, et ce qu'il ne dit pas

La Section VI.E dit que l'audit ToolBench ne teste ni la taxonomie ni la détection au
niveau de la tâche, et la lettre le dit au relecteur dans ses propres termes. Aucun
résultat de cette ronde n'est annoncé. Rien n'est à corriger si elle n'a pas lieu.
