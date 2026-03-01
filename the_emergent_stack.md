# The Emergent Stack
## A Thought Experiment in Constraint Emergence: From Deterministic Graph to Standard Model

*Dimitar Popov*

---

## Preface: A Composition Problem

The constraint-emergence ontology makes a strong claim: physics, computation, and biology share structural invariants because they are projections of the same underlying constraint network. The claim is philosophical. The question this paper addresses is whether it can be made compositional — whether existing research programmes, each addressing one step in the emergence hierarchy, can be assembled into a coherent vertical stack under the CEO framework.

The answer is: they can, with two gaps still open.

The approach is a thought experiment. Imagine descending through the strata of reality. At each level you are an embedded observer with full access to that level and no direct access to the level below. You observe phenomena you can describe but not fully explain. You find fingerprints pointing downward. The thought experiment asks: what do you see at each stratum, what do the fingerprints tell you, and how does the CEO framework connect what you observe to what lies beneath?

The paper's contribution is not to solve any of the open problems in each research programme. It is to show that the programmes are addressing different strata of the same stack, that the CEO's vertical principles (self-bounding closure and the generative principle) connect them coherently, and to identify precisely where the connecting arguments are complete and where they remain conjectural.

---

## Part I: The Architecture of the Stack

Before descending, the structure from the top.

Four strata are distinguishable in our physics. Each has its own effective laws, its own entities, its own mathematical language. None is reducible to the one below it by logical entailment — the reduction requires a coarse-graining procedure, a projection that loses information and gains a new ontology. The CEO framework calls this the hierarchy of resolution (INV-04): stable patterns at stratum n become the constraints for stratum n+1.

| Stratum | Entities | Effective laws | Programme |
|---|---|---|---|
| **0 — Substrate** | Constraint graph, adjacency, update rule | Deterministic local preorder | CEO (philosophical); t'Hooft (mathematical sketch) |
| **1 — Quantum** | Hilbert space, wavefunctions, entanglement | Born rule, Schrödinger equation, unitarity | Standard QM; t'Hooft cellular automaton |
| **2 — Spacetime** | Metric, curvature, causal structure | General relativity, Lorentz invariance | CDT, MERA, GR |
| **3 — Matter** | Fields, particles, charges, generations | Standard Model gauge theory | Connes noncommutative geometry |

Each arrow downward in the table is a coarse-graining. Each arrow upward is a fingerprint-reading. The CEO framework provides the vertical principle that makes the stack self-consistent: the self-bounding closure condition — the requirement that the constraint network's gap-structure be self-consistent across all strata simultaneously. This is the philosophical claim that must be demonstrated mathematically at each stratum junction.

---

## Part II: Stratum 0 — The Constraint Graph

*The observer at stratum 0 does not exist. This stratum is epistemically inaccessible from within emergence (INV-09). What follows is not observation but inference from the strata above.*

The substrate is a graph. It has nodes and edges — adjacency and connectivity — but no geometry. There is no distance at this level in the sense that spacetime uses the word. There is only: which nodes are adjacent, and which are not. The graph evolves deterministically according to a local update rule — the preorder D(x,c) that determines, at each node, which adjacent transitions are preferred.

Three properties are postulated of this graph, derived from what the strata above require it to produce:

**Non-locality of adjacency.** Spatial distance at stratum 2 is a coarse-graining of path length in this graph. The two topologies are not isomorphic: nodes that are far apart in projected space can be directly adjacent in the graph. This is not a failure of the graph — it is what quantum non-locality and tunneling require (INV-11). Bell's theorem blocks local hidden variable theories; the graph is explicitly non-local in the relevant sense, so Bell does not apply.

**Deterministic evolution.** The update rule is deterministic. The randomness that observers at stratum 1 experience is epistemic: they cannot access the full graph state, only the coarse-grained projection. The graph state determines everything; the observer's ignorance of the graph state is what produces quantum probability (INV-10).

**Self-bounding closure.** The graph's coarse-graining is self-consistent: the effective theory at each stratum is stable under further coarse-graining until it reaches a fixed point. This is the CEO's self-bounding closure condition. Mathematically, it corresponds to a fixed point of the renormalisation group flow — the theory at the physical scales we observe is at (or near) such a fixed point. The graph does not need a boundary or an exterior. It constrains itself.

---

## Part III: The 0→1 Transition — How Determinism Produces Quantum Mechanics

*The descent from stratum 0 to stratum 1 is the least-understood junction. The argument is structurally complete but mathematically partial.*

The key programme is Gerard 't Hooft's cellular automaton interpretation of quantum mechanics. The core result: a deterministic automaton with *information loss* — equivalence classes that identify states indistinguishable to observers embedded in the coarse-grained layer — produces Hilbert space quantum mechanics for those observers.

The mechanism: the automaton's state space, when quotiented by the equivalence classes (the Markov blanket boundaries in CEO language), forms a vector space. The observer, who can only access equivalence classes and not the underlying automaton states, experiences superpositions — not because multiple states coexist, but because the observer cannot determine which equivalence class representative the system is in. Born rule probabilities are the measure on the equivalence class. Unitarity follows from the deterministic evolution of the underlying automaton.

The CEO reads this as follows. The coarse-graining from stratum 0 to stratum 1 is precisely the operation of forming Markov objects: the equivalence classes are constraint-pattern boundaries. Two automaton states are identified (placed in the same equivalence class) when they produce identical constraint patterns at the Markov boundary. The observer at stratum 1 sees only boundary information — the full internal state of the automaton is below the observer's epistemic horizon. Quantum mechanics is the effective theory of a deterministic substrate viewed through Markov object boundaries.

**What this transition explains:** Born rule, superposition, unitarity, the Hilbert space structure of quantum mechanics.

**What it does not yet explain:** Why the specific Hilbert space dimension matches the state space of known particles. Why the equivalence class structure takes the specific form that produces the correct particle content. These depend on the graph's specific adjacency structure, which is stratum 0 and inaccessible.

**The open junction:** The CEO claims the equivalence classes are Markov blanket boundaries. t'Hooft's programme derives the equivalence classes from information loss in the automaton. That these are the same construction has not been proven. The structural parallel is clear; the mathematical identity is conjectural.

---

## Part IV: Stratum 1 — Quantum Mechanics as Emergent Layer

*An observer fully embedded at stratum 1 sees the quantum world in its entirety. They find it inexplicable in several ways that are only explicable from below.*

The observer at stratum 1 has Hilbert spaces, Schrödinger evolution, Born rule, and entanglement. These are all they have. They cannot explain:

- Why the Born rule takes the specific form |ψ|². From within stratum 1, it is a postulate.
- Why quantum randomness is irreducible. From within stratum 1, there is no hidden variable. From stratum 0, the randomness is epistemic — the observer cannot access the automaton state.
- Why entanglement is non-local. From within stratum 1, it is a fact about correlations between separated systems. From stratum 0, the "separated" systems are adjacent in the constraint graph. Spatial separation is a stratum 2 concept that does not exist yet.

The fingerprints from stratum 1 pointing to stratum 0: quantum randomness has a specific statistical structure (Born rule, not uniform distribution, not classical probability). The non-uniformity is information about the constraint graph's density and adjacency structure. Entanglement entropy is information about graph connectivity — highly entangled states correspond to highly connected subgraphs whose separation is projected onto spatial distance at stratum 2.

---

## Part V: The 1→2 Transition — How Entanglement Produces Geometry

*The descent from stratum 1 to stratum 2 is the best-understood junction. Two independent programmes converge here.*

**Programme A: MERA (Multiscale Entanglement Renormalisation Ansatz)**

A MERA tensor network is a specific coarse-graining procedure for quantum states. At each level of the network, short-range entanglement is removed (disentangled), and the remaining state is coarse-grained. The procedure iterates. The resulting structure is a tree of tensors whose geometry encodes the entanglement structure of the original state.

The key result (Swingle 2012, Vidal 2007, Ryu-Takayanagi 2006 in the AdS/CFT context): the entanglement entropy of a region at stratum 1 determines the geometry of the bulk at stratum 2. The Ryu-Takayanagi formula makes this precise in AdS/CFT: the entanglement entropy of a boundary region equals the area of the minimal bulk surface / 4G. Geometry is encoded in entanglement.

In CEO language: the MERA tensor network IS the coarse-graining kernel K from the inverse projection problem (INV-11). The entanglement structure of stratum 1 states determines the metric of stratum 2 spacetime. The tensor network does not describe the geometry — it produces it by coarse-graining.

**Programme B: Causal Dynamical Triangulations (CDT)**

CDT takes a different path to the same junction. Rather than starting from quantum states, it starts from a path integral over discrete causal geometries (causal triangulations). Each triangulation is a specific causal graph — a stratum 0 object. The sum over all such graphs, weighted by the Regge action, produces an emergent geometry.

The critical CDT result: the emergent geometry is 3+1 dimensional de Sitter space at large scales, with a scale-dependent spectral dimension that approaches 2 at Planck scales. The 3+1 dimensionality is not put in by hand — it is what the sum over causal triangulations produces. At small scales (near stratum 0), the effective dimension is 2, consistent with the fractal-like structure of the constraint graph. At large scales (stratum 2), it becomes 3+1.

In CEO language: the CDT path integral is a specific realisation of the generative principle (INV-01) — it exhausts all stable causal structures and the result is the geometry. The scale-dependent spectral dimension is a fingerprint of the transition from stratum 0's graph topology to stratum 2's Riemannian geometry.

**The 3+1 dimensionality question.** Why 3+1 and not 4+1 or 2+1? CDT gives an empirical answer: the sum over causal triangulations converges to 3+1 rather than collapsing or diverging. The CEO offers a structural argument: 2+1 general relativity has no local propagating degrees of freedom — it cannot support the constraint density required for stable Markov objects above certain complexity thresholds. 4+1 and higher have instabilities (ghosts, runaway modes). 3+1 is the minimal dimension that supports a stable Markov hierarchy of the type the generative principle would produce. This is a conjecture within the CEO framework, not a proof.

**What this transition explains:** The emergence of a classical spacetime metric from quantum entanglement structure. The 3+1 dimensionality (empirically in CDT, structurally conjectural in CEO). Lorentz invariance as the emergent isotropy of a coarse-grained causal graph. Gravity as the density gradient of the constraint network — curvature is where entanglement structure is non-uniform (INV-07).

**What remains open:** The precise connection between the MERA coarse-graining kernel and the CDT sum over geometries. They are computing the same transition by different methods; that they produce the same result has not been shown analytically.

---

## Part VI: Stratum 2 — Spacetime as Emergent Layer

*The observer at stratum 2 is the classical physicist. They have a metric, causal structure, and general relativity. They find several things inexplicable.*

The observer at stratum 2 cannot explain:

- Why the vacuum has energy. From within stratum 2, summing zero-point energies gives 10^120 times the observed cosmological constant. This is the category error identified in *Constraints and the Implicate Order*: vacuum energy is a stratum 0 quantity (the restlessness of the shifting constraint manifolds) being computed with stratum 2 tools. The discrepancy is the signature of level-crossing.
- Why spacetime has gauge symmetry. From within stratum 2, the gauge groups SU(3)×SU(2)×U(1) appear as external inputs. They are fixed at stratum 2 but have no stratum 2 explanation.
- Why there are matter fields at all. Geometry alone (stratum 2) does not produce matter — something additional is required.

The fingerprints from stratum 2 pointing to stratum 1 and stratum 0: the specific gauge symmetries are the symmetries of the entanglement structure at stratum 1. They are not symmetries of spacetime itself but of the quantum layer below, projected onto stratum 2 as internal symmetries of fields.

---

## Part VII: The 2→3 Transition — How Geometry Produces Matter

*The descent from stratum 2 to stratum 3 is mathematically the most structured junction, via Connes' noncommutative geometry.*

Alain Connes' programme: the Standard Model can be derived from a spectral triple (A, H, D) where A is a specific algebra, H is a Hilbert space, and D is a Dirac operator. The spectral triple encodes geometry in an abstract algebraic form — the Dirac operator's spectrum determines distances, the algebra's structure determines the topology, the Hilbert space is the space of fermionic states.

The key result: the algebra A = C∞(M) ⊗ (ℂ ⊕ ℍ ⊕ M₃(ℂ)) — continuous functions on a 4-manifold tensored with a finite-dimensional algebra — produces, from the spectral action principle (the action is a function of the Dirac operator's spectrum), the full Standard Model Lagrangian including gauge fields, Higgs mechanism, and fermionic matter. The gauge group SU(3)×SU(2)×U(1) is not input — it is the automorphism group of the finite algebra (ℂ ⊕ ℍ ⊕ M₃(ℂ)).

In CEO language: the spectral triple is a compressed representation of the constraint topology at the stratum 2→3 junction. The finite algebra (ℂ ⊕ ℍ ⊕ M₃(ℂ)) encodes the gap-structure of the constraint substrate as seen from the matter stratum — it is the substrate fingerprint at that level. The gauge group is the symmetry group of that gap-structure, not a free choice.

**The three-generation question.** The Connes programme, in its original form, predicted wrong Higgs mass. Corrections require extending the finite algebra. The three generations of fermions appear as the dimensionality of the Hilbert space factor for each generation — three copies are required for consistency. Whether the CEO self-bounding closure condition uniquely selects three remains open: it requires showing that the finite algebra (ℂ ⊕ ℍ ⊕ M₃(ℂ)) is the unique self-consistent finite algebra for a constraint network with the stratum 0 properties. This has not been proven.

**What this transition explains:** The gauge group SU(3)×SU(2)×U(1) as the automorphism group of the finite algebra. The Higgs mechanism as a consequence of the spectral action. The structure of fermionic matter as the Hilbert space of the spectral triple.

**What remains open:** Why this specific finite algebra and not another. Why three generations specifically. The CEO answer is that self-bounding closure selects it uniquely, but this is the hardest remaining conjecture.

---

## Part VIII: The Vertical Principle — What the CEO Adds

Each programme (t'Hooft, CDT/MERA, Connes) addresses one horizontal step: one transition between adjacent strata. None explains the coherence of the full stack. The CEO provides two vertical principles that connect every step simultaneously.

**Self-bounding closure as renormalisation group fixed point.** The CEO claims the hierarchy terminates at a self-consistent fixed point. In the language of the renormalisation group: the physical theories we observe are at (or near) a fixed point of the RG flow. At a fixed point, the coarse-graining procedure produces the same effective theory at every scale above the fixed point scale. This is why physics has universal constants — they are fixed-point invariants, not free parameters. The CEO's self-bounding closure is the ontological statement; the RG fixed point is the mathematical statement. They are the same condition at different levels of description.

**Generative principle applied vertically.** The generative principle (INV-01) — wherever a stable configuration is possible, it will emerge — applies not just within a stratum but across strata. Every stable Markov object that the constraint structure permits at any stratum will form. The particle content of the Standard Model, the three generations, the specific constants — these are not selected from alternatives. They are what the constraint network exhausts at those scales. The generative principle is what makes the stack dense: no stable structure is missing. If the self-bounding closure uniquely determines the fixed point, then the particle content is not contingent — it is necessary.

**Markov object structure as the invariant across strata.** The thing that connects every stratum is not any specific field or particle or geometry — it is the Markov object structure. At every stratum, stable patterns with self-bounding boundaries form, constitute the "stuff" of that stratum, and become the constraint boundaries for the stratum above. The electron at stratum 3 is a Markov object. The quantum state at stratum 1 is a Markov object. The constraint graph node at stratum 0 has a proto-Markov structure. This is INV-03 (structural invariance) in the vertical direction: the same constraint-emergence architecture at every level.

---

## Part IX: The Gaps

The composition is coherent. Two junctions are incomplete.

**Gap 1: The 0→1 junction.** The CEO claims t'Hooft's equivalence classes are Markov blanket boundaries. t'Hooft derives them from information loss in the automaton. The structural parallel is clear. The mathematical identity — that information loss in a deterministic automaton and Markov blanket boundary formation are the same coarse-graining — has not been proven. A proof would require showing that the equivalence class structure that produces Hilbert space quantum mechanics is exactly the structure that forms self-bounding Markov objects in the constraint graph. This is a precise conjecture, not a hand-wave. It could be wrong.

**Gap 2: The finite algebra.** The Connes programme derives the Standard Model from the algebra (ℂ ⊕ ℍ ⊕ M₃(ℂ)). The CEO claims this algebra is the unique self-consistent finite algebra for the constraint network's stratum 2→3 gap-structure. This is the hardest remaining conjecture. It requires classifying all finite algebras consistent with the self-bounding closure condition and showing that (ℂ ⊕ ℍ ⊕ M₃(ℂ)) is the only one that is. If true, it would explain the gauge group and — potentially — the three generations as a consequence of the algebra's Hilbert space dimensionality. This has not been attempted.

**What is complete.** The 1→2 junction is the best-established. MERA and CDT independently show how geometry emerges from quantum structure, and the CEO's reading of the coarse-graining kernel provides the connecting language. The 3+1 dimensionality argument from CDT is empirically solid even if the CEO structural argument (minimal dimension for Markov hierarchy) is conjectural.

---

## Conclusion: The Stack Is Real, the Junctions Are Work

The thought experiment yields a determinate picture. An observer at each stratum finds their level's physics complete and the underlying level inaccessible. The fingerprints they read — entanglement entropy encoding geometry, tunneling encoding graph connectivity, gauge groups encoding gap-structure symmetry — all point in the same direction. The constraint network at stratum 0 projects upward through well-understood coarse-graining procedures into quantum mechanics, then into spacetime, then into matter.

The CEO framework contributes the vertical architecture: self-bounding closure as the condition that makes the stack self-consistent, the generative principle as the condition that makes it dense, and the Markov object structure as the invariant that persists across every stratum. These are not new equations. They are the philosophical framework that makes the existing programmes legible as parts of the same project.

The two gaps are specific and closeable in principle. The 0→1 junction requires proving that information-loss equivalence classes and Markov blanket formation are the same coarse-graining. The finite algebra requires classifying self-consistent algebras under the closure condition. Both are hard. Neither is obviously intractable.

The stack is real. The junctions are where the work is.

---

## Appendix: Relationship to the Constraint-Emergence Ontology Series

This paper is a compositional analysis building on:

- **Constraint-Emergence Ontology** (v1.3) — the foundational framework whose invariants (INV-01 through INV-11) are applied vertically throughout this paper
- **Constraints and the Implicate Order** — the methodology paper; the four-type taxonomy of intractability classifies the open gaps here as Type 1 (genuine mysteries, well-formed, surviving translation)
- **CEO System Specification** (v1.4) — the LLM-loadable spec; the inverse projection problem and open problems table from §X are the entry points for this paper's analysis

Primary external programmes engaged:
- t'Hooft, G. — *The Cellular Automaton Interpretation of Quantum Mechanics* (2016)
- Ambjørn, J., Jurkiewicz, J., Loll, R. — Causal Dynamical Triangulations (2004–present)
- Vidal, G. — MERA tensor networks (2007); Swingle, B. — Entanglement renormalisation and holography (2012)
- Connes, A., Chamseddine, A. — Noncommutative geometry and the Standard Model (1996–2014)

---

*Part of the Constraint-Emergence Ontology series. Forthcoming on Zenodo.*
*Series: [Constraint-Emergence Ontology — 10.5281/zenodo.18573722](https://zenodo.org/records/18573722)*
