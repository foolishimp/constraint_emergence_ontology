# Constraint-Emergence Ontology — Concept Index

The Markov blanket of the document set: every concept the framework introduces, defines, or redefines across the core ontology (`constraint_emergence_ontology.md`) and the Political OS Suite (`political_os/`), with its location, dependencies, and status.

---

## Status Key

| Status | Meaning |
|--------|---------|
| **Axiom** | Assumed; rejecting it rejects the framework |
| **Axiom + Empirical** | Assumed foundational; has empirical support |
| **Axiom (within OS)** | Foundational within a specific Political OS specification |
| **Derived** | Follows from axioms and other derived concepts |
| **Derived (with caveat)** | Follows from axioms but with acknowledged bias or limitation |
| **Instantiation** | Domain-specific instance of a more abstract concept |
| **Conjecture** | Testable claim, not yet verified |
| **Interpretive** | Compatible with existing science; no independent test |
| **Definitional** | Naming convention or terminological clarification |
| **Illustrative** | Thought experiment or explanatory device |
| **Empirical finding** | Observed pattern in real-world governance data |
| **Meta** | About the framework itself, not about reality |

---

## I. Foundational Primitives

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 1 | **Constraint** | A condition that determines which transformations are admissible; not a rule dictating what happens next | §0.3 | — | Axiom |
| 2 | **Constraint network** | The fundamental substrate of reality: a self-consistent, evolving system of allowed and forbidden transitions | §1 | 1 | Axiom |
| 3 | **Generative principle** | As soon as a stable configuration is possible within a constraint structure, it will emerge. Emergence is exhaustive, not selective | §0.3 | 1 | Axiom |
| 4 | **Unit of change** | The discrete step by which the constraint network evolves; its scale and character are epistemically inaccessible from within emergence | §10.3 | 2 | Axiom |
| 5 | **Admissible transformation (morphism)** | A transformation permitted by the constraint structure; what things *do*, not what things *are* | §0.1, §0.2, §0.3 | 1 | Axiom |
| 6 | **Structural invariance** | The claim that what persists across substrates is the architecture of admissible change, not the substance undergoing change | §0.1 | 5 | Axiom |

## II. Core Ontological Concepts

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 7 | **Markov object** | Any stable pattern exhibiting conditional independence of internal dynamics from external dynamics given boundary state; substrate-neutral term for Friston's Markov blanket | §2 | 1, 2, 3 | Axiom + Empirical |
| 8 | **Markov blanket (boundary)** | The boundary of a Markov object; screens interior from exterior. Markov object IS a Markov blanket in substrate-neutral vocabulary | §2, §VIII-D | 7 | Definitional |
| 9 | **Constraint manifold** | The full landscape of constraints defining a possibility space; domain-neutral term for the "surface" on which dynamics occur | §0.4, §VIII | 1, 2 | Derived |
| 10 | **Emergent manifold** | A higher-level constraint surface that appears when stable patterns at one level become constraints for the next | §4, §9 | 7, 9, 11 | Derived |
| 11 | **Hierarchy of constraint resolution** | Constraints → stable patterns → new constraints → new patterns; the recursive engine of emergence | §4 | 1, 7, 3 | Derived |
| 12 | **Emergence as quotienting** | Emergence arises not from adding complexity but from coarse-graining: factoring out irrelevant distinctions to reveal new objects and morphisms | §0.5 | 5, 10 | Derived |
| 13 | **Self-bounding hierarchy** | The chain of emergence terminates at a self-consistent base layer that bounds itself | §12 | 2, 11 | Axiom |
| 14 | **Deep determinism** | The constraint network evolves deterministically; apparent randomness arises from epistemic inaccessibility of the full constraint state | §13 | 2, 4 | Axiom |
| 15 | **Local preorder traversal** | The fundamental operation of all computation: at each point, evaluate the local pre-order on the constraint manifold, move in the preferred direction | §VIII-C | 9, 4 | Derived |
| 16 | **Constraint density** | The concentration of constraint structure per region; drives emergent gravitational effects and determines local update rates | §10 | 2, 9 | Derived |

## III. Physics Instantiations

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 17 | **Standing wave / eigenmode** | Stable excitation of the constraint network; what we call "particles" | §2 | 7, 9 | Instantiation of 7 |
| 18 | **Constraint geometry (field)** | A particular sector of the constraint manifold with its own mesh density and topology; what we call "fields" | §3 | 9 | Interpretive |
| 19 | **Collapse / constraint locking** | The moment the constraint structure resolves into a single definite configuration; three components: objective reduction, decoherence, information projection | §6 | 2, 7 | Interpretive |
| 20 | **Nonlocality / global constraint update** | Entangled systems share constraint structure at the substrate level; no signal travels; the correlation already exists in the geometry | §7 | 2, 14 | Interpretive |
| 21 | **Motion / pattern propagation** | Nothing translates through space; the constraint pattern's influence propagates through adjacent network regions; c is the network propagation rate | §8 | 2, 4, 7 | Interpretive |
| 22 | **Spacetime emergence** | Spacetime is the geometric projection of the constraint network at large scales; not fundamental | §9 | 2, 16, 10 | Interpretive |
| 23 | **Scale-dependent time** | Each emergence layer defines its own timescale: the rate at which patterns on that constraint plane update | §9.1 | 10, 4, 11 | Derived |
| 24 | **Gravity as density variation** | Gravity can be described as emerging from constraint density variation; GR's "curvature" and this framework's "density variation" are both descriptions | §10 | 16, 22 | Interpretive |
| 25 | **Hilbert space as compression** | Not fundamental; the most efficient mathematical encoding of global constraint dynamics | §5 | 2, 9 | Interpretive |
| 26 | **Wavefunction as possibility** | Describes the potentiality structure, not substance; the map, not the territory | §5, §6 | 25 | Interpretive |
| 27 | **Constants as emergent invariants** | Physical constants are invariants of stable attractor states of the constraint network, derivable from deeper structure | §11 | 2, 7, 11 | Conjecture |
| 28 | **Variable c** | c is constant in the network (one edge per unit of change) but appears variable in coordinate projection where constraint density varies | §10.4 | 4, 16, 21, 22 | Interpretive |
| 29 | **Nerf ball model** | Thought experiment: constraints as balls of varying size; reality happens in the gaps between them (absential causation as spatial metaphor) | §10.1.1 | 16, 18, 34 | Illustrative |
| 30 | **Higgs as order parameter** | Not fundamental substance; the macroscopic order parameter of a constraint phase that sets stiffness of certain standing-wave modes | §IV | 7, 18 | Interpretive |
| 31 | **Feynman diagrams as topological extrusion** | Propagator lines = information carried along constraint topology; particle identity = topological signature of the channel; vertices = admissibility conditions | §8 | 21, 18 | Interpretive |

## IV. Observer, Meaning, and Evaluation

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 32 | **Observer as Markov object** | The observer has no special ontological status; it is a Markov object evolved within the manifold through constraint dynamics | §18 | 7, 10, 11 | Derived |
| 33 | **Meaning as structural invariant** | Pattern matched against model; the operation is invariant across scales; what changes is the complexity of the constraint space, not the meaning-operation itself | §18 | 7, 32 | Derived |
| 34 | **Absential causation** | Constraints and absences are generative: what is *not* present shapes what emerges (Deacon's term, mapped in his section, not adopted as working vocabulary) | §II (Deacon) | 1, 3 | Derived |
| 35 | **Evaluator-as-prompter** | A simpler system provides direction (constraint signal); a more complex system does the constrained traversal. Brainstem→cortex, human→LLM, specification→builder — same architecture | §18 | 7, 15, 33 | Derived |
| 36 | **Intent / delta** | The computed difference between current state and target state; the mechanism from which directed action arises | §18 | 32, 33 | Derived |
| 37 | **Caring vs meaning** | Meaning = evaluation producing reference (any evaluator). Caring = self-maintaining system acting on the delta (life). Distinct emergences on distinct constraint surfaces | §18 | 33, 36, 43 | Derived |

## V. Information-Driven Construction Pattern

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 38 | **Encoded representation → constructor → constructed structure** | The universal construction pattern operating across biology, SDLC, politics, LLMs, and neuroscience | §V | 1, 7, 11 | Derived |
| 39 | **Abiogenesis insight** | The constructor precedes the specification in every domain. The encoding emerges as the constructor's solution to reliable replication under constraint. Sequence: constraint → constructor → encoding → encoding drives constructor | §V | 38, 3 | Derived |
| 40 | **Encoded representation (specification / encoding)** | The information that constrains what the constructor produces: DNA, requirements, constitutions, prompts, brainstem affect | §V | 38 | Derived |
| 41 | **Constructor (builder)** | The mechanism that reads the encoding and produces structure: ribosome, LLM agent, governance institutions, cortex | §V | 38 | Derived |
| 42 | **Constructed structure (artifact)** | The output: protein, code, law, evaluation, behaviour | §V | 38 | Derived |
| 43 | **Selection pressure (environment)** | The external constraints that test whether the constructed structure survives: users, regulators, predators, runtime | §V | 38, 1 | Derived |
| 44 | **Feedback / deviation signal** | The environment reporting back to the encoding when the artifact fails; the mechanism by which encodings evolve | §V, §VIII-B | 38, 43 | Derived |
| 45 | **Two compute regimes** | Probabilistic (stochastic expansion, mutation) and deterministic (verification contraction, selection). The specification is the fitness landscape | §V | 38, 40 | Derived |
| 46 | **Living encoding** | Requirements as continuously evolving encoding: defines target, compared against runtime, updated on deviation, drives corrective construction | §V | 40, 44 | Derived |

## VI. Emergence Hierarchy (Deacon Alignment)

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 47 | **Dissipative dynamics (homeodynamic)** | Self-organising flow without stable structure; constraint propagation without Markov object formation | §II (Deacon) | 1, 2 | Derived |
| 48 | **Form-producing dynamics (morphodynamic)** | Stable structure emerges directly from constraints; Markov objects form | §II (Deacon) | 7, 3, 47 | Derived |
| 49 | **Self-maintaining dynamics (teleodynamic)** | A Markov object complex enough to preserve its own boundary conditions; the constructor, prior to any encoding. Deacon's "autogen" | §II (Deacon) | 7, 41, 48 | Derived |
| 50 | **Representational dynamics (beyond Deacon)** | The encoding separates from the mechanism; the constructor develops a representation of what it builds. This framework's extension of Deacon's hierarchy | §II (Deacon) | 38, 39, 49 | Derived |

## VII. LLM Correspondence

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 51 | **Direction function D(x,c)** | Maps (semantic state, context) to a direction on the manifold; attention implements this; the LLM's constraint propagation rule | §VIII-A | 9, 15 | Instantiation of 15 |
| 52 | **Soft unification (interference)** | Weighted similarity matching across key-value pairs; continuous analogue of Prolog's discrete unification; constructive/destructive interference | §VIII-A, Appendix | 51 | Instantiation |
| 53 | **Attractor basin / proto-symbol** | Region in activation space where trajectories converge and remain stable; exhibits Markov blanket boundaries; how symbolic-like behaviour emerges from continuous computation | §VIII-A, Appendix | 7, 51 | Instantiation of 7 |
| 54 | **Hallucination as probability degeneracy** | In manifold regions where Markov objects did not form during training, probabilities become degenerate; multiple paths carry equivalent probability; the label belongs to the observer, not the system | §VIII-A | 7, 9, 53 | Derived |
| 55 | **Collapse = sampling** | The model computes a distribution (superposition); sampling collapses it to a specific token (definite outcome); same abstract operation as decoherence | §VIII-A | 19, 51 | Instantiation of 19 |
| 56 | **Truth as stable pattern** | Truth is a Markov object: a pattern that persists under perturbation in a constraint manifold | §VIII | 7 | Derived |
| 57 | **Polysemanticity as incomplete screening** | When Markov objects share neurons (superposition), boundaries overlap and external context leaks through; the failure mode when activation space is too low-dimensional | §VIII-D | 7, 8, 53 | Derived |

## VIII. Formal Programme

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 58 | **Constraint category C** | Abstract category: objects are (S, B, D, σ) tuples; morphisms preserve boundary structure, Markov property, and stability | §VIII-D | 7, 5, 8 | Conjecture (to be axiomatised) |
| 59 | **Physics functor F_phys** | Maps abstract Markov objects to physical bound states (Hilbert/phase space, potential wells, Hamiltonian evolution) | §VIII-D | 58, 17 | Conjecture (largely supportable) |
| 60 | **LLM functor F_llm** | Maps abstract Markov objects to attractor basins in activation space | §VIII-D | 58, 53 | Conjecture (testable) |
| 61 | **Natural transformation η** | Maps each physical Markov object to its LLM representation, preserving morphism structure; what it means for an LLM to "model" a physical system | §VIII-D | 59, 60 | Conjecture |
| 62 | **Conditional independence conjecture** | For a trained LLM, P(A_I \| A_B, A_E) ≈ P(A_I \| A_B), with tolerance ε decreasing with model scale | §VIII-D | 7, 53, 60 | Conjecture (testable now) |
| 63 | **Emergence morphism** | Components → composite whose boundary screens internals from exterior | §VIII-D | 58, 7 | Derived |
| 64 | **Collapse morphism** | Superposition → single object, induced by constraint over-determination | §VIII-D | 58, 19 | Derived |

## IX. Philosophical and Epistemological Commitments

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 65 | **Laws ≠ Physics** | Mathematical descriptions are maps, not territory; mathematical existence does not confer ontological existence | §0.6 (Phil. Foundation) | — | Axiom |
| 66 | **Aristotelian position (potentiality vs actuality)** | Existence requires actualisation; mathematical consistency is necessary but not sufficient for existence | §0.6 (Phil. Foundation) | 65 | Axiom |
| 67 | **Category theory as orientation** | Philosophical stance (morphisms over objects, structure-preservation over identity, quotients over constructions) — not deployed as formalism | §0.2 | — | Meta |
| 68 | **Philosophy as ontology construction** | Storytelling = constrained manifold traversal that constructs new manifolds for future traversal; all frameworks are stories; the question is productivity | §0.7 | 9, 15 | Meta |
| 69 | **Universal computation as ambient space** | The totality of possible processes; this framework asks what is *inhabitable*, not what is possible | §0.4 | — | Meta |
| 70 | **Recursion barrier** | Gödel, Turing, Cantor are one result: self-referential systems cannot fully characterise themselves from within; resolution is always computation from outside | §15 | 15 | Derived |
| 71 | **Edinburgh error** | Confusing "social beliefs shape social reality" with "base reality is also just belief"; the level confusion between social emergent plane and base constraint network | §II (Ladyman & Ross) | 10, 65 | Derived |
| 72 | **Social emergent plane** | At the social level, models running in heads ARE causal forces; beliefs are real constraints on this plane, even though they do not change physics | §II (Ladyman & Ross) | 10, 7 | Derived |

## X. Research Agenda Concepts

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 73 | **Proton-electron mass ratio challenge** | Derive the ratio ~1836 from constraint topology as a concrete test of "constants are emergent" | §III (Research Agenda) | 27 | Conjecture |
| 74 | **Hybrid constraint manifolds** | Engineered systems combining probabilistic expansion (LLM generation) with deterministic contraction (verification); recapitulates physics pattern | §VIII | 45, 9 | Derived |
| 75 | **LLMs as constraint manifold laboratories** | LLMs are empirically manipulable constraint systems; most accessible direction for testing the framework | §IX.6 | 53, 54, 62 | Meta |
| 76 | **World models as functors** | A world model is a functor from a schema category to the LLM category; alignment is whether η commutes | §VIII-D | 61 | Conjecture |

---

## Dependency Graph (Simplified)

```
AXIOMS
  1  Constraint
  2  Constraint network ──────────────────────────────────────┐
  3  Generative principle ("if possible, will emerge")        │
  4  Unit of change                                           │
  5  Admissible transformation                                │
  6  Structural invariance                                    │
  13 Self-bounding hierarchy                                  │
  14 Deep determinism                                         │
  65 Laws ≠ Physics                                           │
  66 Aristotelian position                                    │
                                                              │
CORE DERIVED                                                  │
  7  Markov object ◄── 1 + 2 + 3                             │
  8  Markov blanket ◄── 7                                     │
  9  Constraint manifold ◄── 1 + 2                            │
  10 Emergent manifold ◄── 7 + 9 + 11                        │
  11 Hierarchy of constraint resolution ◄── 1 + 7 + 3        │
  12 Emergence as quotienting ◄── 5 + 10                      │
  15 Local preorder traversal ◄── 9 + 4                       │
  16 Constraint density ◄── 2 + 9                             │
  34 Absential causation ◄── 1 + 3                            │
                                                              │
INFORMATION-DRIVEN CONSTRUCTION                               │
  38 Encoding → constructor → structure ◄── 1 + 7 + 11       │
  39 Abiogenesis insight ◄── 38 + 3                           │
  40-46 Specification, builder, artifact, etc. ◄── 38         │
                                                              │
OBSERVER & MEANING                                            │
  32 Observer as Markov object ◄── 7 + 10                     │
  33 Meaning as invariant ◄── 7 + 32                          │
  35 Evaluator-as-prompter ◄── 7 + 15 + 33                   │
  36 Intent / delta ◄── 32 + 33                               │
                                                              │
EMERGENCE HIERARCHY (Deacon alignment)                        │
  47 Dissipative → 48 Form-producing → 49 Self-maintaining    │
      → 50 Representational                                   │
  Each transition driven by concept 3 (generative principle)  │
                                                              │
PHYSICS INSTANTIATIONS                                        │
  17-31 Standing waves, fields, collapse, gravity, etc. ◄── 7 + 9
                                                              │
LLM INSTANTIATIONS                                            │
  51-57 Direction function, attractors, hallucination, etc. ◄── 7 + 9 + 15
                                                              │
FORMAL PROGRAMME                                              │
  58-64 Category C, functors, conjectures ◄── 7 + 5 + 8      │
                                                              │
POLITICAL OS SUITE                                            │
  77-83  Governance Stack architecture ◄── 7 + 9 + 10 + 11   │
  84-91  Layer 0 (Hardware / Reality OS) ◄── 1 + 7 + 16      │
  92-102 Layer 1 (Political OS core) ◄── 38 + 40 + 15        │
  103-122 OS-specific concepts ◄── 92-102                     │
  123-133 Structural analysis ◄── 92-102                      │
  134-145 Cross-cutting findings ◄── 123-133                  │
```

---

# Political OS Suite — Concept Index

Source documents: `political_os/political_operating_system.md` (The Political Operating System), four OS specifications, `us_democratic_political_os.md`, `political_os_test_suite.md`, real-world invariant analysis reports.

---

## XI. Governance Stack Architecture

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 77 | **Governance Stack** | Five-layer model: Hardware → Political OS → Runtime → Programs → Bootstrap. Structural analogue of the constraint hierarchy (concept 11) applied to political governance | POS §Stack | 10, 11 | Derived |
| 78 | **Layer 0: Hardware (Reality OS)** | Physical geography, resources, population, borders — the substrate on which governance software runs | POS §L0 | 2, 16 | Derived |
| 79 | **Layer 1: Political OS** | Foundational axioms, invariants, evaluation algorithm — the constraint specification | POS §L1 | 40, 77 | Derived |
| 80 | **Layer 2: Runtime (Institutions)** | Courts, legislatures, enforcement, interpretation — the constructor that reads the specification and produces governance | POS §L2 | 41, 77 | Derived |
| 81 | **Layer 3: Programs** | Policies, laws, institutional arrangements — the constructed structures operating within the OS | POS §L3 | 42, 77 | Derived |
| 82 | **Layer 4: Bootstrap** | Civic education, cultural transmission, OS replication — how the encoding propagates across generations | POS §L4 | 44, 39, 77 | Derived |
| 83 | **Logical Encapsulation** | Four-layer architecture (Constraint, Ontology, Algorithm, Operating Principle) for building LLM constraint specifications | POS §Method, ontology_templates.md | 40, 35 | Derived |

## XII. Layer 0: Hardware / Reality OS

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 84 | **Polity as Markov object** | A stable governance pattern with constraint-defined boundaries; its border is its Markov blanket | POS §L0 | 7, 8 | Instantiation of 7 |
| 85 | **Constraint technology** | A technology that extends the reach of coherent administration (agriculture, writing, roads, print, constitutions) | POS §L0 | 1, 84 | Derived |
| 86 | **Governance scaling** | Polity size determined by which constraint technologies are available; each technology enables a step-change in administrative reach | POS §L0 | 85, 84 | Derived |
| 87 | **Shared legibility** | Common language, civic vocabulary, mutual intelligibility required for the OS to be readable by its users | POS §L0 | 84, 85 | Derived |
| 88 | **Authoritarian ground state** | Within a polity, the default absent governance: the strongest actor dominates. The gravitational attractor every Political OS fights against | POS §L0 | 3, 84 | Derived |
| 89 | **Inter-state anarchy** | Between polities, the stable ground state: no sovereign above states. Stable when actors are powerful enough that none can impose hierarchy | POS §L0 | 88 | Derived |
| 90 | **Asymmetry of construction and destruction** | Distributed governance takes generations to build and a decade to destroy | POS §L0, §L4 | 88, 82 | Derived |
| 91 | **Substrate requirements** | Bounded territory, resource base, governable population, shared legibility, institutional infrastructure — what the Hardware layer must provide | POS §L0 | 78, 84 | Derived |

## XIII. Layer 1: Political OS Core

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 92 | **Political philosophy as constraint specification** | A formal system of axioms, invariants, and evaluation algorithm that determines what counts as legitimate, violation, or evidence | POS §L1 | 40, 79 | Derived |
| 93 | **Primary unit** | The irreducible entity each OS treats as foundational: individual (Liberal), class (Marxist), intersectional identity group (CJ), divine order (Theocratic) | POS §L1 | 7, 92 | Instantiation of 7 |
| 94 | **Pre-order (political)** | The directional gradient each OS defines: Consent > Coercion (Liberal), Emancipation > Exploitation (Marxist), Equity > Domination (CJ), Submission > Autonomy (Theocratic) | POS §L1 | 15, 92 | Instantiation of 15 |
| 95 | **Invariant (political)** | A constraint that defines the political manifold's topology; performs different operations in each OS: prescriptive (Liberal), analytical (Marxist), hermeneutic (CJ), conformity (Theocratic) | POS §L1 | 9, 92 | Instantiation |
| 96 | **Evaluation algorithm** | The procedure by which the OS classifies events against its invariants; what makes the specification mechanically operative | POS §L1, all OS specs | 92, 94, 95 | Derived |
| 97 | **The unit problem** | Why should any particular unit be treated as irreducible? The choice is declared, not argued; each OS defines a different Markov object | POS §Unit Problem | 93, 7 | Derived |
| 98 | **Termination condition** | Can the evaluation algorithm return "stable" or "achieved"? Stable (Liberal), teleological (Marxist), non-terminating (CJ), eschatological (Theocratic) | POS §Structural | 96 | Derived |
| 99 | **OS/Program distinction** | Foundational invariants (OS) vs. policies operating within the OS (Programs); collapsing this distinction is a corruption mechanism | POS §L3 | 79, 81 | Derived |
| 100 | **Diagnostic program vs full OS** | Some candidates self-discover as diagnostic programs (analytical tools) rather than complete operating systems (governance-capable); Marxist and CJ are diagnostics | POS §Structural | 92, 98 | Derived |
| 101 | **Host OS requirement** | Diagnostic programs need a host OS for implementation; they cannot answer "who decides" on their own | POS §Structural | 100 | Derived |
| 102 | **State taxonomy** | Classification of polity states (Stable, Strained, Crisis, Authoritarian Dynamics, Systemic Failure); each OS defines its own variant | All OS specs, Reports | 92, 95, 96 | Derived |

## XIV. OS-Specific Concepts

### Classical Liberal OS

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 103 | **Agency (Invariant 1.1)** | Freedom of choice without coercion | CL OS §Invariants | 95 | Axiom (within OS) |
| 104 | **Information (Invariant 1.2)** | Ability to seek, receive, question information; the replication mechanism of the distributed OS | CL OS §Invariants | 95, 82 | Axiom (within OS) |
| 105 | **Alternatives (Invariant 1.3)** | Real, accessible, non-punitive options must exist | CL OS §Invariants | 95 | Axiom (within OS) |
| 106 | **Revocability (Invariant 1.4)** | Authority removable through peaceful mechanisms; the OS's self-limitation | CL OS §Invariants | 95 | Axiom (within OS) |
| 107 | **Rights as admissible transformations** | Rights are not abstract entities but structural guarantees that certain morphisms remain available (Aristotelian ontology) | CL OS §Rights | 5, 95, 66 | Derived |
| 108 | **Meta-OS** | The Liberal OS as a platform on which other political programs can run accountably; meta-constraints on how constraints may be applied | POS §Cross-cutting | 99, 103-106 | Derived |
| 109 | **Iterative optimisation loop** | Individuals evaluate governance outcomes, explore alternatives, correct course; the Liberal OS does not optimise any single aggregation but protects the conditions for continuous correction | CL OS §Eval Algorithm, POS §L2 | 106, 44 | Derived |

### Marxist OS

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 110 | **Material Conditions (Invariant 2.1)** | Who owns means of production, who labours, who extracts surplus | Marx OS §Invariants | 95 | Axiom (within OS) |
| 111 | **Class Consciousness (Invariant 2.2)** | Degree to which classes understand their objective interests; emergent from material conditions, not injected | Marx OS §Invariants | 95, 3 | Axiom (within OS) |
| 112 | **Contradiction (Invariant 2.3)** | Internal contradictions in the mode of production that drive historical change | Marx OS §Invariants | 95 | Axiom (within OS) |
| 113 | **Path to Emancipation (Invariant 2.4)** | Whether phenomena advance or obstruct collective emancipation | Marx OS §Invariants | 95, 94 | Axiom (within OS) |
| 114 | **Vanguard problem** | Who governs during and after transition, and by what authority? Acknowledged but structurally unresolved — the governance gap in the spec | POS §Structural | 110-113 | Derived |

### Critical Justice OS

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 115 | **Power Asymmetry (Invariant 3.1)** | Group-based hierarchies along identity axes | CJ OS §Invariants | 95 | Axiom (within OS) |
| 116 | **Epistemic Position (Invariant 3.2)** | Whose knowledge is centred or marginalised | CJ OS §Invariants | 95 | Axiom (within OS) |
| 117 | **Structural Reproduction (Invariant 3.3)** | How institutions reproduce asymmetries regardless of intent | CJ OS §Invariants | 95 | Axiom (within OS) |
| 118 | **Transformative Praxis (Invariant 3.4)** | Whether phenomena dismantle or reproduce domination | CJ OS §Invariants | 95, 94 | Axiom (within OS) |

### Theocratic OS

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 119 | **Divine Sovereignty (Invariant 4.1)** | All political authority derives from God; no human institution may claim authority independent of or superior to divine will | Theo OS §Invariants | 95 | Axiom (within OS) |
| 120 | **Revealed Truth (Invariant 4.2)** | Divine revelation is the ultimate source of knowledge for governance; human reason operates within bounds set by revelation | Theo OS §Invariants | 95 | Axiom (within OS) |
| 121 | **Sacred Order (Invariant 4.3)** | Society must be structured in conformity with divine design; social roles, hierarchies, laws must reflect the order God has established | Theo OS §Invariants | 95 | Axiom (within OS) |
| 122 | **Faithful Obedience (Invariant 4.4)** | The faithful community must maintain submission to divine authority as expressed through legitimate religious leadership and divinely ordained law | Theo OS §Invariants | 95 | Axiom (within OS) |

## XV. Structural Analysis Concepts

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 123 | **Consciousness model** | How each OS maintains the awareness its invariants require: emergent from structure (Liberal), emergent from material conditions (Marxist), cultivated/injected (CJ, Theocratic) | POS §Structural | 92, 95 | Derived |
| 124 | **Interpretive class** | A class required to supply or maintain the OS's consciousness: vanguard (Marxist), DEI administrators (CJ), priesthood (Theocratic). The Liberal OS avoids one by making consciousness emergent | POS §Structural | 123, 41 | Derived |
| 125 | **Provenance chain** | Traceable path from authority source through selection, interpretation, law, enforcement, and back to revocation. Only the Liberal OS closes the loop | POS §L2 | 80, 106 | Derived |
| 126 | **Provenance gap** | Points where authority passes through an intermediary that cannot be held accountable; every interpretive class creates one | POS §Structural | 125, 124 | Derived |
| 127 | **Immune maturity** | Resistance of an interpretive class to capture by self-interested actors; theocratic traditions have millennia, CJ has decades | POS §Structural, Theo OS §Immune Maturity | 124, 126 | Derived |
| 128 | **Falsifiability (political)** | Whether the OS can recognise disconfirming evidence. CJ and Theocratic: disagreement is classified as evidence of the thing being critiqued (unfalsifiable by design) | POS §Structural | 92, 96 | Derived |
| 129 | **Symmetry of evaluation** | Whether the same input always gets the same output regardless of actor. Liberal: symmetric. CJ: asymmetric (same action evaluated differently depending on identity position) | POS §Structural | 96, 95 | Derived |
| 130 | **Self-limitation** | Whether the OS constrains its own authority. Revocability (Liberal) is the mechanism; CJ and Theocratic have none | POS §Structural | 106, 92 | Derived |
| 131 | **Program corruption patterns** | Five mechanisms by which programs corrupt the OS: capture, scope expansion, invariant reclassification, indirect degradation, bootstrap corruption | POS §L3 | 99, 81, 79 | Derived |
| 132 | **Bootstrap corruption** | A program captures the OS's replication mechanism (Layer 4); the most dangerous corruption because it is self-replicating | POS §L3, §L4 | 82, 131 | Derived |
| 133 | **Formally intact but operationally hollow** | The signature pattern of program corruption: OS-level protections exist on paper but have been emptied of operational force | POS §L3 | 131 | Derived |

## XVI. Cross-Cutting Findings

| # | Concept | Definition | Location | Depends On | Status |
|---|---------|-----------|----------|------------|--------|
| 134 | **CJ ≈ Theocratic (structural isomorphism)** | Despite opposite content, CJ and Theocratic OS share: interpretive class, consciousness injection, predetermined conclusions, original condition requiring redemption, questioning as evidence, ongoing ritual of submission, eschatological promise without termination | POS §Cross-cutting | 115-118, 119-122, 123-130 | Derived |
| 135 | **Stack-level determines outcome (control functor)** | Same diagnostic at different stack levels produces opposite outcomes: Marxism-as-program → democratic socialism; Marxism-as-OS → authoritarianism | POS §Cross-cutting | 99, 77 | Derived |
| 136 | **Evolved systems vs diagnostic programs** | Liberal and Theocratic evolved from centuries/millennia of governance practice; Marxist and CJ designed to diagnose failures in existing systems | POS §Cross-cutting | 100, 39 | Derived |
| 137 | **The invasive species dynamic** | CJ optimised in academic ecology, propagated into institutional ecology where its natural predators (falsifiability, open debate) do not exist | POS §Propagation | 128, 132 | Derived |
| 138 | **Constitutional hardening** | Whether foundational commitments are constitutionally protected or carried only by tradition. Determines whether democratic self-correction succeeds or fails under stress | Reports | 95, 84 | Empirical finding |
| 139 | **Well-formedness criteria** | Seven structural criteria: separated axioms/derivations, testable invariants, termination condition, complete provenance, self-limitation, falsifiability, emergent consciousness. Acknowledged bias toward Enlightenment tradition | POS §Well-formedness | 92, 123-130 | Derived (with caveat) |
| 140 | **Defence in depth (separation stack)** | Multiple structural separations (federal/state, branches, chambers, elected/appointed, government/individual), each independently preventing power consolidation | US Dem OS §Separations | 108, 138 | Instantiation |
| 141 | **Evolutionary bootstrapping** | The Liberal OS cannot be installed by force; it requires generations of distributed practice before formalisation (the abiogenesis insight applied to politics) | POS §L4, US Dem OS | 39, 82, 90 | Derived |
| 142 | **Pre-Evaluation Triage** | Four-step filter before invariant testing: formal encoding → enforcement asymmetry → runtime distortion → distributional artifact. Prevents both denialism and presumptive encoding | CL OS §Eval Algorithm | 96, 109 | Derived |
| 143 | **Built-in Assumptions** | Pre-loaded empirical claims that function as additional axioms within the CJ OS (e.g., Western colonialism as dominant structure, all disparities as structural). Explicitly declared to distinguish them from formal axioms | CJ OS §Built-in Assumptions | 92, 115-118 | Derived |
| 144 | **Identity Paradox** | The CJ OS deconstructs identity categories (Foucault, Butler) while depending on them as stable units for analysis and policy. Strategic essentialism (Spivak) attempts to manage the tension but is operationally dropped | CJ OS §Open Problem 3 | 93, 115 | Derived |
| 145 | **Reflexivity Deficit** | The CJ OS claims all knowledge is situated but does not apply this to itself; disagreement is classified as evidence of the thing being critiqued, creating structural unfalsifiability | CJ OS §Open Problem 5 | 128, 115-118 | Derived |

