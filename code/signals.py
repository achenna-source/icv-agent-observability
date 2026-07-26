"""
The three detection signals, as run in the study.

Tier 1 (schema validation) is given in two forms. `tier1` is the configuration whose
numbers the paper reports throughout. `tier1_exempt` is the repaired form: a call to a
nonexistent tool is ignored when the agent later issues a valid action and terminates
with a non-empty answer. The predicate is still structural, so the repaired tier stays
within the free, content-agnostic class.

Tier 2 (step consistency) is reproduced from the original run: a duplicate test over
step embeddings and a numeric contradiction test over the final answer.
"""
import re

TOOLS = {"knowledge_base", "calculator", "finish"}
_ARITH = set("0123456789+-*/(). ")
_NUM = re.compile(r"\d[\d\s]{4,}")


def _parses(expr):
    s = str(expr or "").strip()
    if not s or not set(s) <= _ARITH:
        return False
    try:
        eval(s, {"__builtins__": {}}, {})
        return True
    except Exception:
        return False


def _recovers(rest):
    return (any(s.get("action") in TOOLS for s in rest)
            and any(s.get("action") == "finish"
                    and str(s.get("input") or "").strip() not in ("", "None")
                    for s in rest))


def tier1(trajectory, exempt_recovered_detours=False):
    """(flagged, index of the first offending step)."""
    for k, st in enumerate(trajectory):
        action, arg = st.get("action"), st.get("input")
        if action is None or action not in TOOLS:
            if exempt_recovered_detours and _recovers(trajectory[k + 1:]):
                continue
            return True, k
        if arg is None or (isinstance(arg, str) and arg.strip() == ""):
            return True, k
        if action == "calculator" and not _parses(arg):
            return True, k
        if action == "finish" and (arg is None or str(arg).strip() in ("", "None")):
            return True, k
    return False, None


def tier1_exempt(trajectory):
    return tier1(trajectory, exempt_recovered_detours=True)


def _numbers(text):
    if text is None:
        return set()
    out = set()
    for m in _NUM.finditer(str(text).replace(" ", "")):
        d = re.sub(r"\D", "", m.group())
        if d:
            out.add(int(d))
    return out


def tier2(trajectory, encoder=None, threshold=0.92):
    """(flagged, duplicate_flag, contradiction_flag). Pass a SentenceTransformer as
    `encoder` to enable the duplicate test; without one only the contradiction test runs."""
    duplicate = contradiction = False
    if encoder is not None and len(trajectory) >= 2:
        import numpy as np
        texts = [f"{s.get('thought','')} {s.get('action','')} {s.get('input','')}".strip()
                 for s in trajectory]
        e = encoder.encode(texts, normalize_embeddings=True)
        for i in range(len(e)):
            for j in range(i + 1, len(e)):
                if float(np.dot(e[i], e[j])) > threshold:
                    duplicate = True
    retrieved = set()
    for s in trajectory:
        if s.get("action") == "knowledge_base" and s.get("observation") not in (
                None, "Information non trouvée"):
            retrieved |= _numbers(s.get("observation"))
    last = trajectory[-1]
    if last.get("action") == "finish" and last.get("input"):
        for v in _numbers(last.get("input")):
            if v > 50000 and v not in retrieved:
                if not any(abs(v - (a + b)) < 1000 or abs(v - (a - b)) < 1000
                           or abs(v - (a + b) // 2) < 1000
                           for a in retrieved for b in retrieved):
                    contradiction = True
    return (duplicate or contradiction), duplicate, contradiction
