# Provenance of responses_C.jsonl

Extracted on 2026-11-05 by `read_docx_form.py` from
`C:\Users\AJ\Downloads\formulaire_annotateur_C_rempli.docx`, returned as annotator C's
pass by a reader stated to have seen neither A's nor B's file. Fifty items, no blank cell,
no answer needing normalisation, order matching the published seed and the letter C.
`reception.py` accepts it. `instrument = docx-form`, so the duration is null.

Computed labels: S 15, F3 10, F5 7, F2 7, F7 6, F6 4, F4 1.

## This one is an independent reading, and the evidence is in the divergences

Against A and B, which are identical to each other, the free label agrees on 43 of 50,
Cohen's kappa 0.822, and the computed label on 42 of 50, kappa 0.799. No note coincides
with A's or B's, 0 of 50. C departs from its own computed label on 3 items, where A and B
never did on any.

Where it diverges is what makes it credible. The seven items are `t003`, `t176` and `t186`
in the `F2` against `F6` against `F7` block, `t139` where the earliest-fault rule and the
pivot test pull apart, and `t125`, `t143` and `t152` between `F3a`, `F6` and `F7`. Those
are the boundaries reviewer 7 asked about, and they are where a corpus-wide disagreement
should land. C also uses `F4` once and `F6` four times, which A and B do not.

## What still holds across all three files

No unsure answer anywhere, 284 check answers here, 294 in each of the others. The
instrument offers `u` on every check and the instructions ask for it at the first
hesitation. Recorded, not treated as disqualifying.

## How these files must be counted

A and B are one reading, not two: see `provenance_B.md`. For any figure, they count once.
The usable pair is therefore A or B against C, and the disputed set is the seven items
above, which is what the adjudication will arbitrate.
