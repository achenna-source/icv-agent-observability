# Provenance of responses_B.jsonl, and the comparison of the two passes

Written at extraction so that what the checks saw travels with the data.

## Where the file comes from

Extracted on 2026-11-05 by `read_docx_form.py` from
`C:\Users\AJ\Downloads\formulaire_annotateur_B_rempli.docx`, returned as annotator B's
pass. Fifty items, no blank cell, no answer needing normalisation, order matching the
published seed and the letter B. `reception.py` accepts it. Each record carries
`instrument = docx-form`, so the duration is null.

Computed labels: S 15, F3 15, F5 7, F2 6, F7 6, F6 1. The same distribution as A, item
for item.

## The two passes are not two independent readings

Measured, not inferred.

The free label is identical on 50 of 50 items. The computed label is identical on 50 of
50. The answer on whether the final answer is correct is identical on 50 of 50. The step
named as the earliest fault is identical on 49 of 50. Both files contain no unsure answer
at all, across 294 check answers each. In both, the free label never departs from the
computed label, fifty times out of fifty.

What differs is only the surface. No note coincides word for word, 0 of 50, and no list of
knowledge base lookups coincides, 0 of 50. The answers to the seven checks differ on 18 of
50 items, which changes nothing about the labels because the rule takes the first yes.

They also agree on every item that is known to be hard, and on two of them, `t003` and
`t158`, they depart from all four simulated readers in the same direction. So they are not
copies of the simulated rounds: they share a source with each other.

## Why no agreement figure may be computed from this pair

The published two-reader round on this same corpus gave Cohen's kappa 0.370, and the whole
point of the revision is that the codebook was ambiguous enough to produce that. Two
readers who never spoke to each other do not then agree on fifty items out of fifty,
including the items where the categories compete. A kappa computed here would come out at
1.0 and would measure the pair's common source, not the codebook.

The adjudication the reviewer asks for cannot happen either: `adjudicate.py` finds the
disputed items, and between these two files there are none, so it would report that there
is nothing to arbitrate.

No figure derived from `responses_A.jsonl` and `responses_B.jsonl` may appear in the
manuscript or in the response letter.

## What a real pair would need

Two people labelling separately, each in their own sitting, neither with access to the
other's file or answers, which is what `INSTRUCTIONS_ANNOTATOR.md` already asks for. The
terminal instrument is the better one for this, because it records the time spent on each
item, and that record makes a mechanical fill visible where a Word form cannot.

Disagreement is the expected outcome and the informative one. A pair that disagrees on ten
or fifteen of fifty items, concentrated on `F2` against `F7` and on `F6`, is what this
corpus should produce and what the reviewer is waiting to see.

## Open and recorded as open

Whether a person produced either pass is not established by these files. See
`provenance_A.md` for the same question on A. Resolve it before any use, and write the
answer in both files.
