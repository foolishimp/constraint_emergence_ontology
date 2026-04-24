# Topological Model Assessment

**Status:** research-frame note
**Scope:** evaluating LLMs as learned projected topologies before judging
their reasoning behavior
**Companion to:** `emergence_conjecture_program.md`,
`emergent_markov_object_evidence.md`, `empirical_results.md`,
`experiments_25_31_design.md`
**Draft date:** 2026-04-24

---

## 1. Core Claim

The interesting claim is not that LLMs contain clusters of information.
That is expected. A learned model trained on reality-mediated text will
contain basins, directions, manifolds, co-activation sets, label
regions, and context-conditioned regularities.

The interesting claim is:

> An LLM can be evaluated as a learned projected topology before it is
> evaluated as a reasoner.

Reasoning operates over an internal world. If the internal topology is
shallow, brittle, label-bound, or badly factorized, then reasoning
benchmarks mostly show how well the model manipulates that flawed
topology. They do not tell us whether the model has useful object
structure.

So the first question is:

> What world has the model made available to reason over?

---

## 2. From Existence To Shape

Finding a cluster is not enough. The research target is the shape of
the topology projected into the model.

The useful question is not:

> Does the model contain a Markov object?

The better question is:

> What topological form does this representational region have, and does
> any boundary form in that region behave like an effective Markov
> blanket?

Markov blankets are one possible discovered boundary form. They are not
the only useful outcome. A failed blanket test can still be evidence if
it tells us that the local shape is carrier-bound, fragmented,
distributed, stratified, or not yet semantically rich enough.

---

## 3. Candidate Topological Forms

A model region may have several different shapes:

- **Label basin:** surface-token identity dominates. The model knows the
  label-pattern more than the concept.
- **Concept basin:** multiple carriers converge on a shared semantic
  identity.
- **Bundle:** stable core plus context-conditioned coats.
- **Fiber bundle:** a base identity with lawful context-conditioned
  fibers over it.
- **Stratified object:** arithmetic, cultural, referential, symbolic,
  and discourse uses occupy different regimes.
- **Distributed circuit object:** no local blanket appears, but
  interventions across layers or modules move the state lawfully.
- **Schema object:** syntax, role, or institutional constraints define
  the boundary more cleanly than semantic content does.

The current `666/999/137` evidence in GPT-2 small looks less like a
clean conceptual object and more like a carrier-sensitive bundle:
symbol-bound, culturally loaded, fragmented through SAE features,
coherent across layers, and not closed by the tested residual charts.

That is not a useless result. It is a topology description.

---

## 4. Topological Usefulness Before Reasoning

A model can be useful for reasoning only over the topology it has
actually learned.

Topological richness asks whether the model has:

- stable object regions;
- carrier robustness across surface forms;
- core/coat structure;
- context fibers that vary lawfully over stable identities;
- exposed or recoverable boundaries;
- intervention leverage that moves predictions coherently;
- compositional object states;
- cross-layer or cross-module chart coherence;
- transfer across paraphrase, task, and implementation variation.

A weak topology has the opposite profile:

- label basins dominate;
- conceptual carriers do not unify;
- boundaries are leaky;
- context coats are entangled;
- interventions do not preserve identity;
- composition is brittle;
- apparent reasoning works by manipulating shallow label-patterns.

This makes topological assessment an upstream model-evaluation layer.
It should happen before or alongside reasoning benchmarks.

---

## 5. Markov-Object Qualifiers

The mining target is not high activation or interpretability alone. A
candidate Markov-object qualifier should be scored by whether it shows:

1. **Carrier robustness:** the same object state appears across surface
   forms.
2. **Context-conditioned coats:** a stable core supports lawful
   context-specific overlays.
3. **Boundary compression:** a compact state explains many correlated
   features or directions.
4. **Intervention leverage:** moving the state changes downstream
   predictions coherently.
5. **Conditional closure:** after conditioning on the object state,
   residual identity drops.
6. **Composability:** object states combine lawfully.
7. **Chart coherence:** local views align across layers, bases, or
   modules even when leverage differs.

Conditional closure is the strongest Markov-blanket criterion. It is
not the only informative measurement. Failure to close the gate should
classify the topology, not erase the candidate from the map.

---

## 6. Reading Exp 25 Under This Frame

Exp 25 did not show that Markov objects do not exist. It showed that a
simple GPT-2 residual chart did not expose a closed blanket for the
tested token family.

The negative result is local to:

- GPT-2 small;
- targets `999`, `666`, and `137`;
- reference `5`;
- residual stream layers `2/4/6/8`;
- one mean-difference coordinate per layer;
- linear residualization of the concatenated residual;
- the tested prompt family and CI proxy.

The result says:

> This dig site did not expose gold under this assay.

It does not say:

> Gold does not exist.

For GPT-2 small, the observed shape is currently:

- carrier-sensitive rather than carrier-invariant;
- fragmented through the SAE feature basis;
- coherent across layers but not locally sufficient;
- intervention-accessible early and weaker later;
- compositional in direction algebra;
- not closed by single-chart or first multi-layer residual conditioning.

That is a useful map of the local topology.

---

## 7. Model Comparison

The same assays can compare models by topological richness.

A stronger model should show more of the following:

- concept basins separated from labels;
- stable objects across carriers;
- lawful context fibers over object identity;
- effective blankets for some object classes;
- compositional geometry;
- robust chart families across layers or modules;
- lower dependence on shallow token-form shortcuts.

A weaker model may still answer many tasks while showing:

- token-bound label basins;
- poor carrier unification;
- leaky or absent boundaries;
- weak intervention coherence;
- brittle composition;
- prompt-family dependence.

This supports a distinct evaluation claim:

> Topological capability is an upstream capability surface. It measures
> what object world the model has learned before measuring how the model
> reasons over that world.

---

## 8. Reading Exp 32 Under This Frame

Exp 32 applies the topology frame to `value` in GPT-2 small.

The assay asks whether the residual at the token `value` separates
economic, accounting, policy, legal, insurance, moral, personal, social,
information, and medical regimes. It also runs a carrier contrast over
`value`, `price`, `cost`, and `worth` after varied left contexts.

Result:

- best ten-way `value`-regime accuracy is `0.233` at layer 2, against
  `0.100` chance;
- value-regime macro F1 is `0.195`;
- value-regime silhouette is negative (`-0.206`);
- carrier identity is perfectly linearly separable in the tested
  carrier assay;
- at layer 8, value-regime centroids are very close
  (`between - within` cosine distance only `0.0103`);
- carrier centroids are much more separated (`between - within`
  cosine distance `0.1569`);
- the `value` carrier centroid is closest to `price` (`0.8588`), then
  `cost` (`0.8323`), then `worth` (`0.8287`).

Topology reading:

> In GPT-2 small, `value` is primarily a lexical carrier basin with weak
> regime fibers. The tested residual chart does not expose a rich
> cross-regime value topology.

That is the candle baseline. It does not mean that `value` lacks a
topology in richer models. It means GPT-2 small does not strongly
separate market, legal, moral, policy, personal, and informational
regimes at the local `value` token under this assay.

---

## 9. Mining Agenda

The next discovery mode should search GPT-2 and stronger models for
regions where object boundaries are easiest to expose.

Candidate families:

- named entities: cities, countries, people, organizations;
- temporal objects: weekdays, months, holidays, years;
- formal schemas: JSON, Python syntax, URLs, email addresses, citations;
- institutional roles: capitals, presidents, legal articles, offices;
- physical and biological categories: water, gold, cell, dog, bridge;
- discourse objects: speaker, quote, list item, variable name;
- mathematical objects: operators, equations, units, shapes.

For each candidate family:

1. Generate carriers and contexts.
2. Measure carrier robustness.
3. Estimate core/coat decomposition.
4. Fit layer and module charts.
5. Test intervention leverage.
6. Test conditional closure.
7. Classify the discovered topology even when closure fails.

The output is a topology atlas, not just a pass/fail list.

---

## 10. Working Formulation

The research program should be stated this way:

> We evaluate LLMs as learned projected topologies. Markov-object assays
> measure whether a model has formed stable, bounded, compositional
> object structure before we evaluate downstream reasoning over that
> structure. Markov blankets are the strongest boundary result, but
> negative blanket tests still contribute by identifying the shape of
> the projected topology.
