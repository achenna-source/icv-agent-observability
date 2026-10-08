# Codebook and decision procedure

This is the procedure the first annotator applied to all 200 trajectories and the one
given to the second annotator. Section VI.B of the paper reports how far two readers
applying it agree, which is Cohen's kappa = 0.370 on a stratified sample of 50.

## The seven categories

| code | name | first observable fault |
|---|---|---|
| S | success | no observable fault, and the final answer is correct |
| F1 | tool selection error | calls a tool that does not exist, or picks an existing but unfit tool |
| F2 | tool argument hallucination | well-formed arguments containing an invented value, not reused as a pivot |
| F3 | reasoning and retrieval error | residual: wrong or incomplete answer from mishandling available information |
| F4 | planning loop | revisits the same sub-goal without progress |
| F5 | premature termination | stops, or emits an empty or None final answer, with sub-goals open |
| F6 | inter-step inconsistency | contradicts a value it produced earlier |
| F7 | cascading hallucination | fabricates a value and uses it as the pivot of the final computation |

## The three rules that resolve ambiguity

**Primary cause over terminal state.** A trajectory that fails in more than one way
takes the label of its *first observable* error, not of the state it ends in. A
trajectory that mishandles a retrieved value and then also returns nothing is F3, not
F5.

**The residual is defined by exclusion.** F3 is what remains once the other six are
ruled out. It is not a positive diagnosis of reasoning and should not be read as one.

**The pivot test separates F2 from F7.** A one-off invented value that is reported but
not computed with is F2. An invented value that becomes the input of the rest of the
computation is F7. Ask whether removing the invented value would change the final
answer: if yes, it is a pivot, so F7.

## Two conventions that the procedure above leaves open

Section VI.B reports that these two account for most of the disagreement between two
readers, and they should be fixed in writing before the scheme is reused.

**Recovered malformed step.** An agent emits a step naming no registered tool, then
issues a valid action and terminates with a correct non-empty answer. The first
annotator read these as S. Counting them as S rather than F1 raises the two-reader
kappa from 0.370 to 0.477. The schema signal of Section IV.B flags them, and that is
the sole source of its 25 false alarms.

**F2 against F7 on a borderline pivot.** Where it is arguable whether an invented value
was computed with, readers diverge. Treating the F2 and F7 assignment as one decision
raises kappa further, to 0.793, but it dissolves the pivot test, so the paper does not
adopt it.

## What the annotator was and was not given

Given: the task, the full trajectory with observations, and a ground-truth block naming
which facts the store holds and which are absent by design. Not given: the other
annotator's labels, the detector outputs, or the template that generated the task.
