# -*- coding: utf-8 -*-
"""Verifie ce que le papier dira de l'instrument, et echoue sinon.

Quatre affirmations sont verifiables par lecture du fichier, et un relecteur peut les
refaire en une commande.

  1. Aucun modele de langue dans la chaine d'annotation. interview.py n'importe que la
     bibliotheque standard, ne contient aucun appel reseau et aucun nom de modele.
  2. Les sept predicats sont ceux du codebook publie, mot pour mot a la casse et a la
     ponctuation pres.
  3. L'ordre des questions est celui du codebook, et l'entretien s'arrete au premier
     predicat qui se declenche.
  4. L'echantillon remis ne porte aucune etiquette.

    python -I verify_instrument.py

Sortie : code 0 si les quatre tiennent, 1 sinon, avec le detail.
"""
import ast
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.dirname(HERE)
ROOT = os.path.dirname(ANN)

STDLIB = {"argparse", "ast", "glob", "io", "json", "os", "random", "re", "shutil",
          "statistics", "sys", "time", "unicodedata", "collections"}
FORBIDDEN = ("openai", "anthropic", "transformers", "requests", "urllib", "httpx",
             "socket", "subprocess", "llm", "gpt", "qwen", "falcon", "mistral",
             "sentence_transformers", "torch")

fails = []


def check(name, holds, detail=""):
    print("  %-4s %s%s" % ("ok" if holds else "ECHEC", name,
                           "" if not detail else "\n       %s" % detail))
    if not holds:
        fails.append(name)


def without_filenames(s):
    """Les noms de fichiers de corpus sortent du texte avant la recherche des noms de
    modeles. Un echantillon peut s'appeler sample_blind_falcon3.jsonl parce que la
    dorsale qui l'a produit s'appelle ainsi, et le nommer dans un message d'erreur n'est
    pas appeler un modele. Ce que ce controle cherche, ce sont des appels, pas des noms
    de fichiers."""
    return re.sub(r"[\w.\-]+\.(?:jsonl|json|md|docx|csv|xlsx)", " ", s)


def norm(s):
    s = s.lower().replace("`", "").replace("/", " or ")
    for ch in (chr(0x2019),):
        s = s.replace(ch, "'")
    for ch in (chr(0x2014), chr(0x2013)):
        s = s.replace(ch, " ")
    s = re.sub(r"[^a-z0-9' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


src = io.open(os.path.join(HERE, "interview.py"), encoding="utf-8").read()
tree = ast.parse(src)

print()
print("1. AUCUN MODELE DE LANGUE DANS LA CHAINE D'ANNOTATION")

# La lettre promet qu'aucun modele n'intervient dans cette chaine. L'arbitrage en fait
# partie, puisque le relecteur demande une evaluation "with adjudication", donc les deux
# fichiers de l'arbitrage sont verifies comme l'entretien.
for extra in ("adjudicate.py", "adjudication_agreement.py", "reception.py",
              "make_packet.py"):
    q = os.path.join(HERE, extra)
    if not os.path.exists(q):
        check("%s present" % extra, False)
        continue
    s2 = io.open(q, encoding="utf-8").read()
    t2 = ast.parse(s2)
    m2 = set()
    for node in ast.walk(t2):
        if isinstance(node, ast.Import):
            m2.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            m2.add(node.module.split(".")[0])
    # reception.py importe le module de l'entretien pour n'avoir qu'une seule
    # definition de la regle des etapes malformees, celle que l'entretien applique.
    # Deux definitions pourraient deriver, et c'est contre cette derive que le controle
    # de corpus existe.
    allowed = STDLIB | ({"interview"} if extra == "reception.py" else set())
    check("%s n'importe que la bibliotheque standard%s"
          % (extra, " et l'entretien" if extra == "reception.py" else ""),
          m2 <= allowed, "imports : %s" % ", ".join(sorted(m2)))
    b2 = norm(without_filenames(re.sub(r'""".*?"""', " ", s2, flags=re.S)))
    h2 = [w for w in FORBIDDEN if w in b2]
    check("%s : aucun appel reseau ni nom de modele hors docstring" % extra, not h2,
          "trouve : %s" % ", ".join(h2) if h2 else "")

# l'arbitrage ne doit pas pouvoir etre desaveugle depuis le script publie
adj = io.open(os.path.join(HERE, "adjudicate.py"), encoding="utf-8").read()
check("l'ordre d'affichage de l'arbitrage n'est pas tire d'une graine ecrite",
      "SystemRandom" in adj and "BASE_SEED" not in adj)
check("la correspondance des positions part dans un fichier DO_NOT_SHARE",
      "mapping_adjudication_DO_NOT_SHARE.json" in adj)
check("l'arbitre ne choisit que parmi les etiquettes que les lecteurs ont ecrites",
      "tuple(choices)" in adj)
check("un item laisse indecis n'est pas rempli",
      'undecided=(a == "u")' in adj and "adjudicated_label=None if a" in adj)
agr = io.open(os.path.join(HERE, "adjudication_agreement.py"), encoding="utf-8").read()
check("l'accord avant et apres arbitrage sont rapportes tous les deux",
      '("before", False), ("after", True)' in agr)

# Le controle de reception ne doit pas pouvoir ecarter un annotateur sur ses etiquettes :
# il jugerait alors l'accord avec l'auteur, qui est la quantite mesuree.
rec = io.open(os.path.join(HERE, "reception.py"), encoding="utf-8").read()
check("la reception ne lit aucune etiquette de reference",
      "sample_key" not in rec and "label_annotator1" not in rec
      and "label_human" not in rec)
# Le formulaire Word et son extracteur font partie de la meme chaine. Ils importent
# python-docx, qui lit et ecrit un document et n'est pas un modele : la bibliotheque est
# donc admise nommement, et le reste du controle est le meme.
for extra in ("make_docx_form.py", "read_docx_form.py",
              "make_docx_toolbench.py", "read_docx_toolbench.py"):
    q = os.path.join(HERE, extra)
    if not os.path.exists(q):
        check("%s present" % extra, False)
        continue
    s3 = io.open(q, encoding="utf-8").read()
    m3 = set()
    for node in ast.walk(ast.parse(s3)):
        if isinstance(node, ast.Import):
            m3.update(x.name.split(".")[0] for x in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            m3.add(node.module.split(".")[0])
    check("%s n'importe que la bibliotheque standard, docx et l'entretien" % extra,
          m3 <= (STDLIB | {"docx", "interview"}),
          "imports : %s" % ", ".join(sorted(m3)))
    b3 = norm(without_filenames(re.sub(r'""".*?"""', " ", s3, flags=re.S)))
    h3 = [w for w in FORBIDDEN if w in b3]
    check("%s : aucun appel reseau ni nom de modele hors docstring" % extra, not h3,
          "trouve : %s" % ", ".join(h3) if h3 else "")

mk = io.open(os.path.join(HERE, "make_docx_form.py"), encoding="utf-8").read()
rd = io.open(os.path.join(HERE, "read_docx_form.py"), encoding="utf-8").read()
check("le formulaire prend ses predicats et ses conventions de l'entretien",
      "import interview as IVM" in mk and "IVM.RULES" in mk and "IVM.HELP" in mk)
check("le formulaire ne peut pas contenir d'etiquette de reference",
      'assert not bad, bad' in mk and "LEAK = (" in mk)
check("l'extracteur calcule l'etiquette au lieu de la lire du formulaire",
      "label_from(step, correct, opened, checks)" in rd
      and "for key, code, _, _ in IVM.RULES" in rd)
check("l'extracteur n'ecrit rien si le formulaire est incomplet",
      "rien n'est ecrit tant que le formulaire est incomplet" in rd)
check("l'extracteur refuse d'ecraser un fichier de reponses existant",
      "existe deja : deplacez-le avant d'ecrire" in rd)
check("la duree nulle n'est admise que pour un formulaire, enregistrement par "
      "enregistrement",
      'r.get("instrument") != "docx-form"' in rec
      and "un fichier melange deux instruments" in rec)

seed_iv = re.search(r"BASE_SEED = (\d+)", src).group(1)
check("la reception verifie l'ordre contre la graine publiee de l'entretien",
      ("BASE_SEED = %s" % seed_iv) in rec, "graine de l'entretien : %s" % seed_iv)

# Le paquet remis ne doit demander aucune saisie : l'ordre depend de la lettre, et une
# lettre mal tapee changerait l'ordre sans que rien ne le signale sur le moment.
pk = sorted(d for d in os.listdir(HERE)
            if d.startswith("paquet_") and os.path.isdir(os.path.join(HERE, d)))
check("un paquet nomme par annotateur existe", len(pk) >= 2, "trouves : %s" % " ".join(pk))
for d in pk:
    letter = d[len("paquet_"):]
    q = os.path.join(HERE, d, "lancer_entretien_%s.cmd" % letter)
    if not os.path.exists(q):
        check("%s : lanceur portant la lettre" % d, False)
        continue
    cmd = io.open(q, encoding="utf-8").read()
    check("%s : la lettre est dans le lanceur, rien a saisir" % d,
          "set /p" not in cmd and "--annotator %s --resume" % letter in cmd)
    files = os.listdir(os.path.join(HERE, d))
    check("%s : aucune etiquette de reference dans le paquet" % d,
          not any("sample_key" in f or "DO_NOT_SHARE" in f for f in files))

mods = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        mods.update(a.name.split(".")[0] for a in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        mods.add(node.module.split(".")[0])
check("interview.py n'importe que la bibliotheque standard",
      mods <= STDLIB, "imports : %s" % ", ".join(sorted(mods)))
body = norm(without_filenames(re.sub(r'""".*?"""', " ", src, flags=re.S)))
hits = [w for w in FORBIDDEN if w in body]
check("aucun appel reseau ni nom de modele hors docstring",
      not hits, "trouve : %s" % ", ".join(hits) if hits else "")

print()
print("2. LES PREDICATS ET LES CONVENTIONS SONT CEUX DU CODEBOOK CLARIFIE")
CB = os.path.join(ANN, "codebook_clarified_v3.md")
instr = norm(io.open(CB, encoding="utf-8").read())
ns = {}
exec(compile(ast.Module(body=[n for n in tree.body
                              if isinstance(n, ast.Assign)
                              and getattr(n.targets[0], "id", "") in
                              ("RULES", "FREE_LABELS", "REGISTERED")],
                        type_ignores=[]), "<rules>", "exec"), ns)
RULES = ns["RULES"]
check("sept predicats declares", len(RULES) == 7, "%d declares" % len(RULES))
for key, code, text, _ in RULES:
    t = norm(text)
    check("predicat %-4s mot pour mot dans codebook_clarified_v3.md" % code,
          t in instr, "" if t in instr else t[:110])

CONV = ("A malformed step never determines the label",
        "The first fault in time governs, not the first rule in the table",
        "The pivot test requires a computation",
        "A truthful report of absence is a success")
for c in CONV:
    check("convention enoncee dans le codebook v3 : %s" % c[:52],
          norm(c) in instr)
HELPTXT = norm(" ".join(ns.get("HELPVALS", [])) if "HELPVALS" in ns else "")
print()
print("3. L'ORDRE DES QUESTIONS EST CELUI DU CODEBOOK")
expected = ["F1a", "F1b", "F2", "F4", "F5", "F6", "F7"]
check("ordre des codes", [r[1] for r in RULES] == expected,
      "obtenu %s" % [r[1] for r in RULES])
# le premier predicat qui se declenche arrete l'entretien : un seul break apres un y
loop = [n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "interview_item"]
check("interview_item existe", len(loop) == 1)
if loop:
    code = ast.get_source_segment(src, loop[0]) or ""
    cls = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "classify_step"]
    clscode = ast.get_source_segment(src, cls[0]) if cls else ""
    check("l'entretien s'arrete au premier controle vrai",
          'if answers[key] == "y":' in clscode and "break" in clscode)
    check("le residuel F3 n'est pose qu'une fois une faute localisee",
          "label = classify_step(step" in code
          and code.index("label = classify_step(step") < code.index('label = "F3"'))
    check("une justesse laissee incertaine sans faute ne produit pas un S",
          "undetermined = True" in code and 'label = "S"' in code
          and code.index('label = "S"') < code.index("undetermined = True"))
    check("l'etiquette libre de l'annotateur est enregistree a part",
          "free_label=free" in code)
    check("aucune suggestion d'etiquette avant la reponse libre",
          code.count("The questions give the computed label") == 1)
    check("les etapes malformees sont mises de cote avant les controles",
          "malformed_steps(row)" in code and "MALFORMED_NOTE" in code)
    check("la faute la plus precoce est demandee avant la table",
          "earliest step at which something went wrong" in code
          and "first_fault_step" in code)
    check("les etapes malformees ne sont pas candidates",
          "if n not in mal" in code)
    check("la table est appliquee a la faute designee",
          "classify_step(step" in code)

print()
print("4. L'ECHANTILLON REMIS NE PORTE AUCUNE ETIQUETTE")
sample = os.path.join(ANN, "sample_blind.jsonl")
rows = [json.loads(l) for l in io.open(sample, encoding="utf-8") if l.strip()]
keys = set()
for r in rows:
    keys.update(r.keys())
check("%s : %d items, champs %s" % (os.path.basename(sample), len(rows),
                                    " ".join(sorted(keys))),
      keys == {"id", "task", "trajectory"})
suspect = [k for k in keys if "label" in k.lower() or "gold" in k.lower()]
check("aucun champ d'etiquette", not suspect, " ".join(suspect))

print()
if fails:
    print("%d VERIFICATION(S) EN ECHEC : %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("LES QUATRE AFFIRMATIONS SUR L'INSTRUMENT TIENNENT")
sys.exit(0)
