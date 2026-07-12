# Constraint-Emergence Ontology

**A foundational framework proposing that reality, computation, and engineered systems share structural invariants**

---

## Introduction

This repository contains a philosophical ontology and its worked applications. The central thesis: reality is fundamentally a self-organising constraint network. Stable bounded patterns — Markov objects — emerge in the gaps between constraints, and the precision of their screening is a declared empirical exposure. Boundaries, hierarchies, construction, evaluation, and grounded regulation recur across substrates including physics, computation, biology, cognition, and engineered systems.

The framework operates at the level of structure, not material:

> The invariants of reality live in the structure of admissible transformations, not in the material being transformed.

From this ontology, two practical contributions follow:

1. **Emergent Reasoning** — a bounded account of LLM computation as context-conditioned structured traversal, soft relational binding, and candidate semantic objects, exposed to mechanistic and behavioural tests.

2. **Logical Encapsulation** — a method for programming LLM reasoning by loading constraint specifications (axioms, invariants, evaluation algorithms) rather than detailed instructions. This converts an LLM from a generative peer into a mechanical evaluator.

The [Political OS Suite](political_os/) is the primary worked example of Logical Encapsulation: four competing political philosophies expressed as formal constraint specifications, each producing mechanically divergent analyses of the same political phenomena.

## Repository Structure

```
constraint_emergence_ontology/
├── constraint_emergence_ontology_v2.md # THE paper — narrated v2.0 cut (base + content harvest)
├── constraint_emergence_ontology.md    # Published v1.3 originating paper (historical)
├── concepts.md                        # Concept index, dependencies, and status map
├── ontology_templates.md              # Logical Encapsulation meta-template
├── presentations/                     # PDF snapshots (periodically updated)
│   ├── constraint_emergence_ontology.pdf # Published v1.3 snapshot; v2 not yet rendered
│   ├── ontology_templates.pdf
│   └── README.pdf
└── political_os/                      # Worked example: Political OS Suite
    ├── README.md                      # Political OS introduction and reading guide
    ├── classical_liberal_political_os.md
    ├── marxist_political_os.md
    ├── critical_justice_political_os.md
    ├── theocratic_political_os.md
    ├── us_democratic_political_os.md
    ├── political_operating_system.md   # Main paper — start here
    ├── political_os_test_suite.md
    ├── presentations/                 # PDF snapshots (periodically updated)
    │   ├── classical_liberal_political_os.pdf
    │   ├── marxist_political_os.pdf
    │   ├── critical_justice_political_os.pdf
    │   ├── theocratic_political_os.pdf
    │   ├── us_democratic_political_os.pdf
    │   ├── political_operating_system.pdf
    │   ├── political_os_test_suite.pdf
    │   └── README.pdf
    └── reports/                       # Real-world invariant analyses (.md + .pdf)
        ├── 2026-02-16-australia-invariant-analysis.md
        ├── 2026-02-16-uk-invariant-analysis.md
        ├── 2026-02-16-canada-invariant-analysis.md
        ├── 2026-02-16-germany-invariant-analysis.md
        ├── 2026-02-16-united-states-invariant-analysis.md
        └── 2026-02-16-california-invariant-analysis.md
```

## Documents

### Core Framework

| Document | Description |
|----------|-------------|
| [Constraint-Emergence Ontology v2](constraint_emergence_ontology_v2.md) | **The paper — sole current ontology surface.** The narrated v2.0 cut: the full traversal from physics vocabulary through rivals, construction, the evaluator, the observer, the F_P→F_C regime law with its four-role verification contract, the hallucination spiral, the typed vocabulary under the fidelity/loss/failure-condition law, the formal spine with both exposure points and the J-space scoping, the negative experiment record, and the closing harness. No prior paper is required. |
| [Constraints and the Implicate Order](constraints_and_the_implicate_order.md) | **Philosophy of Science** — Extension of the ontology into a diagnostic methodology for intractable problems. Reframes physics problems (cosmological constant, measurement, three generations) as constraint-topology tasks using a Bohmian lens. |
| [Emergent Reasoning](https://github.com/foolishimp/emergent_reasoning) | Detailed companion research programme: transformer state mechanics, soft unification, candidate Markov objects, the full experiment ledger, multi-level hallucination, J-space, and grounded-system architecture. Published cuts are collected on [Zenodo](https://zenodo.org/records/16592399). |
| [Ontology Templates](ontology_templates.md) | The Logical Encapsulation meta-template. How to build constraint specifications that program LLM reasoning within defined axioms and procedures. Published on [Zenodo](https://zenodo.org/records/18653641). |

### Historical Lineage

| Document | Role |
|----------|------|
| [Constraint-Emergence Ontology v1.3](constraint_emergence_ontology.md) | Published originating paper, preserved for provenance. Historical. |
| Narrated base cut | Constitutional base of v2 (register ruled correct by owner). Fully carried into `constraint_emergence_ontology_v2.md`; the standalone file was removed as redundant and is preserved byte-identical in git history at commit `137f55c`. |
| Codex flattened rewrite | Content source for the v2 merge. Four deltas harvested (four-role verification contract with the F_D→F_C reprice, negative experiment record, J-space scoping, fidelity/loss law); its flattened register was ruled against and the surface was superseded in place by the merged cut. |
| [Concept Index](concepts.md) | Historical concept map for the v1.3 line. It does not override v2's inline definitions and statuses. |

### [Political OS Suite](political_os/)

Four political philosophies expressed as formal constraint specifications. Start with **[The Political Operating System](political_os/political_operating_system.md)** — the main paper introducing the Governance Stack model, structural comparison, and key findings. Then load individual OS specifications into an LLM to see them in action.

| Document | Nature |
|----------|--------|
| [The Political Operating System](political_os/political_operating_system.md) | **Entry point** — Governance Stack, structural comparison, key findings |
| [Classical Liberal OS](political_os/classical_liberal_political_os.md) | Full governance specification |
| [Marxist OS](political_os/marxist_political_os.md) | Diagnostic with governance gap |
| [Critical Justice OS](political_os/critical_justice_political_os.md) | Diagnostic program |
| [Theocratic OS](political_os/theocratic_political_os.md) | Full governance specification |

## How to Read This

### If you want to understand the ontology

Read **[Constraint-Emergence Ontology v2](constraint_emergence_ontology_v2.md)**. It is the complete current argument and the only required ontology surface. Read **[Emergent Reasoning](https://github.com/foolishimp/emergent_reasoning)** afterward for the deeper LLM experiment and literature record.

### If you want to see the method in action

1. Read **[Ontology Templates](ontology_templates.md)** to understand Logical Encapsulation.
2. Go to the [Political OS Suite](political_os/) — follow its README for how to load and test the constraint specifications.

### If you want to understand the Political OS

Start with **[The Political Operating System](political_os/political_operating_system.md)** — it frames the entire suite. See the [Political OS README](political_os/README.md) for quick start, test suite instructions, and real-world analysis reports.

## Related Work

- [ai_sdlc_method](https://github.com/foolishimp/ai_sdlc_method) — The AI SDLC methodology providing the software engineering empirical ground referenced in Part VIII
- [emergent_reasoning](https://github.com/foolishimp/emergent_reasoning) — Extended analysis, simulations, and peer review of the emergent reasoning paper

## Publication

- Emergent Reasoning paper: [Zenodo](https://zenodo.org/records/16592399)
- Constraint-Emergence Ontology v1.3: [Zenodo](https://zenodo.org/records/18573722)
- Programming LLM Reasoning (Ontology Templates): [Zenodo](https://zenodo.org/records/18653641)

## Author

Dimitar Popov

## License

This work is shared for academic and philosophical discussion.
