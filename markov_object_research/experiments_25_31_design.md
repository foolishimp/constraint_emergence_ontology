# Experiments 25-31: Design

**Status:** pre-registered design. No results yet.  
**Scope:** seven experiments that test the stronger emergence conjecture:
candidate Markov-object identity is realized across the constrained
technical stack and only projected through local charts.  
**Companion:** `emergence_conjecture_program.md`,
`emergent_markov_object_evidence.md`, `empirical_results.md` section 13.4.  
**Draft date:** 2026-04-24.

---

## Preface

Experiments 19-24 changed the research question.

The old question was whether the layer-8 direction was merely
under-ranked. The answer is no. Rank-k saturation fails at layer 8.
The same mean-diff protocol passes strongly at layer 2. The direction
family is coherent across layers, compositional algebra passes, and the
first Pythia-160M replication is positive. But the single-chart
conditional-independence gate fails at both layer 8 and layer 2.

The current question is therefore sharper:

> Did the promotion gate fail because there is no Markov object, or
> because the tested gate conditioned on one local chart rather than the
> realized topology distributed across the stack?

This document commits to the next evidence wave. The experiments do not
lower the promotion burden. They test whether the correct conditioning
surface is multi-chart, distributed, and implementation-invariant.

All experiments use the same baseline rig as experiments 18-24 unless
otherwise noted:

- GPT-2 small via `transformer_lens`
- residual stream at `blocks.{layer}.hook_resid_pre`
- primary layers `2/4/6/8`, with `10/11` as optional late-depth checks
- primary targets `{999, 666, 137}`
- reference null peer `5`
- matched train, calibration, and held-out template pools
- target/reference paired prompts where possible

Order of priority:

| # | name | closes | gate-level |
|---|---|---|---|
| 25 | multi-layer realized-topology gate | failed single-chart CI | **GATE VARIANT** |
| 26 | distributed ownership audit | local owner vs stack realization | emergence discriminator |
| 27 | partial-chart reconstitution | weak charts jointly reconstruct | emergence discriminator |
| 28 | explicit-object control arm | emergent vs explicit-technology signature | contrast control |
| 29 | training-emergence trajectory | learned emergence vs fixed artifact | developmental |
| 30 | cross-model invariance | implementation variation | robustness |
| 31 | behavioral preservation | object-level behavior | behavioral |

Exp 25 is the direct successor to the failed promotion gate. It does not
promote the construct by itself unless the residual dependence collapses
under pre-registered multi-layer conditioning. Exps 26-31 test whether
the result is truly emergence-shaped rather than an artifact of probe
choice, prompt family, tokenizer, or architecture.

---

## Experiment 25 - Multi-layer Realized-topology Gate

### 25.1 Motivation

Exp 20 subtracts one layer-local identity projection and then tests
whether the orthogonal residual remains predictive of target identity.
It fails at layer 8 and layer 2: `AUC(r_perp)=1.0`, HSIC significant.

The emergence conjecture predicts that one chart is insufficient. If a
candidate object is realized across a constrained technical stack, the
conditioning surface should be a joint chart over several local
projections, not a single layer-local direction.

### 25.2 Hypothesis

Conditioning on a joint chart over layers `2/4/6/8` reduces residual
identity signal materially more than conditioning on the best single
layer chart.

Operational form:

- `AUC(residual | joint_chart)` drops below `0.70` for at least two of
  three targets;
- the mean AUC drop from full residual is at least `0.25`;
- the joint-chart residual AUC is at least `0.15` lower than the best
  single-chart residual AUC;
- HSIC weakens materially relative to exp 20 and is non-significant
  (`p > 0.05`) for at least two of three targets.

### 25.3 Protocol

1. Collect paired target/reference residuals for layers `2/4/6/8` using
   train, calibration, and held-out template pools.
2. For each target and layer, extract a mean-diff direction:
   `d_L = mean(R_target_L) - mean(R_ref_L)`.
3. For each sample, compute joint chart coordinates:
   `z = [dot(r_2, d_2), dot(r_4, d_4), dot(r_6, d_6), dot(r_8, d_8)]`.
4. Construct three residual surfaces:
   - full concatenated residual: `R_all = concat(r_2, r_4, r_6, r_8)`
   - best single-chart residual: remove the strongest single-layer
     coordinate from `R_all`
   - joint-chart residual: regress `R_all` on `z` using train data,
     subtract predicted component on held-out data
5. Train one-vs-reference logistic probes with GroupKFold by template:
   - full residual probe
   - best single-chart residual probe
   - joint-chart residual probe
6. Run HSIC between joint-chart residual and target label on held-out
   data, with permutation null.
7. Secondary check: repeat using rank-k per-layer charts where `k` is
   selected from exp 19 (`k=1` for layer 2; `k=10` upper-bound for layer
   8) and compare against rank-1 joint chart.

### 25.4 Pre-registered expectation

Joint conditioning beats best single conditioning.

Minimum support:

- at least two targets have `AUC_joint <= 0.70`;
- at least two targets have `AUC_joint <= AUC_best_single - 0.15`;
- at least two targets have HSIC `p > 0.05`.

### 25.5 Outcome interpretation

- **Pass**: joint residual AUC and HSIC meet the thresholds above. The
  failed exp 20 gate was chart-insufficient. The emergence conjecture
  gains its first direct gate-level support.
- **Partial**: joint conditioning improves over best single chart, but
  AUC remains in `[0.70, 0.85]` or HSIC remains significant. The object
  is not closed by the tested chart, but the realized-topology reading
  gains partial support.
- **Fail**: joint conditioning adds little over best single chart
  (`AUC` drop < `0.05`) or residual AUC remains `>= 0.90` for all
  targets. The emergence conjecture weakens; either the relevant chart
  is not residual-layer geometry, or the residual identity signal is not
  object-level in the intended sense.

### 25.6 Script shape

`experiments/25_multilayer_realized_topology_gate.py`

Outputs:

- `results/25_multilayer_gate/gate_report.txt`
- `results/25_multilayer_gate/gate_summary.json`
- `results/25_multilayer_gate/auc_comparison.png`
- `results/25_multilayer_gate/hsic_perm_{target}.png`
- `results/25_multilayer_gate/chart_coefficients.png`

---

## Experiment 26 - Distributed Ownership Audit

### 26.1 Motivation

An emergent object should not be cleanly owned by one local module. A
local-owner story predicts a best layer, head, MLP block, or residual
site that accounts for most identity transfer. An emergence story
predicts that matched distributed intervention across the stack
dominates any single local locus.

### 26.2 Hypothesis

Distributed interventions across layers `2/4/6/8` produce stronger and
more stable identity transfer than any single local locus matched for
intervention norm.

### 26.3 Protocol

1. Extract per-layer identity directions for each target.
2. Identify candidate local loci:
   - residual stream layer directions
   - attention output directions per layer
   - MLP output directions per layer
3. For each locus, run an alpha sweep on held-out prompts with
   norm-matched interventions.
4. Construct distributed interventions:
   - equal split across layers `2/4/6/8`
   - transfer-weighted split from exp 21
   - learned split from calibration data, evaluated on held-out data
5. Compare identity transfer, KL stability, and off-target damage.

### 26.4 Pre-registered expectation

Distributed intervention should exceed the best single-locus transfer
by at least `0.15` mean transfer for at least two of three targets, at
matched total norm.

### 26.5 Outcome interpretation

- **Pass**: distributed intervention dominates all single loci. This is
  direct evidence against local ownership.
- **Partial**: distributed intervention matches but does not exceed best
  single locus, while no single head/MLP dominates. Distributed
  realization remains plausible but not proven.
- **Fail**: one locus cleanly dominates and distributed intervention
  adds little. The local-owner alternative becomes the best explanation.

### 26.6 Script shape

`experiments/26_distributed_ownership_audit.py`

Outputs:

- `results/26_distributed_ownership/ownership_report.txt`
- `results/26_distributed_ownership/ownership_summary.json`
- `results/26_distributed_ownership/locus_transfer_bars.png`
- `results/26_distributed_ownership/distributed_vs_single.png`

---

## Experiment 27 - Partial-chart Reconstitution

### 27.1 Motivation

If local charts are partial views of one realized topology, weak charts
should reconstitute the object jointly. If the construct is only a
collection of unrelated local effects, combinations should not improve
lawfully.

### 27.2 Hypothesis

Combining individually subcritical charts from several layers or bases
reconstructs target identity more strongly than any component chart
alone.

### 27.3 Protocol

1. Select weak or partial charts:
   - layer-8 residual direction
   - layer-10 residual direction
   - SAE-core decoder-sum direction at layer 8
   - context-coat direction from symbolic or emergency contexts
2. Measure each chart independently using held-out transfer and probe
   AUC after subtraction.
3. Build combinations:
   - pairwise sums
   - orthogonalized multi-chart bases
   - learned low-rank combination from calibration data
4. Evaluate held-out transfer and residual predictability after
   conditioning on the combined chart.

### 27.4 Pre-registered expectation

The best combined chart improves over the best component chart by at
least `0.20` transfer or reduces residual AUC by at least `0.15` for at
least two targets.

### 27.5 Outcome interpretation

- **Pass**: partial charts jointly reconstruct. This supports the
  chart-family reading.
- **Partial**: some pairwise improvement appears, but only for one
  target or only on transfer, not residual dependence.
- **Fail**: combinations behave like the best single component or worse.
  The partial-chart reconstruction claim weakens.

### 27.6 Script shape

`experiments/27_partial_chart_reconstitution.py`

Outputs:

- `results/27_partial_reconstitution/reconstitution_report.txt`
- `results/27_partial_reconstitution/reconstitution_summary.json`
- `results/27_partial_reconstitution/component_vs_combined.png`
- `results/27_partial_reconstitution/residual_auc.png`

---

## Experiment 28 - Explicit-object Control Arm

### 28.1 Motivation

The emergence conjecture needs a contrast case. If objecthood is made
explicit in the technology layer, it should have a different signature:
localization, clean module ownership, and easier conditional closure.
That contrast helps distinguish emergent realization from simply failing
to find the right local implementation.

### 28.2 Hypothesis

An explicit-object system shows stronger localization and cleaner
conditional closure than GPT-2's learned residual representation.

### 28.3 Protocol

1. Build or use a small explicit-object control:
   - a toy transformer with a learned object-slot bottleneck, or
   - a small classifier/generator with explicit object ID embeddings, or
   - a synthetic residual pipeline where object identity is stored in a
     declared coordinate.
2. Run analogues of exps 20, 25, and 26:
   - single-chart CI
   - joint-chart CI
   - ownership audit
3. Compare signatures:
   - best single locus vs distributed intervention
   - residual AUC after subtracting declared object coordinate
   - HSIC after conditioning
   - transfer under object-coordinate intervention

### 28.4 Pre-registered expectation

The explicit-object control should pass single-chart closure:

- residual AUC after subtracting declared object coordinate in
  `[0.47, 0.53]`;
- HSIC non-significant (`p > 0.05`);
- best local locus explains at least `80%` of distributed intervention
  effect.

### 28.5 Outcome interpretation

- **Pass**: explicit-object systems localize cleanly while GPT-2 does
  not. This strengthens the claim that the GPT-2 pattern is emergent,
  not merely explicit but undiscovered.
- **Partial**: explicit control localizes better than GPT-2 but does not
  fully pass closure. The contrast remains useful but weaker.
- **Fail**: explicit control has the same distributed, non-closing
  signature. The proposed contrast is invalid, or the metrics are not
  discriminating objecthood.

### 28.6 Script shape

`experiments/28_explicit_object_control.py`

Outputs:

- `results/28_explicit_object_control/control_report.txt`
- `results/28_explicit_object_control/control_summary.json`
- `results/28_explicit_object_control/localization_comparison.png`
- `results/28_explicit_object_control/ci_comparison.png`

---

## Experiment 29 - Training-emergence Trajectory

### 29.1 Motivation

Emergence should appear over training. A fixed architecture artifact
should be present before learning or should not show a staged trajectory
from weak chart, to cross-layer coherence, to composition, to resistance
against single-chart closure.

### 29.2 Hypothesis

Across checkpoints, chart strength, cross-layer coherence, and
composition appear gradually, while single-chart closure remains
insufficient after the object becomes distributed.

### 29.3 Protocol

1. Use Pythia checkpoints or another checkpointed transformer family.
2. At each checkpoint, run abbreviated versions of:
   - exp 18 direction transfer
   - exp 21 cross-layer coherence
   - exp 23 composition
   - exp 25 joint conditioning
3. Track emergence metrics over training steps:
   - alpha=1 transfer by layer
   - adjacent-layer cosine
   - composition cosine over compound concepts
   - residual AUC after single and joint conditioning

### 29.4 Pre-registered expectation

The expected order is:

1. weak direction transfer appears;
2. cross-layer coherence rises;
3. composition improves;
4. single-chart closure remains insufficient while joint conditioning
   improves.

At least three of four metrics should move monotonically in the expected
direction across coarse checkpoint bands.

### 29.5 Outcome interpretation

- **Pass**: staged emergence appears. This supports learned emergent
  realization.
- **Partial**: some metrics emerge, but order is noisy or composition
  lags.
- **Fail**: no coherent trajectory appears. The construct may be a
  static representational artifact or a prompt/template effect.

### 29.6 Script shape

`experiments/29_training_emergence_trajectory.py`

Outputs:

- `results/29_training_trajectory/trajectory_report.txt`
- `results/29_training_trajectory/trajectory_summary.json`
- `results/29_training_trajectory/metric_trajectories.png`
- `results/29_training_trajectory/checkpoint_heatmap.png`

---

## Experiment 30 - Cross-model Invariance

### 30.1 Motivation

Exp 24 shows first positive replication in Pythia-160M. The emergence
conjecture needs broader implementation variation. The invariant should
not be the same vector. It should be the same higher-order pattern:
coherent charts, distributed realization, composition, and failure of
naive single-chart ownership.

### 30.2 Hypothesis

Across at least three model families or scales, local realization moves
but the higher-order signature persists.

### 30.3 Protocol

1. Select model set:
   - GPT-2 small
   - Pythia-160M
   - one additional small open transformer with accessible residual
     hooks
   - optional larger Pythia or GPT-2 medium if local compute allows
2. For each model, run abbreviated:
   - exp 18 direction transfer
   - exp 21 cross-layer coherence
   - exp 23 composition
   - exp 25 joint conditioning
3. Normalize layers by proportional depth.
4. Compare model-level signatures rather than raw vector identity.

### 30.4 Pre-registered expectation

At least two of three models should show:

- positive alpha=1 transfer above model-calibrated null;
- adjacent-layer direction cosine above `0.60`;
- composition cosine exceeding random-pair null by at least `0.15`;
- joint conditioning improves over best single conditioning.

### 30.5 Outcome interpretation

- **Pass**: higher-order pattern survives implementation variation. The
  conjecture gains robustness.
- **Partial**: direction transfer and coherence replicate, but
  composition or joint conditioning does not.
- **Fail**: pattern is GPT-2/Pythia-specific. Narrow all claims to the
  model families that pass.

### 30.6 Script shape

`experiments/30_cross_model_invariance.py`

Outputs:

- `results/30_cross_model_invariance/invariance_report.txt`
- `results/30_cross_model_invariance/invariance_summary.json`
- `results/30_cross_model_invariance/model_signature_bars.png`
- `results/30_cross_model_invariance/layer_normalized_heatmap.png`

---

## Experiment 31 - Behavioral Preservation Under Realized-chart Intervention

### 31.1 Motivation

Exp 22 is inconclusive because the lexical classifier over-calls the
reference class at baseline. The stronger test is not free-form lexical
drift. It is whether realized-chart intervention changes object-level
behavior more lawfully than single-layer intervention under controlled
tasks.

### 31.2 Hypothesis

Multi-layer realized-chart interventions preserve or perturb
object-level behavior more cleanly than single-layer interventions.

### 31.3 Protocol

1. Build controlled behavior tasks:
   - null-peer discrimination: choose target vs reference in matched
     contexts
   - paraphrase preservation: same identity under paraphrased prompts
   - distractor robustness: target identity under irrelevant numbers
   - composition: compound prompts such as `page 666`, `room 137`,
     `flight 999`
2. Compare conditions:
   - no intervention
   - best single-layer intervention
   - joint realized-chart intervention from exp 25
   - distributed intervention from exp 26
3. Score by deterministic target/reference log-likelihood margins, not
   broad lexical heuristics.
4. Secondary optional scorer: small rubric judge, used only as
   qualitative support after deterministic metrics.

### 31.4 Pre-registered expectation

Joint or distributed intervention should shift target/reference
log-likelihood margins by at least `0.5` nats more than best
single-layer intervention on at least two task families, without
increasing off-target errors by more than `20%`.

### 31.5 Outcome interpretation

- **Pass**: object-level behavior tracks realized-chart intervention.
  The conjecture gains behavioral support.
- **Partial**: behavior shifts under some tasks but not under
  paraphrase/distractor controls.
- **Fail**: geometric interventions do not produce lawful behavioral
  effects. The evidence remains representational and cannot yet claim
  behavioral objecthood.

### 31.6 Script shape

`experiments/31_behavioral_realized_chart.py`

Outputs:

- `results/31_behavioral_realized_chart/behavior_report.txt`
- `results/31_behavioral_realized_chart/behavior_summary.json`
- `results/31_behavioral_realized_chart/task_margin_bars.png`
- `results/31_behavioral_realized_chart/offtarget_errors.png`

---

## Cross-experiment Sequencing

```
     exp 20 failed gate
             |
             v
    exp 25 realized gate
        /       |       \
       v        v        v
    exp 26   exp 27   exp 31
       \        |        /
        v       v       v
        emergence discriminator set
             |
             v
       exp 30 replication
             |
             v
       exp 29 trajectory

exp 28 explicit-object control can run independently once the control
system is available.
```

Run order:

1. Run exp 25 first. It is the direct successor to exp 20 and determines
   whether the gate failure was chart-insufficiency or deeper leakage.
2. Run exp 26 and exp 27 next. They distinguish distributed realization
   from local ownership and test whether partial views reconstitute.
3. Run exp 31 after exp 25 defines the realized chart. Behavioral
   testing should not precede the chart definition.
4. Run exp 28 whenever an explicit-object control system exists.
5. Run exp 30 after the GPT-2 protocol stabilizes.
6. Run exp 29 when checkpoint compute is available.

---

## Promotion Logic

The emergence conjecture strengthens materially only under a conjunction:

- exp 25: multi-layer conditioning beats single-chart conditioning;
- exp 26: distributed intervention beats local ownership;
- exp 27: partial charts reconstitute the object;
- exp 30: the pattern survives model variation;
- exp 31: behavior tracks realized-chart intervention.

Exp 28 is a contrast arm. It is not required for the conjecture, but it
guards against a weak metric: if an explicit-object system does not show
a different signature, the metric may not discriminate emergence from
technology-layer objecthood.

The conjecture weakens if:

- exp 25 fails and residual identity remains fully predictive after
  joint conditioning;
- exp 26 finds a clean local owner;
- exp 27 fails to reconstitute from partial charts;
- exp 30 shows the pattern is model-family-specific;
- exp 31 shows no controlled behavioral effect.

Do not promote `accepted_markov_object` status from these experiments
unless a gate condition actually closes. Candidate status remains the
default until conditional independence, or a stronger formal substitute,
is satisfied.

---

## File Layout

```
markov_object_research/
├── experiments/
│   ├── 25_multilayer_realized_topology_gate.py
│   ├── 26_distributed_ownership_audit.py
│   ├── 27_partial_chart_reconstitution.py
│   ├── 28_explicit_object_control.py
│   ├── 29_training_emergence_trajectory.py
│   ├── 30_cross_model_invariance.py
│   └── 31_behavioral_realized_chart.py
└── results/
    ├── 25_multilayer_gate/
    ├── 26_distributed_ownership/
    ├── 27_partial_reconstitution/
    ├── 28_explicit_object_control/
    ├── 29_training_trajectory/
    ├── 30_cross_model_invariance/
    └── 31_behavioral_realized_chart/
```
