# -*- coding: utf-8 -*-
"""Le controle d'un fichier rendu par un annotateur, avant qu'il entre dans l'analyse.

Ce que ce script ne fait pas, et pourquoi c'est le point important. Il ne lit jamais les
etiquettes de reference. Un controle de reception qui comparerait le fichier rendu a la
reference ecarterait les annotateurs qui s'ecartent de l'auteur, c'est a dire exactement la
quantite que la ronde mesure : le resultat serait choisi plutot que mesure. Le fichier est
donc juge sur sa forme et sur la facon dont il a ete produit, jamais sur ses etiquettes.

Ce qui fait echouer la reception, parce que le fichier ne porte pas ce qu'il annonce.

  la lettre n'est pas du roster, ou les enregistrements portent une autre lettre ;
  un identifiant ne figure pas dans l'echantillon, ou un item manque, ou un doublon ;
  l'ordre des items n'est pas celui que la graine publiee et la lettre donnent, ce qui
  arrive quand le fichier a ete produit avec une autre lettre ou une autre graine ;
  une etiquette hors du jeu, ou un sous code F3 invalide, ou une cle manquante.

Ce qui est seulement signale, parce qu'un humain doit en juger : la vitesse, les reponses
toutes identiques, la part d'incertitude, une etiquette qui couvre presque tout, l'absence
de recherche dans la base de connaissances, l'ecart entre l'etiquette calculee et
l'etiquette libre. Aucun de ces signaux ne disqualifie un annotateur a lui seul.

    python -I reception.py                     tous les responses_*.jsonl du dossier
    python -I reception.py responses_A.jsonl
"""
import glob
import io
import json
import os
import random
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE_FOR_IMPORT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE_FOR_IMPORT)
import interview as IVM            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)

ROSTER = ("A", "B", "C", "D", "E", "F", "G", "K")
BASE_SEED = 20261105          # la meme que interview.py, publiee avant la ronde
LABELS = ("S", "F1a", "F1b", "F2", "F3", "F4", "F5", "F6", "F7")
SUBCODES = ("F3a", "F3b", "F3c", None, "")
KEYS = ("annotator", "position", "id", "malformed_steps", "answers", "computed_label",
        "computed_undetermined", "free_label", "fault_step", "confidence", "note",
        "kb_lookups", "seconds")


def sample_path(name="sample_blind.jsonl"):
    for q in (os.path.join(HERE, name), os.path.join(ANN, name)):
        if os.path.exists(q):
            return q
    raise SystemExit("%s introuvable" % name)


def load_rows(name="sample_blind.jsonl"):
    return [json.loads(l) for l in io.open(sample_path(name), encoding="utf-8")
            if l.strip()]


def sample_for(recs):
    """L'echantillon que ce fichier annonce, et la raison de ne pas s'en contenter.

    Les deux dorsales portent les memes cinquante identifiants, donc un fichier du second
    corpus passerait le controle des identifiants et celui de l'ordre sans rien signaler.
    Les enregistrements recents nomment leur corpus ; les anciens, ecrits avant que le
    champ existe, sont du premier. Le nom annonce est ensuite verifie contre les etapes
    malformees de chaque item, qui sont une propriete de la trajectoire et non du nom.
    """
    named = {r.get("corpus") for r in recs if r.get("corpus")}
    if len(named) > 1:
        return None, "ce fichier melange %d corpus : %s" % (len(named),
                                                            " ".join(sorted(named)))
    name = named.pop() if named else "sample_blind.jsonl"
    if name == "toolbench":
        return None, "toolbench"
    try:
        return load_rows(name), None
    except SystemExit as e:
        return None, str(e)


def published_order(letter, ids):
    """L'ordre que l'entretien donne pour cette lettre, recalcule ici."""
    order = list(range(len(ids)))
    random.Random("%d:%s" % (BASE_SEED, letter)).shuffle(order)
    return [ids[i] for i in order]


def check(path):
    name = os.path.basename(path)
    letter = name[len("responses_"):-len(".jsonl")]
    hard, soft = [], []
    print("=" * 78)
    print("%s" % name)
    print()

    # Un controle de reception ne doit jamais s'interrompre sur une trace d'erreur :
    # un fichier illisible est un refus, avec la ligne fautive nommee.
    recs = []
    for n, line in enumerate(io.open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            recs.append(json.loads(line))
        except ValueError as e:
            hard.append("ligne %d illisible : %s" % (n, e))
            break
    if hard:
        print("  %d ligne(s) lue(s) avant l'erreur" % len(recs))
        print()
        for h in hard:
            print("  ECHEC : %s" % h)
        print()
        print("  ce fichier n'est pas du JSON Lines ligne par ligne, tel que")
        print("  l'entretien et le formulaire l'ecrivent")
        return hard, soft
    if recs and not isinstance(recs[0], dict):
        hard.append("les lignes ne sont pas des objets JSON")
        print()
        print("  ECHEC : %s" % hard[-1])
        return hard, soft
    if letter not in ROSTER:
        hard.append("la lettre %s n'est pas du roster %s" % (letter, " ".join(ROSTER)))
    if not recs:
        hard.append("fichier vide")
        print("  ECHEC : fichier vide")
        return hard, soft

    # De quel corpus ce fichier vient-il, et ses etapes malformees le confirment-elles.
    rows, why = sample_for(recs)
    if rows is None:
        if why == "toolbench":
            print("  ce fichier vient de la ronde ToolBench, dont l'analyse est "
                  "separee : il n'est pas controle ici")
            return [], []
        hard.append(why)
        print("  ECHEC : %s" % why)
        return hard, soft
    ids = [r["id"] for r in rows]
    by_id = {r["id"]: r for r in rows}
    wrong = [r["id"] for r in recs
             if r["id"] in by_id and r.get("malformed_steps") is not None
             and list(r["malformed_steps"]) != list(IVM.malformed_steps(by_id[r["id"]]))]
    if wrong:
        hard.append("les etapes malformees de %d item(s) ne sont pas celles du corpus "
                    "annonce, dont %s : ce fichier vient d'un autre corpus, et les deux "
                    "dorsales portant les memes identifiants, rien d'autre ne l'aurait "
                    "signale" % (len(wrong), " ".join(wrong[:5])))

    others = sorted({r.get("annotator") for r in recs} - {letter})
    if others:
        hard.append("des enregistrements portent la lettre %s" % " ".join(map(str, others)))
    for k in KEYS:
        miss = sum(1 for r in recs if k not in r)
        if miss:
            hard.append("la cle %s manque dans %d enregistrements" % (k, miss))

    seen = [r["id"] for r in recs]
    unknown = [i for i in seen if i not in ids]
    dup = sorted({i for i in seen if seen.count(i) > 1})
    missing = [i for i in ids if i not in set(seen)]
    if unknown:
        hard.append("identifiants hors echantillon : %s" % " ".join(unknown[:5]))
    if dup:
        hard.append("doublons : %s" % " ".join(dup[:5]))
    if missing:
        hard.append("%d items manquants : %s" % (len(missing), " ".join(missing[:8])))

    # Un lecteur a pu remplir le formulaire d'un autre : l'ordre vient alors de ce
    # formulaire, et le fait est inscrit dans chaque enregistrement.
    forms = {r.get("form_letter") for r in recs if r.get("form_letter")}
    src = forms.pop() if len(forms) == 1 else letter
    if src != letter:
        print("  ces reponses ont ete donnees sur le formulaire de %s, donc dans "
              "l'ordre de %s" % (src, src))
        print("  un effet d'ordre peut se correler entre %s et %s" % (letter, src))
    if letter in ROSTER and not unknown and not dup:
        want = [i for i in published_order(src, ids) if i in set(seen)]
        if seen != want:
            k = next((j for j in range(min(len(seen), len(want)))
                      if seen[j] != want[j]), 0)
            hard.append("l'ordre des items n'est pas celui de la lettre %s : "
                        "position %d porte %s et devrait porter %s"
                        % (letter, k + 1, seen[k], want[k]))

    bad = [r["id"] for r in recs if r.get("free_label") not in LABELS]
    if bad:
        hard.append("etiquette libre hors jeu sur %s" % " ".join(bad[:5]))
    bad = [r["id"] for r in recs
           if not r.get("computed_undetermined")
           and r.get("computed_label") not in LABELS]
    if bad:
        hard.append("etiquette calculee hors jeu sur %s" % " ".join(bad[:5]))
    bad = [r["id"] for r in recs if r.get("f3_subcode") not in SUBCODES]
    if bad:
        hard.append("sous code F3 invalide sur %s" % " ".join(bad[:5]))
    # Une duree absente ou non numerique signale un fichier qui ne vient pas de
    # l'entretien : celui-ci ecrit toujours un nombre. Sans ce controle, le fichier
    # passerait et l'analyse echouerait plus loin sur une trace d'erreur.
    # Un formulaire Word ne mesure pas le temps par item, et y ecrire un nombre serait
    # une invention : la duree nulle est admise pour cette seule raison, declaree
    # enregistrement par enregistrement.
    bad = [r["id"] for r in recs
           if r.get("instrument") != "docx-form"
           and (not isinstance(r.get("seconds"), (int, float))
                or isinstance(r.get("seconds"), bool))]
    if bad:
        hard.append("duree absente ou non numerique sur %d items : %s"
                    % (len(bad), " ".join(bad[:5])))
    forms = sum(1 for r in recs if r.get("instrument") == "docx-form")
    if forms and forms != len(recs):
        hard.append("%d items sur %d viennent d'un formulaire et les autres de "
                    "l'entretien : un fichier melange deux instruments"
                    % (forms, len(recs)))

    print("  %d items rendus sur %d, lettre %s" % (len(recs), len(ids), letter))
    if hard:
        print()
        for h in hard:
            print("  ECHEC : %s" % h)
        print()
        if missing and len(hard) == 1:
            print("  l'annotateur n'a pas fini. Il relance son lanceur, l'entretien")
            print("  reprend au premier item non repondu, et il rend de nouveau.")
        else:
            print("  ce fichier n'entre pas dans l'analyse en l'etat")
        return hard, soft

    # ------------------------------------------------------------------ signaux
    secs = [r["seconds"] for r in recs if isinstance(r.get("seconds"), (int, float))]
    if len(secs) == len(recs):
        fast10 = [r["id"] for r in recs if r["seconds"] < 10]
        fast20 = [r["id"] for r in recs if r["seconds"] < 20]
        print("  duree totale %.0f min, mediane par item %.0f s, le plus court %.0f s"
              % (sum(secs) / 60.0, statistics.median(secs), min(secs)))
        if len(fast10) > 5:
            soft.append("%d items sous 10 s : %s" % (len(fast10), " ".join(fast10[:8])))
        elif len(fast20) > 15:
            soft.append("%d items sous 20 s" % len(fast20))
    else:
        print("  duree non mesuree : formulaire Word, le temps par item n'y existe pas")

    flat = [r["id"] for r in recs
            if r.get("answers") and len(set(r["answers"].values())) == 1
            and len(r["answers"]) > 2]
    if len(flat) > len(recs) * 0.5:
        soft.append("%d items ou toutes les reponses aux controles sont identiques"
                    % len(flat))

    uns = sum(1 for r in recs for v in r.get("answers", {}).values() if v == "u")
    ans = sum(len(r.get("answers", {})) for r in recs)
    print("  %d reponses aux controles, dont %d incertaines, %.0f pour cent"
          % (ans, uns, 100.0 * uns / ans if ans else 0))
    if ans and uns == 0:
        soft.append("aucune reponse incertaine sur tout le fichier, ce qui est rare")

    dist = {}
    for r in recs:
        k = r["free_label"]
        dist[k] = dist.get(k, 0) + 1
    print("  etiquettes libres : %s"
          % "  ".join("%s %d" % (k, dist[k]) for k in sorted(dist)))
    top = max(dist.values())
    if top > len(recs) * 0.9:
        soft.append("une seule etiquette couvre %d des %d items" % (top, len(recs)))

    agree = sum(1 for r in recs if r["free_label"] == r.get("computed_label"))
    print("  etiquette libre egale a l'etiquette calculee sur %d des %d items"
          % (agree, len(recs)))
    if agree == len(recs):
        soft.append("l'etiquette libre ne s'ecarte jamais de la calculee, ce qui peut "
                    "signifier qu'elle a ete recopiee")

    und = [r["id"] for r in recs if r.get("computed_undetermined")]
    if und:
        print("  %d items que les questions ne tranchent pas : %s"
              % (len(und), " ".join(und)))
    kb = sum(len(r.get("kb_lookups") or ()) for r in recs)
    notes = sum(1 for r in recs if (r.get("note") or "").strip())
    print("  %d recherches dans la base de connaissances, %d notes" % (kb, notes))
    if kb == 0:
        soft.append("la base de connaissances n'a jamais ete interrogee, alors qu'elle "
                    "tranche la question la plus difficile")

    print()
    if soft:
        for s in soft:
            print("  a regarder : %s" % s)
        print()
        print("  aucun de ces signaux ne disqualifie l'annotateur, ils se declarent")
    else:
        print("  aucun signal a signaler")
    return hard, soft


paths = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, "responses_*.jsonl")))
print()
if not paths:
    print("aucun fichier responses_*.jsonl dans %s" % HERE)
    print("la ronde humaine n'a encore rien rendu")
    sys.exit(1)

bad = 0
for p in paths:
    h, _ = check(p if os.path.isabs(p) else os.path.join(HERE, p))
    bad += 1 if h else 0
    print()

print("=" * 78)
print("%d fichier(s) controle(s), %d refuse(s)" % (len(paths), bad))
print("aucune etiquette de reference n'a ete lue par ce controle")
sys.exit(1 if bad else 0)
