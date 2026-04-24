# Experiments 19–24: Design

**Status:** pre-registered design. No results yet.
**Scope:** six experiments that push the Markov-object construct from
heliocentric (candidate; right causal order + basic predictive power) toward
stronger truths — Newtonian-level dynamics and the formal promotion gate.
**Companion:** `empirical_results.md` §13.4 "What comes next" lists these
directions in abbreviated form; this document commits to protocols and
thresholds in advance.
**Draft date:** 2026-04-24.

---

## Preface

Exp 18 produced the most load-bearing current result: a single mean-diff
residual direction `d = μ(obj) − μ(null)` transfers identity at
α=1 transfer ≈ 0.27, well below the pre-registered ≥ 0.8 threshold but
directionally non-trivial. Three structural questions remain open and are
named promotion gates in `empirical_results.md` §13.4 and in
`world_model_project_paper.md` §8:

1. **Is the construct low-rank linear?** If transfer saturates at some
   small k ≤ 10, the object is captured by a low-rank subspace — the
   construct has a closed geometric shape. If transfer plateaus below
   threshold, the object is not purely linear.
2. **Is the construct a Markov blanket in the formal sense?** The
   conditional-independence condition (given the projection, residual
   components independent of target) is the statistical closure. Passing
   this gate promotes the construct from candidate to established.
3. **Does the construct behave like an object?** That is, does it
   compose, persist across representation layers, and cause behavioural
   redirection in free-form generation — not only in next-token KL?

These six experiments address those questions. Each carries a
pre-registered quantitative expectation and an outcome-interpretation rule
so it can be scored pass, partial, or fail without post-hoc redrawing of
the threshold.

All experiments use the same baseline rig as exps 08–18 unless otherwise
noted (GPT-2 small via `transformer_lens`, SAE via `sae_lens` for exps
that need feature context, probe layer 8, reference n=5, targets
{666, 999, 137, 42}).

Order of priority (research-program ranking):

| # | name                                          | closes                              | gate-level |
|---|-----------------------------------------------|-------------------------------------|------------|
| 19 | rank-k identity saturation                    | §13.4 multi-direction saturation     | Newtonian |
| 20 | direction-native conditional independence     | §13.4 CI; promotion gate             | **PROMOTION** |
| 21 | multi-layer identity direction                | §13.4 multi-layer direction          | robustness |
| 22 | free-form generation under α-intervention     | §13.4 behavioural validation         | behavioural |
| 23 | compositional algebra of identity directions  | §13.4 object composition             | Newtonian |
| 24 | cross-model replication (Pythia-160M)         | §13.4 replicate at scale             | cross-model |

Exp 20 is the only experiment whose pass/fail status alone promotes the
construct. Exps 19 and 23 close Newtonian-level gaps (low-rank saturation,
compositional algebra) and sharpen what exp 20 tests. Exps 21, 22, 24
close robustness gaps and do not by themselves promote.

Substrate-spanning tests (institutional, biological) are named in
`wmp_so_what.md` §8.4–§8.5 and are out of scope for this design document.
They require external data or external collaborators.

---

## Experiment 19 — Rank-k Identity Saturation

### 19.1 Motivation

Exp 18 used a single mean-diff direction and achieved α=1 transfer
≈ 0.24–0.28. The pre-registered threshold was ≥ 0.8. Two readings of
the shortfall are consistent with the evidence to date:

- the construct is low-rank linear at some k > 1 and a rank-1 extraction
  captures a fraction proportional to the largest principal axis within
  the identity subspace;
- the construct is not purely linear in residual space; additional rank
  does not close the gap.

This experiment discriminates the two readings.

### 19.2 Hypothesis

For each cultural target (666, 999, 137), there exists k* ≤ 10 such that
subtraction of a rank-k* identity projection at α=1 on held-out prompts
achieves transfer ≥ 0.8 in mean over 10 held-out templates.

### 19.3 Protocol

1. Collect paired residuals (object, null) across the train template pool
   (exp 18's TRAIN_TEMPLATES, ≥ 20 paired prompts).
2. Extract ordered orthogonal identity directions by iterated
   residualized mean-diff:
   - `d_1 = μ(R_obj) − μ(R_null)`, normalise.
   - For `k = 2..K_max` (K_max = 10): project R_obj and R_null onto the
     subspace orthogonal to `span(d_1..d_{k-1})`, recompute the mean
     difference in that subspace, normalise, append as d_k.
3. For each rank k from 1 to K_max, form the rank-k identity projector
   `P_k = Σ_{i≤k} d_i d_iᵀ`.
4. On held-out prompts, intervene: `r_new = r − α · P_k(r − μ(R_null))`
   at α ∈ {0.5, 1.0, 1.5}. Record KL-transfer as in exp 18.
5. Secondary construction: replace iterated mean-diff with LDA in
   residual space (regularised) and re-run step 3. Report both curves.

### 19.4 Pre-registered expectation

At k = 5, α = 1, transfer ≥ 0.8 on held-out prompts for at least two of
{666, 999, 137} using mean-diff iteration.

### 19.5 Outcome interpretation

- **Pass**: ≥ 2 targets meet threshold at k ≤ 5. Construct is low-rank
  linear. Downstream claim: published cuts expose a rank-k projection,
  not a rank-1 direction. Storage shape updates.
- **Partial**: 1 target meets threshold at k ≤ 10, or ≥ 2 targets meet
  transfer in [0.5, 0.8) at k = 5. Construct is low-rank but does not
  saturate at the pre-registered depth. Downstream claim: published cuts
  expose the rank at which saturation is observed, with the shortfall
  reported.
- **Fail**: transfer plateaus below 0.5 at k = 10 for all targets.
  Construct is not purely linear. Redirect: consider MLP-layer
  representations, non-linear projectors (kernel or autoencoder-based),
  or accept that the effective blanket is partially non-linear and
  revise WORLD_MODEL_METHOD's Representation Law accordingly.

### 19.6 Dependencies

None beyond exp 18 infrastructure. This is the first extension to run.

---

## Experiment 20 — Direction-native Conditional Independence (Promotion Gate)

### 20.1 Motivation

The formal Markov-blanket condition is: given the blanket, internal
states are conditionally independent of external states. For the
geometric construct this reads: given the projection of a residual onto
the rank-k identity subspace, the orthogonal remainder is independent of
the target class.

This is the named promotion gate. Passing it moves the construct from
candidate to established at the representation depth tested.

### 20.2 Hypothesis

Given the rank-k* identity subspace from exp 19 (k* selected per target
as the rank where transfer either saturates to ≥ 0.8 or plateaus at
k = 10), the residual component orthogonal to that subspace is
conditionally independent of target identity. Operationalised: a
logistic probe trained on the orthogonal component cannot distinguish
target from reference residuals above chance at held-out positions.

### 20.3 Protocol

1. Collect residuals at held-out positions for (target, reference) pairs
   across all cultural targets, at layer 8, from a diverse template set
   separate from exp 19's training set.
2. Construct the rank-k* identity projector P_k from exp 19 for each
   target.
3. For each residual r, compute `r_perp = r − P_k(r − μ(R_null))`.
4. Train a cross-validated logistic probe on `r_perp` with target-class
   labels (one-vs-reference, per target). Use 5-fold CV and report mean
   AUC.
5. Repeat with a matched-control probe trained on full `r` (not
   projected). Compute ΔAUC = AUC(full r) − AUC(r_perp).
6. Secondary test (kernel-independence): compute HSIC between `r_perp`
   and target label on held-out residuals with a Gaussian kernel; compare
   against a permutation null.

### 20.4 Pre-registered expectation

AUC on `r_perp` within 0.03 of chance (0.50) over 5-fold CV, averaged
across targets; ΔAUC vs full residual ≥ 0.20.

HSIC on `r_perp` vs target label not significantly above permutation
null at p > 0.05.

### 20.5 Outcome interpretation

- **Pass**: AUC on `r_perp` in [0.47, 0.53] AND HSIC not significant.
  **Construct promoted from candidate to established at rank-k* in
  layer 8**. WORLD_MODEL_METHOD epistemic-status subsection updates;
  `odd_world_model` can reserve an `accepted_markov_object` publication
  kind for cuts backed by this experiment's evidence.
- **Partial**: AUC in [0.53, 0.60] or HSIC significant at p ∈ [0.01, 0.05].
  Construct captures most but not all identity; residual contains
  partial target information. Publish cuts with a documented
  "information leak beyond rank k*" tag. Do not promote to accepted
  kind.
- **Fail**: AUC > 0.60 or HSIC highly significant. The rank-k*
  projection is not a blanket in the formal sense. Candidate status
  continues; revise §15.1 of `empirical_results.md`; consider whether
  the construct is better framed as an *approximate* or *effective*
  blanket rather than a formal one.

### 20.6 Dependencies

Requires exp 19's rank-k* determination. If exp 19 fails the low-rank
linearity test, run exp 20 with k = 10 as an upper-bound rank and
interpret accordingly.

### 20.7 Notes on the estimator

Probe-based conditional independence is not a formal CI test; it is a
predictive lower bound on mutual information. A probe that cannot
predict establishes that *this probe class* finds no information; a
probe that can predict establishes that *this probe class* does. The
HSIC secondary test complements the probe with a kernel-based
independence measure that does not require a parametric probe. Both
together give a stronger joint signal than either alone. Neither
reaches the formal CI criterion; the joint result is the best practical
proxy at residual-space dimensionality.

---

## Experiment 21 — Multi-layer Identity Direction

### 21.1 Motivation

Exp 10 established layered assembly of SAE features for cultural
tokens: features present from layer 2, strengthening to layer 8. The
identity direction reading (exp 18) was anchored at layer 8. Whether
the direction is a layer-8 artifact or a representation-spanning
invariant is an open question in §13.4.

### 21.2 Hypothesis

The mean-diff identity direction extracted at layer L has high cosine
alignment with the direction extracted at neighbouring layers, and the
direction at any L ∈ {6, 8, 10} transfers identity at a comparable
magnitude when applied at its own layer.

### 21.3 Protocol

1. For each L ∈ {2, 4, 6, 8, 10, 11}, collect residuals and extract
   `d_L` via mean-diff on the training templates.
2. Compute the pairwise cosine matrix C[L, L'] over all pairs.
3. For each L, run an α-sweep intervention at that layer on the same
   held-out prompts used in exp 18. Record transfer per L.
4. Cross-layer test: apply `d_L` as an intervention at a different
   layer L'; record transfer. This is expected to degrade if the
   residual stream rotates between layers.

### 21.4 Pre-registered expectation

- Cosine matrix: `cos(d_L, d_{L+2}) ≥ 0.6` for at least two adjacent
  pairs with L ≥ 4.
- Same-layer transfer: layer-8 transfer remains at ≈ 0.25. At L ∈
  {6, 10}, transfer ≥ 0.15 (i.e. 60% of layer-8 magnitude).
- Cross-layer transfer: `d_L` applied at L' ≠ L degrades monotonically
  with |L − L'|.

### 21.5 Outcome interpretation

- **Pass**: identity direction is layer-continuous. A single mean-over-
  layers direction is a lawful abstraction. The construct has a
  representation-spanning form at least within a trained LLM.
- **Partial**: critical-layer emergence (below some L, direction is
  noisy; above it, direction is stable). Names the minimum layer at
  which the construct is mechanistically present. Consistent with
  exp 10's layered-assembly finding.
- **Fail**: direction rotates layer-by-layer. The identity direction is
  layer-local. Downstream: cuts must pin layer; compositions across
  layers are not lawful without a learned basis change.

### 21.6 Dependencies

None. Can run in parallel with exp 19.

---

## Experiment 22 — Free-form Generation under α-Intervention

### 22.1 Motivation

Exp 18's transfer is measured as next-token KL shift toward the
reference distribution. A 0.27 transfer is meaningful as a metric value.
Whether it corresponds to behavioural redirection in generated text — a
continuation that reads as being about 500 rather than about 999 — is
a separate empirical question. This experiment tests it.

### 22.2 Hypothesis

Under α ∈ [0.5, 2.0] subtraction of `d` at the target token position
during generation, completions exhibit reference-loaded content at
rates that rise monotonically with α and at α = 1 reach ≥ 40%
reference-loaded continuations (vs ≤ 10% at α = 0).

### 22.3 Protocol

1. Select 20 generation prompts per target (distinct from exp 18's
   templates) where the target token appears mid-sentence and the
   model continues for ≥ 30 tokens.
2. For each prompt and α ∈ {0, 0.5, 1.0, 1.5, 2.0}, generate 5
   completions (total 100 per α per target). Use greedy decoding to
   remove sampling variance; optionally repeat with top-k = 5 for
   behavioural diversity.
3. Score each completion along three axes:
   - **Lexical (deterministic)**: frequency of reference-associated
     n-grams (for 999 → 500: "emergency" → "invoice", "fire" → "paid",
     etc.) vs target-associated n-grams. Precompiled lookup per target.
   - **Perplexity**: perplexity of the completion under a
     reference-context prefix vs target-context prefix. Reference-
     loaded completions should have lower perplexity under the
     reference prefix.
   - **Judge (optional)**: LLM-judge (Claude Sonnet 4.6) with a
     rubric rating whether the completion reads as about the target
     or the reference, on a 1–5 scale. Report inter-rater agreement
     against lexical score.

### 22.4 Pre-registered expectation

At α = 1: lexical reference-loaded rate ≥ 40% (vs ≤ 10% at α = 0).
Perplexity under reference-prefix drops ≥ 0.5 nats from α = 0 to
α = 1. Judge rating (if run) shifts ≥ 1 point on the 1–5 scale.

Monotonic trend across α ∈ {0, 0.5, 1.0, 1.5, 2.0}.

### 22.5 Outcome interpretation

- **Pass**: behavioural transfer tracks residual-level KL transfer.
  The direction does real work at the generation level. Construct has
  behavioural evidence.
- **Partial**: behavioural transfer appears only at α ≥ 1.5. Direction
  is real but the object is higher-rank or partly non-linear; exp 19
  rank-k results may explain the shortfall.
- **Fail**: no behavioural signal despite KL shift. The next-token KL
  measure may be an artifact of logit geometry rather than an identity
  shift. Re-examine how "identity transfer" is operationalised.

### 22.6 Dependencies

None beyond exp 18. Independent of exp 19 and 20; complements them.

---

## Experiment 23 — Compositional Algebra of Identity Directions

### 23.1 Motivation

If identity directions compose via vector arithmetic, the construct has
algebra — a Newtonian-level property. §13.4 names this as "object
composition". This experiment tests whether compound-object directions
are linearly reconstructible from component directions.

### 23.2 Hypothesis

For compound concepts (e.g. "666 as a page number"), the identity
direction `d(compound)` has high cosine with the sum
`d(component_1) + d(component_2)` and low cosine with random pairs of
non-related directions.

### 23.3 Protocol

1. Select 20 compound-concept triples of the form (compound, A, B):
   - (page-666, page, 666)
   - (emergency-500, emergency, 500)
   - (room-137, room, 137)
   - (sacred-666, sacred, 666)
   - (price-$999, price, 999)
   - and so on.
2. For each element, extract a mean-diff direction via exp 18's
   protocol with appropriately matched null peers:
   - for "666", null = 5 (as in exp 18)
   - for "page", null = "paragraph" or a generic-noun null
   - for "page-666", null = "page-5"
3. Compute for each triple:
   - `cos(d_compound, d_A + d_B)` normalised
   - `cos(d_compound, d_A)` and `cos(d_compound, d_B)`
   - `cos(d_compound, d_R1 + d_R2)` for random R1, R2 drawn from
     unrelated concept pool (N = 100 random pairs per triple)
4. Test whether the true-pair cosine exceeds the random-pair null at
   p < 0.05 via permutation test.

### 23.4 Pre-registered expectation

Mean `cos(d_compound, d_A + d_B) ≥ 0.5` over the 20 triples.
Mean true-pair cosine exceeds mean random-pair cosine by ≥ 0.3 at
p < 0.01.

### 23.5 Outcome interpretation

- **Pass**: compound directions are (approximately) linear combinations
  of component directions. Identity composes by vector addition.
  Downstream: published cuts can compose via direction sums;
  WORLD_MODEL_METHOD Composition Law has a mechanistic ground.
- **Partial**: compound-to-sum cosine is in [0.3, 0.5] and exceeds
  random; composition is partly linear, partly non-linear. The
  non-linear component may be attention-mediated; name the gap
  quantitatively and defer.
- **Fail**: compound-to-sum cosine ≈ random. Composition is not linear
  at the direction level. Either objects are primitive at this scale,
  or composition happens at a different representation (MLP output,
  attention head). Re-scope.

### 23.6 Dependencies

Exp 18 (baseline direction). Benefits from exp 19 (rank-k may improve
the component directions). Can run with rank-1 directions first.

---

## Experiment 24 — Cross-model Replication (Pythia-160M)

### 24.1 Motivation

All results to date are within GPT-2 small. The construct's claim to
generality over trained representations requires replication in at
least one comparable but distinct model. Pythia-160M is the first
target because it has similar scale, a public residual-stream
architecture, and published SAEs.

### 24.2 Hypothesis

Exps 08 (feature-identity / core-coat), 13 (causal intervention),
17 (boundary leak), and 18 (direction transfer) qualitatively replicate
in Pythia-160M: core/coat decomposes; ablating the core perturbs
target-related continuations; SAE outside-set ablation leaks identity;
a mean-diff direction transfers identity at α = 1 with transfer in
[0.1, 0.5].

### 24.3 Protocol

1. Port experiment scripts 08, 13, 17, 18 to Pythia-160M via
   `transformer_lens` (it supports Pythia). Choose residual layer at
   proportional depth to GPT-2's layer 8 (e.g. Pythia-160M layer 8 of
   12 — same proportional depth).
2. Source an SAE for Pythia-160M. Options:
   - `pythia-160m-deduped-v0-res-jb` release if available at the
     chosen layer.
   - If not available, train a small SAE (EleutherAI `sae` or
     `sae_lens` training script) with matched feature count.
3. Use the same targets (666, 999, 137, 42) and template pool.
4. Run each ported experiment. Report per-experiment pass/fail
   against a GPT-2-calibrated threshold set:
   - Exp 08 port: coat/core ratio ≥ 5× (GPT-2 baseline 20–160×).
   - Exp 13 port: `" 911"` probability drop ≥ 30% under core ablation
     of 999 (GPT-2 baseline 94%).
   - Exp 17 port: outside-set ablation leaks ≥ 10% identity (GPT-2
     baseline 23–28%).
   - Exp 18 port: mean-diff α = 1 transfer ≥ 0.1 for ≥ 2 targets
     (GPT-2 baseline ~0.27).
5. Report the Pythia result table alongside GPT-2 baseline.

### 24.4 Pre-registered expectation

At least 3 of the 4 ported experiments pass the relaxed thresholds
above.

### 24.5 Outcome interpretation

- **Pass**: construct replicates in Pythia. Downstream: WORLD_MODEL_METHOD
  can describe the construct as LLM-general rather than GPT-2-specific
  at candidate status. The institutional-substrate claim in
  `wmp_so_what.md` §3 gains indirect support.
- **Partial**: 2 of 4 replicate. Names which properties are LLM-general
  vs model-specific. Constrains which claims are portable.
- **Fail**: ≤ 1 experiment replicates. Construct is GPT-2-specific. Revisit
  every "LLM" claim in `empirical_results.md` and
  `world_model_project_paper.md`; downgrade to "GPT-2 small" throughout.

### 24.6 Dependencies

SAE availability for Pythia-160M is the first-order risk. If no SAE is
readily available, exp 24 reduces to exps 13 and 18 (which do not need
an SAE) and becomes partial by construction. Exps 08 and 17 require an
SAE.

---

## Cross-experiment sequencing

```
           exp 18 (done)
                │
          ┌─────┼─────┬─────────┐
          ▼     ▼     ▼         ▼
         19    21    22        24
          │
          ▼
         20 (PROMOTION GATE)
          │
          ▼
     23 (uses d from 19 where useful)
```

- Run 19 first; its rank-k* output feeds 20.
- 21, 22, 24 are independent and can run in parallel with 19.
- 20 requires 19.
- 23 can start with rank-1 directions and be re-run with rank-k once
  19 lands.

Decision points after each experiment:

- **After 19**: is the construct low-rank linear? If pass/partial,
  proceed to 20 with the empirical k*. If fail, 20's scope contracts
  to "does a non-linear projection pass CI" and a non-linear projector
  design becomes prerequisite.
- **After 20**: does the construct pass the formal CI gate? If pass,
  WORLD_MODEL_METHOD and `odd_world_model` update to allow
  `accepted_markov_object` publication kind. If partial or fail,
  candidate status continues; the specific failure mode refines the
  method's epistemic-status subsection.
- **After 21**: is the direction layer-continuous? If pass, the
  representation-law language in WORLD_MODEL_METHOD can drop its
  layer-specific hedge. If fail, layer-pinning becomes part of the
  storage contract.
- **After 22**: does the direction redirect behaviour? If pass,
  downstream tooling (odd_world_model materializer) can use direction
  intervention as a verification primitive. If fail, the next-token KL
  metric may be replaced by a behavioural metric in future experiments.
- **After 23**: does identity compose? If pass, cut composition is
  direction-sum at candidate status. If fail, cuts are primitive units
  without algebraic composition and the method's Composition Law is
  emergent-only.
- **After 24**: is the construct LLM-general? If pass, replication lane
  extends (LLaMA, Mistral); institutional-substrate pilot (8.4 from
  wmp_so_what.md) becomes higher-priority. If fail, everything in the
  paper narrows to "within GPT-2 small".

---

## Scope notes

- This design covers intra-LLM verification. Cross-substrate tests
  (institutional paired-records, biological recordings) are out of
  scope here; see `wmp_so_what.md` §8.4–§8.5.
- No experiment here tests dynamics in the temporal sense (state
  evolution under sequential treatments). That lane is deferred until
  compositional algebra (exp 23) closes.
- All pre-registered thresholds are set with the current GPT-2 baseline
  in view. If a pilot run reveals the thresholds are misaligned (e.g.
  GPT-2 transfer is actually ~0.35 on a denser template set), threshold
  reset is lawful *once* and must be noted in the experiment's results
  file, not silently revised.

---

## File layout (proposed)

```
markov_object_research/
├── experiments/
│   ├── 19_rank_k_saturation.py
│   ├── 20_direction_native_ci.py
│   ├── 21_multi_layer_direction.py
│   ├── 22_freeform_generation.py
│   ├── 23_compositional_algebra.py
│   └── 24_cross_model_pythia.py
└── results/
    ├── 19_rank_k_saturation/
    ├── 20_direction_native_ci/
    ├── 21_multi_layer_direction/
    ├── 22_freeform_generation/
    ├── 23_compositional_algebra/
    └── 24_cross_model_pythia/
```

Each results directory will receive a `<name>_report.txt` plus plots
matching the convention of exps 08–18.

---

## What this design does not do

- It does not run any experiment. All numbers above are thresholds, not
  findings.
- It does not promise that any experiment will pass its threshold.
  Pre-registered failure is a legitimate outcome and updates the method
  accordingly.
- It does not replace `empirical_results.md`. Results, when they arrive,
  extend that document; this design document stays unchanged as a
  pre-registration of intent.
