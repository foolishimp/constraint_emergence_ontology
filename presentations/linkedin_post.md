# LinkedIn Post

A little over three years ago, ChatGPT (GPT-3.5) took off and pushed me into an existential question: how is this thing appearing to reason?
As an IT professional, there seemed no bigger question to answer, so I obsessively went down the rabbit hole.
Six months ago, I published my thoughts on the mechanism behind that question.

**Thinking Without the Thinker.**

In trying to program an LLM, I ran thought experiments on how it might be doing what looked like reasoning.
I had recently read *A Thousand Brains* by Jeff Hawkins. His model of cortical columns as distributed model-builders pushed me to ask: how do biological brains reason at all?
The answer pointed toward traversal across constraint surfaces. The Transformer's attention mechanism looked like the same operation.
That became the emergent reasoning hypothesis.

Paper: *Emergent Reasoning in Large Language Models*
https://doi.org/10.5281/zenodo.16592399

**Reality in the Gaps.**

The constraint framing came from merging emergence thinking with Terence Deacon's work on absential constraints, plus universal computational ideas from Stephen Wolfram.
The constraint structures I was seeing in LLMs turned out to be the same structures I had been thinking about in physics, biology, and cognition:
stable patterns that emerge not from the material itself, but from the gaps between constraints.
These long-brewing ideas found a formal home in the *Constraint-Emergence Ontology* — which is really more a personal philosophical foundation for how I reason about everything.

Paper: *Constraint-Emergence Ontology*
https://doi.org/10.5281/zenodo.18573722

**How to Program Your LLM.**

Instead of prompting an LLM with instructions, you can load a constraint specification: axioms, invariants, and an evaluation algorithm. The model shifts from generative peer to mechanical evaluator. Different specifications produce mechanically different outputs from the same input. The method is domain-agnostic: politics, law, medicine, software governance.

This echoes how biological brains work. Mark Solms' *The Hidden Spring* showed me the connection: the brainstem doesn't just keep the lights on — it sets the priority structure that the cortex computes within. The brainstem prompt-engineers the frontal cortex, through emotions. We don't reason first and then care. We care first, and reasoning serves that.

When we load a constraint specification into an LLM, we're doing something analogous to what the brainstem does to the cortex — providing the intentional structure that shapes what the computation produces.

I'm working on this "Consciousness Loop" in the AI SDLC methodology, from which intentionality arises, but that's a future post.

Paper: *Programming LLM Reasoning*
https://doi.org/10.5281/zenodo.18653641

**Before AI Safety, Human Safety.**

This raised an obvious question: if constraint specifications determine what an LLM produces, then AI safety is really about which specifications we load. But you can't define AI safety without first defining what human safety looks like. That's a political question.

**The Operating System Your Society Runs On.**

Four political philosophies - Classical Liberal, Marxist, Critical Justice, Theocratic - each expressed as a formal constraint specification.
Load one into an LLM, ask it to evaluate a political event, and it reasons within that framework's axioms.
The same event produces structurally divergent analyses - not because of opinion, but because of different axiomatic starting points.

The suite includes six worked analyses applying one of the frameworks to real legislative programmes in Australia, the UK, Canada, Germany, the United States, and California. The focus is structural: how different constitutional architectures protect or fail to protect their own foundational commitments.

Paper: *The Political Operating System*
https://doi.org/10.5281/zenodo.18638455

This connects to AI governance.
If we are building guardrails for AI systems, the framework we choose is itself a constraint specification, whether we make it explicit or not.
Making these specifications visible and testable seems like a useful contribution to that conversation.

Everything is open access. The source — including all constraint specifications, ready to load into any LLM — is on GitHub:
https://github.com/foolishimp/constraint_emergence_ontology

If you're curious, load the Classical Liberal OS specification into Claude or ChatGPT and ask it to evaluate a policy question. Then try a different specification in a new session with the same question. The structural divergence is the point.

#AI #LLM #Philosophy #OpenAccess
