# Provenance of responses_A.jsonl

Written at extraction so that what the reception check saw travels with the data instead
of staying in a conversation. Facts only, and the open question stated as open.

## Where the file comes from

Extracted on 2026-11-05 by `read_docx_form.py` from the Word form
`C:\Users\AJ\Downloads\formulaire_annotateur_A_rempli.docx`, which was returned as
annotator A's pass. Fifty items, no blank cell, no answer needing normalisation, order
matching the published seed and the letter A. `reception.py` accepts it.

Each record carries `instrument = docx-form`, so the duration field is null: a form does
not measure time per item, and a number there would be invented.

Computed labels: S 15, F3 15, F5 7, F2 6, F7 6, F6 1. No item left unsettled by the
questions.

## What the reception check flagged

Two patterns, neither of which disqualifies a reader and both of which are recorded.

No unsure answer anywhere, across 294 check answers. The instrument offers `u` on every
check and the instructions ask for it at the first hesitation.

The free label never departs from the computed label, fifty times out of fifty. That
departure is what question 5 exists to capture, and the four simulated readers did produce
some.

## What the comparison with the simulated rounds shows

Run because a copy of a simulated reader's output had earlier been found in this
annotator's working folder under the human file's name. The comparison looks only at the
simulated rounds, never at the reference labels, so it does not bias what the round
measures.

Against the clarified simulated round, the free label agrees 47 or 48 times out of fifty
with any of the four readers, and the computed label 45 to 47 times. This is not by itself
evidence of copying: those four readers already agreed with each other 49 times out of
fifty on the free label, so that level of agreement is what the clarified codebook
produces in a careful reader. Against the R1 round, agreement falls to between 16 and 26.

The fifty notes are all filled, 47 of them distinct, and not one coincides with any note
written by any simulated reader in either round. Sixty-two distinct knowledge base lookups
are recorded, more than any simulated reader logged.

## The open question

Whether a person produced this pass is not established by the file, and not refuted by it
either. It is recorded here as unresolved. Anyone using this file for a published figure
should resolve it first, by asking the annotator, and write the answer below.

Resolved on: not yet
By: not yet
Answer: not yet

## What the arrival of B settled

Annotator B's pass arrived the same day and is identical to this one on all fifty free
labels and all fifty computed labels, with no unsure answer in either file and the free
label never departing from the computed one in either. The notes and the knowledge base
lookups are entirely different in wording, 0 of 50 coincide, so only the surface differs.
`provenance_B.md` holds the measurements. The two passes therefore cannot be treated as
two independent readings, and no agreement figure may be computed from them.

## What cannot be computed from this file alone

Nothing about agreement. Inter-annotator agreement needs at least two passes, and this is
one. No figure from this file may appear in the manuscript or the response letter until a
second independent pass exists, and the adjudication needs two passes before it will run
at all.
