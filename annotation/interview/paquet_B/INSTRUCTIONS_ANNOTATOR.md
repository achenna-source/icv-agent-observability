# Instructions for the annotator

You are labelling trajectories produced by an LLM agent, for a study on how such agents
fail. Your labels measure whether the study's labelling scheme is reproducible by people
other than its author. Work alone. Do not discuss individual items with anyone until your
file is returned, and do not try to guess what another annotator decided: a disagreement
is informative, a forced match is not.

Time needed: about an hour and a half to two hours for fifty trajectories. The first few
items take much longer than the rest, so do not judge the pace by them. Split the work
over two sittings if you prefer, because annotation quality drops sharply when tired. You
can stop at any point and resume where you left off.

## Getting started

You need Python 3.8 or later, and nothing else. Double-click `lancer_entretien_B.cmd`.
Your letter, B, is already set, so there is nothing to type. If the window says Python is not found,
install it from python.org with "Add python.exe to PATH" ticked, then run the file again.

To stop, type `save` at any prompt and close the window. Running the file again continues from the next unanswered trajectory.

## One section of the codebook does not apply to you

The codebook opens with a section headed "What you receive". It was written for an earlier
round in which two readers filled in a spreadsheet, and it does not describe your work.
Ignore it. It names three things you do not have.

- `sample_packet.md` and `annotations_annotator2.xlsx` are not in your packet. The
  trajectories reach you through the interview, and your answers are recorded by it.
- It promises each trajectory with "the ground-truth answer from the knowledge base".
  There is no such answer in this study, and the earlier round did not have one either.
  What settles whether a value was retrievable is `knowledge_base_observed.json`, which
  lists every query the store ever answered, and which you search with `kb` at any prompt.

Everything else in the codebook applies in full: the categories, the ordered checks, the
four conventions and the three judgment calls. Use this file for how to work and the
codebook for how to decide.

## How the interview works

For each trajectory you see the task, every step the agent took with what each step
returned, and the agent's final answer. Then the program asks a fixed series of questions
and the label follows from your answers by the published rule. You do not pick a code from
a list, with one exception: at the end of each trajectory you are asked which single code
you would assign on your own. Both are recorded, and a difference between them is a useful
finding rather than a mistake.

The sequence has three parts.

First, the program lists the steps whose action names no registered tool. That reading is
mechanical, not a judgment, and those steps are set aside: by the study's convention a
malformed step never gives a trajectory its label, whether or not the agent recovers from
it.

Second, you are asked whether the final answer is correct, and then which is the **earliest
step at which something went wrong**, leaving the malformed steps aside. This is where your
reading of the trajectory does its work. The first fault in time governs: where two faults
of different kinds occur, the label comes from the earlier one.

Third, the program applies the ordered checks to the step you named, and stops at the first
one you answer yes to. The checks are in a fixed order, but that order ranks the questions,
not the faults, which is why you locate the fault before the checks begin.

Answer each question on its own terms rather than steering towards a label you already have
in mind. `u` for unsure is a real answer and a useful one, so use it whenever you hesitate.
If an item cannot be settled by the questions, the program records that instead of inventing
a label.

## Commands available at any prompt

| | |
|---|---|
| `y` `n` `u` | yes, no, unsure |
| `?` | what this question means, in the codebook's own words |
| `rules` | the four conventions, in full |
| `kb <text>` | search the knowledge base: what could the agent actually have retrieved? |
| `tools` | the registered tool set |
| `steps` | show the trajectory again |
| `back` | re-answer the previous check of this trajectory |
| `save` | save and stop, resume later |

Use `kb` freely. Deciding whether a value the agent asserted was invented or retrieved is
the commonest hard call, and the knowledge base settles it.

## The four conventions

`rules` shows these in full at any prompt, and `?` shows the one that bears on the question
you are answering.

**A malformed step never determines the label.** A step whose action names no registered
tool is a defect in the form of the call, not a diagnosis of what the agent was trying to
do. Recovered or not, it is set aside.

**The first fault in time governs, not the first rule in the table.** The table orders the
checks; it does not rank the faults.

**The pivot test requires a computation.** `F7` applies when a fabricated value is used as
an input to a computation whose result is the final answer. A fabricated value that is
merely reported, and not computed with, is `F2` when nothing else in the final answer is
grounded in a value the store returned, and `F3`, sub-code `F3c`, when the answer also
reports a value the store did return. An answer built on nothing the store returned is a
fabricated answer; an answer that reports a retrieved fact and pads it with an invented
one is a partial answer.

**A truthful report of absence is a success.** Where the knowledge base genuinely lacks
what the task asks for and the agent's answer says so without asserting any invented value,
the trajectory is `S`.

## The three questions that need judgment

Most checks are mechanical. Three need your judgment, and these are exactly the ones the
study wants measured.

**Tool fitness.** "Unfit" means a competent solver would not have chosen that tool for that
sub-goal, not merely that a different tool would also have worked.

**Semantic repetition.** Two steps are equivalent if they pursue the same sub-goal by the
same means, even when the wording differs. A genuine follow-up query on the same entity is
not a repetition.

**The pivot test.** Would removing the invented value change the final answer, and did a
computation carry it there?

## What not to do

Do not skip an item you find hard, since an unsure answer on a hard item is far more useful
than a gap. Do not search the web for the study, the paper, or the detection results. Do
not revise trajectories you have already finished if your understanding shifts later: note
it in the note line and it will be handled at adjudication.

## When you finish

Return the single file `responses_B.jsonl` that the program wrote next to the
launcher. Nothing else is needed. The file holds your answers, your own codes, your notes,
and how long each item took. It holds no judgment of your answers.
