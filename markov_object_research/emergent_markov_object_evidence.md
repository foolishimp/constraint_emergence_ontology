# Evidence Brief: Emergent Markov Object Proposition

**Status:** experimental evidence brief  
**Scope:** support and limits for the stronger emergence proposition  
**Companion to:** `emergence_conjecture_program.md`, `empirical_results.md`  
**Draft date:** 2026-04-24

---

## 1. Proposition

The stronger proposition is:

> A Markov object in an LLM is not owned by one local technological
> component. It is emergent from the constrained interaction of the
> technical stack and is projected through local representational charts.

This is stronger than the engineering claim. The engineering claim only
needs candidate object cuts, explicit projections, null peers, core/coat
evidence, and honest candidate status. The emergence proposition asks
whether local charts are partial views of a broader realized topology.

This brief grades the present experiments against that proposition.

---

## 2. Evidence Pattern

### 2.1 Single local chart is useful but insufficient

Exp 18 found a direction-native chart in residual space. A mean-difference
direction `d = mu(object) - mu(null)` transferred identity across held-out
prompts at layer 8, but only weakly: roughly `0.24-0.28` at `alpha=1`.

Exp 19 sharpened the result. At layer 8, adding rank did not close the
gap:

| layer | result | max transfer at alpha=1 |
|---|---:|---:|
| 8 | FAIL | 999: `0.259`, 666: `0.243`, 137: `0.284` |
| 2 | PASS | 999: `0.874`, 666: `0.928`, 137: `0.903` |

The same protocol is strong at layer 2 and weak at layer 8. That is not
consistent with one simple story in which the object is stored in a
single preferred layer-8 locus. It is more consistent with a chart whose
leverage depends on where the representation is sampled.

### 2.2 Direction family is coherent across layers

Exp 21 found strong adjacent-layer coherence across layers
`2/4/6/8/10/11`.

For the three targets, adjacent-layer cosines are all high:

| target | adjacent cosine range |
|---|---:|
| 999 | `0.927-0.960` for the main adjacent pairs, `0.941` for 10->11 |
| 666 | `0.932-0.954` for the main adjacent pairs, `0.940` for 10->11 |
| 137 | `0.921-0.962` for the main adjacent pairs |

The same-layer intervention strength then drops monotonically with depth:

| target | L2 | L4 | L6 | L8 | L10 | L11 |
|---|---:|---:|---:|---:|---:|---:|
| 999 | `0.872` | `0.611` | `0.382` | `0.258` | `0.195` | `0.094` |
| 666 | `0.927` | `0.572` | `0.419` | `0.241` | `0.150` | `0.068` |
| 137 | `0.903` | `0.581` | `0.449` | `0.275` | `0.164` | `0.099` |

This is the central positive evidence for the emergence reading:
directions are not random or local-only, but causal leverage is not
constant across the stack. The object looks like a coherent chart family,
not a single chart.

### 2.3 Single-chart promotion gate fails

Exp 20 is the direct conditional-independence proxy. After subtracting
the selected identity projection, the orthogonal residual remains fully
predictive of target identity.

| layer | k* | AUC(r_perp) | HSIC p | outcome |
|---|---:|---:|---:|---|
| 8 | 10 | `1.000` for all targets | `0.005` | FAIL |
| 2 | 1 | `1.000` for all targets | `0.005` | FAIL |

This is negative for the formal Markov-blanket promotion claim. It is
also positive for the emergence proposition in a narrower sense: one
local projection, even a strong one at layer 2, does not exhaust target
identity. Residual identity remains elsewhere in the realized system.

The correct reading is not "promotion passed." It did not. The correct
reading is: single-chart ownership failed.

### 2.4 SAE feature basis senses and fragments the object

Exps 08-17 show that SAE features provide an attribute basis, not the
object itself.

Observed pattern:

- cultural tokens recruit interpretable features;
- each target has a small invariant core and a large context-selected coat;
- core identity matters more than core size;
- overwriting outside the active feature set still leaks `23-28%`
  identity transfer;
- the identity direction has partial alignment with SAE-core decoder
  vectors, not identity with them.

This supports the projection reading. A feature dictionary senses the
object and fragments it across atoms. That is exactly the pattern expected
if local representations are charts over a broader realized topology.

### 2.5 Composition is real

Exp 23 tested whether identity directions compose.

Result:

| metric | value |
|---|---:|
| mean `cos(d_compound, d_A + d_B)` | `0.936` |
| mean random-pair cosine | `0.634` |
| excess over random null | `0.302` |
| permutation p-value | `0.0099` |

This is positive evidence that the direction family behaves object-like,
not merely as isolated probes. Composability is a key discriminator
between "feature cluster" and "candidate Markov object."

### 2.6 First cross-model replication is positive

Exp 24 ported the direction-native transfer assay to Pythia-160M without
SAEs.

| target | alpha=1 transfer | relaxed threshold |
|---|---:|---:|
| 999 | `0.207` | `0.1` |
| 666 | `0.176` | `0.1` |
| 137 | `0.159` | `0.1` |

All three targets pass the relaxed replication criterion. This does not
prove substrate neutrality. It does show the phenomenon is not GPT-2-only.

### 2.7 Behavioural generation remains inconclusive

Exp 22 did not provide clean behavioural closure. Both layer-8 and layer-2
free-form generation assays are confounded by high reference-class
baseline rates at `alpha=0`.

That matters because the emergence proposition should eventually explain
object-level behavior, not only residual geometry. The present evidence is
geometric and intervention-local, not yet behaviorally closed.

---

## 3. Evidence Grade

Current evidence supports this narrower claim:

> Candidate Markov-object identity is expressed by a coherent,
> layer-sensitive direction family whose local charts compose and begin
> to replicate across model families, while no tested single chart closes
> the conditional-independence gate.

That is evidence for emergent realization over local ownership.

Current evidence does not support the stronger claim:

> The Markov object is formally established as a Markov blanket in the
> tested system.

The promotion gate fails at both tested layers. Accepted status is not
earned.

---

## 4. Alternative Explanations Still Live

The current results do not eliminate these readings:

- **Early-layer ownership:** layer 2 may be the primary local owner, with
  later layers carrying transformed traces. Exp 20 weakens this because
  subtracting the layer-2 chart leaves identity perfectly predictable, but
  it does not fully rule it out.
- **Prompt-template artefact:** paired templates may induce a reusable
  contrast direction that is less general than object identity.
- **Token-form artefact:** GPT-2 scale remains symbol-bound. The result may
  concern token identities more than concepts.
- **Representation-family artefact:** GPT-2 small plus Pythia-160M is not
  broad model coverage.
- **Probe strength mismatch:** the CI failure may show that the projection
  is insufficient, or that the residual probe can exploit information that
  is not object-level in the intended sense.

These alternatives define the next discriminators.

---

## 5. Discriminating Next Experiments

The next evidence wave should not soften the promotion gate. It should
test whether the failed gate was using the wrong chart.

### 5.1 Multi-layer realized-topology conditioning

Build a joint chart over layers `2/4/6/8`, then condition on the joint
coordinates and test whether residual target prediction drops.

Prediction if the emergence proposition is right:

- joint conditioning reduces residual identity signal more than the best
  single-layer subtraction;
- residual AUC and HSIC weaken materially relative to exp 20.

Prediction if local-chart ownership is right:

- the best single chart performs about as well as the joint chart.

### 5.2 Distributed ownership audit

Compare:

- best single-layer direction;
- best single head or MLP-family intervention;
- matched distributed intervention across layers.

Prediction if the emergence proposition is right:

- distributed intervention dominates any single local locus.

### 5.3 Partial-chart reconstitution

Take individually weak charts from several layers or bases and test
whether their combination reconstructs identity more strongly than any
one chart alone.

Prediction if the emergence proposition is right:

- subcritical local views compose into a strong realized view.

### 5.4 Training trajectory

Run the same assay across checkpoints.

Prediction if the emergence proposition is right:

- chart coherence, composition, and resistance to single-chart CI closure
  appear gradually as the model learns the object.

### 5.5 Broader implementation variation

Repeat the assay across more model families, scales, and tokenizers.

Prediction if the emergence proposition is right:

- local realization moves, but the higher-order pattern persists:
  coherent charts, positive composition, single-chart insufficiency.

---

## 6. Working Conclusion

The strongest current conclusion is:

> The experiments support an emergent-chart reading of candidate Markov
> objects. Identity is not exhausted by one SAE feature set, one residual
> direction, one rank-k layer-8 projector, or even one strong layer-2
> projector. It appears as a coherent family of projections across the
> stack, with layer-sensitive causal leverage, compositional algebra, and
> first cross-model replication. The formal Markov-blanket gate still
> fails, so the proposition remains a research conjecture, not an
> accepted result.

