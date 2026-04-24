"""
Experiment 01: Activation Clustering

Does GPT-2 encode concepts as stable, bounded regions in activation space?

Method:
  - Run each prompt family through GPT-2
  - Extract hidden states at each layer (mean-pooled over tokens)
  - Reduce to 2D with UMAP
  - Plot: if Markov objects exist, same-family prompts cluster together
    and different-family prompts separate

One plot per layer, plus a summary across all layers.
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from prompts.concept_families import CONCEPT_FAMILIES

RESULTS_DIR = Path(__file__).parent.parent / "results" / "01_activation_clustering"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_model():
    import torch
    from transformers import GPT2Model, GPT2Tokenizer
    print("Loading GPT-2...")
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    model = GPT2Model.from_pretrained("gpt2", output_hidden_states=True)
    model.eval()
    return model, tokenizer, torch


def extract_activations(model, tokenizer, torch, prompts):
    """
    Returns: activations of shape (n_prompts, n_layers, hidden_size)
    Each layer vector is mean-pooled over token positions.
    """
    all_hidden = []
    with torch.no_grad():
        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt")
            outputs = model(**inputs)
            # hidden_states: tuple of (n_layers+1) tensors, each (1, seq_len, hidden_size)
            # index 0 is embedding layer, 1..12 are transformer layers
            layer_vecs = [
                hs[0].mean(dim=0).numpy()  # mean over tokens → (hidden_size,)
                for hs in outputs.hidden_states
            ]
            all_hidden.append(layer_vecs)
    # shape: (n_prompts, n_layers+1, hidden_size)
    return np.array(all_hidden)


def build_labels(families):
    labels, family_names = [], []
    for name, prompts in families.items():
        for _ in prompts:
            labels.append(name)
            family_names.append(name)
    return labels


def reduce_umap(vectors):
    from umap import UMAP
    reducer = UMAP(n_components=2, random_state=42, n_neighbors=5, min_dist=0.1)
    return reducer.fit_transform(vectors)


def reduce_pca(vectors):
    from sklearn.decomposition import PCA
    return PCA(n_components=2, random_state=42).fit_transform(vectors)


def reduce(vectors):
    try:
        return reduce_umap(vectors), "UMAP"
    except ImportError:
        print("umap-learn not available, falling back to PCA")
        return reduce_pca(vectors), "PCA"


def plot_layer(coords, labels, layer_idx, method, out_path):
    families = list(CONCEPT_FAMILIES.keys())
    palette = sns.color_palette("tab10", n_colors=len(families))
    color_map = {name: palette[i] for i, name in enumerate(families)}

    fig, ax = plt.subplots(figsize=(9, 7))
    for family in families:
        mask = [l == family for l in labels]
        xs = coords[mask, 0]
        ys = coords[mask, 1]
        ax.scatter(xs, ys, label=family, color=color_map[family], s=80, alpha=0.85)

    ax.set_title(f"Layer {layer_idx} — {method}")
    ax.set_xlabel(f"{method} dim 1")
    ax.set_ylabel(f"{method} dim 2")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  saved: {out_path.name}")


def cluster_separation_score(coords, labels):
    """
    Ratio of between-family to within-family variance.
    Higher = better separation = more evidence of bounded regions.
    """
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    numeric_labels = le.fit_transform(labels)
    if len(set(numeric_labels)) < 2:
        return float("nan")
    return silhouette_score(coords, numeric_labels)


def main():
    model, tokenizer, torch = load_model()

    all_prompts = []
    labels = []
    for name, prompts in CONCEPT_FAMILIES.items():
        all_prompts.extend(prompts)
        labels.extend([name] * len(prompts))

    print(f"Extracting activations for {len(all_prompts)} prompts...")
    activations = extract_activations(model, tokenizer, torch, all_prompts)
    # activations: (n_prompts, n_layers+1, hidden_size)

    n_layers = activations.shape[1]
    scores = {}

    print(f"\nReducing and plotting {n_layers} layers...")
    for layer_idx in range(n_layers):
        layer_vecs = activations[:, layer_idx, :]  # (n_prompts, hidden_size)
        coords, method = reduce(layer_vecs)
        score = cluster_separation_score(coords, labels)
        scores[layer_idx] = score

        out_path = RESULTS_DIR / f"layer_{layer_idx:02d}.png"
        plot_layer(coords, labels, layer_idx, method, out_path)

    # Summary: silhouette score per layer
    print("\nSilhouette scores by layer (higher = cleaner concept separation):")
    print(f"{'Layer':>6}  {'Score':>8}")
    for idx, score in scores.items():
        bar = "█" * int(max(0, score) * 30)
        print(f"{idx:>6}  {score:>8.3f}  {bar}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(list(scores.keys()), list(scores.values()), marker="o")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Layer")
    ax.set_ylabel("Silhouette score")
    ax.set_title("Concept separation by layer\n(evidence of Markov objects)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    summary_path = RESULTS_DIR / "silhouette_by_layer.png"
    fig.savefig(summary_path, dpi=150)
    plt.close(fig)
    print(f"\nSummary chart: {summary_path}")
    print(f"\nAll results in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
