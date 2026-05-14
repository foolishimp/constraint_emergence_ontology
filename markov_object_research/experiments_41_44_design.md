# Experiments 41-44: Dynamical Blanket Wave

**Status:** pre-registered design. Wave 5 of the program.
**Supersedes:** the static-projection K-inversion frame of exps 33-38, which de-promoted across two model scales (GPT-2 small + Llama-3 8B). Static residual-stream snapshots do not host a globally-coherent geometric Markov object; the construct cannot be tested as a property of static state.
**Companion:** `constraint_emergence_ontology_spec.md`, Hipólito, Ramstead, Convertino, Bhat, Friston, Parr (2021) "Markov blankets in the brain" (*Neuroscience & Biobehavioral Reviews* 125: 88-97), `experiments_33_40_design.md`.
**Draft date:** 2026-05-02.

---

## Preface — frame change

The static reframe (waves 0-4 / exps 33-38) tested whether the residual stream at one layer hosts a geometric boundary that distinguishes target identity. It does not. Five orthogonal gates failed at two scales (124M and 8B parameters), with a validated instrument (exp 40 toy PASS).

Hipólito et al. 2021 supplies the constructive correction. The Markov blanket is **not** a property of any one snapshot of the system's state. It is a property of the system's *equations of motion*. A four-way partition of the state into `(internal μ, sensory s, active a, external η)` is a Markov blanket iff it satisfies their Eq. 2:

```
μ̇ = f(μ, s, a)        internal-state dynamics independent of external given blanket
ȧ = f(μ, s, a)        active-state dynamics independent of external given blanket
η̇ = f(η, s, a)        external-state dynamics independent of internal given blanket
ṡ = f(η, s, a)        sensory-state dynamics mediate external -> internal
```

This is a claim about *the structure of the update rule*, not about geometry of the state.

For an LLM the layer-to-layer transition `r_{L+1} = F_L(r_L)` is the equation of motion. The right empirical test of a blanket is therefore:

> Does there exist a four-way partition of `r_L` into `(μ, s, a, η)` such that intervening on `η` at layer `L` leaves the downstream trajectory of the `μ`-projection unchanged?

This wave operationalizes that question.

The static experiments are not refuted by this reframe — they were measuring the wrong shape of object. The dynamical experiments here test the construct in the form Hipólito et al. actually defines it.

---

## Construct (LLM mapping of Hipólito et al. Eq. 2)

For a chosen blanket layer `L_blanket` in a transformer:

- **Joint state:** `r_L ∈ R^d` (the residual stream at layer L_blanket at the target token position).
- **Partition:** a tuple of orthogonal projections `(P_μ, P_s, P_a, P_η)` summing to identity. Each projects `r_L` onto its component subspace.
- **Dynamics:** the deterministic forward map `F_{L:L'}: r_L → r_{L'}` for `L' > L_blanket`. The "trajectory" of component `μ` is the sequence `(P_μ F_{L:L+k} r_L)_{k=1..K}` for some lookahead `K`.
- **Intervention:** replace `P_η r_L` with the same projection of a *reference prompt's* residual at the same layer/position. All other components unchanged.
- **Blanket criterion:** the intervention preserves the `μ`-trajectory across `K` downstream layers; symmetric internal/external roles hold; the partition is non-trivial (no component dominates).

This yields a concrete, falsifiable test.

---

## Wave structure

| # | name | gate-level |
|---|---|---|
| 41 | Random-partition baseline + identity-direction blanket test | calibration / probe-driven |
| 42 | Learned-partition blanket search | construct-search |
| 43 | Path-patching as connectivity-asymmetry blanket | architectural-graph |
| 44 | Multi-layer hierarchical blanket nesting (INV-04 test) | multi-scale |

Exp 41 is the simplest concrete test and the entry point. Exp 42 generalizes to a learned partition. Exps 43-44 close the design.

---

## Experiment 41 — Identity-direction blanket dynamical test

### 41.1 Motivation

The simplest concrete dynamical-blanket hypothesis is:

> The "internal" subspace `μ` is the identity-direction we found via probing (per exp 37); the "external" subspace `η` is everything orthogonal to it after embedding-stripping.

If that probed direction *is* the system's internal-state subspace, then intervening on `η` should leave the downstream `μ`-trajectory invariant. This recasts the failed exp 37 causal-faithfulness test as a *dynamical-trajectory* test rather than a static-margin test.

### 41.2 Hypothesis

For each target T at blanket layer L:

- the embedding-stripped probed identity-direction `n_T^L` defines a candidate `μ` subspace (1-D);
- everything orthogonal to `n_T^L` (and orthogonal to the embedding direction) is a candidate `η`;
- intervening on `η` (replacing it with reference-prompt η) leaves the `μ`-trajectory across layers `L+1..L+K` invariant up to a small tolerance ε;
- random-direction `μ` choices fail this test.

### 41.3 Protocol

For each (target T, blanket layer L_blanket ∈ {2, 8, 16, 24}):

1. Fit `n_T^L` (the embedding-stripped identity-direction at L) using the exp 37 protocol.
2. For each held-out prompt:
   a. Run native forward; capture residuals at layers `L_blanket, L_blanket+k` for k ∈ [1..K], K=8.
   b. Compute `μ_native(k) = (n_T · r_{L+k}) ` — scalar projection of the downstream residual onto `n_T^L`.
   c. Compute corresponding reference-prompt residuals at the same layers.
   d. Construct intervention: `r_L_intervened = P_μ r_L_native + P_η r_L_reference` where `P_μ = n_T^L (n_T^L)^T` (1-D projector) and `P_η = I - P_μ - P_e` (with `P_e` the embedding-direction projector).
   e. Forward through remaining layers from the intervened state at L. Capture `μ_intervened(k)`.
   f. Compute `Δμ(k) = μ_native(k) - μ_intervened(k)` for k = 1..K.
3. Random-partition baseline: same protocol with `n_T^L` replaced by a random unit direction in the embedding-stripped subspace, matched in 1-D dimensionality.
4. Symmetric test: also compute the `η`-trajectory under intervention. A *real* blanket should preserve `μ` AND substantially perturb `η`. If both are preserved, the partition is trivial.

### 41.4 Pre-registered expectation

**For the probed direction to be a blanket internal-direction:**
- `mean |Δμ(k)| / native μ-RMS < 0.15` for all k ≤ K, averaged over targets;
- `mean |Δη(k)| / native η-RMS > 0.5` (intervention had real effect on the external trajectory);
- random-baseline `mean |Δμ(k)| / native μ-RMS > 0.4` (random direction does NOT pass the blanket condition).

### 41.5 Outcome interpretation

- **PASS:** the probed direction satisfies the dynamical blanket condition. The identity-direction *is* the internal-state subspace; the failed exp 37 result was an artifact of measuring static margins instead of dynamical trajectories. Reframe required for the broader program.
- **PARTIAL:** the probed direction is *partly* preserved (μ-disturbance in [0.15, 0.4]). Identity-direction is closer to internal than random but not a clean blanket. Indicates a "soft blanket" or that the right μ subspace is higher-rank.
- **FAIL:** Δμ ≈ Δrandom. The probed direction has no blanket-like dynamical structure. Move to exp 42 (learned partition) — the right `μ` is not the probed direction.

### 41.6 Outputs

`results/41_dynamical_blanket_identity/`
- `report.txt`, `summary.json`
- `mu_trajectory_disturbance.png` (Δμ across k for probed vs random)
- `eta_trajectory_disturbance.png` (Δη across k — confirms intervention had effect)
- `per_layer_blanket_score.png` (1 - Δμ/Δη at each blanket layer L)

### 41.7 Dependencies

Embedding-direction `e_emb^L` from exp 33. Probed direction `n_T^L` from exp 37 protocol (refit per blanket layer).

---

## Experiment 42 — Learned partition blanket search

### 42.1 Motivation

If exp 41 fails, the blanket-`μ` is not the static-probed direction. Try to *find* a partition that satisfies the dynamical blanket condition by gradient descent. If no such partition exists, the construct is empirically refuted at this scale; if one does, what its `μ`-subspace looks like is the actual finding.

### 42.2 Hypothesis

For each target T and blanket layer L, there exists a learnable rotation `R ∈ SO(d)` and a 4-way block split such that the partition `R r_L = (μ, s, a, η)` minimizes `||Δμ-trajectory after η-intervention||` while keeping `||Δη-trajectory||` large.

### 42.3 Protocol

1. Parameterize partition via a `d × d` rotation matrix `R` (Cayley parameterization, or via Givens rotations to keep search tractable; for Llama-3 d=4096, restrict to a learnable orthogonal projection onto a low-rank subspace and treat the orthogonal complement as `η`).
2. Define loss:
   `L = E_prompts [||Δμ_traj||^2 / ||μ_native_traj||^2] + λ_1 max(0, τ - ||Δη_traj||) + λ_2 trivial-partition penalty`
3. Optimize over training prompts; evaluate on held-out.
4. Inspect learned `μ`-subspace: does it correspond to anything semantically interpretable (cosine with embedding, with probed direction, with token-vector axes)?

### 42.4 Pre-registered

(Detailed in 42.4-42.6 once exp 41 lands.)

---

## Experiment 43 — Connectivity-asymmetry blanket

### 43.1 Motivation

Hipólito et al. validate the cortical-column blanket structurally — by *missing* connections (no spiny stellate to other-column superficial pyramidal). The transformer analogue is the attention pattern: which heads at which layers attend to which positions. A blanket-shaped sub-circuit would have asymmetric attention: internal-mediating heads attend to the marker token; external-mediating heads attend to context tokens; sensory-mediating heads bridge the two.

### 43.2 Hypothesis

A path-patching analysis identifies an attention sub-graph with the asymmetry pattern of Hipólito Eq. 2: paths into `μ` come only from `s` and `a`, never directly from `η`.

### 43.3 Protocol

(Detailed once exp 42 lands.)

---

## Experiment 44 — Multi-layer hierarchical blanket nesting

### 44.1 Motivation

The spec's INV-04 ("hierarchy of resolution") and Hipólito's multi-scale nesting (neuron → column → network) imply that blankets at one layer should compose into blankets at a coarser layer. Test whether per-layer blanket structure (from exp 41/42) composes hierarchically.

(Detailed once exps 41-43 land.)

---

## Promotion logic

The construct moves from `de_promoted_static` (current state) to `candidate_dynamical_blanket` on the conjunction:
- exp 41 PASS or PARTIAL (probed-direction shows blanket-like dynamical structure), **OR**
- exp 42 PASS (some learned partition satisfies the dynamical blanket condition);
- exp 43 PASS (the partition is realized in the attention graph as connectivity asymmetry).

The construct moves to `accepted_dynamical_blanket` only if exp 44 also passes (multi-layer composition holds).

If exp 41 and exp 42 both FAIL, the dynamical reframe is also empirically refuted at the residual-stream layer of trained LLMs. The construct then either lives at a different system (cf. Hipólito's brain examples) or doesn't exist as an LLM-recoverable structure.

---

## What this design does not do

- It does not run any experiment. Pre-registered thresholds, not findings.
- It does not promise success of the dynamical reframe. The static frame failed comprehensively; the dynamical frame may also fail.
- It does not replace `experiments_33_40_design.md`. It supplements it with the corrected operational test per Hipólito et al.

---

## File layout

```
markov_object_research/
├── experiments_41_44_design.md          (this document)
├── experiments/
│   ├── 41_dynamical_blanket_identity.py
│   ├── 42_learned_partition_blanket.py
│   ├── 43_connectivity_asymmetry.py
│   └── 44_multilayer_blanket_nesting.py
└── results/
    ├── 41_dynamical_blanket_identity/
    ├── 42_learned_partition_blanket/
    ├── 43_connectivity_asymmetry/
    └── 44_multilayer_blanket_nesting/
```
