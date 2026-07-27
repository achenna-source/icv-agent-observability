# Action-side observability of LLM agent failures — artifact

Data, labels and code for the paper *What Can Be Verified for Free? The Observability
Boundary of LLM Agent Failures in Retrieval-and-Arithmetic Tasks*.

Abdelbassette Chenna, Djallel Eddine Boubiche, Abdellah Chehri and Gwanggil Jeon.

If you use the corpus or the labels, please cite the paper. The annotations are one
author's work and carry the limitations set out below; they are released so that they
can be checked, not because they are settled.

## What is here

```
data/    the 200-trajectory corpus with human labels, F3 sub-codes, judge labels and
         cluster ids; the 30-trajectory pilot; the knowledge base as observed
code/    the three detection signals as run, and the estimators including the cluster
         correction
annotation/  the blinded packet for an independent second annotator
reproduce.py  regenerates every number the paper reports
MAPPING.md    which script produces which number in which table
DATA_CARD.md  provenance, construction, and the known defects
```

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
