# Markov-Object Assurance Program

**Status:** proposal. Methodological reframe of the empirical program.
**Companion:** `markov_object_research.md`,
`emergence_conjecture_program.md`, `emergent_markov_object_evidence.md`,
`topological_model_assessment.md`, `experiments_41_44_design.md`,
`/Users/jim/src/apps/constraint_emergence_ontology/constraint_emergence_ontology.md`.
**Draft date:** 2026-05-11.

---

## 1. Frame

A Markov object is a substrate-neutral construct
(`constraint_emergence_ontology.md`: "stable patterns with
constraint-defined boundaries — IS Friston's Markov blanket in
substrate-neutral vocabulary"). The object lives in the constraint
topology that the implementation realizes; the implementation is one
chart of the realization.

For an LLM, the traversal is the semantic operation; the residual
stream, attention pattern, and SAE feature basis are charts of how the
traversal is implemented in this substrate. Charting the chart is not
testing the object.

The empirical fate of the construct must therefore be decided at the
level the construct lives at:

> Behavioral invariance under semantic intervention, with pre-registered
> nulls, executed across architecturally-distinct models.

The destination is **model assurance**: each candidate Markov object
becomes a falsifiable invariance specification; each model gets a
topology card recording which objects it realizes, how tightly bounded,
how lawfully compositional, and how carrier-invariant. Reasoning
benchmarks become downstream of topology assessment.

### 1.1 Methodological landscape

The substrate-neutral retreat is also a response to a known
methodological hazard. Bruineberg, Dołęga, Dewhurst, Baltieri (2022),
"The Emperor's New Markov Blankets," *Behavioral and Brain Sciences*
45:e183, argues that much Friston-blanket work conflates Pearl blankets
(graphical-statistical) with Friston blankets (dynamical, with sparse
coupling implying causal isolation). Any substrate-mathematical
Markov-object claim must declare which blanket it is claiming. The
behavioural reframe sidesteps the conflation by retreating to observable
input-output structure — Pearl-honest about what the residual stream
buys you, Friston-aligned about what the construct is supposed to be.

The closest extant empirical tool is Beck, Friston, Da Costa et al.
(2025), "Dynamic Markov Blanket Detection for Macroscopic Physics
Discovery" (arXiv 2502.21217). Variational Bayesian EM that detects
Markov-blanketed subsystems in observed dynamics. Applied to physics
simulations, not yet to LLM activations. If the dynamical-state-update
reframe (`experiments_41_44_design.md`) survives Exp 42, applying Beck
et al. to layer-wise transformer dynamics is the next substrate-level
escalation before the retreat to semantic gates becomes the only move.

---

## 2. Reflection On Existing Waves

Reclassified under the semantic-construct reading. Numbered findings are
recovered, not invalidated.

### 2.1 Chart-discovery waves (Exps 08-18)

What they did: located representational regions sensitive to candidate
identity in residual streams and SAE feature spaces. Found a
direction-native chart at layer 8 with weak transfer, a stronger chart
at layer 2, fragmentation across SAE atoms, and core/coat separation.

Reclassified: chart-shape descriptions of the substrate, not
construct-existence findings. Useful because they document how this
substrate projects the candidate object — fragmented, layer-sensitive,
context-coated. None of this either confirms or refutes the object.

### 2.2 Single-chart conditional-independence gate (Exp 20)

What it did: subtracted the selected projection at layer 2 and layer 8;
tested whether residual identity remained predictive.

Result: residual remained fully predictive (`AUC=1.000`, `HSIC p=0.005`).

Reclassified: chart-insufficiency. The simplest projection of the
substrate does not exhaust identity. Under the semantic reading, this is
expected — the object isn't owned by one direction in r_L, so removing
one direction shouldn't make residual identity vanish.

### 2.3 Multi-layer realized-topology gate (Exp 25)

What it did: built a joint chart over layers `2/4/6/8`; tested residual
prediction.

Result: joint chart did not beat best single chart
(`AUC ≈ 0.989-1.000`).

Reclassified: chart-family insufficiency. Linear residualization over
mean-difference coordinates is one chart family. Its failure is
informative about that family, not about the construct.

### 2.4 Compositional algebra (Exp 23)

What it did: tested whether identity directions compose under lawful
combination.

Result: `cos(d_compound, d_A + d_B) = 0.936` vs random pair `0.634`,
permutation `p = 0.0099`.

**This is already a semantic-level positive.** Lawful composition is a
behaviour of the object, not of the substrate. The geometric form was a
proxy for the semantic property and the proxy passed against a
pre-registered null. Under the assurance program this finding is
promoted from "supporting evidence" to "first semantic-gate pass."

### 2.5 Cross-model replication (Exp 24)

What it did: ported the direction-native transfer assay to Pythia-160M.

Result: all three targets pass relaxed replication (transfer
`0.159-0.207` at `α=1`, threshold `0.1`).

Reclassified: substrate-neutrality probe. The construct survives
substrate change. Under the assurance reading this is the second
semantic-level positive, also against a pre-registered null. Modest
result, but at the right altitude.

### 2.6 Static reframe waves (Exps 33-38)

What they did: five orthogonal static gates at GPT-2 124M and Llama-3
8B, with a toy validator (Exp 40 PASS).

Result: comprehensive de-promotion at the static residual-stream layer.

Reclassified: thorough proof that no static linear chart of r_L
transparently exposes the candidate boundary at either tested scale.
**This is now a strong substrate-shape finding, not a construct
finding.** The construct survives because its empirical fate was never
decidable by static r_L charts.

### 2.7 Dynamical reframe (Exp 41)

What it did: tested whether the probed identity-direction satisfies
Hipólito Eq. 2 dynamics under η-intervention on Llama-3 8B.

Result: probed-direction μ-disturbance `0.362` vs random `0.420`. FAIL.

Reclassified: the static-probed direction is not the dynamical-state
update internal subspace. This is informative about the substrate's
update geometry, not about the construct. Hipólito Eq. 2 is a
substrate-mathematical formulation; its failure here says the LLM's
state-update dynamics don't carry the object as a clean orthogonal
partition of r_L.

### 2.8 Free-form generation (Exp 22)

What it did: behavioural assay of identity-direction injection.

Result: confounded by reference-class baselines.

Reclassified: closest of all existing waves to the right altitude, but
ran without a sufficient null. The proposal below absorbs this design
and adds the falsifiability discipline that Exp 22 lacked.

### 2.9 Topology atlas (Exps 32, 45-47b)

What they did: mining for semantic-shape classifications across `value`,
named entities, named categories, speech acts.

Result: shape descriptions (carrier-bound bundle, regime-fiber
topology, etc.).

Reclassified: this is **already at the assurance altitude**. The atlas
produces topology-card outputs. Under the assurance program these waves
are promoted from "discovery" to "candidate assurance grades pending
behavioral confirmation."

### 2.10 Net reflection

The program already contains semantic-level positives (Exps 23, 24) and
already produces assurance-grade shape outputs (Exps 32, 45-47b). The
de-promotions (Exps 20, 25, 33-38, 41) measured chart families of the
substrate and found them insufficient — that is real evidence about
this substrate's projection of the construct, not refutation of the
construct.

What is missing: a falsifiable behavioural-preservation gate executed
across architectures with pre-registered nulls.

---

## 3. Proposed Test Program

### 3.1 Construct

For an LLM `M` and a candidate semantic object `O`:

- **Carrier set** `C(O) = {c_1, ..., c_n}`: surface forms that should
  preserve `O` (paraphrase, null-peer substitution, distractor padding,
  syntactic rewrite preserving referent).
- **Perturbation set** `P(O) = {p_1, ..., p_m}`: substitutions that
  should perturb `O` (target replacement, role swap, semantic
  reversal).
- **Behavioural readout** `B(M, prompt)`: a vector of measurable model
  outputs — next-token distribution on diagnostic continuations,
  completion under sampling, compositional-task accuracy.

`O` is a candidate Markov object in `M` iff:

1. `B(M, c_i)` clusters tightly across `C(O)` (carrier invariance);
2. `B(M, p_j)` lies away from that cluster (boundary effect);
3. The cluster is not explained by surface-feature similarity alone;
4. The boundary is not explained by surface-feature dissimilarity
   alone;
5. Composition `O_1 ∘ O_2` produces lawful behaviour at the cluster
   level;
6. The pattern persists across architecturally-distinct `M`.

The strongest claim is (1)+(2)+(3)+(4) jointly, which corresponds to
the substrate-neutral form of the conditional-independence statement:
behaviour conditional on the boundary is independent of the perturbation
that crosses the boundary.

### 3.2 Wave A — Behavioural Carrier Invariance

**Ancestor.** Ribeiro, Wu, Guestrin, Singh (2020), "Beyond Accuracy:
Behavioral Testing of NLP Models with CheckList," ACL 2020 (arXiv
2005.04118). CheckList introduced the
invariance-test / directional-test / minimum-functionality split and
remains the canonical behavioural-testing reference. Wave A inherits
that split but retargets it: CheckList tests behavioural *quality*; Wave
A tests *entity existence* via the surface-feature null. The same shape
of measurement; a different epistemic claim. The 2025 robustness surveys
(arXiv 2505.18658, 2511.21568) treat paraphrase-invariance as a quality
dial; no published work uses paraphrase-invariance failure as a
falsification gate for an entity-existence claim. That gap is what the
surface-feature null discipline closes.

**Hypothesis.** For candidate objects in the topology atlas (named
entities, categories, speech acts), behavioural readout `B` is preserved
under carrier substitution and perturbed under perturbation
substitution. The preservation/perturbation gap exceeds a
surface-feature null.

**Protocol.**

1. Select 30 candidate objects from existing atlas (Exps 45-47b) plus
   the legacy `666/999/137` set for continuity.
2. For each object, generate `n=20` carrier prompts and `m=20`
   perturbation prompts, paired by structure.
3. For each prompt, capture `B(M, prompt) =` next-token distribution
   over a diagnostic vocabulary of size `V=500` plus completion under
   greedy sampling at `K=32` tokens.
4. Compute carrier cluster `μ_C` and perturbation cluster `μ_P` in
   behaviour space.
5. Compute the behavioural separation index
   `S = (||μ_C - μ_P|| - within_C - within_P) / (within_C + within_P)`.

**Surface-feature null.** Replace `B(M, prompt)` with a surface-feature
embedding (token n-grams, edit distance) and recompute `S`. The
behavioural `S` must exceed the surface-feature `S` for the object to
qualify; otherwise the boundary is explained by surface form alone.

**Pre-registered thresholds.** Object qualifies as candidate if:
- behavioural `S > 0.3`;
- surface-feature `S < 0.5 × behavioural S`;
- 90% bootstrap CI excludes zero on the difference.

**Outputs.** `results/wave_A_carrier_invariance/`:
- `report.txt`, `summary.json`
- `behavioural_separation_per_object.png`
- `surface_feature_null_comparison.png`
- topology-card excerpt per qualifying object

**Falsification.** If fewer than 50% of atlas candidates qualify, the
atlas is not picking up semantic objects but topological artefacts.

### 3.3 Wave B — Compositional Lawfulness (Behavioural)

**Hypothesis.** For pairs of candidate objects `(O_1, O_2)`, the
behavioural signature of a compositional prompt
(`"<O_1> in the manner of <O_2>"`, etc.) is closer to a structured
combination of the individual signatures than to either alone or to a
random-pair baseline.

**Protocol.**

1. Take 30 ordered pairs `(O_1, O_2)` with semantically meaningful
   composition.
2. Generate composition prompts; capture `B(M, comp_prompt)`.
3. Capture `B(M, O_1_alone_prompt)` and `B(M, O_2_alone_prompt)`.
4. Compute compositional alignment
   `A_pair = sim(B(comp), f(B(O_1), B(O_2)))`
   for several reduction operations `f` (mean, weighted mean, max,
   token-wise interpolation).

**Random-pair null.** For 30 random pairs `(O_i, O_j)` with no
meaningful composition, compute `A_random` under the same protocol.

**Pre-registered thresholds.**
- mean `A_pair - A_random > 0.15`;
- permutation `p < 0.01`;
- stable across at least two reduction operations `f`.

**Outputs.** `results/wave_B_compositional_lawfulness/`:
- `report.txt`, `summary.json`
- `composition_alignment_per_pair.png`
- `random_null_distribution.png`

**Falsification.** If `A_pair ≈ A_random` across all reduction
operations, the direction-algebra finding from Exp 23 was a chart
artefact, not a semantic-object property.

**Continuity.** Re-runs the Exp 23 result at the behavioural level. Exp
23 is a positive geometric proxy for this gate; Wave B is the gate
proper.

### 3.4 Wave C — Inter-Object Discrimination Gradient

**Hypothesis.** Behavioural distance between objects tracks ontological
distance. Substituting Beethoven → Mozart produces a smaller behavioural
shift than Beethoven → cardboard, with a gradient over an ontological
distance metric (taxonomic depth, embedding distance from a
ground-truth ontology, expert-rated similarity).

**Protocol.**

1. Build an ontological-distance matrix over 50 objects using one or
   more independent metrics (WordNet path length, expert ratings,
   embedding distance in a model not under test).
2. Generate substitution prompts and measure behavioural distance
   `||B(O_i_prompt) - B(O_j_prompt)||`.
3. Test correlation between behavioural distance and ontological
   distance.

**Null.** Permute the ontology distance matrix and recompute. The
permutation null distribution is the falsifier.

**Pre-registered thresholds.**
- Spearman `ρ > 0.4` between behavioural and ontological distance;
- permutation `p < 0.01`;
- correlation stable across at least two ontological-distance metrics.

**Outputs.** `results/wave_C_discrimination_gradient/`:
- `report.txt`, `summary.json`
- `behavioural_vs_ontological_distance.png`
- `correlation_per_metric.png`

**Falsification.** If behavioural distance is uncorrelated with
ontological distance, objects are at best label-bound (chart-bound),
not semantic.

### 3.5 Wave D — Cross-Architecture Invariance

**Precedents.** Two existing lines come close to this gate, neither
asks the entity-invariance question with a pre-registered null:

1. Paulo, Marshall, Belrose (2024), "Does Transformer Interpretability
   Transfer to RNNs?" (arXiv 2404.05971). Tests whether contrastive
   activation steering, tuned lens, and latent-knowledge elicitation
   transfer from transformers to Mamba and RWKV. Most methods transfer.
   This asks whether *methods* transfer, not whether *the same
   constraint-bounded entity* recurs. Wave D narrows the question to
   per-object behavioural-invariance signatures across substrates.

2. Huh, Cheung, Wang, Isola (2024, ICML), "The Platonic Representation
   Hypothesis" (arXiv 2405.07987). Argues representations across
   architectures and modalities converge to a shared statistical
   model. The 2026 follow-up "Revisiting the Platonic Representation
   Hypothesis: An Aristotelian View" (arXiv 2602.14486) reports that
   after calibration, global-metric convergence largely disappears and
   only local-neighborhood metrics retain cross-modal alignment. **Wave
   D pre-registers against the Aristotelian-view caveat, not the
   original Platonic claim.** The expected pattern is local
   neighborhood preservation per object, not global geometric
   alignment. This is the load-bearing methodological choice.

**Hypothesis.** The same candidate objects realize with similar
invariance signatures across architecturally-distinct models. Local
chart varies; semantic invariance persists. The expected form of the
invariance is local (per-object behavioural-separation correlation),
not global (geometry-wide alignment).

**Protocol.**

1. Select at least three architecturally-distinct models — for example,
   GPT-2 (transformer, post-LN), Llama-3 8B (transformer, pre-LN, GQA),
   Mamba (state-space), at minimum.
2. Run Wave A on each.
3. For each candidate object, compute the across-model correlation of
   per-object behavioural separation index.

**Null.** Substitute behavioural readout with surface-feature readout
on each model; recompute correlations.

**Pre-registered thresholds.**
- Behavioural across-model correlation `> 0.5` over the candidate-object
  set;
- behavioural correlation exceeds surface-feature correlation by `≥
  0.2`.

**Outputs.** `results/wave_D_cross_architecture/`:
- `report.txt`, `summary.json`
- `cross_architecture_correlation_matrix.png`
- per-object scatter plots

**Falsification.** If across-model behavioural correlation is at or
below the surface-feature null, the construct is substrate-bound rather
than substrate-neutral. This is the strongest available test of the
substrate-neutrality claim. Failure here would weaken the construct
substantially because substrate-neutrality is load-bearing in the
ontology.

### 3.6 Wave E — Capability Gradient (Assurance)

**Hypothesis.** Model capability tracks topology richness, not just
absolute task performance. A stronger model holds more candidate
objects, with tighter boundaries, lawful composition, and stable
cross-architecture invariance signatures.

**Protocol.**

1. Run Waves A, B, C on a model series with known capability gradient
   (e.g., GPT-2 124M, GPT-2 1.5B, Llama-3 8B, Llama-3 70B; or
   Pythia-160M through Pythia-12B).
2. Compute per-model:
   - candidate-object count passing Wave A;
   - mean compositional alignment from Wave B;
   - discrimination correlation from Wave C.
3. Correlate against task benchmarks (MMLU, BBH, etc.).

**Output.** A topology-card schema:

```
model: <name>
parameters: <n>
training_tokens: <n>
candidate_object_inventory:
  named_entity_tier: <count>, mean_S=<x>
  named_category_tier: <count>, mean_S=<x>
  speech_act_tier: <count>, mean_S=<x>
compositional_lawfulness: A_pair_minus_random=<x>, p=<x>
discrimination_correlation: ρ=<x>, p=<x>
cross_architecture_signature_match: <x> if available
substrate_chart_dependencies: layer-sensitivity_profile, sae_fragmentation_index, etc.
```

**This is the assurance product.** Models compared on the topology card,
not just on benchmark scores.

**Outputs.** `results/wave_E_capability_gradient/`:
- per-model topology card
- `capability_vs_topology_richness.png`
- `topology_richness_vs_benchmark_score.png`

### 3.7 Wave F — Adversarial Boundary Probing

**Hypothesis.** A genuine candidate object's behaviour is robust to
perturbations that should be irrelevant (paraphrase attacks,
distractor injection, format changes) and breaks under perturbations
that should matter (semantic role swap, target substitution).

**Protocol.**

1. For Wave A qualifying objects, generate adversarial carrier prompts
   (jailbreak-style paraphrases, distractor padding, format mutation).
2. Generate adversarial perturbation prompts (subtle role swaps near the
   target).
3. Measure behavioural preservation under adversarial carriers and
   behavioural perturbation under adversarial perturbations.

**Pre-registered thresholds.**
- Wave A behavioural preservation degrades by `< 0.2` under adversarial
  carriers;
- Wave A behavioural perturbation amplifies by `≥ 1.5×` under adversarial
  perturbations;
- Brittleness profile differs between objects (a uniform brittleness
  pattern would indicate no object structure, only general fragility).

**Outputs.** `results/wave_F_adversarial_probing/`:
- per-object robustness profile
- topology-card extension: object-level robustness grade

**Why this matters for assurance.** Models that pass Wave A but fail
Wave F have brittle objects. The topology card grades both presence and
robustness.

---

## 4. Falsifiability Discipline

The substrate-neutral move is empirically dangerous because it lets any
substrate-level negative slide into "wrong chart." The discipline that
prevents this:

1. **Every wave declares a falsifier in advance.** Pre-registered
   thresholds and pre-registered nulls. No "we now reframe the negative
   as informative" reads after the fact.
2. **Every wave includes an irrelevance null.** A null where, if the
   construct does not exist, the measurement should also pass. If the
   measurement passes but the irrelevance null also passes, the wave
   does not qualify the construct.
3. **At least two waves must run cross-architecture before any
   construct-level claim.** Substrate-bound passes on one architecture
   are insufficient.
4. **Capability-gradient tests are required for assurance claims.** A
   measurement that doesn't separate weak from strong models on
   topology richness has low information about model assurance.
5. **Negative behavioural results count as construct-weakening.** If
   Wave A fails on a candidate object across architectures, that object
   is removed from the topology atlas, not reclassified into another
   chart family.

---

## 5. Promotion Logic

A candidate object earns the **`candidate_semantic_markov_object`** kind
when it passes Wave A on at least one architecture, with the
surface-feature null cleared.

It earns the **`replicated_semantic_markov_object`** kind when it
additionally passes Wave A on a second architecturally-distinct model
with cross-architecture signature correlation per Wave D.

It earns the **`compositional_semantic_markov_object`** kind when it
participates in at least one Wave B passing pair.

It earns the **`graded_semantic_markov_object`** kind when it
participates in a Wave C correlation that clears the permutation null.

It earns the **`robust_semantic_markov_object`** kind when it
additionally clears Wave F adversarial probing.

A model earns a **topology card** by running Waves A, B, C, F on a
fixed atlas; the card reports the four object grades plus
cross-architecture correlation when Wave D is available.

The construct earns the **`accepted_semantic_markov_object`** status
only when the conjunction holds across at least three
architecturally-distinct models on a non-trivial fraction (`> 50%`) of
the atlas.

The construct is **`refuted`** if Wave A fails on `> 75%` of atlas
candidates with surface-feature nulls cleared, or if Wave D shows
cross-architecture correlation at or below surface-feature null. Either
condition is sufficient.

---

## 6. Assurance Vocabulary

**Position in the assurance landscape.** Existing model-assurance
frames are capability-threshold-based (Anthropic Responsible Scaling
Policy v1-v3; Phuong et al. 2024 "Evaluating Frontier Models for
Dangerous Capabilities," arXiv 2403.13793; Anthropic Sabotage
Evaluations), benchmark-grid-based (Liang et al. 2022 HELM, arXiv
2211.09110 — note that HELM Lite collapsed robustness because it
correlated with accuracy), or sociotechnical (Weidinger et al. 2023,
"Sociotechnical Safety Evaluation of Generative AI Systems," arXiv
2310.11986, with explicit modality, risk-coverage, and context gap).
Topological-data-analysis applied to LLMs has begun to surface the
shape question (e.g. "Persistent Topological Features in Large
Language Models," arXiv 2410.11042; "Hidden Holes," arXiv 2406.05798)
but does not translate the topology into an assurance artifact.

The topology card slots beneath capability-threshold and grid-based
frames as the **upstream topology layer**. RSP and HELM measure what
the model can do; the topology card measures what semantic structure
the model has formed to do it over. Wave E grading is substrate-neutral
in a way HELM (architecture-blind benchmarks) and RSP (capability
thresholds) are not: a Mamba and a Llama can be compared on the same
candidate-object inventory via Wave A/D signatures.

The destination of this program is to use Markov-object grades as the
upstream layer of model assurance:

```
topology_card:
  candidate_semantic_markov_objects: <n>
  replicated_semantic_markov_objects: <n>
  compositional_semantic_markov_objects: <n>
  graded_semantic_markov_objects: <n>
  robust_semantic_markov_objects: <n>
  cross_architecture_signature_correlation: <ρ>
  per_object_robustness_profile: <map>
```

A model with a richer topology card has better-formed semantic
structure to reason over. Reasoning benchmarks measure how well the
model traverses its topology; topology cards measure what topology the
model has.

Assurance applications:

1. **Pre-deployment grading.** A model with a sparse topology card on
   safety-critical objects (deception, harm, regulated entity classes)
   has measurable semantic risk that scalar benchmarks miss.
2. **Capability comparison.** Two models with similar MMLU scores can
   have very different topology cards. The card distinguishes
   surface-pattern competence from semantic structure.
3. **Tracking through training.** Topology richness across checkpoints
   identifies when the model formed its objects, which connects to
   `emergence_conjecture_program.md §6.4` (training-emergence
   trajectory) but at the semantic altitude.
4. **Architecture comparison substrate-neutrally.** Topology cards
   abstract over architecture. Mamba and Llama get compared on the
   same object inventory.
5. **Audit trail.** Each candidate object on a topology card has a
   pre-registered test bundle. Re-running the bundle on a new model
   variant produces an audit-grade comparison.

This is the engineering exit of the program: Markov-object vocabulary
becomes assurance vocabulary, and the construct's pre-registered
falsifiers become the assurance test methodology.

---

## 7. Relation To Existing Engineering Line

The engineering line in `emergence_conjecture_program.md §8` already
publishes candidate-class object cuts. Under this proposal, the cuts
acquire a behavioural test bundle as part of their candidate
publication. The publication moves from:

```
candidate Markov-object cut + projection-first storage + null peers + core/coat
```

to:

```
candidate Markov-object cut
+ projection-first storage
+ null peers
+ core/coat
+ pre-registered Wave A/B/C/F bundle
+ topology-card grade
```

The cuts remain candidate; the assurance grade tells the consumer how
well the candidate is supported. No engineering-line work has to wait
on Wave A. The cuts ship, and the topology grade is appended as it
accrues.

---

## 8. Non-Goals

- This proposal does not run any experiment. Pre-registered design
  only.
- It does not retire `experiments_41_44_design.md`. Exp 42 (learned
  dynamical partition) may still be informative as a substrate-shape
  finding; under this proposal it is downgraded from "live promotion
  gate" to "chart-family probe."
- It does not claim that semantic-level testing is the only correct
  level. It claims that, given the substrate-neutral construct
  definition in `constraint_emergence_ontology.md`, the gate must be at
  the semantic level for any negative result to refute the construct.
  Substrate-level negatives remain informative about charts.
- It does not declare the engineering line conditional on Wave success.
  The engineering line is independently earned. This proposal supplies
  the assurance grading on top.
- It does not propose a unified framework that eliminates all chart
  work. The atlas, SAE assays, dynamical experiments, and topology
  measurements remain the chart-mapping layer beneath the assurance
  layer.

---

## 9. File Layout

```
markov_object_research/
├── markov_object_assurance_program.md   (this document)
├── experiments/
│   ├── wave_A_carrier_invariance.py
│   ├── wave_B_compositional_lawfulness.py
│   ├── wave_C_discrimination_gradient.py
│   ├── wave_D_cross_architecture.py
│   ├── wave_E_capability_gradient.py
│   └── wave_F_adversarial_probing.py
└── results/
    ├── wave_A_carrier_invariance/
    ├── wave_B_compositional_lawfulness/
    ├── wave_C_discrimination_gradient/
    ├── wave_D_cross_architecture/
    ├── wave_E_capability_gradient/
    └── wave_F_adversarial_probing/
```

---

## 10. Working Formulation

```
A Markov object is a substrate-neutral constraint-topology construct
realized through the model's traversal. Its empirical fate is decided
by behavioural invariance under semantic intervention against
pre-registered nulls, executed across architecturally-distinct models.
Substrate-level chart failures are informative about how the substrate
projects the construct, not about the construct's existence. The
program's engineering output is the topology card: a per-model grade
that classifies which Markov objects the model has formed, how robust
the boundaries are, how lawfully objects compose, and how invariant
the structure is across substrate variation.
```
