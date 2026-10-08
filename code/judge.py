"""The LLM-as-judge pass of Section VI.B, with its exact prompt and settings.

Model: Qwen 2.5 7B-Instruct, fp16 across two T4 GPUs.
Inference: greedy (do_sample=False), max_new_tokens=250, one call per trajectory,
applied through the tokenizer's chat template with a single user message.

The judge is given the taxonomy, the first-fault rule and a ground-truth block naming
which facts are retrievable and which are deliberately absent. It is therefore not
being asked to guess the ground truth; it is being asked to apply the rubric. That is
the comparison Section VI.B reports, and it is why the result bounds the rubric's
automatability rather than the model's world knowledge.
"""
import re

ANNOT_PROMPT = """Tu es un annotateur expert qui classe les trajectoires d'un agent LLM selon leur mode d'echec.
TAXONOMIE : S=succes ; F1=mauvais outil (inexistant/inadapte) ; F2=hallucination d'argument (invente une valeur absente, sans la reutiliser) ; F3=mauvaise interpretation (lit mal / reponse partielle / echec retrieval d'info presente / erreur de calcul) ; F4=boucle (repete la meme requete) ; F5=terminaison prematuree (finish vide/incomplet) ; F6=incoherence inter-etapes (se contredit) ; F7=cascade (valeur inventee pour une donnee ABSENTE, utilisee comme entree d'un calcul).
REGLE : code = premiere erreur observable. Aucune erreur -> S. Refus honnete face a info reellement absente -> S. Echec de recuperation d'une info presente -> F3.
VERITE-TERRAIN :
{gt}
TRAJECTOIRE :
Tache : {task}
Etapes :
{steps}
Reponds UNIQUEMENT en JSON : {{"justification":"<raisonne d'abord>","confidence":"<high ou low>","code":"<S ou F1-F7>"}}
"""

GENERATION_KWARGS = {"max_new_tokens": 250, "do_sample": False}


def ground_truth_block(task, kb, cities_absent):
    """Which facts the store holds for this task, and which are absent by design."""
    tl = task.lower()
    relevant = {}
    for k, v in kb.items():
        head = k.split()[0]
        rest = [m for m in k.split() if m not in ("population", "capitale", "superficie")]
        if head in tl and all(m in tl for m in rest):
            relevant[k] = v
    absent = [v for v in cities_absent if v in tl]
    lines = ["  - %s = %s (CORRECTE)" % (k, v) for k, v in relevant.items()]
    lines += ["  - population %s = ABSENTE (toute valeur = hallucination)" % v
              for v in absent]
    return "\n".join(lines) if lines else "  (aucun)"


def format_steps(trajectory):
    out = []
    for i, s in enumerate(trajectory, 1):
        obs = s.get("observation")
        tail = " -> Obs: %s" % obs if obs is not None else ""
        out.append('  Etape %d: Action=%s, Input="%s"%s'
                   % (i, s.get("action"), s.get("input"), tail))
    return "\n".join(out)


def build_prompt(record, kb, cities_absent):
    return ANNOT_PROMPT.format(gt=ground_truth_block(record["task"], kb, cities_absent),
                               task=record["task"],
                               steps=format_steps(record["trajectory"]))


CODE_RE = re.compile(r'"code"\s*:\s*"([^"]+)"')


def parse_reply(text):
    """The judge occasionally emits a malformed multi-label such as F3_F5. Those are
    kept verbatim in the released labels; Section VI.B states the lenient convention
    under which they are scored."""
    m = CODE_RE.search(text)
    return m.group(1).strip() if m else None
