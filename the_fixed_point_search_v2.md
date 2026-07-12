# The Critical-Surface Search
## A Computational Research Programme for the Emergent Stack — v2

*Dimitar Popov*

---
epistemic_status: research-programme specification; the RG picture used throughout is the established Wilsonian account; the claim that a Stratum-0 rule sits on a locatable critical surface is a declared conjecture; the proton–electron mass ratio is the programme's single empirical-exposure-point
---

## Digest of This Cut

This cut supersedes *The Fixed-Point Search* (v1). Three of v1's arguments rested on a single error — treating the renormalisation-group fixed point as a contracting attractor in the sense of the Banach fixed-point theorem — and all three are rebuilt here.

1. **Existence.** v1 claimed the existence of the physical fixed point was "guaranteed under mild conditions" because the RG operator is a contraction near it. That claim is withdrawn. Physically interesting RG fixed points are saddle points of the flow, with expanding directions; no contraction argument applies, and existence must be established case by case **(established result)**.
2. **The search gradient.** v1 ranked candidate rules by how quickly they stopped moving under coarse-graining — a proximity measure that assumes flow *toward* the target. The generic flow near a critical fixed point runs *away* from it along its relevant directions **(established result)**. The search target is rebuilt as the critical surface separating phases, located by bisection between rules that flow to different trivial endpoints — the standard numerical method for finding criticality.
3. **The cheap screen.** v1's first filter discarded any rule that moved under a few coarse-graining steps. That filter is biased against exactly the rules sought: everything off a fixed point moves, including every point of the critical surface. It is replaced by a sensitivity screen — retain rules whose flow endpoint is sensitive to small perturbations of the rule, because endpoint sensitivity is the signature of a nearby phase boundary.

Two further corrections: the Standard Model is not at an RG fixed point, and v1's statement implying otherwise is repaired; and v1's "fixed points are the primes of rule space" analogy is demoted to explicit metaphor, because RG flows partition rule space into basins rather than factorisations.

What survives from v1 unchanged in substance: the intractability of brute-force search, the CDT spectral-dimension target (with one slip repaired), the Ray/JAX/TRG computational architecture (retargeted), the coarse-graining-operator bottleneck, and the 1836.15 exposure point.

---

## Abstract

The Constraint-Emergence Ontology proposes that physical reality is a deterministic constraint network whose large-scale structure emerges through successive coarse-graining. The missing piece is a computational strategy for finding a Stratum-0 rewriting rule that produces our physics.

Brute-force simulation of candidate rules is intractable. The Wilsonian renormalisation group offers a tractable alternative, but only if its actual structure is respected: the fixed points that control non-trivial large-scale physics are critical saddle points, reached by tuning to a critical surface, never by generic flow **(established result)**. The search problem is therefore the location of critical surfaces in rule space — the boundaries between basins of attraction of trivial endpoints — followed by classification of the fixed points that control them.

This paper specifies that programme: a massively parallel phase-mapping of hypergraph rewriting rules, a sensitivity screen for rules near phase boundaries, bisection between phases to locate critical surfaces, and classification of the controlling fixed points by physical invariants, with the proton–electron mass ratio as the terminal falsifiability criterion **(empirical-exposure-point)**.

The outer loop is embarrassingly parallel (Ray, CPU cluster). The inner coarse-graining step is GPU-accelerated tensor computation (JAX/TRG). The mathematical bottleneck is unchanged from v1: the rigorous definition of the coarse-graining operator for hypergraph rewriting rules.

---

## Part I: The Search Problem

### 1.1 Why Brute Force Fails

The space of hypergraph rewriting rules is vast. Wolfram's enumeration up to 3-node rewrites yields on the order of 10^6 to 10^8 candidates after symmetry reduction. For each candidate, checking whether it produces correct physics requires long simulation runs, spectral-dimension measurement, stability analysis of persistent structures, and comparison against a conjunction of observational criteria. Each evaluation is expensive, and the evaluations do not inform one another: if rule R₁₄₇ almost works and R₁₄₈ fails completely, brute force learns nothing from the near-success. The search has no gradient.

### 1.2 What the Renormalisation Group Actually Offers

The Wilsonian renormalisation group organises theories by their behaviour under coarse-graining **(established result)**. Its structure, stated honestly, is this:

Coarse-graining defines a flow on the space of theories. Almost every starting point flows to a *trivial* endpoint — in statistical-mechanics language, the fully ordered or fully disordered phase; in rule-space language, the frozen graph, the empty graph, or unbounded structureless growth. These trivial endpoints are the stable attractors of the flow, and they are physically empty.

The interesting fixed points — the ones controlling scale-invariant, structured physics — are different objects. A critical fixed point such as Wilson–Fisher has both irrelevant directions (eigenvalues of the linearised flow inside the unit circle, contracting) and at least one *relevant* direction (eigenvalue outside the unit circle, expanding) **(established result)**. It is a saddle. A system placed near it does not fall in; it is expelled along the relevant direction toward one of the trivial attractors. Reaching such a fixed point requires *tuning*: the relevant couplings must be set exactly on the fixed point's stable manifold — the **critical surface**. In the laboratory this is the experimentalist tuning temperature to T_c. Nothing flows to criticality on its own; criticality is the boundary between the things that flow elsewhere.

This inverts v1's central operational assumption. v1 treated "close to the fixed point" as a condition the flow improves. The established picture is the opposite: the flow degrades it, exponentially, along every relevant direction. Any search procedure built on "run the flow and keep what converges" collects the trivial attractors and discards the critical physics.

The correct consequence for search is equally standard. The critical surface of a fixed point with *k* relevant directions has codimension *k* in theory space. For *k* = 1 the surface is a wall between two basins: rules on one side flow to one trivial endpoint, rules on the other side to a different one. Walls between basins are *locatable* even though they have measure zero, because membership in a basin is cheap to test — run the flow, see where it lands — and the wall can then be found by bisection **(established result; this is the standard numerical method for locating criticality)**. That is the tractable structure the RG offers, and it is what this programme is built on.

### 1.3 Universality, Correctly Stated

What survives fully intact from the Wilsonian picture is universality **(established result)**: every point on a given critical surface flows, *within* the surface, to the controlling fixed point, and therefore shares its large-scale behaviour — critical exponents, scaling dimensions, symmetry structure. The universality class is the critical surface, and it is characterised by a small number of parameters rather than by any microscopic rule. The Wilsonian bargain therefore still holds: we do not need the exact Stratum-0 rule; we need its universality class. What changes is only where that class lives — on a tuned boundary between phases, never at the bottom of a generic flow.

v1 called non-trivial fixed points "the primes of rule space" and invoked a Fundamental-Theorem analogy in which every rule flows to a unique irreducible fixed point. That analogy is hereby demoted to explicit metaphor, and a limited one: RG flows partition rule space into *basins*, a rule's endpoint depends on which side of each critical surface it starts on, and there is no factorisation structure and no uniqueness of the "flows to a unique fixed point" kind. The sieve intuition — eliminate cheaply, certify expensively — survives as a description of the filter pipeline, and nothing more.

### 1.4 The Standard Model Is Not at a Fixed Point

v1 stated that "the physical universe's effective theories are all at or near RG fixed points." That statement is repaired here.

QCD is asymptotically free: its coupling flows to the trivial Gaussian fixed point in the ultraviolet **(established result)**. The U(1) hypercharge coupling runs the other way, growing toward a Landau pole at inaccessibly high energy **(established result at the level of perturbation theory)**. Every observed coupling runs with scale; that running is measured. The Standard Model as observed is not scale-invariant and is not sitting at a fixed point of anything.

The honest formulation of the target: the question is what *UV completion* the Standard Model plus gravity flows down from. Asymptotic safety — the proposal that gravity possesses a non-trivial UV fixed point with a finite-dimensional critical surface — is a live candidate with supporting functional-RG computations and no proof **(conjecture, contested)**. This programme's thesis is structurally parallel: that there exists a critical fixed point in hypergraph-rule space whose universality class, flowed down through the strata, yields our effective physics. That thesis inherits the same hedged status **(conjecture)**, and this paper keeps the hedge visible throughout.

### 1.5 Self-Bounding Closure, Restated

Within the CEO framework, the self-bounding closure condition — the requirement that the constraint network's gap-structure reproduce itself under coarse-graining — is the RG fixed-point condition stated ontologically: the effective theory at the coarse-grained level is the same theory, up to rescaling **(theorem-within-set: the identification follows from the framework's definitions of closure and coarse-graining)**.

v1 then claimed the existence of such a fixed point was guaranteed by the Banach fixed-point theorem under mild contraction conditions. That claim is withdrawn without replacement. The Banach theorem requires a contraction on a complete metric space; the linearised RG flow at any critical fixed point has expanding eigenvalues, so the operator is not a contraction on any neighbourhood of the object sought, and the theorem's hypotheses fail exactly where they were needed. No general existence guarantee is currently available. Existence of the specific fixed point this programme targets is part of the conjecture, to be established — if at all — the way Wilson–Fisher was: by controlled approximation and numerics, case by case.

The closure condition does retain one honest additional role. A rule sitting *on* a critical surface is a measure-zero circumstance, and the framework owes an account of why Stratum 0 would occupy it. Self-bounding closure, read as a selection principle — only self-consistent-under-coarse-graining configurations persist as substrates for emergence at all — is the framework's candidate account **(conjecture; the framework's central one)**. The computational programme does not assume this principle. It searches for the surface regardless, and the principle stands or falls with what is found.

---

## Part II: What the Target Must Produce

The physical universality class, once located, must yield the following. Statuses are marked per claim, because they differ sharply.

**Geometric targets (from the causal structure of the fixed-point theory):**

- Spectral dimension running from ≈ 2 near the discreteness scale to ≈ 4 at large scales. This is the signature result of Causal Dynamical Triangulations **(established numerical result within CDT)**. One slip in v1 is repaired here: the spectral dimension is a single scale-dependent number extracted from random-walk return probabilities. It does not decompose into spatial and temporal parts, does not fix the metric signature, and does not by itself certify 3+1 structure or Lorentz invariance. Matching d_s(t) is a necessary check; signature and Lorentz structure require separate, harder diagnostics.
- Lorentz invariance of the emergent metric, tested directly on the emergent light-cone structure **(necessary condition from observation; the test design is open work)**.
- de Sitter-like behaviour at the largest scales **(necessary condition from observation)**.

**Quantum targets (from the branchial structure):**

- Causal invariance, so that the branchial graph is well-defined independent of rule-application order **(necessary condition within the framework)**.
- A natural measure on branchial branches reproducing Born statistics **(conjecture, contested; this is Gap 1 of *The Emergent Stack*, the Markov-quotient proposal, and it remains unproven)**.
- Entanglement entropy consistent with Ryu–Takayanagi in the appropriate limit, via the conjectured MERA–CDT correspondence **(conjecture, contested)**.

**Matter targets (from stable persistent structures):**

- Two or more classes of stable particle-like structures.
- A fixed-point symmetry structure containing SU(3)×SU(2)×U(1), on the Connes finite-algebra route **(conjecture, contested; Gap 2 of *The Emergent Stack*)**.
- Characteristic-scale ratio of the two simplest stable structures equal to 1836.15 **(empirical-exposure-point; Part V states why this number, of all numbers, is the honest one to stake)**.

---

## Part III: The Corrected Search

### 3.1 The Three Rebuilt Moves

**Existence: dropped.** The programme carries no existence theorem and pretends to none. No weakened substitute is offered either. Phase 1 is designed so that its earliest deliverable — the phase map — is informative even if no non-trivial critical surface exists in the searched rule space: that outcome is itself a falsification result at the searched complexity bound (§5.2).

**The gradient: from convergence speed to bisection depth.** v1's proximity measure — rank rules by how few coarse-graining steps they need to stop moving — selects for rules already deep in trivial basins, since those are the rules that stop moving fastest. The corrected search quantity is *basin membership*, which is cheap: run the flow, classify the trivial endpoint (frozen / empty / divergent / other). The corrected gradient is *bisection*: given rules R_A and R_B landing in different basins, parametrise a path between them (in the coupling-tensor representation, a linear interpolation suffices; in discrete rule space, a lattice path through single-edit neighbours), and bisect on the endpoint classification. Each bisection step halves the bracket; convergence to the critical surface is exponential in evaluations **(established method)**. A point on the surface, flowed *within* the surface (numerically: flowed while re-tuning the bracket at each step, the standard shooting technique), approaches the controlling fixed point, whose linearised flow then yields the eigenvalue spectrum — the relevant/irrelevant classification and the critical exponents that name the universality class.

**The screen: from stillness to sensitivity.** v1's Miller-Rabin-style filter — apply k random coarse-graining steps, discard anything that moved — is replaced by its near-opposite. The cheap first-pass screen now retains rules whose flow *endpoint* is sensitive to small perturbations of the rule: perturb R to R+δ several times, run short flows, and flag R when the perturbed copies land in different trivial basins. Endpoint sensitivity under small perturbation is the signature of a nearby basin boundary, hence of a nearby critical surface. Rules deep inside a single basin — the overwhelming majority — are insensitive and are discarded cheaply. The rules v1's screen would have kept (moved least) and the rules this screen keeps (most boundary-sensitive) are close to disjoint sets; this is the concrete measure of how wrong the v1 filter was.

### 3.2 Data Flow

```
enumerate_rules(max_complexity)
        │
        ▼
    [R₁, R₂, ..., Rₙ]                    ← millions of candidates
        │
        │  (Ray: distribute across workers)
        ▼
classify_endpoint(Rᵢ)                    ← CHEAP: short flow, label trivial basin
        │                                   (frozen / empty / divergent / other)
        ▼
sensitivity_screen(Rᵢ, m perturbations)  ← CHEAP: do perturbed copies of Rᵢ
    │                                       land in different basins?
    ├── insensitive → discard (~large majority eliminated)
    └── sensitive   → near a phase boundary; keep
            │
            ▼
   pair_across_basins(kept rules)        ← adjacent rules with different endpoints
            │
            ▼
   bisect_to_surface(R_A, R_B)           ← exponential convergence to the
            │                               critical surface; JAX/GPU inner loop
            ▼
   flow_within_surface → fixed point R*  ← shooting method; then linearise:
            │                               eigenvalues → relevant directions,
            │                               critical exponents, universality class
            ▼
   compute_invariants(R*)
            ├── spectral-dimension profile wrong → discard
            ├── no causal invariance            → discard
            ├── quantum/matter targets          → filter (contested-conjecture
            │                                     checks flagged as such)
            ▼
   measure_mass_ratio(R*)  →  compare to 1836.15
```

The pipeline remains a sieve — cheap elimination first, expensive certification last — with the two cheap stages rebuilt as described.

### 3.3 Two-Level Parallelism (Retained from v1, Retargeted)

The architecture survives the correction intact, because it never depended on what was being computed per rule.

**Level 1 — across rules and across bisection paths (embarrassingly parallel, CPU cluster).** Endpoint classification and the sensitivity screen are pure maps over the rule set; each bisection is an independent job over a rule pair. Ray or Dask distributes; no shared state. The one structural change: the unit of expensive work is now a *bisection path* rather than a single rule's convergence run, and paths are generated dynamically from the screen's survivors — a two-stage map rather than a single map, which Ray handles natively.

**Level 2 — within a coarse-graining step (GPU, JAX).** Unchanged. The coarse-graining step is a tensor contraction with truncation to bond dimension D — the Tensor Renormalisation Group operation **(established method in condensed-matter computation)** — running in milliseconds per step on a modern GPU. Bisection multiplies the number of short flows required per surviving candidate by a factor of order log(1/ε); the sensitivity screen's aggressive early elimination is what keeps the total budget comparable to v1's estimates.

### 3.4 The Mathematical Bottleneck (Unchanged)

The entire programme still depends on a rigorous coarse-graining operator CG_λ for hypergraph rewriting rules — Problem 3c of *The Emergent Stack*: defining constraint density, and hence blocking, on a substrate with graph adjacency and no geometry. The candidate definition (block by constraint-topology distance; extract the rule best reproducing inter-block dynamics) and the three correctness properties carry over from v1 verbatim:

1. **Consistency:** CG_λ ∘ CG_μ = CG_{λμ}
2. **Monotonicity:** information is lost, never gained, per step
3. **Correctness:** applied to a known lattice theory, CG_λ reproduces that theory's known RG flow

Property 3 remains the validation test, and it gains force under the corrected picture: the known flows it must reproduce include known *critical* fixed points and their exponents (2D Ising under TRG is the canonical benchmark), which directly exercises the saddle-point structure this programme searches for. Phase 1 proceeds with approximate block-spin coarse-graining before the rigorous operator exists; the approximation suffices for basin classification and phase mapping, which is all Phase 1 needs.

---

## Part IV: Research Phases

**Phase 1 — Phase Map (Months 1–4).** Enumerate rules to complexity ≤ 3 (adapting Wolfram's open-source enumeration); classify every rule's trivial endpoint under approximate coarse-graining; run the sensitivity screen; deliver the *phase diagram of rule space* — the basins, their boundaries' approximate locations, and the census of boundary-sensitive rules. Requires engineering and textbook block-spin methods; requires no new mathematics. Note the corrected success criterion: Phase 1 succeeds by mapping basins, and a map showing *no* non-trivial boundaries is a reportable falsification result at this complexity bound.

**Phase 2 — Rigorous Operator (Months 3–9, overlapping).** Define CG_λ rigorously; prove or disprove properties 1–3 for TRG-style coarse-graining on hypergraph coupling tensors; validate against 2D Ising and lattice-QCD benchmark flows, including recovery of known critical exponents. This is the research problem.

**Phase 3 — Surface Location and Classification (Months 8–18).** Bisect to the critical surfaces bracketed in Phase 1, using the rigorous operator; flow within-surface to the controlling fixed points; linearise and extract eigenvalue spectra; classify universality classes; apply geometric filters (spectral-dimension profile, causal invariance, Lorentz diagnostics).

**Phase 4 — Physical Tests (Months 16–24).** For surviving classes: branchial-measure analysis against Born statistics **(contested-conjecture check, reported as such)**; stable-structure identification; mass-ratio measurement against 1836.15.

Compute estimates carry over from v1 within a small factor (bisection overhead offset by cheaper screening): Phase 1 at complexity ≤ 3 in the low thousands of dollars of cloud time; complexity ≤ 4 requires dedicated cluster access. The software stack is unchanged — Python, Ray/Dask, NetworkX, JAX-based TRG, nauty/traces — and the reusable prior art (Wolfram Physics Project enumeration code, open-source TRG libraries, CDT spectral-dimension code) is unchanged.

---

## Part V: The Exposure Point

### 5.1 Why 1836.15

The proton–electron mass ratio is the programme's terminal test **(empirical-exposure-point)**, and it is worth stating exactly why it would be remarkable to derive.

The two masses come from different sectors of the Standard Model. The proton mass is overwhelmingly Λ_QCD in origin — generated by dimensional transmutation and confinement, with the quark Yukawa contributions a small correction **(established result)**. The electron mass is a Higgs Yukawa coupling, a free parameter of the theory with no accepted explanation **(established result)**. Within known physics the ratio 1836.15 therefore ties together two numbers that have *no common origin*: one emerges from non-perturbative gauge dynamics, the other is an unexplained input. A universality class whose two simplest stable structures exhibited this ratio — without the number appearing anywhere in the rule — would be deriving a cross-sector coincidence that the Standard Model treats as brute fact. The number is dimensionless, measured to better than six significant figures, and structurally beyond the reach of parameter-fitting within the framework, which is what qualifies it as the exposure point rather than a demonstration target.

### 5.2 Checkpoints, Corrected

| Checkpoint | What it tests | What failure means |
|---|---|---|
| Non-trivial critical surfaces exist in searched space | The conjecture's minimal precondition | No critical physics at this complexity bound; raise the bound or revise |
| Spectral-dimension profile 2 → 4 | Geometric structure of the controlling fixed point (necessary; does not certify signature or Lorentz structure) | Wrong geometry; class eliminated |
| Direct Lorentz/light-cone diagnostics | Emergent relativistic structure | Framework needs revision at the geometric stratum |
| Born-statistics branchial measure | The Markov-quotient conjecture (contested) | Gap 1 proposal wrong; quantum stratum account fails |
| Symmetry structure ⊇ SU(3)×SU(2)×U(1) | The Connes route (contested) | Gap 2 proposal wrong; matter stratum account fails |
| Mass ratio 1836.15 | The full conjecture | The conjecture is false as computed, or the rule space is too small, or the operator is wrong |

Each row is a go/no-go decision, and the contested-conjecture rows are labelled so that their failure is charged to the right claim: a Born-measure failure falsifies the Markov-quotient proposal and does not by itself falsify the constraint-network substrate.

### 5.3 On Uniqueness

v1 posed fixed-point uniqueness as a theorem target, backed by the prime analogy. With the analogy demoted, the honest residue is this: multiple universality classes passing the geometric filters may exist, and if more than one passes every filter, the question "why this class?" becomes a genuine open selection problem for the framework **(the framework's Type-1 mystery classification applies)**. A uniqueness theorem — that the observed invariants over-determine a single class — remains a legitimate mathematical target, structurally parallel to the Connes finite-algebra uniqueness programme **(conjecture, contested)**. No part of the computational search assumes it.

---

## Conclusion

The programme survives its own audit, and it is sharper for it. The substrate thesis needs no contraction theorem, and the search needs no rule that obligingly flows to the answer. What the established RG picture supplies is harder-edged and sufficient: trivial endpoints that are cheap to classify, phase boundaries that bisection locates at exponential rate, universality classes that make the microscopic rule irrelevant, and eigenvalue spectra that name what has been found. The claim that one of those classes is ours — that a Stratum-0 rule sits on a locatable critical surface whose fixed point projects down to our physics — is the conjecture this programme exists to expose **(conjecture)**, and 1836.15 is where it is exposed **(empirical-exposure-point)**.

The one unsolved mathematical piece is unchanged: the rigorous coarse-graining operator for non-spatial hypergraphs. Everything else is engineering, and the engineering is standard. Phase 1's phase map is informative in every outcome, including the null one.

The stack is real as a proposal. Whether any critical surface in rule space carries our physics is exactly what the computation is for.

---

## Appendix: Open Problems as Research Tasks

| Open Problem (CEO System Specification §X) | Phase | What resolution looks like |
|---|---|---|
| Discrete/continuous gap | 3 | Spectral-dimension crossover in the fixed-point causal graph |
| Constraint density metric | 2 | Rigorous ρ_c definition satisfying properties 1–3 |
| Constant derivation | 4 | 1836.15 from fixed-point structure |
| Three generations | 4 | Hilbert-space dimension of the fixed-point symmetry algebra |
| Self-bounding closure | 2–3 | Case-by-case existence of the targeted critical fixed point (no general theorem claimed) |
| Inverse projection problem | 3 | Identification of a CG_λ consistent with all observed spacetime properties |

---

*Part of the Constraint-Emergence Ontology series. Supersedes* The Fixed-Point Search *(v1). Forthcoming on Zenodo.*
*Series: [Constraint-Emergence Ontology — 10.5281/zenodo.18573722](https://zenodo.org/records/18573722)*
