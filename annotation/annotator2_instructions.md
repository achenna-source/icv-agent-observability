# Instructions for the second annotator

You are labelling agent trajectories for a study on how LLM agents fail. Your labels will be
compared with a first annotator's labels to measure how reproducible the labelling scheme is.
**You should not try to guess what the first annotator decided.** Disagreement is informative;
a forced match is not. Work alone, and do not discuss individual items with the other authors
until your sheet is submitted.

Time needed: roughly 3–4 hours for 50 trajectories, including breaks. Split it over two
sittings if you prefer — annotation quality drops sharply when tired.

## What you receive

- `sample_packet.md` — 50 trajectories, each with the task, the ground-truth answer from the
  knowledge base, every step the agent took, and its final answer.
- `annotations_annotator2.csv` — the sheet to fill in (`id,label,confidence,notes`).
- The codebook (category definitions and worked examples).

## The procedure

For each trajectory, first decide whether it **succeeded**: did the agent's final answer match
the ground truth? If yes, and no fault occurred along the way, label it `S`.

If it failed, apply the decision procedure **in this order** and stop at the first rule that
fires. The label is the category of the *first observable fault*, not the state the trajectory
ends in — a trajectory that mishandles a retrieved value and then also returns nothing is a
reasoning error (F3), not a termination error (F5).

| Order | Check | Label |
|---|---|---|
| 1 | The agent called a tool that does not exist in the registered tool set | `F1a` |
| 2 | The agent called an existing tool that does not fit the sub-goal, when a better one was available | `F1b` |
| 3 | Arguments are well formed but contain a value absent from the knowledge base, **and** that value is not later used as the pivot of the final result | `F2` |
| 4 | The agent repeats an equivalent step without progress until the budget runs out (verbatim, or rephrased but functionally the same) | `F4` |
| 5 | The agent stops, or emits an empty/`None` final answer, before finishing | `F5` |
| 6 | The final answer contradicts a value the agent itself produced earlier | `F6` |
| 7 | The agent fabricates a value absent from the sources and uses it as the **pivot** of the final computation (shown in a calculation, or reconstructible from the final number) | `F7` |
| 8 | None of the above, and the answer is wrong or incomplete — the residual category | `F3` |

For `F3`, add a sub-code in the `notes` column if it is clear: `F3a` wrong calculation over
correctly retrieved values, `F3b` failed or misdirected retrieval of a fact that was present
(e.g. querying the wrong key), `F3c` partial or ungrounded answer.

## The three judgment calls

Most items are mechanical. Three predicates need your judgment, and these are exactly the ones
we want measured:

**Tool fitness (rule 2).** "Unfit" means a competent solver would not have chosen it for that
sub-goal — not merely that a different tool would also have worked.

**Semantic repetition (rule 4).** Two steps are equivalent if they pursue the same sub-goal by
the same means, even when the wording differs. A genuine follow-up query on the same entity is
not a repetition.

**The pivot test (rules 3 vs 7).** This is the distinction that separates `F2` from `F7`. Ask:
does the fabricated value *carry through* into the final result? If the agent invents a
population figure and then divides it by something to produce its answer, that is `F7`. If it
invents a value, gets an error or ignores it, and reaches its answer another way, that is `F2`.

## The confidence column

Mark `high` when the rule fired cleanly, `low` when you hesitated between two categories.
Low-confidence items are the ones we will look at when we adjudicate disagreements, and they
tell us which parts of the codebook are ambiguous. Do not leave it blank.

## The notes column

One line, when useful: which step contained the fault, or which two categories you were torn
between. This is what makes adjudication fast rather than a re-annotation.

## What not to do

Do not skip items you find hard — a `low` confidence label on a hard item is far more useful
than a blank. Do not go back and revise earlier labels after your understanding shifts; if the
codebook felt wrong at item 40, note it, and we will handle it in adjudication. Do not look at
the detection signals' output, the first annotator's labels, or the paper's results tables.
