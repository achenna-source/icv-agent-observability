"""Signal A, logit-based confidence, with the decision rule of Section IV.B.

Requires white-box access: the token-level score distributions must be captured at
generation time. They were captured for the 30-trajectory pilot and not for the
200-trajectory run, which is why Section IV.B reports Signal A on the pilot only and
says so rather than implying wider coverage.

The rule has two levels, and the distinction matters because an earlier draft of this
file described the second one wrongly. Within a step, the entropy is the unweighted
mean over the tokens that step generated. Across steps, the trajectory score is the
maximum of those per-step values, not their mean: one sufficiently uncertain step is
enough to flag the trajectory, and a long confident stretch does not dilute it. Taking
the mean across steps instead gives a precision of 0.86 and a recall of 0.35 at the a
priori threshold, where the paper reports 0.53 and 0.47.

The top-1 margin is recorded alongside as a diagnostic and is not part of the rule
evaluated in the paper.

Thresholds reported: 0.90, fixed before the pilot was scored, and 0.55, the F1-optimal
value on the pilot. The second is a development-set figure by construction, since the
pilot is the corpus on which it was chosen.
"""

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
    """The trajectory score: the maximum of the per-step mean entropies.

    This is the quantity the threshold is applied to and the one behind every Signal A
    figure in the paper. `trajectory_entropy_mean` below is kept for reference because
    the stored results record both, but it is not the decision variable.
    """
    return max(step_entropies) if step_entropies else 0.0


def trajectory_entropy_mean(step_entropies):
    """The mean across steps. Reported as a descriptive statistic only."""
    return sum(step_entropies) / len(step_entropies) if step_entropies else 0.0


def signal_a(step_entropies, threshold=THRESHOLD_APRIORI):
    """(flagged, trajectory score). The score is the maximum per-step entropy."""
    h = trajectory_entropy(step_entropies)
    return h > threshold, h
