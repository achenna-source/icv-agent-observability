# Which number comes from where

All of these are printed by `reproduce.py`, in this order.

| paper | quantity | produced by |
|---|---|---|
| Table IV | failure-mode distribution | `Counter` over `label_human` |
| §VI.A | 130 distinct, design effect 2.34, n_eff 85.5 | `metrics.design_effect` over `cluster_id` |
| §VII.B | agreement 60/200, κ = 0.115 lenient, 58/200 strict | judge block in `reproduce.py` |
| §VII.B, Table VI | judge as binary detector, MCC +0.026 | same block |
| §VII.B | 32B scale control: κ = 0.421 on the 50, 0.401 on the 200 | scale-control block, `results/judge_32b_fr.json` |
| §VII.B | language control: 32B English κ = 0.341 on the 50, 0.383 on the 200 | same block, `results/judge_32b_en.json` |
| §VII.B | paired Δκ: −0.051 against the second annotator, +0.292 against the 7B, +0.018 French minus English | `metrics.cluster_bootstrap` |
| §VII.B, Table VI | 32B as binary detector: precision 0.906, recall 0.977, MCC +0.826, 13 false alarms | same block |
| §VII.B | 44 of the 47 residual F3 flagged by the 32B, 16 by the 7B | same block |
| Table V | per-mode matches for both judges | same block |
| §VII.G | every detector rescored under each annotator on the 50 double-labelled items | `code/label_sensitivity.py` |
| §VII.G | 32B judge: κ 0.421 against annotator 1, 0.202 against annotator 2 | same script |
| Table VI | Tier 1: 37 TP, 25 FP, MCC −0.060 | `signals.tier1` |
| Table VI | Tier 2: 39 TP, 0 FP, MCC +0.369 | `signals.tier2` (needs `--full` for the duplicate test; 38 without it) |
| Table VI | B ∨ C: 68 TP, 25 FP, MCC +0.177 | union |
| Table VI | B\*: 21 TP, 0 FP, MCC +0.257 | `signals.tier1_exempt` |
| Table VI | B\* ∨ C: 59 TP, 0 FP, MCC +0.485 | union |
| §VII.C | c_F = 0.895, c_M = 0.378, cluster-corrected intervals | `metrics.wilson_clustered` |
| §VII.E, Table VIII | lead time, 25 of 37 true positives firing early | `signals.tier1` step index |
| §VII.F | 44/63 recovered, 1 false alarm on 36 held-out successes | entailment block, `--full` |
| §VII.F | F3a 0/9, F3b 12/21, F3c 32/33 | same block, split by `label_f3_subcode` |

The 32B labels in `results/` are outputs, not inputs: `code/judge_scale_control.ipynb`
regenerates them from the corpus on two free-tier T4 GPUs in about three and a half hours.

For the Neurocomputing revision specifically:

| paper | quantity | produced by |
|---|---|---|
| Table 3 | TP/FP/precision/recall/F1-score/MCC for B, C and their union | `signals.tier1`, `signals.tier2` over `data/trajectories_200.jsonl` |
| Table 4 | per-mode detection for each signal and the union | same |
| Figure 6 | the same values, redrawn per signal | same |
| Section VI.B | kappa = 0.370 two-reader agreement, and its decomposition | `annotation/compute_agreement.py` |
| Section IV.B | Signal A pilot figures, incremental over B and C, bootstrap intervals | `results/signal_a_and_pilot_icv.json` |
| Section VI.D | composition standardisation, pilot per mode | `reproduce.py` and the per-mode rates above |
| Section VI.A | 179/200 naive success count | `signals`-free, final-step check over the corpus |

Figures not regenerated here are plots of the tables above.
