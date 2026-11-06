# Provenance of responses_D.jsonl, and how the four files must be counted

Extracted on 2026-11-05 by `read_docx_form.py` from
`C:\Users\AJ\Downloads\formulaire_annotateur_D_reanalyse_independante.docx`, whose title
is the D form and whose item order is the one the published seed gives the letter D.
Fifty items, no blank cell, no answer needing normalisation. `reception.py` accepts it.
`instrument = docx-form`, duration null.

Computed labels: S 15, F3 11, F7 7, F5 7, F2 6, F6 3, F4 1.

An earlier file offered as D's pass was in fact the C form filled a second time, with 13
of 50 notes identical to C's. It was refused rather than written, and it is not part of
the round.

## There are two readings in these four files, not four

Pairwise, on the free label, with the number of word-for-word identical notes:

    A against B   50 of 50 identical labels, kappa 1.000, 0 of 50 notes shared
    C against D   48 of 50 identical labels, kappa 0.950, 45 of 50 notes shared
    A against C   43 of 50, kappa 0.822, 0 notes shared
    A against D   45 of 50, kappa 0.872, 0 notes shared
    B against C   43 of 50, kappa 0.822, 0 notes shared
    B against D   45 of 50, kappa 0.872, 0 notes shared

A and B give the same label on every item while sharing no sentence, so one decision
process was written out twice in different prose. C and D share 45 of 50 notes verbatim,
so one text was edited into two files. Across the two groups the files diverge normally.

The round therefore has two readings. For any published figure, {A, B} counts once and
{C, D} counts once, and the usable agreement is the one between the two groups, kappa
0.822 to 0.872, with five to seven items in dispute.

## What also holds across all four

No unsure answer anywhere, although the instrument offers `u` on every check and asks for
it at the first hesitation. A and B never depart from the computed label; C and D do so on
three items each.

## What may and may not be claimed

Two independent readings may be reported, declared as two, with these provenance files
beside them. The published round already had two readers and reached kappa 0.370, so a
two-reader figure here is comparable and is a result.

Four independent annotators may not be claimed. Reviewer 7 asked for a multi-annotator
evaluation, and four files are not four annotators when two pairs share labels or share
text.
