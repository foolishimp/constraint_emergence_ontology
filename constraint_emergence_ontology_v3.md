---
kind: working_paper
version: 3.0
status: draft
author: Dimitar Popov
revised: 2026-09-22
revision_basis: 2da7871bf48d3144e4e83d5e8a336671251a6c76
---

# Constraint and Emergence

*A functional model of persistence, construction and evaluation*

## Abstract

Constraints limit what a system can do. Dynamics determine which possibilities
it reaches. Some resulting patterns persist, maintain the conditions of their
persistence, and become components of further construction. Encodings then
allow constructive processes to be retained, copied and directed. Evaluation
relates outcomes to a model or target and supplies feedback. This paper
proposes that these relationships provide a useful common description of
physical, biological and computational systems. Cross-domain transfer requires
an explicit account of what is preserved, what is lost and where predictions
fail. The engineering application separates proposal, evaluation, verification
and acceptance. The empirical programme tests both learned boundaries in
language models and the usefulness of the framework as reasoning context.
Existing experiments support some structured representations and interventions;
the tested screening claims remain unestablished.

## Constraints and the formation of structure

A constraint specifies an admissibility condition: which states or
transformations are allowed. Dynamics determine what happens among the allowed
possibilities. An evaluation criterion ranks outcomes for a purpose. Keeping
these roles distinct is necessary to explain how structure forms.

A physical constraint is realised through physical interactions. A requirement
constrains an engineered system only through the people and mechanisms that
interpret or enforce it. A test observes selected properties. A prompt
conditions a model's behaviour. These can participate in comparable functional
relationships while having different mechanisms and strengths of enforcement.

The starting question is what a system's organisation allows to persist. A
bound-state model, for example, describes stable solutions under particular
interactions and conditions. Those solutions depend on the governing dynamics.
A diagram of permitted states alone does not establish that any particular
state will be reached or maintained.

This gives a bounded form of the original generative principle. Where a stable
configuration is reachable, the system has opportunities to form it, and its
conditions persist, repeated construction can make that configuration common.
Possibility, reachability and persistence are separate requirements. Energy
barriers, initial conditions, resources and finite time can prevent a possible
configuration from appearing.

The proposed explanatory move is to follow that causal chain. Constraints shape
the available transformations; dynamics produce a history; some structures
survive or reproduce; those structures change the conditions for subsequent
transformations. The resulting organisation can enable processes that were
unavailable before it formed.

The word “traversal” describes an actual sequence of transitions. It carries no
general promise of descent toward an optimum. Cycles, oscillations and driven
processes are possible. A function cannot decrease strictly around a closed
cycle and return to its original value. Gradient descent, stationary action and
feedback control therefore need their own dynamics; calling each a traversal
does not make them the same algorithm.

## Persistence, boundaries and emergence

Persistence means retaining specified properties across a declared interval
and class of disturbances. The relevant identity may survive changes in
material composition or internal state. Explaining persistence requires
identifying what changes, what remains, and which interactions maintain it.

A boundary selects how a system interacts with its surroundings. It may be a
physical interface, a set of measured variables or an enforced software
interface. Conditional screening is a stronger property. Given interior $I$,
boundary $B$ and exterior $E$, a statistical Markov boundary requires:

$$
P(I\mid B,E)=P(I\mid B).
$$

Once the boundary is known, the exterior adds no information about the
interior under the specified distribution. Approximate screening requires a
declared tolerance. A dynamical claim must also specify a time horizon and
test whether relevant external changes affect future internal behaviour.

This paper reserves “Markov object” for a persistent system whose proposed
boundary satisfies the declared screening claim. A candidate remains a
candidate until that claim is tested. A potential well, membrane, semantic
cluster or software interface does not establish conditional independence by
its name or by the fact that something persists.

Emergence concerns the availability of a useful description at another scale.
A molecule can be treated as a component without tracking every constituent
degree of freedom. A software interface can support composition while hiding
implementation details. The abstraction succeeds when the omitted differences
do not change the behaviour being predicted within its stated limits.

The persistent structure also has a physical or operational effect: it changes
what can happen next. A membrane alters transport; an enzyme changes reaction
rates; an implemented interface changes which operations a component exposes.
Coarse-graining describes the resulting organisation. The causal interactions
produce it. Keeping those two claims separate avoids treating an observer's
choice of description as the cause of the observed structure.

Timescale matters. Fast variation may average out in a slower description;
slow variables may be approximately fixed during a short observation. Neither
approximation is universal. A boundary or abstraction that works for one
horizon can fail at another.

## Construction before effective specification

An encoding acquires a constructive role through a mechanism capable of using
it. DNA has consequences within cellular machinery. A program has consequences
within an execution system. A specification guides construction through
builders, tools and evaluation. The interpretation mechanism is part of what
makes the encoding effective.

Mature systems can obscure that dependency. The visible sequence begins with
a specification and ends with a product. The capacity to interpret, build and
evaluate already exists. The specification directs that capacity.

The developmental hypothesis is that repeatable activity can precede a
separately retained description of how to reproduce it. Practice becomes a
procedure; a procedure becomes a specification; a specification then governs
later practice. Retaining the encoding allows successful construction to be
copied, varied and tested with less dependence on the circumstances of its
first occurrence.

This is a claim about the origin of an effective relationship between encoding
and construction. It is not a universal chronology for every artifact. An
existing general constructor can build a new mechanism from a prior design.
In early life, catalytic and informational functions may overlap and
co-evolve. The proposal does not establish that a complete cell preceded every
genetic precursor.

Protocell experiments provide a concrete example of mutual support: internal
catalytic activity can improve membrane stability under conditions relevant to
RNA chemistry. That result supports a particular coupling between construction
and its sustaining conditions; it does not settle the historical order of
life's origins. [Adamala, Engelhart and Szostak (2016)](https://www.nature.com/articles/ncomms11041)

A useful progression is therefore from organised activity, to persistent
structure, to maintenance of that structure, and then to retained encodings
that help reproduce or modify it. Each transition requires a mechanism.
Montévil and Mossio's account of *closure of constraints* addresses the
interdependence of biological processes that maintain their own enabling
conditions. It supplies a developed treatment of part of this progression.
[Montévil and Mossio (2015)](https://montevil.org/publications/articles/2015-mm-organisation-closure-constraints/)

Construction history also matters when comparing what is possible with what
a system can repeatedly produce. Assembly theory offers one proposed way to
study formation histories and selection. Its measures require their own
validation; citing them supplies no proof of a universal constructor-first
law. [Sharma et al. (2023)](https://www.nature.com/articles/s41586-023-06600-9)

## Meaning, evaluation and self-maintenance

Meaning is used here in a relational sense: the organisation of associations
among distinguishable patterns. Their relevance and strength depend on a
reference frame. Nearness expresses association within that frame. A concrete
model must specify its measure and how that measure predicts behaviour.

Evaluation uses some of those relationships to compare a state or candidate
with a criterion. A target can be encoded explicitly, learned from experience,
or represented by conditions the system regulates. The result directs what
happens next. Evaluation gives relationships a role in selection and control;
it need not be the point at which all relational meaning first appears.

The feedback sequence is concrete. A system acquires information about its
current state, evaluates it against a model or target, selects an intervention,
and observes the consequences. Those observations can revise the next action,
the model or the target. An account that omits the return from consequence to
model cannot explain correction.

A thermostat, a planning system and a human deliberating over alternatives can
all be described through comparisons and feedback. Their models, timescales,
learning capacities and available actions differ. The shared description earns
its value by predicting relevant behaviour while preserving those differences.

The comparison between affect and a prompt belongs at this functional level:
a signal may redirect attention or action without specifying every subsequent
operation. A detailed neurological claim requires evidence for the particular
circuits and effects. A shared feedback diagram cannot establish anatomical or
phenomenological identity.

Self-maintenance adds a further condition. Some systems regulate processes
that preserve their own capacity to continue. A model can evaluate an outcome
without maintaining its own existence. An organism's regulation can contribute
to its continued viability. This functional distinction supplies no account of
subjective experience.

An observer is also part of the process it observes. It acquires records
through interactions and interprets them using a limited model. Separating
physical interaction from the observer's inference clarifies what an
explanation owes. It does not, by itself, solve the quantum measurement
problem.

## Proposal, verification and acceptance

A constructive system needs a way to distinguish a candidate from an outcome
on which it can rely. Generation supplies possibilities. Evaluation supplies
preferences. Evidence supports particular claims. A decision makes a result
operative.

These functions produce four useful roles. A **proposer** supplies candidates.
An **evaluator** ranks or assesses them against a criterion. A **verifier**
checks a declared property and returns evidence. An **admitter** authorises a
candidate's use, publication or execution. The last role belongs to the
decision rules of the surrounding engineered or organisational system.

One component can perform several roles. Its outputs still need distinct
interpretations. A type checker can establish a type property under its
assumptions. A reward score can rank candidates. Neither alone establishes
that an application achieved its purpose or that someone authorised its
deployment.

Probabilistic computation, $F_P$, and deterministic computation, $F_D$,
describe how calculations are performed. The assurance process, $F_C$,
describes how evidence and decisions support use. It can contain deterministic
checks, statistical tests and human judgments. These labels describe different
dimensions of a system.

Determinism concerns repeatability for fully specified inputs and state.
Correctness concerns whether a particular claim holds. Grounding concerns how
the evidence connects to the subject. Authority concerns who or what can make
a decision effective. None implies all the others.

The engineering argument is consequently narrower than “probabilistic output
without deterministic checking is hallucination.” Unchecked output can be
correct; deterministic checks can be wrong or incomplete. The problem is the
unsupported promotion of a candidate into an accepted fact or action. Where a
reliable consequence matters, the system needs evidence and an acceptance
rule adequate to that consequence.

Selection can reduce a candidate set without establishing truth. A false
belief can be stable, and a wrong implementation can pass inadequate tests.
Truth concerns the claim's relation to its subject. Verification and
acceptance provide bounded reasons for relying on it; persistence and
procedural approval do not redefine it.

## Failure, correction and cost

A language model can produce a fluent answer that its evidence does not
support. Several conditions can contribute: missing information, misleading
associations, a mistaken inference, poor calibration or a task that demands an
answer despite unresolved uncertainty. High probability and stability are
compatible with factual error.

Under-specification is one particular failure mechanism. Several candidates
may satisfy the available description while differing on a consequence the
user cares about. A useful added constraint distinguishes those candidates.
An irrelevant restriction adds work without resolving the uncertainty.
Conflicting restrictions can prevent a satisfactory result altogether.

This account produces a testable engineering prediction: constraints that
capture relevant distinctions should reduce the corresponding failure classes,
subject to the builder's ability to use them. Raw document length, test count
and “constraint density” are inadequate substitutes for that distinction.
Correctness can improve, remain unchanged or decline as more material is added.

The comparison to quantum degeneracy carries no demonstrated mechanism.
Equal energy values, similar token probabilities and ambiguous requirements
are different mathematical situations. Each can motivate a question about
underdetermination. The answer must come from the dynamics and evidence of the
particular system.

Cost requires the same discipline. Compute time, memory, physical energy and
human effort are different quantities. Combining them requires declared
conversion factors or a multi-objective comparison. A penalty for unmet
requirements is an engineering objective, not a physical Hamiltonian.
Associative nearness also supplies no intrinsic energy or execution cost.

Useful contraction preserves adequate outcomes while reducing unnecessary
work. It can come from a better frame, a more informative measurement, a
simpler representation or reuse of evidence whose basis remains valid. Adding
checks is beneficial only where their expected contribution justifies their
cost under the task's requirements.

A construction history makes that judgment inspectable. Retain the target,
inputs, material decisions, intermediate results and evidence needed to explain
why an output follows. When a dependency changes, reassess the claims that
depend on it. A new function call or handoff alone does not invalidate an
unchanged fact.

## What transfers across domains

A cross-domain comparison must name the source and target, the relationship
claimed to survive, the acceptable error, the information discarded, and a
condition under which the mapping fails. Shared terminology cannot perform
that work.

For example, a membrane and an API both mediate interactions. The comparison
can preserve a claim about controlled access across a boundary. It discards
material transport, metabolism and the different mechanisms of enforcement.
It fails if the software permits relevant effects outside the interface, or if
the biological claim requires a form of isolation the membrane does not
provide.

A functional mapping can be stated without assuming a common material
substrate. Let $s$ be a concrete state, $u$ a relevant input, $T$ the concrete
transition, and $\alpha$ an abstraction into a chosen frame. Let
$\widehat{T}$ predict change in that frame. The required correspondence is:

$$
\alpha(T(s,u))\approx\widehat{T}(\alpha(s),u).
$$

The domain, prediction horizon and tolerated discrepancy must be fixed. The
selected observable outputs must also survive the abstraction through a
declared readout. For stochastic transitions, compare outcome distributions.

This criterion identifies a failure directly. If the abstraction merges two
states that have materially different retained futures under the same input,
it has discarded a necessary distinction. The repair is to retain more state,
change the model or narrow its scope.

Two implementations can be functionally equivalent within that frame while
differing in energy, latency, learning or memory. Bringing one of those
properties into the frame can expose a difference. The value of the shared
model is that it identifies which mechanisms may change while the required
function survives.

A formal theory of composition would additionally have to show that its
mappings preserve the relevant behaviour when systems are combined.
Conditional independence is not preserved by arbitrary composition. Naming
objects and maps supplies no such proof.

## The stronger physical conjecture

The broader conjecture is that familiar physical objects and spacetime could
be emergent descriptions of more basic relational dynamics. This is a claim
about what exists. The functional comparisons above do not establish it.

The motivating distinction is between a description of possibilities and the
process realised in a particular system. A mathematical state space contains
possible descriptions. Its existence as mathematics does not decide which
physical interpretation is correct. Conversely, describing a process as
successive updates does not prove that only the present exists.

“Computational presentism”—the claim that only the current state exists—remains
an optional interpretation. A discrete transition rule does not show that the past was
destroyed, that the future is undetermined, or that nature has a global
computational clock. A deterministic rule can fix future states without
enumerating them. A physical account must also explain how its proposed
description relates to relativistic observations.

The same limit applies to quantum measurement. Decoherence concerns the
suppression of observable interference through interaction with an
environment. Updating an observer's information and proposing a physical
collapse mechanism are additional claims. Separating these processes is
necessary; it does not derive a unique outcome or settle the choice among
interpretations. [Schlosshauer (2019)](https://arxiv.org/abs/1911.06282)

Many-worlds follows from a particular interpretation of universal quantum
dynamics. It cannot be dismissed merely by calling it a catalogue of
uncomputed possibilities. A competing single-outcome account needs its own
dynamics and empirical adequacy. Likewise, a metaphor of constraint density
does not derive gravity, the Higgs mechanism or a propagation speed.

The proton-to-electron mass ratio remains a useful example of an unmet
ambition. A proposed deeper theory must calculate an independently testable
quantity without fitting the answer. This framework supplies no such
derivation. Renaming existing quantities as properties of a constraint
network creates no additional physical result.

The intellectual motivation draws from Bohm's emphasis on underlying process
and Deacon's treatment of constraints and emergence. Constructor theory offers
a more explicit related programme organised around possible and impossible
physical transformations. Its formal development does not automatically
transfer to this proposal. [Deutsch (2012)](https://arxiv.org/abs/1210.7439)

Computational limits also require precise scope. Gödel's incompleteness
results, Turing's undecidability results and Cantor's diagonal argument concern
different objects and assumptions. Their related techniques do not make them
one universal theorem of emergence. An observer can bring information absent
from a particular formal system; another algorithm still cannot decide every
instance of an undecidable problem. Executing a process does not generally
tell us that a non-terminating process will never terminate.
[Turing (1936)](https://turingarchive.kings.cam.ac.uk/computable-numbers)

## What the experiments establish

The retained experiments investigate whether learned representations possess
identifiable structure and whether particular proposed boundaries screen that
structure from the rest of a model. These are separate questions.

There are bounded positive results. The recorded composition assay passed its
criterion for relationships among identity directions. A Pythia-160M
replication passed its stated qualitative transfer criterion. These support
the particular representational and intervention effects measured.
[Composition result](markov_object_research/results/23_compositional_algebra/compositional_summary.json);
[replication result](markov_object_research/results/24_cross_model_pythia/cross_model_summary.json).

The screening record is negative for the tested constructions. Overwriting
sparse-autoencoder features outside a target's active set still transferred
identity information. The direction-native test left identity fully readable
by its probe after the proposed subspace was removed. A multilayer successor
also failed its acceptance criterion.
[Boundary assay](markov_object_research/results/17_boundary_tightness/boundary_report.txt);
[direction-native test](markov_object_research/results/20_direction_native_ci/ci_report.txt);
[multilayer test](markov_object_research/results/25_multilayer_gate/gate_summary.json).

The Llama-3 8B dynamical test also recorded a failure under its declared rule.
An explicit-object toy model passed its training, directional-alignment and
transfer thresholds. That control demonstrates those measured properties in
the constructed architecture. It does not establish that every screening
assay can detect a Markov boundary.
[Dynamical test](markov_object_research/results/41_dynamical_blanket_identity/report.txt);
[toy control](markov_object_research/results/40_explicit_object_control/report.txt).

A recorded failure needs an interpretable measurement. Some retained Llama-3
intervention results contain zero baseline and perturbed scores throughout.
Those observations limit what that assay can discriminate and warrant checking
its readout before drawing a conclusion about the representation.
[Intervention record](markov_object_research/results/37_causal_faithfulness_llama3/summary.json).

The warranted conclusion is that the selected tests found some usable
structure without establishing the proposed screening boundaries. Failure
does not prove that no other boundary exists. It does count against the
tested boundary claim. A successor hypothesis needs a stated reason and a new
test; repeated failures cannot be removed from the evidence by renaming the
instrument.

A workspace that makes information available for report or flexible reuse is
also different from a screening boundary. Workspace analysis can suggest
locations to investigate. Its results alone cannot satisfy the
conditional-independence test.

## Two uses, two tests

The framework has two proposed uses. As a functional model, it must predict
the behaviour it claims to explain. As context for a language model, it must
improve the work produced. Success in one use does not establish success in
the other.

The first research claim concerns learned screening. Define the proposed
interior, boundary and exterior independently of the evaluation outcomes.
Test conditional dependence and relevant interventions on held-out contexts.
A claim that screening improves with scale requires comparable measurements
across models and control of relevant training and architectural differences.
The existing failures leave that claim unestablished.

The second claim concerns engineered systems. Explicit representations,
interfaces, evidence provenance and acceptance rules may reduce unsupported
outputs and improve performance under changed conditions. Compare them with
matched systems lacking the selected mechanisms. Measure task success,
incorrect acceptance, unnecessary refusal and resource use. Enforced access
boundaries and statistical Markov boundaries require separate tests.

The context-use experiment compares the same model and tasks with the paper,
without it, and with a concise task-specific specification. A length-matched
control helps distinguish the proposed relationships from additional context
or instruction volume. Freeze the prompts, model configuration, available
tools and evaluation criteria before comparing results.

The outcome measures are consistency, transfer and useful discovery.
Consistency asks whether the reasoning respects its stated definitions and
assumptions. Transfer asks whether a cross-domain mapping preserves the
relationship it claims. Useful discovery asks whether a new proposal survives
an appropriate proof, observation or practical test. A separate model can help
identify candidate defects or ideas; its opinion cannot establish a mechanical
property or a physical claim.

Retain the source version, material reasoning steps, outputs and evaluation
evidence so that a later revision can be compared with the same task
population. A vocabulary that increases internal agreement while reducing
external accuracy has failed the relevant use. A shorter paper that preserves
the results has reduced the cost of the frame.

This editorial revision reports existing evidence and proposes comparisons.
It adds no experimental result. Its next empirical task is a bounded
comparison in which the retained relationships predict an outcome or
intervention effect that a matched baseline misses.
