# Which number comes from where

All of these are printed by `reproduce.py`, in this order.

| paper | quantity | produced by |
|---|---|---|
| Table IV | failure-mode distribution | `Counter` over `label_human` |
| §VI.A | 130 distinct, design effect 2.34, n_eff 85.5 | `metrics.design_effect` over `cluster_id` |
| §VII.B | agreement 60/200, κ = 0.115 lenient, 58/200 strict | judge block in `reproduce.py` |
| §VII.B, Table VI | judge as binary detector, MCC +0.026 | same block |
| Table VI | Tier 1: 37 TP, 25 FP, MCC −0.060 | `signals.tier1` |
| Table VI | Tier 2: 39 TP, 0 FP, MCC +0.369 | `signals.tier2` (needs `--full` for the duplicate test; 38 without it) |
| Table VI | B ∨ C: 68 TP, 25 FP, MCC +0.177 | union |
| Table VI | B\*: 21 TP, 0 FP, MCC +0.257 | `signals.tier1_exempt` |
| Table VI | B\* ∨ C: 59 TP, 0 FP, MCC +0.485 | union |
| §VII.C | c_F = 0.895, c_M = 0.378, cluster-corrected intervals | `metrics.wilson_clustered` |
| §VII.E, Table VIII | lead time, 25 of 37 true positives firing early | `signals.tier1` step index |
| §VII.F | 44/63 recovered, 1 false alarm on 36 held-out successes | entailment block, `--full` |
| §VII.F | F3a 0/9, F3b 12/21, F3c 32/33 | same block, split by `label_f3_subcode` |

Figures not regenerated here are plots of the tables above.
