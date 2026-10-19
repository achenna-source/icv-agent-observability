# Codebook for the ToolBench sample

This is the procedure of `codebook.md`, applied to trajectories the authors did not
produce. The seven categories, the three disambiguation rules and the two open
conventions are unchanged, and are not restated here: read `codebook.md` first. What
follows is only what a different tool surface forces us to change, and why.

The sample is sixty trajectories drawn from the released ToolBench corpus, stratified
on evidence that needs no label. The first annotator labels all sixty. A second
annotator, blind, labels twenty-five of them.

## What changes, and what it costs

**There is no ground-truth block.** On the paper's own benchmark the annotator was told
which facts the store held and which were absent by design, so "the final answer is
correct" was checkable. ToolBench carries no such key: its own evaluation uses a model
judge, not a reference answer.

The consequence is confined to one category and must be stated wherever the resulting
numbers are reported. **S now means: no observable fault at the action interface, and a
final answer consistent with the observations the trajectory actually obtained.** It
does not mean the answer is correct. A trajectory that retrieves nothing useful, invents
nothing, contradicts nothing, and then answers plausibly from parametric memory will be
read as S here and might not have been on the original corpus.

Every other category is judged exactly as before, because each is defined by something
visible in the trace rather than by the truth of the answer: a call to a tool that does
not exist or does not fit, an invented argument, a repeated sub-goal, a stop with
sub-goals open, a contradiction with an earlier value, a fabricated pivot.

**"Registered tool" means the API list declared in the system turn.** Each task declares
its own tools with their required and optional parameters. `Finish` is declared among
them, with `return_type` required, taking `give_answer` or `give_up_and_restart`.

**An environment failure is not an agent failure.** This corpus runs against live
services, and roughly nine rejections in ten are infrastructure: dead endpoints, server
faults, timeouts, exhausted quotas. A step whose observation is a 5xx, a timeout or a
quota message is not a fault of the agent and must not be labelled as one. What *is*
judgeable is what the agent does next: repeating the same failing call without progress
is F4, answering as though the call had succeeded may be F7, giving up with sub-goals
open is F5.

**`give_up_and_restart` is not automatically a failure label.** It is an outcome, not a
category. Apply the first-observable-fault rule: if the agent gave up after an
unrecoverable environment failure and nothing in its own conduct was at fault, the
trajectory can still be S under the definition above.

## What the annotator is given

Given: the task as the agent received it, the names of the tools declared for that task,
and the full trajectory with each thought, action, action input and the observation
returned.

Not given: the stratum the trajectory was drawn from, any detector output, the other
annotator's labels, and, for the second annotator, the order in which the sample was
assembled.

## An eighth outcome, deliberately available

If a trajectory contains an observable fault that none of the seven categories
describes, label it **X** and say in the notes what the fault was. The paper claims the
taxonomy covers single-agent failures at the action-tool interface; a corpus the authors
did not design is the first real test of that claim, and an X is a result, not a
nuisance. Do not force such a case into F3, which is the residual for *reasoning and
retrieval* and not a bucket for anything unclassified.

## Reporting

The sample is stratified, so its label frequencies are not population estimates. The
unstratified base rates of the four stratification signals are recorded in
`sampling_key.json` and must be reported alongside any composition figure.

Agreement between the two annotators on the twenty-five shared items is a different
estimand from the kappa of 0.370 reported in Section VI.B: different corpus, different
category marginals, different tool surface. It should be reported as its own number and
not compared as though it were nested.
