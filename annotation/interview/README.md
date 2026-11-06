# The interview instrument for the human annotator round

This directory holds the instrument used for the independent human multi-annotator round,
the annotator-facing instructions, and the script that turns the annotators' files into
the formats the agreement scripts in `..` already read.

## Why the questions are scripted and not generated

The labels from this round serve as a human reference. A language model that formulates the
questions can lead the answer, which would make the resulting label partly the model's own,
so no model takes part in the labelling path. Nothing in `interview.py` is generated: the
predicates are copied verbatim from `../codebook_clarified_v3.md`, they are asked in that
document's order, the interview stops at the first check that fires, and the label is
computed from the answers by the published rule. The judgment is the annotator's, the label
is a function of that judgment, and the file keeps both.

The program never shows another annotator's answers, any detector output, or any reference
label. Its only reference to the study's data is a deterministic substring lookup over
`../../data/knowledge_base_observed.json`, which the annotator invokes with `kb <text>`.
Every lookup is recorded.

`verify_instrument.py` checks these claims in one command and exits non-zero otherwise: no
import outside the standard library, no network call and no model name, every predicate and
every convention found verbatim in the clarified codebook, the order as published, the stop
at the first check that fires, the malformed steps set aside before the checks, the earliest
fault located before the table is applied, and a sample carrying no labels.

## Why the reference document is the clarified codebook

A first version of this instrument asked the seven checks of `../annotator2_instructions.md`
in the order of its table, with no conventions, because that is the document the second
annotator received. A trial on three trajectories put it against the reference labels and it
diverged on all three: `t154` gave F1a where the reference is S, `t063` gave F7 where the
reference is F2, and `t183` gave F1a where the reference is F7. The instrument was faithful
and the table was not: read literally and in its own order, the table does not describe the
procedure that produced the labels. Each of the three divergences is settled by one of the
four conventions, and `interview.py` reproduces all three reference labels once those
conventions are in the question sequence.

That version is kept as `interview_table_only.py` so the finding can be reproduced. It is
not for annotating.

The consequence for the paper is worth stating plainly. The released decision table is
incomplete in a way that a human reader papers over and a literal reader cannot, which is
part of why two readers agreed at 0.370. It also means the nine F1 disagreements of the
two-reader round are not noise: in all nine the second annotator wrote F1 and the first
wrote something else, which is one reader applying the table and the other applying the
conventions.

## What this adds over the spreadsheet used in the first round

1. The order of the checks is enforced, and the fault is located before they begin. The
   spreadsheet let an annotator write a code directly, so which rule decided is unknown.
2. Each predicate is recorded separately, so a disagreement localises to the question that
   caused it, and therefore to the sentence of the codebook to rewrite.
3. The annotator also gives a free label, without being bound by the questions. Two
   agreement figures follow: the computed label measures the codebook, and the free label is
   the quantity comparable to the first round, which was run on a spreadsheet with no
   questions.
4. Unsure is an admitted answer on every check, instead of a confidence column filled in
   afterwards.
5. Presentation order is shuffled per annotator from a seed published in advance, so an
   order effect cannot correlate across annotators.
6. Each answer is written to disk as it is given.

Point 3 matters for disclosure. A round run on this instrument and compared with the 0.370
of the spreadsheet round compares two instruments as well as two codebooks, and part of any
gain could come from the instrument. The free label is what makes the two rounds comparable,
and both figures must be reported.

## Running it

The annotator receives a self-contained packet carrying `codebook_clarified_v3.md`, reads
`INSTRUCTIONS_ANNOTATOR.md`, and double-clicks the launcher. No dependency beyond the
Python standard library.

    python -I make_packet.py                     packet_annotateurs/, letter typed in
    python -I make_packet.py --letters A B C D   paquet_A/ ... paquet_D/

The second form is the one to hand out. The presentation order is drawn from the published
seed and the annotator letter, and the output file is named from the letter, so a mistyped
letter would change both and nothing would say so at the time. In a named packet the letter
is written into the launcher and the annotator types nothing. Every other file is asserted
byte-identical to the shared source, and no packet may carry a reference label, a detector
output or the paper.

`RECRUTEMENT.md` holds what the four passes need from people rather than from code: who
can annotate, the message to send, the three profile questions the response letter needs,
and what to run as each file comes back. It is not shipped in any packet.

    python -I interview.py --annotator A
    python -I interview.py --annotator A --resume

`essai_3_items.cmd` runs the same interview on three trajectories, for anyone who wants to
see the instrument before committing to fifty. Its answers are written to `essai/` and
deleted on each launch.

The seed is `BASE_SEED` in `interview.py`, currently 20261105. It is published before the
labelling begins and never changed afterwards, since the presentation order is part of the
protocol.

## Collecting the round

    python -I reception.py

checks each returned `responses_*.jsonl` before it enters the analysis. It refuses a file
whose letter is not on the roster, whose records carry another letter, which is missing
items or holds duplicates, whose label or `F3` sub-code is outside the published set, or
whose item order is not the one the published seed and that letter give, which is what a
file produced with the wrong launcher looks like. It reports without refusing the pace, the
absence of any unsure answer, a label covering almost every item, and whether the knowledge
base was ever queried.

It never reads the reference labels. A reception check that compared a returned file with
the reference would set aside the annotators who depart from the author, which is precisely
the quantity this round measures, so the result would be chosen rather than measured.
`verify_instrument.py` asserts that property on the file.

    python -I to_sheets.py

reads every `responses_*.jsonl` in this directory and writes, under `human_round/`:

- `computed/annotations_<X>.csv` and `computed/labels_<X>.json`, from the computed labels;
- `free/annotations_<X>.csv` and `free/labels_<X>.json`, from the free labels;
- `localisation.txt` and `localisation.json`, which question each disagreement starts at.

Those two formats are what `../compute_agreement.py` and `../panel_agreement.py` consume, so
the existing analysis runs unchanged on human output.

An item the questions do not settle, because the annotator left the correctness of the final
answer unsure and located no fault, is excluded from the computed set and counted there. It
is never filled in silently.

## What the instrument does not do

It does not adjudicate. Adjudication is a separate step with its own blinding: the
adjudicator sees the label sets without knowing which annotator produced which.

It does not fix the sampling problem either. The present sample of fifty draws each fault
category from a single task template, so the boundaries between F2, F3, F6 and F7 are never
put in competition inside one task, and no round on this sample can establish them. A sample
in which the competing categories share templates has to be built first.

The reference document is `../codebook_clarified_v3.md`, which is `../codebook_clarified.md`
with one clause changed in the pivot convention. The clause settles whether a fabricated
value that is only reported is `F2` or `F3c`, by the grounding of the final answer rather
than by where the value sits, and `../llm_profile_panel` is the round that established it.

That choice has a cost, and it is stated here rather than discovered later. The LLM panel of
`../panel` read `../codebook_clarified.md`, so the human round and that panel no longer read
the same document: the comparison between them is no longer a comparison of who reads, and
it would take a re-run of the panel on the version 3 document to recover it. The human round
reads the document the paper will publish, which is the property worth having here.

The file carries seven em dashes inherited from `../annotator2_instructions.md`, which are
left alone deliberately.
