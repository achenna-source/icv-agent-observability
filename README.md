# Action-side observability of LLM agent failures, artifact

## Which submission does this state support?

This repository carries the data and code for two related manuscripts from the same
study. **Read the tag, not the branch**, if you are reviewing one of them.

| tag | manuscript | what the tag holds |
|---|---|---|
| **`neucom-d-26-17269-r1`** | *Structural Signals Are Insufficient for Detecting Reasoning Failures: A Taxonomy and In-Chain Verification Study of LLM Agents*, Neurocomputing, first revision | Everything the revision's data availability statement names, and nothing later. Frozen. |
| *(branch `master`)* | *What Can Be Verified for Free? The Observability Boundary of LLM Agent Failures in Retrieval-and-Arithmetic Tasks*, in preparation | The above plus later work that is **not** part of the Neurocomputing submission: a 32B judge scale and language control, and a label-uncertainty sensitivity analysis. |

If you arrived here from the Neurocomputing manuscript, check out the tag:

```
git clone https://github.com/achenna-source/icv-agent-observability
cd icv-agent-observability
git checkout neucom-d-26-17269-r1
python reproduce.py
```

The files that belong to the later work, and that the tag therefore does **not**
contain, are `results/judge_32b_fr.json`, `results/judge_32b_en.json`,
`results/judge_32b_run.log`, `code/judge_scale_control.ipynb` and
`code/label_sensitivity.py`. Checking out the tag gives you the Neurocomputing
artifact and nothing beyond it. They remain on `master`, and in the history, for the
second manuscript.

Data, labels and code for the study described in the two manuscripts above.

Abdelbassette Chenna, Djallel Eddine Boubiche, Abdellah Chehri and Gwanggil Jeon.

If you use the corpus or the labels, please cite the paper. The annotations are one
author's work and carry the limitations set out below; they are released so that they
can be checked, not because they are settled.

## What is here

```
data/    the 200-trajectory corpus with human labels, F3 sub-codes, judge labels and
         cluster ids; the 30-trajectory pilot; the knowledge base as defined for the
         run, with the earlier observation-based reconstruction kept beside it
code/    the agent with its tool schemas, the benchmark's templates and generation
         rules, the judge with its exact prompt and inference settings, all three
         detection signals as run, and the estimators including the cluster correction
annotation/  the codebook and decision procedure, the blinded packet for an
         independent second annotator, and the labels returned
results/     Signal A's pilot results with the per-mode and bootstrap figures;
         and, on the branch only, the 32B judge's labels for both language arms
reproduce.py  regenerates every number the paper reports
MAPPING.md    which script produces which number in which table
DATA_CARD.md  provenance, construction, and the known defects
```

`code/label_sensitivity.py` rescores every detector and both judges under each annotator
in turn, on the fifty double-labelled trajectories. It is the sensitivity analysis behind
Section VII.G, and it is the one script here whose result argues against the paper.

`code/judge_scale_control.ipynb` is the notebook that produced `results/`. It runs on two
free-tier T4 GPUs and needs no key: it loads Qwen 2.5 32B-Instruct in 4-bit, labels the
200 trajectories from the French suite, machine-translates the same trajectories into
English and labels them again. The French arm takes about 68 minutes, the English arm
about 145 minutes including translation.

## Reproducing the paper

```
pip install -r requirements.txt
python reproduce.py           # CPU, seconds, no model download
python reproduce.py --full    # adds the embedding and entailment tiers
```

Each line prints the computed value beside the value the paper states. The script exits
non-zero if any of them disagree. On the released data it prints `all reproduced`.

## Two things to read before using the corpus

**It is smaller than it looks.** Decoding is greedy and four of the eight templates draw
their 25 instances from a pool smaller than 25, so the 200 trajectories are 130 distinct
ones. `cluster_id` in the data marks identical trajectories. Every interval in the paper
is computed at the resulting effective sample size of 85.5, and `metrics.wilson_clustered`
does that for you. Treating the 200 as independent narrows every interval by a factor of
1.53.

**Seven F3 labels are inconsistent with the printed procedure.** Algorithm 1 returns F5
when the final answer is empty, so every F3 trajectory should carry an answer; seven do
not (`t145 t151 t165 t167 t172 t180 t189`). They were labelled by the fault the annotator
judged decisive rather than by the first rule that fires. We report rather than silently
relabel them; reassignment would move F3 from 69 to 62 and F5 from 13 to 20.

## Licence

Code under MIT (`LICENSE-CODE`), data and annotations under CC BY 4.0 (`LICENSE-DATA`).
