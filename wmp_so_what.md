# What The World Model Project Means For Corporate Data

**Audience:** developers who build, maintain, or depend on corporate data
systems — warehouses, catalogs, schemas, data contracts, entity resolution,
lineage, MDM, AI-on-your-data.
**Companion to:** `world_model_project_paper.md` (the research findings) and
`specification_methodology/specification/standards/WORLD_MODEL_METHOD.md`
(the construction method).
**Status:** commentary. Candidate-evidence framing throughout.
**Draft date:** 2026-04-22.

---

## What this paper is

This paper translates the World Model Project's findings and method into
consequences for day-to-day corporate-data work. It does not re-prove the
research. It reads the research with a developer's question in front: *if
this reframing holds, what changes on Monday?*

Epistemic frame. The research is graded at candidate status. The method is
already usable at candidate status. This paper is honest about both and
names where claims become overclaim.

---

## 1. The problem you already have

Every corporate data stack reaches the same wall.

- Two systems model "the customer" with different schemas. Neither is wrong.
  They disagree.
- The catalog lists one logical entity. The warehouse stores five physical
  shapes. Reports reconcile them by convention.
- Entity resolution scores match probabilities across the shapes. The
  scores are useful. They are also brittle, unexplained when wrong, and
  owned by nobody.
- A data contract pins columns, types, and nullability. It does not pin
  what the record is evidence *of*.
- AI-on-your-data retrieves rows. It cannot say which rows name the same
  thing across sources. Retrieval-augmented reasoning inherits the
  fragmentation.

The stack accumulates tooling around this wall: MDM, record linkage,
surrogate keys, reference data, master hierarchies, semantic layers, data
contracts, ontology layers. Each attacks the symptom. None of them names
the missing primitive.

The missing primitive is the unit that carries *identity* across sources
and treatments. The current stack carries *values* and infers identity
downstream.

---

## 2. What the research found

The companion paper now reports a first wave of seventeen experiments
(`08–24`) inside GPT-2 small, plus an initial cross-model replication in
Pythia-160M. The findings that matter for corporate data are these.

**Finding 1 — objects decompose into a small invariant core and a
context-selected coat.** For loaded tokens (666, 999, 42), a small set of
internal features fires in every context the token appears in. A larger
set fires per context (page number, currency, address, symbolic usage).
Core-to-coat ratios run 20–160×. The invariant core is what persists when
context changes.

**Finding 2 — the attribute basis senses identity and fragments it.**
The LLM's sparse-autoencoder dictionary (24 576 features) partially aligns
with each object's identity and distributes it across many atoms. No
single feature *is* the object. No small feature set exclusively bounds
the object. This was the experimental result, not a theoretical
commitment.

**Finding 3 — the set-theoretic blanket fails.** Overwriting features
*outside* a target's active set still leaked 23–28% identity transfer. A
partition by "which features fire" is not a clean boundary.

**Finding 4 — identity is recoverable as a direction in representation
space.** A single vector `d = μ(object) − μ(null-peer)` across paired
prompts transferred identity at α=1 transfer ratios of ≈ 0.24–0.28 at
held-out positions. The direction lives in the representation space the
feature dictionary sits over. The dictionary senses the direction
partially; the direction is not the dictionary.

**Finding 5 — layer choice dominates the apparent strength of the
construct.** Follow-up experiments changed the story. The weak layer-8
direction does **not** become strong by simply adding more rank there.
But the same rank-k experiment at layer 2 passes immediately: rank-1
mean-diff transfer is already ≈ 0.87–0.93 across targets. The right
reading is therefore "layer-sensitive identity-direction family," not
"one weak direction in layer 8."

**Finding 6 — the promotion gate still fails.** Even after subtracting
the chosen identity subspace, the residual remains perfectly predictive
of target vs reference at both tested layers (`AUC=1.0`, `HSIC p=0.005`).
So the construct is still candidate-class rather than established in the
formal Markov-blanket sense.

**Finding 7 — composition and cross-model replication are both real
positives.** Compound directions align strongly with vector addition
(`cos(d_c, d_A+d_B)=0.936`, `p=0.0099`), and the direction-native
transfer effect survives a first SAE-free port to Pythia-160M.

**Honest calibration.**

- Pre-registered α=1 transfer threshold was ≥ 0.8. At layer 8 the
  observed effect was ~0.27. At layer 2, the same protocol now exceeds
  that threshold strongly. So the low-rank claim got stronger and the
  layer-8 generalisation got weaker.
- All results are within one model (GPT-2 small, 124M params).
- The formal Markov-blanket condition is no longer merely untested. The
  first practical promotion-gate assay has been run and failed at both
  layer 8 and layer 2. Candidate status therefore remains.
- Cross-substrate propagation (brains → texts → LLMs → institutional
  systems) is the *motivating* hypothesis. No experiment tests it.

Grading. The work is still at candidate status, but it is stronger than
the first wave alone. Rank-k saturation and compositional algebra are no
longer missing. The remaining blocker is the failed promotion gate, plus
the absence of cross-substrate closure.

---

## 3. Why this maps to corporate data

The experimental setup and a corporate data stack share structure.

| LLM verification lane | Corporate data stack |
|-----------------------|----------------------|
| Sparse-autoencoder dictionary | Schemas, catalogs, reference data |
| Features that fire for a token | Columns that populate for a record |
| Residual-stream vector | "The customer", "the trade", "the product" — the thing |
| Core/coat decomposition | Invariant fields vs. context-specific fields |
| Ablation / injection interventions | Migrations, system changes, ETL transforms |
| Identity direction `d` | The missing primitive |

Reading the table as a working analogy:

- Your schemas are an attribute basis over the domain. They sense
  objects. They do not isolate them.
- Your catalog is a surface over that basis. It inherits the basis's
  fragmentation.
- Your warehouse stores projections of the basis. Each projection is
  evidence for identity, not identity itself.
- Entity resolution is the retrofitted attempt to recover identity from
  the basis, after the basis has already fragmented it.

This is a candidate reading. The empirical evidence sits inside one
learned representation system. Treating institutional systems as
comparable is a working hypothesis. It is plausible because LLMs were
trained on the texts institutional systems emit, and because the same
constraint topology is the animating ontological commitment of the
program. It is not proven.

What the reading predicts, if it holds:

- Column-level data contracts will keep leaking identity at system
  boundaries because columns are sensing, not carrying.
- MDM accuracy will track how well your probabilistic layer recovers
  the missing direction from the basis — bounded above by what the basis
  can reveal.
- Adding more columns will not, past a point, reduce fragmentation.
- Swapping schemas, warehouses, or catalog tools will not change what
  the stack is missing.

---

## 4. The unit: a Markov-object cut

The World Model Project proposes one unit of construction. A **published
Markov-object cut** carries five components.

1. **Identity projection.** The direction that names the object. In a
   learned representation this is a vector. In an institutional domain
   it is a named projection (prompt template, feature combination, or a
   frozen vector backed by a real run). Without this, a cut is a catalog
   entry with a new name.
2. **Distributed attribute evidence.** The schema columns, reference
   codes, identifiers, text fields, and fact rows that sense the
   identity. Evidence is plural, partial, and explicitly marked as
   evidence.
3. **Verification record.** The run or runs that showed identity is
   preserved under treatment. Every cut carries a test.
4. **Null-peer record.** A paired cut that is intentionally *not* the
   object. The projection is the difference. Without a null peer, there
   is no difference.
5. **Core/coat partition.** Which evidence is invariant across contexts
   (core) and which varies by context (coat). Both are kept. Neither is
   collapsed into the other.

A cut is published as a **candidate** by default. The corresponding
accepted kind is reserved for cuts that pass the conditional-independence
promotion gate — the direction-native test that would formally close the
construct. No cut published today is accepted-class.

What a published cut is not:

- a catalog entry with extra fields
- a universal canonical record
- a replacement for the source system
- a proof that the object exists ontologically

It is a **derived, published, challengeable semantic unit** carrying an
explicit projection, explicit evidence, and explicit epistemic status.

---

## 5. What changes for developers

The reading above suggests concrete shifts. Each is compatible with
candidate status: adopt the unit now; do not wait for the promotion gate.

### 5.1 Entity resolution

Today: match scores across column sets, tuned per source pair, opaque at
the boundary.

Under the cut: match scores are evidence for or against a single
identity projection. The projection is the thing. When two sources
disagree, the question shifts from "which record wins" to "what does the
projection say each source is evidence of".

Day-one move. Persist the projection identifier alongside match scores.
Treat the projection, not a surrogate key, as the resolved identity.

### 5.2 Data contracts

Today: column names, types, nullability, SLA. Optionally a semantic
description per column.

Under the cut: contracts pin (i) which identity projection a payload is
evidence for, (ii) which fields are core vs. coat evidence, (iii) which
null peers the contract excludes. Column types remain. They are no
longer the contract's subject.

Day-one move. Add an identity-projection reference and a core/coat split
to the contract. Keep the column contract intact.

### 5.3 Lineage

Today: "column A is derived from column B by transform T". Useful.
Insufficient for reasoning about meaning.

Under the cut: lineage tracks whether a transform **preserves** or
**perturbs** the identity projection. A pure rename preserves. An
aggregation over a coat axis may preserve the core projection while
erasing coat evidence. A join across differently projected sources may
produce a new cut rather than a transformed one.

Day-one move. Annotate lineage edges with a preserves/perturbs tag against
named projections. This is coarse. It is still new information.

### 5.4 Catalogs

Today: catalogs are the primary reference surface; schemas, owners,
descriptions, tags.

Under the cut: catalogs become an index over published cuts. The cut is
the primary; the catalog entry is derived.

Day-one move. Publish cuts as first-class assets. Let the catalog
resolve to cuts rather than to tables.

### 5.5 AI grounding

Today: retrieval-augmented reasoning over rows and documents. The model
gets values. It infers identity.

Under the cut: retrieval resolves against cuts. The model gets
identity-projection references and the distributed evidence supporting
them. Hallucination pressure shifts — the model is no longer asked to
invent identity from values.

Day-one move. Build a cut-aware retrieval layer over the existing index.
Return cut references alongside rows. Evaluate whether downstream
hallucination changes.

### 5.6 Migrations and system changes

Today: schema migrations are evaluated for data shape compatibility.

Under the cut: migrations are evaluated for projection preservation. A
migration that holds all columns identical but changes what the columns
are evidence *of* is a projection-breaking migration. That is currently
invisible in migration review.

Day-one move. Add projection-preservation to migration review. Flag
migrations that silently re-purpose existing fields.

---

## 6. Source systems stay sovereign

A point easy to miss at first pass. The World Model Project is not an
attempt to replace operational systems.

- Your CRM owns customer operational truth.
- Your order book owns trade operational truth.
- Your billing platform owns invoice operational truth.
- Your product catalog owns SKU operational truth.

The Markov-object cut is a **derived, published semantic layer** over
those systems. Cuts trace source evidence, carry it, and reproject it.
Operational updates continue to flow through their owning systems.

This matters because the alternative path — build a central canonical
system that owns all identity — is what MDM promised and did not deliver.
The cut approach does not try. It stays derived and stays honest about
where operational authority lives.

---

## 7. What this does not promise

The research is at candidate status. The method is at candidate status.
The corporate-data implications in this paper inherit that status.

Do not tell stakeholders:

- that a Markov-object cut is formally proven to be the right primitive
- that cross-substrate propagation has been shown empirically
- that identity-projection retrieval will saturate entity resolution
- that this replaces your data-contract tooling tomorrow

Do tell stakeholders:

- candidate evidence from a controlled LLM program is consistent with
  this reading of identity
- the method is usable now, as a candidate discipline
- what would promote the construct from candidate to established is
  named (direction-native conditional-independence test); the team can
  track when that result lands
- published cuts are explicitly candidate-class; the storage,
  materializer, and validator enforce this

The honesty is load-bearing. It is also the reason the method is adopt-
able at candidate status: adopters know what they are adopting.

---

## 8. The tests this indicates

Each calibration point in §2 names a class of test. Running them is how
the construct moves from candidate to established, and how the corporate-
data claims in §3–§5 become validated rather than analogical.

**Status update (2026-04-24).** `8.1`, `8.2`, `8.3`, and `8.6` now have
first results. The headline is not "everything passed" or "everything
failed." It is narrower:

- `8.1 rank-k` is now **answered**, but in a layer-sensitive way:
  layer 8 fails, layer 2 passes strongly.
- `8.2 promotion gate` is now **run**, and still fails at both tested
  layers.
- `8.3 cross-model` has a **first positive** SAE-free port in
  Pythia-160M.
- `8.6 compositional algebra` has a **first positive** result.
- `8.4 institutional` remains the most important unrun bridge for the
  corporate-data claims of this paper.

### 8.1 Rank-k saturation

*From*: α=1 transfer observed ≈ 0.27 at layer 8 vs pre-registered ≥ 0.8.

*Test*: extract k orthogonal identity directions (iterated mean-diff
with residualization). Measure transfer as k grows. Find the rank at
which transfer saturates to the pre-registered threshold, if any.

*Outcome shape*: a rank-k transfer curve per target class. Either a
saturation rank exists (construct is low-rank linear, not rank-1), or
transfer plateaus below threshold (construct is not purely linear).

*Status*: **run**. The result is now clear: rank-k saturation does not
rescue layer 8, but layer 2 passes immediately at rank 1. The right
update is "layer-sensitive low-rank construct," not "no low-rank
construct."

### 8.2 Direction-native conditional independence (the promotion gate)

*From*: the formal Markov-blanket condition is the construct-level
promotion gate.

*Test*: given the identity projection, test whether residual components
are independent of target under plausible treatments. Requires a
direction-native conditional-independence estimator in residual space
(standard CI tests assume discrete or low-dimensional conditioning;
none applies directly).

*Outcome shape*: a binary gate pass/fail with an effect-size or p-value
on independence. This is the **named promotion gate**. A pass moves
the construct from candidate to established.

*Status*: **run** and currently **failed** at both tested layers. That
failure is load-bearing: it keeps the construct candidate-class even
after the stronger layer-2 intervention result.

*Next refinement*: the current gate is probably still too close to the
technological implementation surface. It conditions on one layer-local
projection, whereas the object may be emergent from the full constrained
technical stack and only *projected* through local residual charts. The
next version of the gate should therefore test **multi-layer realized-
topology conditioning**: build a joint identity chart across several
layers, and ask whether residual variation remains predictive once that
full realized chart is conditioned on. That would distinguish "the
object is absent" from "one local chart was insufficient."

### 8.3 Cross-model replication

*From*: all results are within GPT-2 small (124M params).

*Test*: re-run experiments 08 (core/coat), 13 (causal directionality),
17 (boundary leak), 18 (direction transfer) in Pythia, LLaMA, and at
least one model of a different scale. Measure whether core/coat
decomposes; whether direction transfers; whether magnitudes hold.

*Outcome shape*: a replication table across models and scales.
Establishes whether the construct is GPT-2-specific or
LLM-general.

*Status*: **first tractable port run**. A Pythia-160M SAE-free version of
the direction-native transfer test passes a relaxed qualitative
threshold, which is enough to say the phenomenon is not obviously
GPT-2-specific.

### 8.4 Cross-substrate — institutional

*From*: substrate propagation is motivating hypothesis, not finding.
This is the test most directly relevant to the claims in §3–§5 of this
paper.

*Test*: take paired institutional records (the same trade booked under
two conventions; the same customer modelled in two CRMs; the same
product described across marketing, warehouse, and billing). Extract a
direction-like structure from the attribute basis — for example, a
mean-difference over paired records in a dense embedding of concatenated
fields. Measure whether projection onto that direction transfers
identity across held-out records better than column-match baselines.

*Outcome shape*: institutional analogue of experiment 18. A non-trivial
effect would promote the corporate-data reading from analogy to
candidate finding in its own right.

*Cost*: medium; requires a real paired-record dataset and willingness
to publish results on it.

### 8.5 Cross-substrate — biological

*From*: full substrate-neutrality requires a non-engineered layer.

*Test*: neural recording with comparable intervention capability
(ablation, injection, paired-stimulus). Test whether core/coat
decomposition recovers and whether a mean-diff direction transfers
identity.

*Outcome shape*: biological analogue of the LLM verification lane.
Closes the Einsteinian-level upgrade (substrate-spanning closure).

*Cost*: high, long-horizon; requires neuroscience collaboration.

### 8.6 Compositional algebra

*From*: the original Newtonian-level gap included missing dynamics,
missing rank-k saturation, and missing compositional algebra. The first
compositional result now exists; the broader dynamics story still does
not.

*Test*: define operations over cuts — join, specialize, compose,
subsume. Test whether operations preserve identity directions or
transform them predictably. For example: does the projection of
"customer who is a premium customer" equal the sum, difference, or
some other function of the "customer" and "premium" projections?

*Outcome shape*: a small algebra of cuts with preservation theorems
(or documented failure modes). Enables reasoning about composed cuts
without re-extracting directions for every composition.

*Status*: **run**. The first result is positive: compound directions
align strongly with vector addition and beat a random-pair null.

### 8.7 Test dependencies

```
rank-k saturation ──────┐
                        ├──► promotion gate (8.2) ──► accepted status
direction-native CI ────┘
                        │
cross-model (8.3) ──────┼──► LLM-substrate robustness
                        │
institutional (8.4) ────┼──► corporate-data candidate finding
                        │
biological (8.5) ───────┼──► cross-substrate closure
                        │
compositional (8.6) ────┘──► Newtonian-level dynamics
```

Priority for a developer-facing program:

- **8.4 institutional** is the test that validates the claims of this
  paper specifically. Without it, §3–§5 remain analogical.
- **8.2 conditional independence** is the construct-level promotion
  gate. Without it, the method stays candidate-class. That is still the
  current state.
- **8.1 rank-k** is no longer open. It now says the construct is
  layer-sensitive rather than simply weak.
- **8.3 cross-model** has begun to separate GPT-2 peculiarity from
  general learned-representation phenomenon, but needs broader model
  coverage.
- **8.5 biological** remains long-horizon.

At candidate status, the practical front is now `8.2 + 8.4`: formal
promotion and institutional bridge.

That practical front should not be conflated with the stronger
theoretical line. The engineering case is already sufficient to justify
candidate-class cuts, projection-first storage, and institutional
experiments. A separate conjecture remains open: the Markov object may
be emergent from the full constrained technical stack and only
projected through local charts. That conjecture now deserves its own
research program rather than being smuggled into the engineering claim.

---

## 9. What to do on Monday

Pick one of the following, in rising order of commitment. None require
waiting for the promotion gate.

1. **Read one cut.** Take one high-value entity (a customer segment, a
   product line, a regulated position) and write a candidate cut for
   it on paper. Identity projection, distributed evidence, verification
   plan, null peer, core/coat. An hour of thinking. The value is seeing
   which of the five components your stack already has and which are
   missing.
2. **Write one cut.** Pick a domain where entity resolution is painful.
   Build one candidate cut. Use prompt-template projections if you do
   not have a frozen vector. Publish it as candidate-class. Do not
   migrate downstream tooling. Use it as a reference while the stack
   operates unchanged.
3. **Index against cuts.** Add a cut-reference index to an existing
   catalog. Let one downstream consumer (a report, a retrieval layer)
   resolve through cuts. Measure whether ambiguity drops.
4. **Pin a contract.** Add identity-projection references and core/coat
   tags to one high-traffic data contract. Keep the column contract.
   See whether contract review catches more drift.
5. **Migrate under the cut discipline.** Run the next substantial
   schema migration through projection-preservation review. Tag each
   changed field as preserves/perturbs against its owning cut. This is
   the highest-commitment option; it changes migration process.

Each of these is reversible. Each yields signal at candidate status. None
require the research to have closed its promotion gate.

---

## 10. Where to read further

- `world_model_project_paper.md` — the research findings and the
  hypothesis-to-method pipeline, with candidate-evidence framing.
- `markov_object_research/empirical_results.md` — the full empirical
  case; per-experiment protocols; §13.4 names the promotion gate;
  §15 discriminates geometric from set-theoretic readings.
- `specification_methodology/specification/standards/WORLD_MODEL_METHOD.md`
  — the method. Position, manifesto, constitutional intents, Markov
  Object Representation Law, Materialization Law, Construction Law,
  epistemic status of the construct.
- `specification_methodology/specification/standards/DESIGN_MODULE_METHOD.md`
  — related engineering law on smallest lawful carrier sets and
  resistance to boundary inflation.
- `odd_world_model/.ai-workspace/comments/claude/20260422T101500Z_STRATEGY_markov-object-epistemic-downgrade-after-crackpot-review.md`
  — the storage-posture reading that keeps candidate status honest
  through tooling.

---

## 11. Bottom line

Corporate data today stores values and reconstructs identity downstream.
The reconstruction is brittle because the missing primitive is not named.

The World Model Project names the primitive and proposes a published
unit — the Markov-object cut — that carries identity explicitly. The
supporting empirical evidence is candidate-level: consistent with a
geometric-blanket reading inside one LLM, below the pre-registered
magnitude threshold, with the formal conditional-independence test named
as the outstanding gate.

At candidate status the discipline is adoptable. It asks for honest
epistemic tags and a small set of new surfaces (projection, evidence,
verification, null peer, core/coat). It does not ask for a rebuild. It
does ask that "what is this a record of" become a first-class question
again.
