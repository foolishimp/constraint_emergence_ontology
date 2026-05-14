# Experiments 33-40: Inverting K To Recover The Substrate Boundary

**Status:** pre-registered design. None executed.
**Supersedes:** experiments 26-31 as currently designed (linear-residualization +
unbounded-probe instrument family is gate-mismatched per analysis in
`empirical_results.md` §13.4 and the discussion thread that produced this
document). Exp 28's intent is preserved as exp 40 (explicit-object control);
the rest of 26-31 are replaced.
**Companion:** `constraint_emergence_ontology_spec.md` (esp. §III, §VIII, INV-11,
§X Inverse Projection Problem), `emergence_conjecture_program.md`,
`topological_model_assessment.md`, `empirical_results.md`.
**Draft date:** 2026-05-01.

---

## Preface — frame change

Under INV-11 the substrate is graph-topological; geometric appearance in the
LLM residual stream is a coarse-graining projection through K (the trained
forward map). The Markov object lives at the substrate as a graph-topological
gap-pattern; what shows up at any chosen layer is the image of that pattern
under K.

Three direct consequences:

1. **The construct is stochastic in substrate, geometric in projection.** A
   boundary exists; finding it requires inverting through K, not extracting
   from a single layer.
2. **Object-level "saying" is structurally unfaithful (§8.4).** Every previous
   experiment that tried to identify the object as a vector at a layer (exps
   18, 20, 25) failed at object-level; every experiment that tried morphism-
   level "showing" (exps 21, 23, 24) passed. This is the spec's prediction
   reproduced empirically.
3. **The empirical task is to characterize K.** Once K's local-tangent
   behavior is mapped, morphism-level fingerprints can be glued into a
   global geometric boundary by inversion. The boundary may be nonlinear,
   may have non-trivial topology, may be fuzzy at small scales — but it
   exists.

The new central question:

> Does a level-set boundary in joint state `s` exist whose local-tangent atlas
> glues into a global geometric object that is causally faithful to behavior
> and aligns with a graph cut in the computational graph?

All experiments use the same baseline rig as exps 18-25 unless noted:
- GPT-2 small via `transformer_lens`
- residual stream at `blocks.{layer}.hook_resid_pre`
- primary layers `{2, 4, 6, 8, 10}`
- primary targets `{999, 666, 137}`
- reference: replaced from single null `5` to a battery (see exp 34)

Order of priority:

| # | name | wave | gate-level |
|---|---|---|---|
| 33 | embedding-decomposition audit | 0 | confound removal |
| 34 | multi-null direction stability | 0 | confound removal |
| 40 | explicit-object control | 0 | instrument calibration |
| 35 | bounded-capacity boundary fitting | 1 | instrument |
| 36 | local-tangent atlas + curl test | 2 | **GLUING TEST** |
| 37 | causal faithfulness of the level set | 3 | causal validation |
| 38 | graph-cut signature via path patching | 3 | substrate alignment |
| 39 | behavioral object-level closure | 4 | object closure |

Exp 36 is the central experiment. PASS = global geometric object exists;
FAIL = only local charts exist and the global-object claim collapses.

---

## Wave 0 — Confound Removal And Instrument Calibration

These must run before any boundary-fitting experiment. Without them downstream
results inherit two known confounds (token embedding, single-null contrast)
and one unknown (whether the boundary instrument can find a real object on a
system known to have one).

---

### Experiment 33 — Embedding-Decomposition Audit

#### 33.1 Motivation

Layer-2 mean-diff transfer (exp 19 PASS at 0.87/0.93/0.90) is at the depth
where token-embedding contrast and learned constraint topology are hardest
to distinguish. Every subsequent claim inherits this confound.

#### 33.2 Hypothesis

A genuine learned object should retain meaningful transfer after stripping
the static token-embedding contrast from each direction at each layer.

#### 33.3 Protocol

1. Define a neutral template pool `NEUTRAL_TEMPLATES` of generic
   single-number frames (e.g. "Box {n} contains", "There were {n} people",
   "Pick number {n}") where the number does not carry strong cultural
   loading. Target N >= 30.
2. For each target T and reference R, layer L:
   - `e_T^(L)` = mean residual contrast at the target token across the
     neutral templates only.
   - `d_T^(L)` = mean residual contrast across the diverse pool used in
     exp 18.
3. Decompose `d_T^(L) = alpha * e_T^(L) + d_T^(L,perp)` with
   `d_T^(L,perp) ⊥ e_T^(L)` (Euclidean).
4. Re-run exp 18 alpha-sweep transfer using `d_T^(L,perp)` only. Compare to
   the unstripped direction.
5. Re-run exp 23 composition with embedding-stripped directions (`d_compound,perp`
   vs `d_A,perp + d_B,perp`).
6. Report per-layer: fraction of transfer attributable to `e_T^(L)` vs
   `d_T^(L,perp)`, magnitudes and norms.

#### 33.4 Pre-registered expectation

For a learned (non-lexical) object:
- at layers L >= 6, `d_T^(L,perp)` retains >= 50% of original transfer at
  alpha=1;
- at layer 2, embedding-attributable share will be substantial (50-90%);
  the residual `d_T^(L,perp)` is the candidate learned signal;
- composition cosine on stripped directions retains >= 0.5 excess over
  random-pair null.

#### 33.5 Outcome interpretation

- **Pass:** `d_T^(L,perp)` retains >= 50% transfer at L >= 6 and composition
  remains positive after stripping. Object is real and learned.
- **Partial:** retention 25-50% at L >= 6; object real but partly confounded.
  All claims qualified to "learned + lexical" rather than "learned".
- **Fail:** retention < 25% at all layers. The reported "object" reduces
  substantially to lexical contrast. Reframe.

#### 33.6 Script

`experiments/33_embedding_decomposition.py`

Outputs: `results/33_embedding_decomposition/{report.txt, summary.json,
transfer_by_layer.png, parallel_perp_decomposition.png}`.

#### 33.7 Dependencies

None. Runs first. Calibrates every subsequent direction.

---

### Experiment 34 — Multi-Null Direction Stability

#### 34.1 Motivation

All identity directions to date are `mu(target) - mu(5)`. Direction is
target-specific only if it is stable across choice of null. Otherwise it
is a target-vs-this-null contrast and the word "identity" is unearned.

#### 34.2 Hypothesis

A target identity direction has high cosine across multiple null choices;
its first principal component across null choices captures most cross-null
variance.

#### 34.3 Protocol

1. Null battery: `{5, 2, 50, 250, 800, 41, 7, 11}` (8 nulls, all generic).
   Optional cultural-null arm: `{42, 100, 7, 11}` to test whether the
   direction discriminates target-from-other-cultural vs target-from-generic.
2. For each target T (cultural: 999, 666, 137) and null N_i, extract
   `d_{T,N_i}` via exp 18's mean-diff at layers `{2, 8}` (start there).
3. Compute pairwise cosine matrix `C[i, j] = cos(d_{T,N_i}, d_{T,N_j})`.
4. Compute target-stable component as PC1 of `{d_{T,N_i}}`; report
   explained-variance ratio.
5. Test transfer at alpha=1 of the target-stable component vs each
   per-null direction.
6. Cultural-null arm: report whether direction picks out target identity
   (stable across all nulls) or target-vs-generic (stable only across
   generic nulls, varies vs cultural nulls).

#### 34.4 Pre-registered expectation

- mean cross-null cosine >= 0.6 at layer 2; >= 0.4 at layer 8;
- target-stable PC1 explained variance >= 60% at layer 2, >= 50% at layer 8;
- transfer of target-stable PC1 within +/- 20% of best per-null direction.

#### 34.5 Outcome interpretation

- **Pass:** target-stable component dominates; subsequent experiments use
  it as the actual identity direction.
- **Partial:** stable across some nulls, unstable across others. Directions
  are partly target-specific, partly target-vs-null contrast. Subsequent
  experiments must report which null and acknowledge the dyadic frame.
- **Fail:** explained variance < 30%. Directions are essentially dyadic
  contrasts. The "target identity" claim is unearned; reframe to
  "target-vs-reference contrast direction" throughout.

#### 34.6 Script

`experiments/34_multinull_stability.py`

Outputs: `results/34_multinull_stability/{report.txt, summary.json,
cosine_matrix_{target}_{layer}.png, pc1_explained_variance.png}`.

#### 34.7 Dependencies

None. Parallel with 33 and 40.

---

### Experiment 40 — Explicit-Object Control On Toy System

#### 40.1 Motivation

Without a known-object reference, "GPT-2 doesn't pass" is uninterpretable.
A toy system with explicit object slots that **does** pass each instrument's
gate validates that the instruments work. Without it, a FAIL on GPT-2 is
ambiguous between "construct missing" and "instrument broken."

#### 40.2 Hypothesis

On a small transformer with explicit object-slot embeddings, instruments
35-37 PASS at thresholds substantially above noise.

#### 40.3 Protocol

1. Construct toy transformer:
   - 4 layers, d_model=128, single attention head per layer
   - 16-dim object-slot embedding `o_T` per target T
   - synthetic next-token task: predict target-conditional continuation
     from prompt + object slot
   - object slot is injected at layer 2 residual stream additively
2. Train to convergence (target accuracy >= 95% on test).
3. Run exp 35 (bounded-capacity boundary fitting): the boundary is the
   subspace spanned by `{o_T}`; fit recovery should be exact at low
   capacity.
4. Run exp 36 (local-tangent atlas): tangent normals should be globally
   coherent (low curl, low closure error) since the object is genuinely
   global.
5. Run exp 37 (causal faithfulness): across-boundary intervention shifts
   behavior cleanly; along-boundary leaves it invariant.
6. Calibrate PASS thresholds for each instrument against the toy.

#### 40.4 Pre-registered expectation

Each of 35, 36, 37 PASS on the toy at thresholds well above the GPT-2
results. If any instrument fails the toy, that instrument is broken or
its threshold is mis-set; revise before running on GPT-2.

#### 40.5 Outcome interpretation

- **Pass:** instruments validated; carry their PASS thresholds to GPT-2.
- **Partial / Fail on instrument X:** instrument X needs revision before
  it can be run on GPT-2.

#### 40.6 Script

`experiments/40_explicit_object_control.py`

Outputs: `results/40_explicit_object_control/{report.txt, summary.json,
toy_training_loss.png, instrument_calibration.png}`.

#### 40.7 Dependencies

None. Parallel with 33 and 34.

---

## Wave 1 — Boundary Instrument

### Experiment 35 — Bounded-Capacity Level-Set Fitting

#### 35.1 Motivation

A Markov object's image under K is a level set `lambda_T(s) = 0` on joint
state. Whether this level set exists *as a real object* — not just as the
decision boundary of an unbounded probe — is determined by whether a
capacity-budgeted estimator can recover it accurately. Exp 20's AUC=1.000
across all conditions is precisely the failure mode of unbounded probes;
this experiment fixes the gate.

#### 35.2 Hypothesis

The boundary `lambda_T(s) = 0` admits compact representation: a low-capacity
estimator achieves high target/reference accuracy on embedding-stripped
joint state.

#### 35.3 Protocol

1. Joint state `s` per prompt = concat of residuals at layers
   `{2, 4, 6, 8, 10}` at the target token position. Dim ~ 5 * 768 = 3840.
2. Embedding-strip each layer's residual via exp 33's `e^(L)` projection
   so `s` carries only learned signal.
3. Capacity ladder of estimators for `lambda_T(s)`:
   - linear logistic regression
   - MLP with hidden width `h in {16, 64, 256, 1024}`
   - kernel density-ratio (KLIEP) with bandwidth ladder
4. Per estimator, measure on 30 held-out templates (GroupKFold by template):
   - target/reference discrimination accuracy
   - calibration of `lambda_T` (Brier score)
   - capacity needed to reach >= 90% accuracy
5. Compare embedding-stripped vs raw joint state; the capacity gap is the
   embedding-confound contribution.

#### 35.4 Pre-registered expectation

A genuine compact object: hidden width `h <= 64` achieves >= 90% accuracy
on embedding-stripped `s`. Linear may already exceed 80%.

#### 35.5 Outcome interpretation

- **Pass:** `h <= 64` achieves >= 90%. Boundary `lambda_T = 0` is a
  candidate object's image under K. Carry the fitted `lambda_T` forward.
- **Partial:** moderate capacity (`h in [256, 1024]`) required. Boundary
  is real but high-curvature; downstream interpretation must accept that
  the "object" requires non-linear charts.
- **Fail:** only unbounded capacity works. There is no compact boundary
  in joint state; the construct collapses to "K's high-dimensional
  response is target-discriminative" — uninteresting as object claim.

#### 35.6 Script

`experiments/35_bounded_capacity_boundary.py`

Outputs: `results/35_bounded_capacity_boundary/{report.txt, summary.json,
capacity_accuracy_curve.png, brier_calibration.png, lambda_T_*.npz}`.

#### 35.7 Dependencies

Exp 33 (embedding-stripping projection), exp 34 (target-stable direction
component to seed initial estimator if needed), exp 40 (instrument
calibration thresholds).

---

## Wave 2 — Gluing Test (The Central Experiment)

### Experiment 36 — Local-Tangent Atlas And Curl Test

#### 36.1 Motivation

The single most important experiment in the program. Per INV-11 the
substrate boundary projects through K to a possibly-nonlinear, possibly-
fuzzy hypersurface. Whether this hypersurface is *one global object* or
merely a collection of unrelated local effects is the operational
question. A real object means the local tangent planes glue — the normal
vector field is integrable. No object means they don't.

This test is what finally distinguishes "we found a learned linear
contrast family" (the current strong claim) from "we found a global
geometric Markov object" (the spec's claim).

#### 36.2 Hypothesis

Local linear discriminants fitted in joint-state neighborhoods produce a
unit-normal field whose curl is small and whose parallel-transport
closure error is small — i.e., the field is integrable up to a global
boundary.

#### 36.3 Protocol

1. Sample joint states `s` from a dense template pool (>= 200 prompts x 3
   targets + reference battery from exp 34).
2. For each `s_i`, build neighborhood `N(s_i)` of its k=20 nearest joint-
   state neighbors (across all targets + reference, weighted by target
   identity).
3. In each `N(s_i)`, fit a local linear discriminant separating target
   from reference. Record unit normal `n_i` and local accuracy.
4. Integrability tests:
   - **Curl test:** for each oriented triangle `(s_i, s_j, s_k)` of nearby
     samples, compute holonomy of `n` around the loop (sum of signed
     angles between transports); aggregate `|holonomy|` distribution.
   - **Closure test:** parallel-transport `n_i` to `s_j` along the chord,
     compare to `n_j`; mean angular deviation is closure error.
5. Null model: shuffle target labels within the same template pool;
   refit local discriminants; compute the same statistics.
6. Optional secondary: vary k in `{10, 20, 50}` to test scale stability
   of the gluing.

#### 36.4 Pre-registered expectation

Global boundary exists iff:
- mean closure error < 30 degrees;
- null-shuffle closure error > 60 degrees;
- mean |curl| statistic < 1/3 of null-shuffle |curl|;
- behavior stable across k in {10, 20, 50}.

#### 36.5 Outcome interpretation

- **Pass (low curl, low closure error):** local tangents glue. There is
  a global geometric boundary in joint state. The spec's substrate-side
  Markov-object claim is empirically vindicated at LLM scale via K's
  projection.
- **Partial (moderate curl, sectional closure):** local tangents glue
  within sub-regions of joint state but not globally. The construct is
  sheaf-of-charts, closer to a "stratified Markov object" in the spec's
  §III sense. Methodology must publish *charts* not *the object*.
- **Fail (high curl, no closure):** no global object. What looks like
  cross-layer coherence (exp 21) is K-induced smoothness, not object
  integrity. The spec's global-object claim at LLM scale must be given
  back; the program reduces to charting K.

#### 36.6 Script

`experiments/36_local_tangent_atlas.py`

Outputs: `results/36_local_tangent_atlas/{report.txt, summary.json,
curl_distribution.png, closure_error_distribution.png,
neighborhood_accuracy.png}`.

#### 36.7 Dependencies

Exp 33, exp 35. Validated against exp 40.

---

## Wave 3 — Causal Validation Of The Boundary

### Experiment 37 — Causal Faithfulness Of The Level Set

#### 37.1 Motivation

The boundary fitted in exp 35 is *representational*. Whether it is
*causal* — moving `s` across `lambda_T = 0` produces lawful behavior change,
moving along it leaves behavior invariant — is the spec's INV-04
condition that real layers cause real boundary behavior at the layer
above.

#### 37.2 Hypothesis

Across-boundary interventions produce target-coherent behavior shifts;
along-boundary interventions preserve behavior at matched perturbation
norm.

#### 37.3 Protocol

1. For each held-out prompt: compute `s` and project to
   `(lambda_T(s), s_perp)` where `s_perp` is the component orthogonal to
   `grad lambda_T(s)` in joint state.
2. **Across-boundary intervention:** move `s` to a fixed reference value
   of `lambda_T` while preserving `s_perp`. To realize this in the
   model, intervene at the layer with steepest
   `partial lambda_T / partial r_L` (typically L=2 per exp 19); propagate
   forward.
3. **Along-boundary intervention:** move `s` along `s_perp` while holding
   `lambda_T` fixed at the original value, at matched perturbation norm.
4. Behavior measurement:
   - target/reference next-token margin
   - paraphrase-robust target identification (5 paraphrased downstream
     queries per prompt)
   - compositional probes (page-T, room-T, flight-T constructions)
5. Random-direction control: norm-matched random vector intervention,
   to set the noise floor for "any perturbation moves things."

#### 37.4 Pre-registered expectation

- across-boundary intervention shifts margin by >= 0.5 nats more than
  random-direction control, on >= 3 of 4 task families;
- along-boundary intervention preserves margin (shift <= 0.15 nats more
  than random control) on >= 3 of 4 task families;
- paraphrase robustness >= 80% under across; >= 80% preservation under
  along.

#### 37.5 Outcome interpretation

- **Pass:** the geometric boundary is causally faithful. Object identity
  is the level-set coordinate.
- **Partial:** across works, along leaks. Boundary is causal but tangent
  space carries some target information.
- **Fail:** neither test discriminates. Boundary is a representational
  artifact of K's geometry, not a causal feature of the network's
  computation.

#### 37.6 Script

`experiments/37_causal_faithfulness.py`

Outputs: `results/37_causal_faithfulness/{report.txt, summary.json,
across_vs_along_margins.png, paraphrase_robustness.png}`.

#### 37.7 Dependencies

Exp 35 (fitted lambda_T), exp 36 (PASS or PARTIAL gives the geometric
warrant).

---

### Experiment 38 — Graph-Cut Signature Via Path Patching

#### 38.1 Motivation

Per the spec (§III, INV-11), the substrate object is a *graph cut* — a
minimal set of substrate nodes whose ablation severs target-relevant
computation. K projects this cut through the network's computational
graph. The question is whether the geometric boundary in joint state
corresponds to a graph cut in the network's computational graph.
This is the bridge from projection-side geometry back to substrate-side
graph topology that the spec demands.

#### 38.2 Hypothesis

The minimum-cardinality computational-graph cut for target identification
(`C_T`) projects through K to a subspace whose principal directions
align with `grad lambda_T(s)`.

#### 38.3 Protocol

1. Path patching: identify the minimum set of computational-graph nodes
   (residual sites + attention heads + MLP outputs) whose ablation
   collapses target-identification accuracy below a chosen threshold
   (e.g., 60% of original margin). Use iterative greedy patching with
   counterfactual prompts.
2. `K_C(C_T)` = the joint-state subspace spanned by activations at nodes
   in `C_T` projected to the joint-state coordinate system used in
   exps 35-37.
3. Alignment tests:
   - cosine of `grad lambda_T(s)` (averaged over held-out s) with the top
     principal directions of `K_C(C_T)`;
   - reconstruction loss of `grad lambda_T` projected onto `K_C(C_T)`;
   - cardinality of `C_T` versus dimensionality of the recovered
     boundary's tangent space.
4. Null model: random node sets of matching cardinality.

#### 38.4 Pre-registered expectation

- cosine of `grad lambda_T` with top PC of `K_C(C_T)` >= 0.7;
- reconstruction loss < 0.3;
- random-node-set null cosine < 0.3.

#### 38.5 Outcome interpretation

- **Pass:** geometric boundary is the projected image of a computational-
  graph cut. Substrate-side construct is empirically reachable through
  K. The spec's graph-topological Markov-object construct has been
  shown at LLM scale.
- **Partial:** alignment exists but is weak. Boundary is influenced by
  but not identified with the cut set. The bridge to substrate is
  partial.
- **Fail:** no alignment. Geometric boundary is K-induced and does not
  correspond to a substrate-side cut. Either the boundary is not the
  object, or the path-patching procedure does not find the right cut
  family. Reframe.

#### 38.6 Script

`experiments/38_graph_cut_signature.py`

Outputs: `results/38_graph_cut_signature/{report.txt, summary.json,
cut_set_visualization.png, alignment_cosines.png}`.

#### 38.7 Dependencies

Exp 35, exp 36. Independent of exp 37 but informative when read jointly
with it.

---

## Wave 4 — Behavioral Closure

### Experiment 39 — Behavioral Object-Level Closure

#### 39.1 Motivation

Final closure: does the recovered geometric boundary govern object-level
*behavior* across paraphrase, distractor, and compositional contexts?
Replaces and supersedes exp 31 in spirit, on the new instrument family.

#### 39.2 Hypothesis

Across-boundary intervention via the fitted `lambda_T` shifts object-level
behavior more than norm-matched controls and does so paraphrase-robustly.

#### 39.3 Protocol

1. Behavioral test battery:
   - **Paraphrase preservation:** target identity under 10 paraphrased
     prompt forms.
   - **Distractor robustness:** target identity under prompts containing
     2-5 irrelevant numbers.
   - **Compositional binding:** target identity in (page-T, room-T,
     code-T, flight-T) compounds.
   - **Cross-form (carrier) test:** target as digit, word, roman numeral.
2. Score by margin (target_logit - reference_logit) under:
   - no intervention
   - across-boundary intervention from exp 37
   - along-boundary intervention from exp 37
   - random-direction intervention (norm-matched control)
3. Scoring is deterministic (log-likelihood margins on canonical
   continuations). No lexical n-gram heuristics; no LLM-judge unless
   used as auxiliary qualitative report after deterministic numbers.

#### 39.4 Pre-registered expectation

- across-boundary intervention shifts margin by >= 0.4 nats more than
  random-direction control on >= 3 of 4 task families;
- along-boundary preserves margin (shift <= 0.15 nats more than random
  control) on >= 3 of 4 families.

#### 39.5 Outcome interpretation

- **Pass:** geometric boundary governs object-level behavior. Object is
  closed at the behavioral layer.
- **Partial:** behavior tracks the boundary on some but not all tasks.
  Construct has partial behavioral closure.
- **Fail:** behavior is independent of boundary intervention. Boundary
  is real geometry but not behaviorally load-bearing — reframe as
  observation about K, not about object identity.

#### 39.6 Script

`experiments/39_behavioral_closure.py`

Outputs: `results/39_behavioral_closure/{report.txt, summary.json,
margin_by_task.png, paraphrase_distractor.png}`.

#### 39.7 Dependencies

Exp 37 (across/along intervention machinery).

---

## Sequencing And Promotion Logic

```
   Wave 0 (parallel):   33 ──┐
                        34 ──┤
                        40 ──┘
                                │
   Wave 1:                     35 (boundary instrument)
                                │
   Wave 2:                     36 (THE central gluing test)
                                │
   Wave 3 (parallel):    37 ──┬── 38
                                │
   Wave 4:                     39 (behavioral closure)
```

### Promotion criteria

The construct moves from `candidate_residual_identity_chart` (today's
status) to `candidate_markov_object_image` on the conjunction:
- exp 33 PASS or PARTIAL (object isn't pure embedding contrast);
- exp 34 PASS (target-stable across nulls);
- exp 35 PASS (capacity-bounded boundary fit exists);
- exp 36 PASS or PARTIAL (local atlas glues globally or sectionally);
- exp 37 PASS (causal faithfulness);
- exp 39 PASS or PARTIAL (behavioral closure).

The construct moves from `candidate_markov_object_image` to
`accepted_markov_object` (final spec kind, the strongest reachable claim
under §8.4 / INV-11) only on the additional conjunction:
- exp 38 PASS (graph-cut signature aligns) — connecting the geometric
  image back to the substrate object via K.

### Note on the promotion ceiling

Even full PASS does not give a *formal* CI Markov blanket — that is now
understood to be unattainable at the projection layer per §8.4 / INV-11.
"Accepted" status under this design means: *the geometric image of a
substrate Markov object has been recovered, glues globally, is causally
faithful, governs behavior, and aligns with a computational-graph cut.*
That is the strongest claim physically reachable at the projection layer
and is the spec's actual prediction.

### De-promotion criteria

Any of the following collapses the construct to a weaker kind:
- exp 33 FAIL → object is lexical, not a learned topology;
- exp 34 FAIL → no target identity, only target-vs-null contrasts;
- exp 36 FAIL → no global object, only local charts of K;
- exp 37 FAIL → boundary is K-geometry, not object identity;
- exp 38 FAIL → no substrate-side cut corresponds to the recovered
  geometry; reframes the entire program.

---

## What This Design Buys

- **Replaces the gate-mismatch instrument family** (linear residualization +
  unbounded probe) with bounded-capacity boundary fitting + integrability +
  causal faithfulness.
- **Honors §8.4** by using only morphism-level (showing) instruments to
  glue toward the object, never object-level (saying) extraction.
- **Operationalizes INV-11** through K-inversion: every experiment is
  characterizing K's projection of a substrate boundary.
- **Provides falsifiable de-promotion paths** at every wave — the program
  can lose the construct cleanly.
- **Calibrates against a known-object reference** (exp 40), so "GPT-2
  fails" is no longer ambiguous between "construct missing" and
  "instrument broken."
- **Brings the spec and the empirical program into alignment.** Before
  this design, the spec asserted graph-topological substrate and
  projected geometry while the empirical program tested for residual-
  space CI. The two did not converge. This design closes that gap.

---

## File Layout

```
markov_object_research/
├── experiments_33_40_design.md          (this document)
├── experiments/
│   ├── 33_embedding_decomposition.py
│   ├── 34_multinull_stability.py
│   ├── 35_bounded_capacity_boundary.py
│   ├── 36_local_tangent_atlas.py
│   ├── 37_causal_faithfulness.py
│   ├── 38_graph_cut_signature.py
│   ├── 39_behavioral_closure.py
│   └── 40_explicit_object_control.py
└── results/
    ├── 33_embedding_decomposition/
    ├── 34_multinull_stability/
    ├── 35_bounded_capacity_boundary/
    ├── 36_local_tangent_atlas/
    ├── 37_causal_faithfulness/
    ├── 38_graph_cut_signature/
    ├── 39_behavioral_closure/
    └── 40_explicit_object_control/
```

Each results directory: `<name>_report.txt`, `<name>_summary.json`, plots
matching the convention of exps 08-25.

---

## Scope Notes

- This design covers intra-LLM verification under the K-inversion frame.
  Cross-substrate tests remain out of scope; the institutional/biological
  arms are governed by `wmp_so_what.md` §8.4-§8.5.
- No experiment here replaces exp 32's value-topology probe — that is a
  separate model-evaluation strand under
  `topological_model_assessment.md`.
- All pre-registered thresholds are set with the GPT-2 small + Pythia-160M
  baseline and the toy-system calibration (exp 40) in view. Threshold
  reset is lawful *once* per experiment if calibration warrants and must
  be noted in that experiment's results file.

---

## What This Design Does Not Do

- It does not run any experiment. All numbers above are thresholds, not
  findings.
- It does not promise that any experiment will pass. Pre-registered
  failure is a legitimate outcome and updates the spec accordingly:
  empirical de-promotion of a spec construct is also constitutional
  evidence.
- It does not replace `empirical_results.md`. Results extend that
  document; this design stays unchanged as pre-registration of intent.
