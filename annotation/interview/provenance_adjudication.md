# The adjudication, and what it says about the reference labels

Extracted on 2026-11-05 by `read_docx_adjudication.py` from
`C:\Users\AJ\Downloads\formulaire_arbitrage_AC_rempli.docx`. Adjudicator AC, who is the
author. The adjudication was blind: the readers appeared as Reader 1 to Reader 4 in an
order drawn from the system for each item, recorded only in
`mapping_adjudication_DO_NOT_SHARE.json`, and the adjudicator stated that the four
response files were not opened before the form was returned. No reference label was in the
form.

Fourteen items arbitrated on the computed label, thirteen on the free label, none left
undecided.

## The two figures

Before adjudication, on the four distinct readings, the free label gives a mean pairwise
Cohen's kappa of 0.817 and a Fleiss kappa of 0.816, with 37 of 50 items unanimous. The
computed label gives 0.797 and 0.796, with 36 of 50 unanimous. This is the quantity
comparable to the published 0.370, and it is the only one that measures the codebook.

After adjudication both come out at 1.000 with 50 of 50 unanimous. That is true by
construction and carries almost no information: once every disputed item has been given
one label, the readers agree perfectly. The one thing it does say is that the codebook
settled all twenty-seven contested items in the adjudicator's judgment, since none was
left undecided.

The informative post-adjudication number is the panel's agreement with the published
reference, which is 0.749 for all four readers alike, since they now carry the same
labels.

## The finding: the adjudicated panel moves away from the reference

0.749 is lower than reader A alone reached before adjudication, 0.846, and lower than
reader K alone, 0.897. On the fourteen arbitrated items the adjudicator agrees with the
first annotator's published label on four. The adjudicated label coincides with reader E
on nine of fourteen, with C on eight, with K on six and with A on five.

The ten departures from the reference are:

    t003   reference F6, adjudicated F1b; no reader chose F6
    t028   reference F3, adjudicated F1b
    t125   reference F3, adjudicated F7
    t143   reference F3, adjudicated F7
    t158   reference F6, adjudicated F3
    t178   reference F7, adjudicated F3
    t183   reference F7, adjudicated F4
    t186   reference F7, adjudicated F6
    t194   reference F3, adjudicated F5; three of the four readers also said F5
    t197   reference F3, adjudicated F5; three of the four readers also said F5

They fall on the same boundaries the round already localised: the `F2` against `F6`
against `F7` block, and `F3` against `F5` where the open-subgoals convention applies.

## What this means, stated plainly

On the items where the categories compete, the published labels are not what the clarified
codebook yields when four readers apply it and a blind adjudicator settles the
disagreements. That is a result about the reference, not about the readers: three of the
four readers and the adjudicator all read `t194` and `t197` as `F5` where the reference
says `F3`.

Two honest ways forward, and the choice is the author's. Either the reference labels on
these ten items are re-examined, and the detection results that depend on them are
recomputed. Or the paper reports that the adjudicated panel departs from the released
labels on ten of fourteen contested items, and says so in Section VI.B rather than leaving
a reader of the repository to find it.

What may not be done is to report 0.817 and 1.000 and leave the 0.749 out, since the
panel's distance from the reference is the part that bears on the taxonomy's reliability.

## Caveats that travel with these numbers

The adjudicator is the author. A non-author adjudicator would be better and the letter
must say which it was.

No file in the round carries a single unsure answer, although the instrument offers `u` on
every check.

Readers E and K both filled the A form, so all three saw the items in the same order and
an order effect could correlate between them.

Readers B and D are set aside in `passes_non_independantes/` and are not counted; see
`provenance_B.md` and `provenance_D.md`.
