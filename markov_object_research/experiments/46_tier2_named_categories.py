"""
Experiment 46 (Tier 2): Named-category continuation cluster — black-box

Tier 1 (exp 45) verified that continuations cluster by named entity. Tier 2
asks the harder question: does the model *abstract over instances* to a
category-level Markov object?

If yes:
  continuations from prompts containing different-instances-of-the-same-category
  should cluster together (category dominates clustering)
  even though instance-level identity also varies

The test compares THREE silhouette scores:
  - silhouette by CATEGORY  (target)
  - silhouette by INSTANCE  (within-category; should be lower if abstraction works)
  - silhouette by TEMPLATE  (control)

Pre-registered (Tier 2):
  PASS    silhouette(cat) >= 0.20  AND  silhouette(cat) > silhouette(inst) + 0.05
                                   AND  silhouette(cat) > silhouette(tpl)  + 0.10
  PARTIAL silhouette(cat) >= 0.10  AND  cat > inst AND cat > tpl
  FAIL    otherwise

Outputs:
  results/46_tier2_named_categories/
    report.txt, summary.json
    embedding_pca.png  (colored by category)
    silhouette_comparison.png
    continuation_examples.txt
"""

import json, time, random
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results" / "46_tier2_named_categories"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LLM_NAME = "meta-llama/Meta-Llama-3-8B"
DEVICE   = "mps"
DTYPE    = torch.float16
EMBED_MODEL = "all-mpnet-base-v2"

CATEGORIES = {
    "city":        ["London", "Paris", "Tokyo"],
    "weekday":     ["Monday", "Wednesday", "Friday"],
    "scientist":   ["Einstein", "Newton", "Darwin"],
    "monetary":    ["$5", "$100", "$1000"],
    "emotion":     ["happy", "sad", "angry"],
}

TEMPLATES = [
    "When I think of {e},",
    "The thing about {e} is",
    "People often associate {e} with",
    "In a few words, {e} means",
]

N_GEN_PER_PROMPT = 5
MAX_NEW_TOKENS  = 24
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
    em = SentenceTransformer(EMBED_MODEL)
    return em


def generate_continuations(model, prompt, n=N_GEN_PER_PROMPT,
                            max_new_tokens=MAX_NEW_TOKENS,
                            temperature=TEMPERATURE):
    outputs = []
    tokens = model.to_tokens(prompt, prepend_bos=True).to(DEVICE)
    for i in range(n):
        torch.manual_seed(SEED + i * 17 + hash(prompt) % 100)
        with torch.no_grad():
            gen = model.generate(
                tokens, max_new_tokens=max_new_tokens,
                temperature=temperature, top_k=40, top_p=0.95,
                stop_at_eos=True, verbose=False,
            )
        text = model.tokenizer.decode(gen[0].cpu().tolist(),
                                       skip_special_tokens=True)
        completion = text[len(prompt):].strip() if text.startswith(prompt) else text.strip()
        outputs.append(completion)
    return outputs


def main():
    random.seed(SEED); torch.manual_seed(SEED); np.random.seed(SEED)
    llm = load_llm()
    embedder = load_embedder()

    print("\n=== generation phase ===")
    samples = []
    examples_log = []
    total_cells = sum(len(insts) for insts in CATEGORIES.values()) * len(TEMPLATES)
    cell = 0
    t_total_start = time.time()
    for cat, instances in CATEGORIES.items():
        for inst in instances:
            for tmpl in TEMPLATES:
                cell += 1
                prompt = tmpl.format(e=inst)
                t0 = time.time()
                comps = generate_continuations(llm, prompt)
                elapsed = time.time() - t0
                for c in comps:
                    samples.append({"category": cat, "instance": inst,
                                      "template": tmpl, "prompt": prompt,
                                      "completion": c})
                print(f"  [{cell:3d}/{total_cells} cat={cat:<10s} "
                      f"inst={inst:<10s} t={tmpl[:25]:<25s}] "
                      f"{N_GEN_PER_PROMPT} in {elapsed:.1f}s")
                if cell <= 20 or cell % 10 == 0:
                    examples_log.append(f"\n## {cat}|{inst}|{tmpl}")
                    for c in comps[:2]:
                        examples_log.append(f"    > {c[:200]}")
    print(f"\nTotal generation time: {(time.time()-t_total_start)/60:.1f} min")
    print(f"Total samples: {len(samples)}")

    print("\n=== embedding phase ===")
    completions = [s["completion"] for s in samples]
    embeddings = embedder.encode(completions, show_progress_bar=False,
                                   convert_to_numpy=True)
    print(f"  embedded {len(completions)} continuations -> {embeddings.shape}")

    cat_labels   = [s["category"] for s in samples]
    inst_labels  = [s["instance"] for s in samples]
    tpl_labels   = [s["template"] for s in samples]

    print("\n=== silhouette / cluster geometry ===")
    sil_cat   = float(silhouette_score(embeddings, cat_labels,  metric="cosine"))
    sil_inst  = float(silhouette_score(embeddings, inst_labels, metric="cosine"))
    sil_tpl   = float(silhouette_score(embeddings, tpl_labels,  metric="cosine"))
    print(f"  silhouette by CATEGORY:  {sil_cat:+.3f}")
    print(f"  silhouette by INSTANCE:  {sil_inst:+.3f}")
    print(f"  silhouette by TEMPLATE:  {sil_tpl:+.3f}")

    # Per-category centroid + within-category tightness
    cat_centroids = {}
    cat_within   = {}
    for cat in CATEGORIES.keys():
        mask = np.array([s["category"] == cat for s in samples])
        em = embeddings[mask]
        c = em.mean(0)
        cat_centroids[cat] = c
        cn = c / (np.linalg.norm(c) + 1e-9)
        en = em / (np.linalg.norm(em, axis=1, keepdims=True) + 1e-9)
        cat_within[cat] = float(np.mean(en @ cn))
    print("\n  per-category within-cluster cosine to centroid:")
    for cat, v in cat_within.items():
        print(f"    {cat:<10s}  {v:+.3f}")

    # Per-instance within-instance tightness (should also be high; we want to
    # show category-level >= category-level even with instance variation).
    inst_within = {}
    for cat, insts in CATEGORIES.items():
        for inst in insts:
            mask = np.array([s["instance"] == inst for s in samples])
            em = embeddings[mask]
            if len(em) == 0:
                continue
            c = em.mean(0); cn = c / (np.linalg.norm(c) + 1e-9)
            en = em / (np.linalg.norm(em, axis=1, keepdims=True) + 1e-9)
            inst_within[f"{cat}/{inst}"] = float(np.mean(en @ cn))
    avg_inst_within = float(np.mean(list(inst_within.values())))
    avg_cat_within  = float(np.mean(list(cat_within.values())))
    print(f"\n  avg within-CATEGORY tightness: {avg_cat_within:+.3f}")
    print(f"  avg within-INSTANCE tightness:  {avg_inst_within:+.3f}")
    # If within-instance > within-category, instance is tighter (model
    # discriminates instances). If similar, category-level abstraction is real.

    # Pairwise category centroid cosines
    cats = list(CATEGORIES.keys())
    cat_pair_cos = {}
    for i, c1 in enumerate(cats):
        for c2 in cats[i+1:]:
            v1 = cat_centroids[c1] / (np.linalg.norm(cat_centroids[c1]) + 1e-9)
            v2 = cat_centroids[c2] / (np.linalg.norm(cat_centroids[c2]) + 1e-9)
            cat_pair_cos[f"{c1}--{c2}"] = float(np.dot(v1, v2))

    # Verdict
    if sil_cat >= 0.20 and sil_cat > sil_inst + 0.05 and sil_cat > sil_tpl + 0.10:
        verdict = "PASS"
    elif sil_cat >= 0.10 and sil_cat > sil_inst and sil_cat > sil_tpl:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    print(f"\nVERDICT: {verdict}")

    # Plots
    pca = PCA(n_components=2)
    proj = pca.fit_transform(embeddings)
    fig, ax = plt.subplots(figsize=(11, 8))
    cmap = plt.cm.tab10(np.linspace(0, 1, len(CATEGORIES)))
    for color, cat in zip(cmap, CATEGORIES.keys()):
        mask = np.array([s["category"] == cat for s in samples])
        ax.scatter(proj[mask, 0], proj[mask, 1], color=color, label=cat,
                   alpha=0.6, s=30)
        cm = proj[mask].mean(0)
        ax.scatter(cm[0], cm[1], color=color, marker="X", s=300,
                   edgecolors="black", linewidths=1.5)
        # Annotate per-instance centroids with smaller markers
        for inst in CATEGORIES[cat]:
            mask_i = np.array([s["instance"] == inst for s in samples])
            if mask_i.sum() == 0:
                continue
            cm_i = proj[mask_i].mean(0)
            ax.annotate(inst, (cm_i[0], cm_i[1]), fontsize=8, alpha=0.7,
                         color=color)
    ax.legend(fontsize=10, loc="best")
    ax.set_title(f"PCA — colored by CATEGORY, instances annotated\n"
                 f"silhouette: cat {sil_cat:+.3f}  inst {sil_inst:+.3f}  "
                 f"tpl {sil_tpl:+.3f}")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% var)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% var)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "embedding_pca.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(["category", "instance", "template"],
                   [sil_cat, sil_inst, sil_tpl],
                   color=["steelblue", "tomato", "lightgray"])
    ax.axhline(0.20, color="green", linestyle="--", alpha=0.5, label="PASS thr 0.20")
    ax.axhline(0.10, color="orange", linestyle="--", alpha=0.5, label="PARTIAL thr 0.10")
    ax.set_ylabel("silhouette score (cosine)")
    ax.set_title("Tier 2: silhouette by category vs instance vs template")
    ax.legend(); ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "silhouette_comparison.png", dpi=150)
    plt.close(fig)

    (RESULTS_DIR / "continuation_examples.txt").write_text("\n".join(examples_log))

    # Report
    lines = [f"Exp 46 - Tier 2 Named-Category Continuation Cluster",
             f"Substrate: {LLM_NAME}   Embedder: {EMBED_MODEL}", "=" * 70, ""]
    lines.append(f"Categories ({len(CATEGORIES)}): {list(CATEGORIES.keys())}")
    for cat, insts in CATEGORIES.items():
        lines.append(f"  {cat}: {insts}")
    lines.append(f"Templates: {len(TEMPLATES)}, "
                 f"Generations per (instance, template): {N_GEN_PER_PROMPT}")
    lines.append(f"Total samples: {len(samples)}")
    lines.append("")
    lines.append("Pre-registered outcome rules:")
    lines.append("  PASS    silhouette(cat) >= 0.20  AND  cat > inst + 0.05  AND  cat > tpl + 0.10")
    lines.append("  PARTIAL silhouette(cat) >= 0.10  AND  cat > inst AND cat > tpl")
    lines.append("  FAIL    otherwise")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict}")
    lines.append(f"  silhouette by CATEGORY: {sil_cat:+.3f}")
    lines.append(f"  silhouette by INSTANCE: {sil_inst:+.3f}")
    lines.append(f"  silhouette by TEMPLATE: {sil_tpl:+.3f}")
    lines.append(f"  category - instance gap: {sil_cat - sil_inst:+.3f}")
    lines.append(f"  category - template gap: {sil_cat - sil_tpl:+.3f}")
    lines.append("")
    lines.append("Per-category within-cluster cosine to centroid:")
    for cat, v in cat_within.items():
        lines.append(f"  {cat:<10s}  {v:+.3f}")
    lines.append("")
    lines.append(f"avg within-CATEGORY tightness: {avg_cat_within:+.3f}")
    lines.append(f"avg within-INSTANCE tightness: {avg_inst_within:+.3f}")
    lines.append("")
    lines.append("Pairwise category centroid cosine (lower = more separated):")
    for k, v in sorted(cat_pair_cos.items(), key=lambda x: -x[1]):
        lines.append(f"  {k:<32s}  {v:+.3f}")
    (RESULTS_DIR / "report.txt").write_text("\n".join(lines))
    print(f"\nReport: {RESULTS_DIR / 'report.txt'}")

    summary = {
        "design": "exp 46: Tier 2 named-category continuation cluster",
        "llm": LLM_NAME,
        "embedder": EMBED_MODEL,
        "categories": CATEGORIES,
        "templates": TEMPLATES,
        "n_total_samples": len(samples),
        "silhouette_by_category": sil_cat,
        "silhouette_by_instance": sil_inst,
        "silhouette_by_template": sil_tpl,
        "category_minus_instance_gap": sil_cat - sil_inst,
        "category_minus_template_gap": sil_cat - sil_tpl,
        "per_category_within_cosine": cat_within,
        "per_instance_within_cosine": inst_within,
        "avg_within_category": avg_cat_within,
        "avg_within_instance": avg_inst_within,
        "pairwise_category_centroid_cosines": cat_pair_cos,
        "verdict": verdict,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
