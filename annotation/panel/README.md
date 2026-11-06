# Annotations produced by language models, reported nowhere

These files are the output of three language models asked to annotate the 128 failures,
each in an isolated folder without the reference labels, without the detector outputs and
without the paper. They were produced during the revision, and **no figure in the
manuscript rests on them**.

They are kept in the release for one reason: `code/experiments/flag_fault_alignment.py`
reads them, and a script that ships without its inputs cannot be checked. Both are here
so that a reader can see what was computed and why it was withdrawn.

## Why it was withdrawn

The measurement these files supported, the coincidence between an alarm and the first
faulty step, needs a target whose own reproducibility is known. A model annotation gives
no such guarantee, and presenting it beside a human one would invite the reader to treat
the two as equivalent. Section VI.C now reports that measurement against a human index
instead, from the independent round, on the 31 failures that round settles. The source
grounding axis was likewise reannotated by two human readers.

`results/flag_fault_alignment.json` is the output of the withdrawn computation. It is
cited nowhere in the manuscript or in the response to reviewers.

## What is not here

`rater_mapping_DO_NOT_SHARE.json` stays out of the release: it maps the panel's letters
to the models that produced them, and the de-anonymisation it allows serves no reader.
