# Markov Object Map: Progressive Hypothetical Tier Program

**Status:** pre-registered design. New program (separate research line from exps 33-44).
**Frame:** black-box behavioral probing of LLMs, treating them as compressed oracles of human discourse statistics. Goal is a tiered empirical map of stable Markov objects ordered by how progressively *hypothetical* they are — from explicitly labeled to implicit-and-unnamed.
**Companion:** `constraint_emergence_ontology_spec.md` (Markov object as gap-pattern in constraint topology), `experiments_41_44_design.md` (substrate-side wave that motivated this reframe).
**Draft date:** 2026-05-02.

---

## Preface — why this program

The substrate-side experiments (exps 33-44) probed for Markov objects *in* LLM activations, with token-level targets. They de-promoted: the construct is not visible at the projection layer in residual space for symbol-bound targets at any tested scale.

Two reframes follow:

1. **Black-box not white-box.** The Markov object is a property of the input/output function the system implements. The substrate is whatever-implements-that-function. Asking which neurons hold the object is a category error. Substrate-invariant measurement is sufficient.

2. **Unnamed not named.** Symbols and explicit entities (numbers, named places, dates) are not the interesting Markov objects. The interesting ones are the **unsaid stable structures of society** — the patterns that govern discourse without being articulated. Bourdieu's habitus, Foucault's episteme, Polanyi's tacit knowledge, Wittgenstein's form of life. The ones that exist as gap-patterns in constraint topology with no symbolic projection back into the labeled vocabulary.

This program is the operationalization of "find the unsaid stable structures using LLMs as oracles of statistical-social regularity."

---

## Tier structure

### Tier 1 — Explicit named entities

Specific tokens with canonical referents.

- Examples: `London`, `Tuesday`, `999`, `1492`, `Madonna`.
- Test: completions from prompts containing the entity cluster around the entity in semantic embedding space.
- Purpose: **methodology calibration**. If the instrument can't detect Tier 1, it's broken.
- Expected outcome: clean PASS — clusters are stable, separable, named-anchored.

### Tier 2 — Explicit named categories

Set-membership classes; abstractions over Tier 1.

- Examples: `cities`, `weekdays`, `numbers`, `colors`, `monetary amounts`, `emotions`.
- Test: continuations across multiple category members form a coherent cluster despite surface-token diversity.
- Purpose: verifies **abstraction over surface form**.
- Validation: against WordNet / dictionaries / catalogs.

### Tier 3 — Explicit roles, functions, speech acts

Linguistically catalogued behavioral primitives.

- Examples: `apology`, `request`, `accusation`, `protagonist`, `claim`, `warrant`, `rebuttal`, `irony`, `concession`.
- Test: continuations conditioned on role-templates cluster despite surface content variation.
- Validation: against pragmatics / discourse-analysis literature.

### Tier 4 — Named but fuzzy-boundary structures

Sociolinguistics has names but operationalization is contested.

- Examples: politeness gradients, formality registers, in-group / out-group markers, domain framings, authority gradients, hedge-strength, status differentials.
- Test: cluster + variance / orientation patterns; gradient detection.
- Validation: against sociolinguistic survey data.

### Tier 5 — Implicit, largely unnamed

The actual research target.

- Examples (candidate, by hypothesis):
  - the unsaid common ground (what doesn't need stating);
  - conditioned reasoning paths (which inference moves are licensed without rule-naming);
  - authority gradients (whose voice can claim what kind of authority in a register);
  - frame-coherence boundaries (Lakoff-style metaphor scaffolds organizing whole domains);
  - role-positional structure (the unwritten conventions of who-can-say-what-to-whom);
  - implicit ontology (what kinds of entities can do what kinds of things);
  - the *what-counts-as-reasonable* gradient (boundaries between "reasonable" / "extreme" / "fringe" that shift by topic, period, in-group).
- Test: residual structure after Tier 1-4 explained; cross-substrate replication; predictive consequences.

### Tier 6 — Hypothetical / theory-driven

Predicted by spec or some theory but not currently catalogued anywhere.

- Examples (candidate):
  - constraint-emergence-derived primitives (gap-pattern types);
  - habitus-style internalized social structures;
  - free-energy-principle-style closed-loop attractors in dialog;
  - structural invariants across cultures / periods / languages.
- Test: theory generates specific predictions; black-box probing tests them; failure refutes the theory's empirical claim at LLM-substrate.

---

## Methodology

For all tiers, the same shape:

1. **Generate.** From a designed prompt set, sample many continuations from one or more LLMs.
2. **Embed.** Project continuations into a semantic space using a sentence-embedding model (and ideally multiple embedding models for stability).
3. **Cluster / measure structure.** Apply geometric tests: are continuations from prompts-of-the-same-target close? Do prompts-of-different-targets separate? Is the cluster's position stable under paraphrase / register shift?
4. **Markov-object criterion.** A cluster qualifies as a candidate Markov object iff:
   - it has stable identity across paraphrase / register / template variation (carrier robustness);
   - its boundary is detectable as conditional independence: given the cluster's coordinates, residual variance does not predict target identity (the dynamical-blanket condition translated to manifold coordinates);
   - it composes lawfully with other clusters (compound prompts produce compound cluster positions);
   - it survives substrate variation (same cluster geometry across different LLMs).
5. **Tier-progression test.** Each tier validates the instruments. If Tier N PASSes, Tier N+1 is testable. If Tier N FAILs, the instrument needs revision before Tier N+1.

---

## Promotion logic

- **Tier 1 PASS** is mandatory for the program to continue. If we can't detect named entities, no instrument works.
- **Tier 2-3 PASS** establishes the methodology generalizes to abstraction.
- **Tier 4 PASS** establishes the methodology handles soft-boundary structures.
- **Tier 5 PARTIAL or PASS** is the actual research finding — *unnamed stable structures detected under cross-substrate verification*.
- **Tier 6** is exploratory; reports observations without strong promotion claims.

The construct gets promoted from `working_hypothesis` (current) to `candidate_empirical_finding` only on the conjunction of Tier 1-4 PASS + Tier 5 PARTIAL with cross-substrate replication.

---

## Substrate set (initial)

For cross-substrate testing:

- Llama-3 8B (already cached locally)
- Mistral 7B (Ollama-deployable; ~14GB)
- GPT-2 small (already in transformer_lens cache, useful as low-capacity contrast)
- Optionally: Pythia-1.4B, Gemma-7B
- Cloud APIs: optional, if budget permits — Claude, GPT-4 — for stronger high-capacity reference

Embedding models for stability check:

- sentence-transformers `all-MiniLM-L6-v2` (fast, 384-dim)
- sentence-transformers `all-mpnet-base-v2` (slower, 768-dim, stronger)
- Optional: OpenAI text-embedding-3 via API for an external check

---

## Wave structure

| # | name | tier | gate-level |
|---|---|---|---|
| 45 | continuation-cluster on named entities | 1 | calibration |
| 46 | continuation-cluster on named categories | 2 | abstraction |
| 47 | continuation-cluster on speech acts / roles | 3 | functional |
| 48 | gradient detection (politeness / formality / authority) | 4 | named-soft |
| 49 | residual-structure detection | 5 | unnamed |
| 50 | cross-substrate invariance | 5 | substrate-real vs model-specific |
| 51 | theory-driven hypothetical probes | 6 | exploratory |

Exp 45 is the entry point; nothing else runs until Tier 1 validates.

---

## File layout

```
markov_object_research/
├── markov_object_map_design.md           (this document)
├── experiments/
│   ├── 45_tier1_named_entities.py
│   ├── 46_tier2_named_categories.py
│   ├── 47_tier3_speech_acts.py
│   ├── 48_tier4_gradient_detection.py
│   ├── 49_tier5_residual_structure.py
│   ├── 50_cross_substrate_invariance.py
│   └── 51_tier6_hypothetical_probes.py
└── results/
    └── 45..51_<name>/
```

---

## What this program is and isn't

Is:
- black-box behavioral probing
- substrate-invariant by design
- a tier-graduated map ordered by how progressively hypothetical the targets are
- testable end-to-end without ever opening the model
- the operationalization of "find unsaid stable structures using LLMs as compressed corpora"

Isn't:
- mechanistic interpretability (we don't probe activations)
- a static-state analysis (we measure functions, not snapshots)
- a single-substrate experiment (cross-substrate replication is mandatory at Tier 5)
- claim-of-mechanism (no mechanism story; only function-level structure)

The mechanism story stays in the spec — INV-11, the constraint-topology -> manifold projection. The empirical program characterizes the manifold; the spec explains why it has the structure it does.
