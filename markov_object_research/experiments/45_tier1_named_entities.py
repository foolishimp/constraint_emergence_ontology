"""
Experiment 45 (Tier 1): Named-entity continuation cluster — black-box

Methodology calibration. The simplest possible test of the manifold-side
empirical program: do continuations from prompts containing different named
entities cluster cleanly in semantic embedding space?

If YES (clean per-entity clusters, high silhouette score, stable across
templates) — the black-box methodology works at the easiest case and we can
proceed up the tier ladder.

If NO — the methodology is broken (cannot detect even Tier 1 named entities).
Stop and revise.

Method:
  1. Pick 5 named entities (heterogeneous: city, weekday, person, decade, etc).
  2. For each entity, 6 prompt templates that elicit a continuation about the entity.
  3. Generate K=8 continuations per (entity, template) at temperature=0.7.
  4. Embed all continuations using sentence-transformers all-mpnet-base-v2.
  5. Compute geometry:
     - silhouette score by entity-label across all continuations
     - silhouette score by template-label (control: should be lower)
     - between-cluster vs within-cluster distance ratio per entity
     - cluster stability: re-run with different generation seeds, do clusters agree
  6. Verdict (per design doc 45 Tier 1):
     PASS    silhouette by entity >= 0.30  AND  silhouette by entity > silhouette by template + 0.15
     PARTIAL silhouette by entity >= 0.10  but does not dominate template
     FAIL    no clean entity clustering — instrument broken

Outputs:
  results/45_tier1_named_entities/
    report.txt
    summary.json
    cluster_silhouette.png
    embedding_pca.png
    continuation_examples.txt
"""

import json, os, time, random
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results" / "45_tier1_named_entities"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Substrate: Llama-3 8B (already cached). For Tier 1 calibration one substrate
# is enough; cross-substrate test happens in exp 50.
LLM_NAME = "meta-llama/Meta-Llama-3-8B"
DEVICE   = "mps"
DTYPE    = torch.float16

# Embedder: sentence-transformers all-mpnet-base-v2 (768-dim).
EMBED_MODEL = "all-mpnet-base-v2"

ENTITIES = [
    "London",      # city
    "Tuesday",     # weekday
    "Madonna",     # person (proper noun, contemporary)
    "Einstein",    # person (proper noun, historical)
    "1492",        # year (numeric proper)
]

TEMPLATES = [
    "When I think of {e},",
    "The thing about {e} is",
    "People often associate {e} with",
    "What everyone knows about {e}:",
    "If you've heard of {e}, you know that",
    "In a few words, {e} means",
]

N_GEN_PER_PROMPT = 8
MAX_NEW_TOKENS  = 32
TEMPERATURE     = 0.8
SEED            = 42


def load_llm():
    from transformer_lens import HookedTransformer
    print(f"Loading {LLM_NAME} on {DEVICE} ({DTYPE})...")
    t0 = time.time()
    model = HookedTransformer.from_pretrained(LLM_NAME, device=DEVICE,
                                                dtype=DTYPE)
    model.eval()
    print(f"  loaded in {time.time()-t0:.1f}s.")
    return model


def load_embedder():
    from sentence_transformers import SentenceTransformer
    print(f"Loading embedder {EMBED_MODEL} ...")
    t0 = time.time()
    em = SentenceTransformer(EMBED_MODEL)
    print(f"  loaded in {time.time()-t0:.1f}s.")
    return em


def generate_continuations(model, prompt, n=N_GEN_PER_PROMPT,
                            max_new_tokens=MAX_NEW_TOKENS,
                            temperature=TEMPERATURE):
    """Use HookedTransformer.generate() with stochastic sampling."""
    outputs = []
    tokens = model.to_tokens(prompt, prepend_bos=True).to(DEVICE)
    for i in range(n):
        torch.manual_seed(SEED + i)
        with torch.no_grad():
            gen = model.generate(
                tokens,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_k=40,
                top_p=0.95,
                stop_at_eos=True,
                verbose=False,
            )
        text = model.tokenizer.decode(gen[0].cpu().tolist(),
                                       skip_special_tokens=True)
        # Strip prompt prefix
        completion = text[len(prompt):].strip() if text.startswith(prompt) else text.strip()
        outputs.append(completion)
    return outputs


def main():
    random.seed(SEED)
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    llm = load_llm()
    embedder = load_embedder()

    print("\n=== generation phase ===")
    samples = []  # list of {entity, template, completion, prompt}
    examples_log = []
    for entity in ENTITIES:
        for tmpl in TEMPLATES:
            prompt = tmpl.format(e=entity)
            print(f"  [{entity:>10s} | {tmpl[:30]:<30s}] generating {N_GEN_PER_PROMPT} ...")
            t0 = time.time()
            comps = generate_continuations(llm, prompt)
            for c in comps:
                samples.append({"entity": entity, "template": tmpl,
                                  "prompt": prompt, "completion": c})
            elapsed = time.time() - t0
            examples_log.append(f"\n## {entity}  |  {tmpl}\n  [{elapsed:.1f}s for {N_GEN_PER_PROMPT}]")
            for c in comps[:3]:
                examples_log.append(f"    > {c[:200]}")

    print(f"\nTotal samples: {len(samples)}")

    print("\n=== embedding phase ===")
    completions = [s["completion"] for s in samples]
    t0 = time.time()
    embeddings = embedder.encode(completions, show_progress_bar=False,
                                   convert_to_numpy=True)
    print(f"  embedded {len(completions)} continuations in {time.time()-t0:.1f}s")
    print(f"  embedding shape: {embeddings.shape}")

    # Labels
    entity_labels = [s["entity"] for s in samples]
    template_labels = [s["template"] for s in samples]

    # Silhouette
    print("\n=== silhouette / cluster geometry ===")
    sil_entity = float(silhouette_score(embeddings, entity_labels,
                                          metric="cosine"))
    sil_template = float(silhouette_score(embeddings, template_labels,
                                            metric="cosine"))
    print(f"  silhouette by entity:   {sil_entity:+.3f}")
    print(f"  silhouette by template: {sil_template:+.3f}")

    # Per-entity centroid distances
    centroids = {}
    for e in ENTITIES:
        mask = np.array([s["entity"] == e for s in samples])
        centroids[e] = embeddings[mask].mean(axis=0)
    pairwise = {}
    for i, e1 in enumerate(ENTITIES):
        for e2 in ENTITIES[i+1:]:
            c1 = centroids[e1] / (np.linalg.norm(centroids[e1]) + 1e-9)
            c2 = centroids[e2] / (np.linalg.norm(centroids[e2]) + 1e-9)
            cos = float(np.dot(c1, c2))
            pairwise[f"{e1}--{e2}"] = cos
    mean_pairwise_cos = float(np.mean(list(pairwise.values())))
    print(f"  mean pairwise cosine between entity centroids: {mean_pairwise_cos:+.3f}")
    print(f"    (lower = entities more separated)")

    # Within-cluster spread
    within = {}
    for e in ENTITIES:
        mask = np.array([s["entity"] == e for s in samples])
        em = embeddings[mask]
        cm = em.mean(axis=0)
        cm_n = cm / (np.linalg.norm(cm) + 1e-9)
        en = em / (np.linalg.norm(em, axis=1, keepdims=True) + 1e-9)
        within_cos = float(np.mean(en @ cm_n))
        within[e] = within_cos
    mean_within = float(np.mean(list(within.values())))
    print(f"  mean within-entity cosine to centroid: {mean_within:+.3f}")
    print(f"    (higher = tighter clusters)")

    # Verdict
    if sil_entity >= 0.30 and sil_entity > sil_template + 0.15:
        verdict = "PASS"
    elif sil_entity >= 0.10:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    print(f"\nVERDICT: {verdict}")

    # PCA visualization
    print("\n=== visualization ===")
    pca = PCA(n_components=2)
    proj = pca.fit_transform(embeddings)
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.tab10(np.linspace(0, 1, len(ENTITIES)))
    for color, e in zip(colors, ENTITIES):
        mask = np.array([s["entity"] == e for s in samples])
        ax.scatter(proj[mask, 0], proj[mask, 1], color=color, label=e,
                   alpha=0.7, s=30)
        cm = proj[mask].mean(axis=0)
        ax.scatter(cm[0], cm[1], color=color, marker="X", s=300,
                   edgecolors="black", linewidths=1.5)
    ax.legend(fontsize=10)
    ax.set_title(f"PCA of continuation embeddings by entity\n"
                 f"silhouette: entity {sil_entity:+.3f} vs template {sil_template:+.3f}")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% var)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% var)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "embedding_pca.png", dpi=150)
    plt.close(fig)
    print(f"  saved: embedding_pca.png")

    # Silhouette comparison plot
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(["by entity", "by template"], [sil_entity, sil_template],
                   color=["steelblue", "lightgray"])
    ax.axhline(0.30, color="green", linestyle="--", alpha=0.5, label="PASS thr 0.30")
    ax.axhline(0.10, color="orange", linestyle="--", alpha=0.5, label="PARTIAL thr 0.10")
    ax.set_ylabel("silhouette score (cosine)")
    ax.set_title("Cluster coherence: entity vs template labelling")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "cluster_silhouette.png", dpi=150)
    plt.close(fig)
    print(f"  saved: cluster_silhouette.png")

    # Continuation examples
    (RESULTS_DIR / "continuation_examples.txt").write_text("\n".join(examples_log))

    # Report
    lines = [f"Exp 45 - Tier 1 Named-Entity Continuation Cluster (black-box)",
             f"Substrate: {LLM_NAME}   Embedder: {EMBED_MODEL}", "=" * 70, ""]
    lines.append(f"Entities:  {ENTITIES}")
    lines.append(f"Templates: {len(TEMPLATES)} per entity")
    lines.append(f"Generations per (entity, template): {N_GEN_PER_PROMPT}")
    lines.append(f"Max new tokens: {MAX_NEW_TOKENS}, temperature: {TEMPERATURE}")
    lines.append(f"Total samples: {len(samples)}")
    lines.append("")
    lines.append("Pre-registered outcome rules:")
    lines.append("  PASS    silhouette(entity) >= 0.30 AND silhouette(entity) > silhouette(template) + 0.15")
    lines.append("  PARTIAL silhouette(entity) >= 0.10")
    lines.append("  FAIL    otherwise")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict}")
    lines.append(f"  silhouette by entity:   {sil_entity:+.3f}")
    lines.append(f"  silhouette by template: {sil_template:+.3f}")
    lines.append(f"  mean pairwise centroid cosine: {mean_pairwise_cos:+.3f}")
    lines.append(f"  mean within-entity centroid cosine: {mean_within:+.3f}")
    lines.append("")
    lines.append("Per-entity within-cluster cosine:")
    for e, v in within.items():
        lines.append(f"  {e:>10s}  {v:+.3f}")
    lines.append("")
    lines.append("Pairwise entity centroid cosine (lower = more separated):")
    for k, v in sorted(pairwise.items(), key=lambda x: -x[1]):
        lines.append(f"  {k:<28s} {v:+.3f}")
    (RESULTS_DIR / "report.txt").write_text("\n".join(lines))
    print(f"\nReport: {RESULTS_DIR / 'report.txt'}")

    summary = {
        "design": "exp 45: Tier 1 named-entity continuation cluster",
        "llm": LLM_NAME,
        "embedder": EMBED_MODEL,
        "entities": ENTITIES,
        "templates": TEMPLATES,
        "n_gen_per_prompt": N_GEN_PER_PROMPT,
        "n_total_samples": len(samples),
        "silhouette_by_entity":   sil_entity,
        "silhouette_by_template": sil_template,
        "mean_pairwise_centroid_cosine": mean_pairwise_cos,
        "mean_within_entity_cosine":     mean_within,
        "per_entity_within_cosine": within,
        "pairwise_centroid_cosines": pairwise,
        "verdict": verdict,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
