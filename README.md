# Constraint and Emergence

**A working model of persistence, construction and evaluation across physical, biological and computational systems**

---

## Introduction

This repository contains the [current paper](constraint_emergence_ontology_v3.md), its research records and related applications. The paper's core proposal is that constraints and dynamics produce persistent structures; those structures enable further construction; encodings retain and direct constructive processes; and evaluation supplies feedback.

Cross-domain comparisons must state which relationships survive, what the mapping discards and where its predictions fail. The stronger conjecture about the physical basis of reality remains separate from the functional model and its evidence.

Two related applications are developed here and in the companion work:

1. **Emergent Reasoning** — a bounded account of LLM computation as context-conditioned structured traversal, soft relational binding, and candidate semantic objects, exposed to mechanistic and behavioural tests.

2. **Logical Encapsulation** — reusable reasoning context that declares assumptions, criteria and checks. Whether it improves a model's work is an empirical question; loading a specification does not establish mechanical correctness.

The [Political OS Suite](political_os/) is a worked application of Logical Encapsulation: four competing political philosophies expressed as constraint specifications for contrasting analyses of the same political phenomena.

## Repository Structure

```
constraint_emergence_ontology/
├── constraint_emergence_ontology_v3.md # Current concise working paper
├── constraint_emergence_ontology_v2.md # Original v2 paper, preserved unchanged
├── constraint_emergence_ontology_v2.pdf # Earlier v2 export
├── constraint_emergence_ontology_v2.html # Earlier v2 export
├── constraint_emergence_ontology.md    # Published v1.3 originating paper (historical)
├── concepts.md                        # Concept index, dependencies, and status map
├── ontology_templates.md              # Logical Encapsulation meta-template
├── presentations/                     # PDF snapshots (periodically updated)
│   ├── constraint_emergence_ontology.pdf # Published v1.3 snapshot
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
| [Constraint and Emergence v3](constraint_emergence_ontology_v3.md) | **The current standalone paper.** A concise account of constraints, persistence, construction, relational meaning and assurance. It retains the cross-domain argument, separates the physical conjecture from the functional model, and links positive results, failed screening tests and the proposed evaluation programme. |
| [Constraints and the Implicate Order](constraints_and_the_implicate_order.md) | **Philosophy of Science** — Extension of the ontology into a diagnostic methodology for intractable problems. Reframes physics problems (cosmological constant, measurement, three generations) as constraint-topology tasks using a Bohmian lens. |
| [Emergent Reasoning](https://github.com/foolishimp/emergent_reasoning) | Detailed companion research programme: transformer state mechanics, soft unification, candidate Markov objects, the full experiment ledger, multi-level hallucination, J-space, and grounded-system architecture. Published cuts are collected on [Zenodo](https://zenodo.org/records/16592399). |
| [Ontology Templates](ontology_templates.md) | The Logical Encapsulation meta-template. How to build constraint specifications that program LLM reasoning within defined axioms and procedures. Published on [Zenodo](https://zenodo.org/records/18653641). |

### Historical Lineage

| Document | Role |
|----------|------|
| [Constraint-Emergence Ontology v1.3](constraint_emergence_ontology.md) | Published originating paper, preserved for provenance. Historical. |
| [Constraint-Emergence Ontology v2](constraint_emergence_ontology_v2.md) | The original 13,471-word paper is preserved unchanged, matching commit `2da7871`. The concise rewrite is a separate v3 paper. The earlier standalone base remains in history at `137f55c`. |
| Earlier Codex rewrite | A historical input to the v2 merge. Its contributions included the four assurance roles, negative experiment record, workspace/screening distinction and explicit limits on cross-domain mappings. |
| [Concept Index](concepts.md) | Historical concept map for the v1.3 line. It does not override the current paper's definitions and claim status. |

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

### If you want to understand the model

Read **[Constraint and Emergence v3](constraint_emergence_ontology_v3.md)**. It contains the complete current argument. Read **[Emergent Reasoning](https://github.com/foolishimp/emergent_reasoning)** afterward for the deeper LLM experiment and literature record.

The v3 Markdown paper is the current source. The original v2 Markdown and its earlier HTML and PDF exports remain separate. No v3 HTML or PDF has been generated.

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
