# The AI SDLC Method
## Bootstrapping Intent — or, The Future is Organic

*Dimitar Popov*

---

> *This document is a companion to the AI SDLC slide deck. The slides show the big picture. This document explains the mechanics — particularly the feedback loops — that make the system work.*

---

## 1. Where Does Intent Come From?

IT systems are built to solve real-world problems. But the real world is infinitely complex — far more than any person can hold in their head. Our minds store a small working abstraction of reality, and our IT systems store even less.

This creates a loop that all useful system-building starts from:

```
Reality ──→ Person observes ──→ Evaluates against
            and measures         their mental model
                                       │
                              Gap detected: reality
                              doesn't match the model
                                       │
                                       ↓
                                    Intent
                                       │
                                       ↓
                           Build a system to close the gap
```

**Intent is not invented.** It is the gap between what you observe and what your model of the world says should be there. A person watches a slow process, compares it against their sense of how it should run, and feels the mismatch. That feeling is intent. It drives them to build or change something.

This is the starting point for all engineering. Not a feature request. Not a roadmap. The observed gap between reality and expectation, in a specific person's mind, at a specific moment.

---

## 2. Building Systems from Intent

Once intent exists, the job is to capture it precisely enough that a system can be built to satisfy it — and to know when the system has done so.

The AI-augmented pipeline from intent to running system looks like this:

```
         Requirements    Technology    Shepherd         Operations
              │               │           │                 │
              ▼               ▼           ▼                 ▼
Intent ──→ Specification ──→ Design ──→ Code ↔ Tests ──→ Deploy ──→ IT System
              ▲                                                         │
              │                                                    Telemetry
              └────────────── Tracing, Feedback & Iteration ───────────┘
```

The human role throughout is to **observe, evaluate, provide intent, and guide the outcome**. Not to write every line. Not to approve every decision. To hold the intent and evaluate whether the system is converging toward it.

The loop closes through telemetry: the running system feeds signals back, generating new observations, new gaps, new intent. **The pipeline is circular, not linear.**

### The Thread That Holds It Together: Traceability

Every piece of work in the pipeline carries a tracking number — call it a requirement key. Like a parcel tracking number that follows a package from warehouse to doorstep, the requirement key threads through every stage: specification, design, code, tests, and all the way into the running system's telemetry.

```
Spec:       REQ-001  "User can log in with email and password"
Design:     REQ-001  "Implements: REQ-001"
Code:       REQ-001  "# Implements: REQ-001"
Tests:      REQ-001  "# Validates: REQ-001"
Telemetry:  REQ-001  login_event, req="REQ-001", latency_ms=42
```

This is not bureaucracy. When something breaks in production, you follow the thread back to the requirement it was supposed to satisfy. When a requirement changes, you find every artifact that touches it. Without the thread, you're debugging from scratch every time.

---

## 3. How Every Step Works: The Iteration Loop

This is the mechanic behind every arrow in the pipeline diagram. **Each stage is not a one-pass process.** It is a loop.

```
              ┌─────────────────────────────┐
              │                             │
              ▼                             │
         Produce a                    Not yet —
         candidate ──→ Evaluate it ──→ revise and
         output           │              try again
                          │
                     Good enough?
                          │
                          ▼
                    Promote to next stage
```

Think of editing a document: you write a first draft, read it back, find problems, fix them, read again, fix again — until it's good enough. Then you send it. The AI SDLC runs this same loop at every stage, with or without a human doing the reviewing.

**The stopping condition is always the same: does the output satisfy the criteria for this stage?**

This raises the key question: who or what evaluates? And how do you know when "good enough" actually means good enough?

---

## 4. The Three Levels of Evaluation

Not all evaluation is equal. Some checks are instant and free. Others require judgment. The system uses three levels, from cheapest to most expensive:

```
LEVEL 3   Human judgment       The genuinely novel, strategic,
          ─────────────────    or high-stakes — fires rarely
LEVEL 2   Agent evaluation     The interpretive — fires when
          ─────────────────    automated checks pass but something
                               still needs to be reviewed
LEVEL 1   Automatic checks     Always on, instant, free — fires
                               on every change
```

**Level 1 — Automatic:** Does the code compile? Do the tests pass? Does the format match the schema? Does the response time stay under 200ms? These run instantly, every time, at near-zero cost. They produce a clear yes/no. No human attention required.

**Level 2 — Agent:** For things that need reading and interpretation. Does this code actually do what the specification says? Are there edge cases the automatic tests don't cover? Does this design document hold together logically? An AI agent reads the output and classifies what it finds. Faster and cheaper than a human, but able to handle nuance that a rule-based check can't.

**Level 3 — Human:** For things that require business context, strategic judgment, or domain expertise that hasn't been captured in any specification. Is this actually what the customer needs? Does this match what we agreed with the client? Should we change the approach entirely? Expensive and valuable — which is why it should only fire when the lower levels can't resolve the question.

**The efficiency principle:** most evaluation should happen at Level 1. It is free, instant, and scales without limit. Level 2 handles what Level 1 misses. Level 3 handles only what Level 2 cannot resolve. If a human is spending time on things an automatic check could catch, the system is mis-configured.

### A Measurement Is Not an Opinion

For any of this to work, "good enough" must be measurable.

"The system should be fast" — unmeasurable. How fast? Fast compared to what? There is no gradient to follow, no way to know if you're getting closer or further away.

"Response time under 200 milliseconds for 99% of requests" — measurable. The automatic check either passes or fails. The system either corrects toward it or it doesn't. The feedback loop has something to close on.

**A specification without a measurable threshold is a preference, not a constraint.** The evaluation cascade only works if Level 1 has something to evaluate against.

---

## 5. Spec-Driven Development and Context Engineering

The LLM's context window is its working memory. Like a person, it can only attend to what's currently in front of it. Overload it and attention drifts. Underload it and it has insufficient context to reason accurately.

To get reliable output, you manage what's in the context window:

```
┌─────────────────────────────────────────────────────┐
│  LLM Context Window = Active Working Memory          │
│                                                      │
│   ┌────────────┐  ┌──────────────┐  ┌────────────┐  │
│   │  Calc      │  │    Best      │  │    Not Too │  │
│   │  Design    │  │  Practices   │  │  Technical │  │
│   │            │  │              │  │            │  │
│   │    ┌───────┴──┴──────────────┤  │            │  │
│   │    │      Data Definitions   │  │            │  │
│   │    │                         │  │            │  │
│   └────┤   ┌─────────────────────┴──┘            │  │
│        │   │  Regulations                        │  │
│        └───┴─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Where the context is most constrained and specific — where the overlapping circles are smallest — that is where the solution lives.** The LLM reasons toward the intersection, not the union.

Too much context: attention drifts, partial results.
Too little context: the model fills gaps with plausible guesses — hallucination.

The specification is the most important piece of context. It tells the model what "correct" means — which directly constrains where the answer can be. A precise specification, combined with the right supporting context, makes the answer discoverable. A vague specification leaves many equally plausible answers; the model picks one at random.

**"Build a calc for me with the provided docs"** — the instruction is one sentence. The context is everything. The context does the work.

---

## 6. The Structural Parallel: Humans, LLMs, and Agents

For the purpose of system design, a person and an LLM are structurally equivalent in three ways:

```
┌──────────────────────┐          ┌──────────────────────┐
│       HUMAN          │          │         LLM           │
│                      │          │                       │
│  Working Memory      │◄────────►│  Context Window       │
│                      │          │                       │
│  Attention / Focus   │◄────────►│  Attention / Focus    │
│                      │          │                       │
│  Knowledge           │◄────────►│  Latent Space         │
│  (Life experiences)  │          │  (All recorded        │
│                      │          │   human knowledge)    │
└──────────────────────┘          └──────────────────────┘

┌──────────────────────┐          ┌──────────────────────┐
│  Observe → Evaluate  │◄────────►│  Agents              │
│       → Intent       │          │  (Proxies for        │
│                      │          │   human intent)      │
└──────────────────────┘          └──────────────────────┘
```

The three constraints are parallel. The difference is in the bottom row.

A person observes, evaluates against their model, and generates intent. This loop is internal — it runs automatically, continuously, without instruction. The person arrives at work already directed by it.

An agent is a proxy for human intent. It executes within a context window provided externally. It does not generate its own intent. The observe-evaluate-intent loop must be provided — and continuously maintained — from outside.

**Agents are not people. They are proxies for intent. The intent must come from somewhere.**

---

## 7. Human Organisational Tools Apply to AI

People have limited capabilities. An individual can only hold so much in working memory, attend to so many things, and draw on so much knowledge. Yet humans have built organisations that can manage global supply chains, run financial markets across twenty countries, and coordinate thousands of specialists toward a shared outcome.

How? Through structure:

```
         ┌─────────────┐
         │   Person    │ ← Full context, intent, evaluation
         └──────┬──────┘
                │
    ┌───────────┼───────────┐
    │           │           │
┌───▼───┐  ┌───▼───┐  ┌───▼───┐
│Person │  │Person │  │Person │ ← Delegated context + agents
└───────┘  └───────┘  └───┬───┘
                           │
               ┌───────────┼───────────┐
               │           │           │
           ┌───▼───┐   ┌───▼───┐  ┌───▼───┐
           │Person │   │Person │  │Person │ ← Narrower context
           └───────┘   └───────┘  └───────┘
```

Hierarchy and delegation exist because they solve the capacity problem. Each level holds the context relevant to its decisions. The level above sets direction; the level below executes within it.

**The same model applies to AI systems.** Large parts of this hierarchy can be automated by agents operating within context windows provided by the level above. The structure stays the same. The substrate changes.

You are not building something new. You are applying the organisational architecture you already have to a new class of agent.

---

## 8. Human in the Middle: The Intent Engine

The current state of the art is **human-in-the-middle** asset building.

```
                    Human
                 (Intent Engine)
                      │
          ┌───────────┼───────────┐
          │           │           │
   Manages          Directs    Evaluates
   Context            │          Output
          │           ▼           │
          │    ┌─────────────┐    │
          └───►│ Agent Code  │────┘
               │  Builder   │
               │  [Context  │──────► Output Asset
               │   Window]  │
               └─────────────┘
               ▲
    Full Context
    of Project
```

The human manages what goes into the agent's context window, directs the agent's task, and evaluates the output against intent. The agent executes within the provided context.

The three evaluation levels described in Section 4 determine how much of this the human must do personally. The more that can be evaluated automatically (Level 1) or by an agent (Level 2), the less the human's attention is consumed by routine checking — and the more it can focus on the judgment calls that actually require human insight.

**The progression:**

| Stage | Who evaluates | Human role |
|---|---|---|
| Now (early) | Mostly human | Review most outputs directly |
| Near term | Human + agent | Review exceptions; agent handles routine |
| Mature | Agent + automated | Define the criteria; review only escalations |

**The human moves up the stack: from evaluating outputs to defining what correct means.** This is not a reduction in the human's importance. It is a change in where their attention is most valuable.

---

## 9. The Self-Correcting System

Once you have the three-level evaluation cascade running, something important happens: **the system starts correcting itself.**

Automatic checks run continuously. When they detect a drift from the specification — a test starts failing, a latency threshold is breached, a data format changes — they emit a signal. That signal is classified by severity. Routine drift gets handled automatically. Significant deviations get escalated.

The system behaves like an autopilot:

```
Target heading ─────────────────────────────────────────────┐
                                                             │
Current heading → Measure gap → Apply correction → New heading
        ▲                                                    │
        └────────────────────────────────────────────────────┘
```

The autopilot doesn't wait for the pilot to notice the plane is off course. It measures the gap continuously and makes small corrections automatically. The pilot sets the destination and handles turbulence the autopilot can't manage.

In the AI SDLC, the specification is the target heading. The evaluation cascade measures the gap. The iterate loop makes corrections. The human handles the turbulence — the novel, high-stakes, or genuinely ambiguous situations that automated and agent layers cannot resolve.

**The system tends toward its specification without continuous human intervention.** This is what makes it scalable. A system that requires a human decision for every deviation cannot run twenty markets. A system that escalates only what it cannot resolve can.

---

## 10. The Future Is Constant Transformation

The individual-level loop — observe reality, evaluate against model, generate intent, build — scales to the organisation:

```
Reality ──→ Organisation ──→ Evaluates against
            observes            business model
                                      │
                             Gap detected
                                      │
                                      ↓
                                  Intent
                                      │
                                      ↓
               ┌──────────────────────────────────┐
               │  Humans + Agents + AI Systems     │
               │                                   │
               │    ┌───┐    ┌───┐    ┌───┐        │
               │    │ H │    │ A │    │ H │        │
               │    └───┘    └───┘    └───┘        │
               │               │                   │
               │        ┌──────┴──────┐            │
               │        │ A    A    H │            │
               │        └─────────────┘            │
               └──────────────────────────────────┘
```

Spec-driven development at the business and organisation level enables **constant reconfiguration and evolution**. The organisation is not restructured every three years in a transformation programme. It adjusts continuously, driven by the gap between observed reality and current model.

The same pipeline — iterate, evaluate, correct — runs at every scale simultaneously:

| Scale | What's being measured | What corrects it |
|---|---|---|
| Single task | Output vs specification | Agent revises |
| Feature | Feature vs requirement | Shepherd redirects |
| Product | Product vs user needs | Product manager updates roadmap |
| Organisation | Capability vs market demand | Leadership reconfigures |

Each level feeds the one above it. Telemetry from the running system informs the product. Product signals inform strategy. Market signals inform organisational structure. **The feedback loops are nested: each outer loop sets the target for the inner one.**

The organisation that has built these loops at every level doesn't transform every three years. It is always transforming — in small, continuous, measured steps. The gap between where it is and where it needs to be is always closing, at every scale, simultaneously.

---

## Summary

| Concept | One Line |
|---|---|
| **Intent** | The gap between observed reality and your model of how it should be |
| **SDLC Pipeline** | The path from intent to running system — circular, not linear |
| **Iteration Loop** | Every stage: produce → evaluate → revise → repeat until good enough |
| **Three Evaluation Levels** | Automatic (free, always on) → Agent (interpretive) → Human (judgment only) |
| **Measurable Thresholds** | A specification without a measurable threshold is a preference, not a constraint |
| **Traceability** | A requirement key threads every artifact from spec to telemetry — the feedback thread |
| **Context Engineering** | Managing what's in the LLM's working memory to make the answer discoverable |
| **Human Org Tools** | The hierarchical delegation architecture that scales human capability applies directly to AI |
| **Self-Correction** | With evaluators defined, the system tends toward its specification without constant intervention |
| **Constant Transformation** | Nested feedback loops at every scale — the organisation is always adjusting, never done |

> The system is not something you build once. It is the loop itself — running at every scale, from a single task to the whole organisation, closing the gap between where you are and where you need to be.

---

*Part of the Corporate Operating System series.*
*Foundation: [Constraint-Emergence Ontology](https://zenodo.org/records/18573722)*
*Methodology: [AI SDLC Asset Graph Model](https://github.com/foolishimp/ai_sdlc_method)*
