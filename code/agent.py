"""The agent, its tools and their schemas, exactly as run.

Transcribed from the generation notebook. The three tool names the agent may emit are
the whole tool surface, which is what makes the schema signal of Section IV.B cheap:
validating a call is a membership test and a type check, not a model call.

Inference settings for the 200-trajectory run: Qwen 2.5 1.5B-Instruct, greedy decoding
(do_sample=False), max_new_tokens=150 per step, six-step budget, one T4.
"""
import re

# The tool surface. `finish` is handled by the loop rather than dispatched, so it is a
# valid action name but not a callable tool.
VALID_TOOLS = ["knowledge_base", "calculator"]
TOOL_SCHEMAS = {
    "knowledge_base": {"args": ["query"], "types": {"query": "str"},
                       "returns": "str",
                       "note": "short unaccented query, e.g. 'population paris'"},
    "calculator": {"args": ["expression"], "types": {"expression": "str"},
                   "returns": "str",
                   "note": "arithmetic only, e.g. '2100000 + 3500000'"},
    "finish": {"args": ["answer"], "types": {"answer": "str"},
               "returns": None,
               "note": "terminates the trajectory with the final answer"},
}

SYSTEM_PROMPT = """Tu es un agent qui resout des taches en utilisant des outils.
Outils disponibles :
- knowledge_base(query): cherche un fait. Requete COURTE et SANS ACCENTS (ex: "population paris").
- calculator(expr): UNIQUEMENT pour le calcul mathematique (ex: "2100000 + 3500000").
- finish(answer): termine avec la reponse finale.

Format STRICT a respecter a chaque etape :
Thought: <raisonnement bref>
Action: <nom_outil>
Action Input: "<argument>"
"""

THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\nAction:|\Z)", re.DOTALL)
ACTION_RE = re.compile(r"Action:\s*(\w+)")
INPUT_RE = re.compile(r'Action Input:\s*"?([^"\n]+)"?')


def parse_action(text):
    """Parse one generated step. A missing action yields None, which is what the
    schema signal later flags as a nonexistent-tool call."""
    th, ac, inp = (THOUGHT_RE.search(text), ACTION_RE.search(text),
                   INPUT_RE.search(text))
    return {"thought": th.group(1).strip() if th else "",
            "action": ac.group(1).strip() if ac else None,
            "input": inp.group(1).strip() if inp else None}


def calculator(expr):
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return "Erreur: %s" % e


def make_knowledge_base(kb):
    """All query words must appear in a key for it to match; otherwise the store
    returns not-found. This is the behaviour behind the F3b exonym cases."""
    def knowledge_base(query):
        q = query.lower().strip()
        for k, v in kb.items():
            if all(w in q for w in k.split()):
                return v
        return "Information non trouvee"
    return knowledge_base


def run_agent(task, llm_generate, kb, max_steps=6):
    """llm_generate(prompt) -> str. Greedy decoding, max_new_tokens=150 as run."""
    tools = {"calculator": calculator, "knowledge_base": make_knowledge_base(kb)}
    trajectory = []
    context = SYSTEM_PROMPT + "\n\nTache : %s\n\n" % task
    for _ in range(max_steps):
        parsed = parse_action(llm_generate(context))
        action, inp = parsed["action"], parsed["input"]
        if action == "finish":
            trajectory.append({"thought": parsed["thought"], "action": "finish",
                               "input": inp, "observation": None})
            break
        obs = (tools[action](inp) if action in tools and inp
               else "Erreur: outil inconnu '%s'" % action)
        trajectory.append({"thought": parsed["thought"], "action": action,
                           "input": inp, "observation": obs})
        context += ('Thought: %s\nAction: %s\nAction Input: "%s"\nObservation: %s\n'
                    % (parsed["thought"], action, inp, obs))
    return {"task": task, "trajectory": trajectory}
