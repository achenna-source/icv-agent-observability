# Les quatre passes humaines : recruter, remettre, recevoir

Ce fichier est pour l'auteur, pas pour l'annotateur. Il ne part dans aucun paquet.

La ronde demande quatre personnes. C'est la seule piece de l'etude qui ne peut pas etre
produite depuis la machine : un modele de langue qui remplirait une passe ferait de la
reference humaine une annotation machine, et le relecteur demande justement l'inverse.
Tout le reste est pret et verifie.

## Qui peut annoter

Quatre personnes qui remplissent les quatre conditions suivantes.

Elles ne sont pas auteurs de l'article et n'ont pris aucune part a l'etude, ni au codebook,
ni aux etiquettes, ni au detecteur. Elles lisent les deux langues du materiel : les
cinquante taches et les trajectoires sont en francais, le codebook et les questions de
l'entretien sont en anglais. Elles connaissent assez la
notion d'agent outille, boucle pensee, action, observation, pour lire une trajectoire sans
qu'on la leur explique : un etudiant de master en informatique ou en IA suffit, un
doctorant convient tres bien. Elles disposent d'une heure et demie a deux heures, en une ou
deux seances.

Une competence prealable sur le schema de fautes n'est pas demandee, et elle serait meme
genante : la ronde mesure si le codebook se suffit a lui meme pour un lecteur qui le
decouvre.

## Ce que chaque personne recoit

Un dossier et une lettre, rien d'autre. Les quatre dossiers sont prets :

    paquet_A/   paquet_B/   paquet_C/   paquet_D/

La lettre est deja inscrite dans le lanceur de chaque dossier, donc personne n'a de lettre
a saisir. Ce detail compte : l'ordre de presentation des items est tire de la graine
publiee et de la lettre, et une lettre mal tapee aurait change l'ordre et le nom du
fichier rendu sans que rien ne le signale sur le moment.

Aucun dossier ne contient d'etiquette de reference, de sortie de detecteur, ni l'article.
`make_packet.py` le verifie a chaque construction et refuse de produire un paquet sinon.

## Le message a envoyer

> Bonjour,
>
> Je prepare la revision d'un article sur les modes de defaillance des agents fondes sur
> des modeles de langue. Un relecteur demande une verification que je ne peux pas faire
> moi-meme : savoir si la grille de classification que j'ai publiee est applicable par
> quelqu'un d'autre que son auteur. Il faut pour cela que plusieurs personnes etiquettent
> les memes cinquante trajectoires, chacune de son cote.
>
> Est-ce que tu accepterais d'en etre une ? Concretement : un dossier a decompresser, un
> fichier a double-cliquer, et un programme qui te pose pour chaque trajectoire une suite
> de questions fixes. Tu ne choisis pas un code dans une liste, tu reponds aux questions
> et le code en decoule, sauf a la fin de chaque trajectoire ou l'on te demande aussi le
> code que tu aurais mis de ton propre chef. Rien a installer sinon Python. Les
> trajectoires que tu lis sont en francais, les consignes et les questions en anglais.
>
> Compte une heure et demie a deux heures, en une ou deux seances, et tu peux t'arreter et
> reprendre a tout moment. Les premieres trajectoires sont beaucoup plus lentes que les
> suivantes.
>
> Deux choses importantes. Travaille seul et n'en discute avec personne avant d'avoir rendu
> ton fichier : un desaccord entre annotateurs est exactement ce que la mesure cherche, et
> un accord obtenu en se concertant ne vaut rien. Et ne cherche pas l'article ni ses
> resultats, pour la meme raison.
>
> Un desaccord avec moi n'est pas une erreur de ta part. Si la grille est ambigue, c'est
> elle qui doit etre reecrite, et c'est le resultat que le relecteur attend. Reponds
> `u` pour incertain chaque fois que tu hesites : une hesitation enregistree vaut mieux
> qu'un choix force.
>
> A la fin, tu me renvoies un seul fichier, `responses_<ta lettre>.jsonl`, ecrit a cote du
> lanceur. Je ne te demande rien d'autre.
>
> Ta contribution sera mentionnee dans les remerciements de l'article, sous ton nom ou
> anonymement, comme tu preferes : dis-moi lequel. Les trajectoires ne sont pas
> confidentielles mais elles ne sont pas encore publiees, donc merci de ne pas les diffuser.

## Les trois questions a poser a chaque personne avant qu'elle commence

La lettre aux relecteurs doit decrire le panel sans nommer personne, donc il faut ces trois
elements, a consigner dans `profils_annotateurs.md` que vous creez a cote de ce fichier.

1. Son niveau et son domaine : master, doctorat, enseignant, ingenieur, et en quoi.
2. Son experience des agents fondes sur des modeles de langue : aucune, lecteur, ou
   praticien qui en a construit.
3. Sa reponse sur les remerciements : nom ou anonyme.

Ces elements ne doivent jamais etre associes a la lettre dans un fichier remis a
l'arbitre, puisque l'arbitrage est aveugle a qui a produit quelle etiquette.

## Ce que vous faites a la reception de chaque fichier

Deposez `responses_A.jsonl` et les suivants dans ce dossier, puis :

```
python -I reception.py
```

Le controle refuse un fichier qui n'est pas du roster, auquel il manque des items, dont
l'ordre ne correspond pas a sa lettre, ou dont une etiquette sort du jeu. Il signale sans
refuser la vitesse, l'absence d'incertitude, une etiquette qui couvre presque tout, et
l'absence de recherche dans la base de connaissances.

Ce controle ne lit jamais les etiquettes de reference. Un controle qui comparerait le
fichier rendu a la reference ecarterait les annotateurs qui s'ecartent de l'auteur, c'est a
dire exactement ce que la ronde mesure.

## Ensuite

Des que deux fichiers au moins sont recus et acceptes :

```
python -I to_sheets.py
```

```
python -I adjudicate.py --adjudicator X
```

```
python -I adjudication_agreement.py
```

L'arbitre peut etre l'auteur, et le fait doit etre ecrit dans la lettre. Il voit les jeux
d'etiquettes sans savoir qui a produit lequel, l'ordre d'affichage est tire du hasard du
systeme a chaque item, et il ne voit a aucun moment les etiquettes de reference. Un arbitre
qui n'est pas auteur serait meilleur, et si une cinquieme personne est disponible, c'est a
elle qu'il faut confier ce role.

## Ce que cette ronde n'etablira pas

Les frontieres entre F2, F3, F6 et F7, parce que l'echantillon de cinquante tire chaque
categorie d'un seul gabarit de tache : un lecteur qui separe les gabarits separe les
etiquettes sans rien dire des frontieres. Cela demande un autre echantillon, ou les
categories concurrentes partagent les gabarits, et il reste a engendrer. La ronde en cours
mesure la reproductibilite du codebook, ce qui est la premiere des deux demandes du
relecteur.
