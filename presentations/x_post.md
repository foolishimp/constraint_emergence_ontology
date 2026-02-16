# X Post

A little over three years ago, ChatGPT (GPT-3.5) took off and pushed me into an existential question: how is this thing appearing to reason?
As an IT professional, there seemed no bigger question to answer, so I obsessively went down the rabbit hole.
Six months ago, I published my thoughts on the mechanism behind that question.

**Thinking Without the Thinker.**

In trying to program an LLM, I ran thought experiments on how it might be doing what looked like reasoning.
I had recently read *A Thousand Brains* by Jeff Hawkins. His model of cortical columns as distributed model-builders pushed me to ask: how do biological brains reason at all?
The answer pointed toward traversal across constraint surfaces. The Transformer's attention mechanism looked like the same operation.
That became the emergent reasoning hypothesis.

https://doi.org/10.5281/zenodo.16592399

**Reality in the Gaps.**

The constraint framing came from merging emergence thinking with Terence Deacon's work on absential constraints, plus computational ideas from Stephen Wolfram.
The constraint structures I was seeing in LLMs turned out to be the same structures I had been thinking about in physics, biology, and cognition:
stable patterns that emerge not from the material itself, but from the gaps between constraints.
These long-brewing ideas found a formal home in the *Constraint-Emergence Ontology* — which is really more a personal philosophical foundation for how I reason about everything.

https://doi.org/10.5281/zenodo.18573722

**How to Program Your LLM.**

Instead of prompting an LLM with instructions, you can load a constraint specification: axioms, invariants, and an evaluation algorithm. The model shifts from generative peer to mechanical evaluator. Different specifications produce mechanically different outputs from the same input. The method is domain-agnostic: politics, law, medicine, software governance.

This echoes how biological brains work. Mark Solms' *The Hidden Spring* showed me the connection: the brainstem doesn't just keep the lights on — it sets the priority structure that the cortex computes within. The brainstem prompt-engineers the frontal cortex, through emotions. We don't reason first and then care. We care first, and reasoning serves that.

When we load a constraint specification into an LLM, we're doing something analogous to what the brainstem does to the cortex — providing the intentional structure that shapes what the computation produces.

I'm working on this "Consciousness Loop" in the AI SDLC methodology, from which intentionality arises, but that's a future post.

https://doi.org/10.5281/zenodo.18653641

**Before AI Safety, Human Safety.**

This raised an obvious question: if constraint specifications determine what an LLM produces, then AI safety is really about which specifications we load. But you can't define AI safety without first defining what human safety looks like. That's a political question.

**The Operating System Your Society Runs On.**

Four political philosophies — Classical Liberal, Marxist, Critical Justice, Theocratic — each expressed as a formal constraint specification you can load into an LLM. Ask it to evaluate a political event and it reasons within that framework's axioms. The divergence is mechanical, not rhetorical.

Some of what fell out:

- Critical Justice and Theocratic specifications are structurally isomorphic despite opposite content. Same architecture: unfalsifiable axioms, no internal correction mechanism, diagnostic without governance. They're the same program wearing different clothes.

- The Marxist specification has a governance gap. Strong diagnosis of exploitation, then a hand-wave at the vanguard transition. The gap is structural, not historical — it's in the spec itself.

- The same diagnostic produces opposite outcomes depending on where it sits in the governance stack. A program that identifies structural power can protect invariants when running on a liberal OS, or degrade them when it tries to become the OS.

https://doi.org/10.5281/zenodo.18638454

**Are You Losing Your Democracy?**

Six real-world analyses: Australia, UK, Canada, Germany, the United States, and California. Each scored against one framework's invariants using real legislation from 2020-2026.

The prediction: constitutional hardening of foundational commitments determines whether democratic self-correction succeeds or fails. Tradition-carried invariants (Australia, UK) are fragile. Constitutionally hardened invariants (US, Germany) resist — but Germany's militant democracy doctrine creates an override mechanism that allows degradation through the constitution rather than despite it. Canada's Charter contains its own escape valve (Section 33). California shows that sub-national governance can degrade invariants but federal courts + ballot initiatives + exit provide three correction layers.

The evidence confirmed the prediction across all six cases. The spectrum runs from Australia (no constitutional wall, tradition-only defence) to the US (strongest hardening, but speed and standing gaps). Every case found the same pattern: invariant degradation succeeds where there's no constitutional mechanism to stop it, and fails where there is — unless the constitutional mechanism itself contains an override.

**Why this matters for AI.**

If we're building guardrails for AI systems, the framework we choose is a constraint specification whether we acknowledge it or not. "Align AI with human values" is a spec — it just hasn't been written down. Making these specifications explicit, formal, and testable is the difference between guardrails and ideology.

The political proof of concept demonstrates the stakes: load different axioms, get different conclusions. If the axioms aren't visible, you can't audit the output. This is true for political systems and it's true for AI systems.

**Everything is open access.**

All four papers are on Zenodo. All constraint specifications — ready to load into any LLM — are on GitHub:

https://github.com/foolishimp/constraint_emergence_ontology

Try it yourself: load the Classical Liberal OS into Claude or ChatGPT and ask it to evaluate mandatory digital identity systems. Then load the Critical Justice OS in a new session with the same question. The divergence is mechanical. That's the point.

The self-referential joke from my original post still holds — I used the thing to build the thing that explains the thing. It's constraints all the way down.
