"""Estimators used in the paper, including the cluster correction."""
import math
from collections import Counter


def wilson(k, n, z=1.96):
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def design_effect(cluster_ids):
    """Sum of squared cluster sizes over n. Identical trajectories receive identical
    labels under a deterministic rubric, so the intra-cluster correlation is one."""
    sizes = Counter(cluster_ids).values()
    n = sum(sizes)
    return sum(s * s for s in sizes) / n if n else 1.0


def wilson_clustered(k, n, cluster_ids, z=1.96):
    deff = design_effect(cluster_ids)
    ne = n / deff
    return wilson(k / n * ne, ne, z)


def mcc(tp, fp, fn, tn):
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return (tp * tn - fp * fn) / den if den else float("nan")


def balanced_accuracy(tp, fp, fn, tn):
    return 0.5 * (tp / (tp + fn) + tn / (tn + fp))


def kappa_lenient(ref, pred, valid):
    """Cohen's kappa under the paper's lenient multi-label convention.

    A predicted string outside `valid` (the set of codes the first annotator
    actually assigned) is read as a malformed multi-label and resolves to the
    reference code when it contains it. p_o and p_e are computed on the same
    resolved sequence, so the coefficient is internally consistent.
    """
    def resolve(p, r):
        return r if (p not in valid and r in p) else p

    res = [resolve(p, r) for p, r in zip(pred, ref)]
    n = len(ref)
    if not n:
        return float("nan")
    po = sum(1 for a, b in zip(ref, res) if a == b) / n
    cr, cp = Counter(ref), Counter(res)
    pe = sum(cr[k] * cp[k] for k in set(cr) | set(cp)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def cluster_bootstrap(items, stat, B=5000, seed=42):
    """Resample whole clusters, not items. `items` is a list of (cluster_id, payload)
    and `stat` maps a list of payloads to a scalar. Returns the 95% percentile bounds
    and the resampled values."""
    import random
    rng = random.Random(seed)
    groups = {}
    for cid, payload in items:
        groups.setdefault(cid, []).append(payload)
    keys = list(groups)
    out = []
    for _ in range(B):
        draw = []
        for _ in range(len(keys)):
            draw.extend(groups[rng.choice(keys)])
        v = stat(draw)
        if v == v:
            out.append(v)
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))], out
