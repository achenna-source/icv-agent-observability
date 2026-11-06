# The external adjudication of the three residual items

## Why only three items went outside

The blind adjudication of the fourteen disputed items was carried out by the author, who
is also the first annotator, so it is blind but not independent. On most items that is a
caveat. On three it was more than that: `t003`, `t028` and `t183` are the only items where
the adjudication places a label in `F1b` or `F4`, the two categories the main corpus does
not exercise at all. An author settling those three alone would be choosing, on the only
items with no corpus evidence behind them, in favour of categories the paper declares
unexercised.

Those three were therefore referred to an adjudicator who is not an author, on a form
generated for them alone.

## What the external adjudicator saw, and did not see

The same blinded material: the trajectory, and the four readers' labels as Reader 1 to
Reader 4 with their own notes, in an order drawn afresh from the system for each item.
That order differs from the author's on all three items, and both orders are recorded
under their adjudicator in `mapping_adjudication_DO_NOT_SHARE.json`, which the generation
script nests per adjudicator so that a second form cannot overwrite the first one's
blinding record.

They did not see the author's choices, the author's reasons, the reference labels, or any
reader's letter. The generation script checks the finished document for all of these
before saving it.

## The outcome

On all three items, and on both label sets, the external adjudicator reached the label the
author had reached: `F1b` on `t003`, `F1b` on `t028` and `F4` on `t183`. The reasons given
are their own and differ in wording from the author's.

No figure changes. `adjudication_agreement.py` gives the same pre-adjudication and
post-adjudication values, and `label_sensitivity.py` gives the same three detector columns
as before, with the base rate unchanged at 35 failures of 50 under both the released
labels and the panel.

`label_sensitivity.py` now reads every adjudication file for a label set and lets a
non-author adjudicator keep the item where they ruled, so the published artefact reflects
the external verdict rather than only the author's. It records, per item, who settled it.

## What this does and does not buy

It removes the author-as-adjudicator objection on exactly the items where it had force,
and it does so without moving a number, which is the strongest form the removal can take.

It does not make the fourteen-item adjudication independent as a whole: ten items were
still settled by the author, and the manuscript and the letter say so. It does not
establish `F1b` or `F4` as exercised categories either. Two readers agreeing that a
trajectory belongs in a category the corpus never otherwise uses is a statement about
those three trajectories, not evidence that the category is validated.
