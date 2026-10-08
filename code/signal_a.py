"""Signal A, logit-based confidence, with the decision rule of Section IV.B.

Requires white-box access: the token-level score distributions must be captured at
generation time. They were captured for the 30-trajectory pilot and not for the
200-trajectory run, which is why Section IV.B reports Signal A on the pilot only and
says so rather than implying wider coverage.

The rule is deliberately plain. A trajectory is flagged when the mean token-level
entropy over all of its generated tokens exceeds a threshold. Aggregation is an
unweighted mean over tokens, with no per-step voting. The top-1 margin is recorded
alongside as a diagnostic and is not part of the rule evaluated in the paper.

Thresholds reported: 0.90, fixed before the pilot was scored, and 0.55, the F1-optimal
value on the pilot. The second is a development-set figure by construction, since the
pilot is the corpus on which it was chosen.
"""
import math

THRESHOLD_APRIORI = 0.90
THRESHOLD_F1_OPTIMAL = 0.55


def step_entropy_and_margin(scores, eps=1e-9):
    """scores: the per-token logit tensors returned by generate(output_scores=True,
    return_dict_in_generate=True). Returns (mean entropy, mean top-1 margin)."""
    import torch
    entropies, margins = [], []
    for score in scores:
        probs = torch.softmax(score[0], dim=-1)
        p = probs[probs > eps]
        entropies.append(float(-(p * torch.log(p)).sum()))
        top2 = torch.topk(probs, 2).values
        margins.append(float(top2[0] - top2[1]))
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    return mean(entropies), mean(margins)


def trajectory_entropy(step_entropies):
    """Unweighted mean over all generated tokens in the trajectory."""
    return sum(step_entropies) / len(step_entropies) if step_entropies else 0.0


def signal_a(step_entropies, threshold=THRESHOLD_APRIORI):
    """(flagged, mean entropy)."""
    h = trajectory_entropy(step_entropies)
    return h > threshold, h
