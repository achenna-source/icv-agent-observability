# The source-grounding axis, two human readers, and what it supports

Extends `provenance_grounding_A.md`. Reader B's form was extracted on 2026-11-06 from
`C:\Users\AJ\Downloads\formulaire_ancrage_B_rempli.docx`, with the corrected wording and
its own presentation order.

## What the axis applies to

Two hundred trajectories, of which 39 are outside the axis: 21 emit no final answer, which
is a mechanical reading, and 18 are arithmetic-only tasks that supply their own operands
and so have nothing retrieved to be grounded in. The remaining 161 are judged by both
readers. The 18 are excluded from both readers rather than from one, because reader A
judged them under a wording that did not yet name that case.

## The agreement, which is what the axis needed

On the 161, raw agreement 0.981 and Cohen's kappa 0.961, with a template-clustered
interval of [0.897, 1.000]. Three disagreements: `t050`, `t070`, `t149`. Neither reader
used the unsure answer, and neither filled a note, so there is no textual signal of
independence in either direction.

For comparison, the category codebook of the same corpus reaches 0.817 among four readers.
A binary question with a concrete referent is reproducible where a seven-way scheme is not,
which is a result about question design rather than about readers.

## What the axis says that the reference label does not

On the 158 items both readers agree on: `F2` is ungrounded 19 of 19, `F6` is grounded 7 of
7, `F7` is ungrounded 14 with 2 grounded, and the in-scope successes are grounded 54 of 54.

`F3` splits 31 ungrounded against 30 grounded. That is the point of the axis: `F3` is where
the reference label is silent about grounding, and the axis is not.

It also cross-validates the released sub-code. Of the `F3c` trajectories in scope, 27 are
ungrounded against 6 grounded; `F3b` is grounded 16 against 3; `F3a` grounded 8 against 1.

## The detectors against the axis, with intervals

Scored on those 158 items, with 64 positives:

    B, schema        precision 0.130  recall 0.047  MCC -0.231  CI [-0.462, -0.015]
    C, consistency   precision 0.639  recall 0.359  MCC +0.259  CI [-0.189, +0.624]
    B*, exempted     fires on no item of this subset, so its correlation is undefined
    B* or C          identical to C here, for the same reason

The removed model-annotated version gave the consistency signal 0.641 at 0.362 for +0.306,
and schema validation 0.081 at 0.072 for -0.373. The human axis therefore reproduces that
measurement almost exactly on the consistency signal, which is worth stating as a check on
both.

What the intervals add, and what they take away. Schema validation is established as
anti-correlated with grounding: its interval excludes zero. The consistency signal is not
established as correlated: its interval contains zero at eight clusters. The contrast
between the two signals survives in the point estimates and does not survive as a
significance claim, and any sentence written from this table has to say so.

## What may be claimed

That the axis is reproducible by human readers at 0.961, that it separates grounding
inside `F3` where the label does not, that it cross-validates `F3c`, and that schema
validation is anti-correlated with it. Not that the consistency signal detects
ungroundedness at a distinguishable rate on this corpus.

## Recorded with the figures

No unsure answer and no note, from either reader, on two hundred items each. The same
pattern holds in every file returned in this round and is recorded rather than treated as
disqualifying. The target excludes the three disagreements instead of adjudicating them,
so no third judgment enters it.
