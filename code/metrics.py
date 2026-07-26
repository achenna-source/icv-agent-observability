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
