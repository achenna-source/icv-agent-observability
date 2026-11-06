# Provenance of grounding_A.jsonl, the source-grounding axis by a human reader

Extracted on 2026-11-06 by `read_docx_grounding.py` from
`C:\Users\AJ\Downloads\formulaire_ancrage_A_rempli.docx`. Two hundred trajectories, one
question each, no blank where a final answer exists, order matching the published seed and
the letter A.

The axis asks whether the final answer asserts a numeric value that no observation of its
own trajectory returned. The twenty-one trajectories that emit no final answer are read
mechanically and were not put to the reader; that count matches the mechanical reading
exactly.

## What the reader returned

On all two hundred: ungrounded 68, grounded 111, no answer 21, unsure 0.

On the 128 failures: ungrounded 66, grounded 41, no answer 21. The earlier annotation,
produced by three language models and since removed from the manuscript, gave 69, 38 and
21 on the same failures. A single human reader therefore lands within three items of that
panel on every cell.

On the 72 successes, which the earlier annotation never covered: grounded 70, ungrounded 2.

## What the axis separates, and where it is informative

Against the reference label: `F2` is ungrounded 21 of 21, `F7` is ungrounded 14 with 2
grounded and 2 without an answer, `F6` is grounded 7 of 7, and `F5` is 12 without an
answer and 1 grounded.

`F3` splits almost exactly in half, 31 ungrounded against 31 grounded with 7 lacking an
answer. That is the whole point of the axis: `F3` is where the reference label says nothing
about grounding, and the axis says something there.

It also cross-validates the released sub-code. Of the 34 trajectories marked `F3c`,
partial or ungrounded answers, 27 are judged ungrounded. The earlier model annotation gave
the same 27 of 34.

## A defect in the question, found by the data rather than by review

The two successes judged ungrounded are `t007` and `t008`, both arithmetic-only tasks of
template T0 of the form "Combien font 13 multiplié par 39". Their answers, 903 and 507, are
correct, but no observation returned them: the operands come from the task statement and
the result from the calculator, so nothing was retrieved at all.

The reader followed the question as written. The question is what is incomplete: it admits
arithmetic over the values the observations returned and says nothing about values the task
itself supplies. Nineteen trajectories of template T0 are arithmetic-only and fall in that
gap.

The principled repair is to put arithmetic-only tasks outside the axis, since a task whose
answer is computed from operands given in its own statement has no retrieval to be grounded
in. That excludes nineteen items, of which the two above are the only ones whose verdict it
changes, and none of the 128 failures is affected. The second reader's form will carry the
corrected wording, and these nineteen items will be excluded from both readers rather than
compared across two wordings.

## What this file does not yet permit

A target. One reader gives no reproducibility, and a figure scored against a target whose
own agreement is unknown is exactly the defect that removed the previous version of this
axis from the manuscript. Nothing from this file may be written into the paper until a
second independent reader has returned.

## Recorded with the figures

No unsure answer anywhere, and no note filled, on two hundred items. The same pattern holds
in every file returned in this round, and it is recorded here as it is in
`provenance_A.md`, `provenance_C.md` and `provenance_D.md` rather than treated as
disqualifying.
