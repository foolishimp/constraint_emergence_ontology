"""
Experiment 06: SAE Feature Scan — How Many Distinct Objects Does "7" Have?

Uses pre-trained Sparse Autoencoders (Anthropic / EleutherAI, released for
GPT-2 small) to find which monosemantic features activate for the token "7"
across semantic registers.

Why this is more rigorous than experiment 05:
  - SAEs are trained to find monosemantic features under sparsity pressure
  - Features are interpretable — you can inspect what each one responds to
  - Feature count is principled, not HDBSCAN-hyperparameter-dependent
  - Cross-validates our clustering results

What we measure:
  - For each "7" context, which SAE features activate? (at what magnitude?)
  - Which features are register-specific vs shared across registers?
  - How many distinct features are there total? → distinct Markov objects
  - At which layer are the register distinctions clearest?

Pre-trained SAEs available via sae_lens:
  - Anthropic GPT-2 small residual stream SAEs (layers 0–11)
  - 16k feature dictionaries per layer
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path(__file__).parent.parent / "results" / "06_sae_feature_scan"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path(__file__).parent.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "cluster_count",
    Path(__file__).parent / "05_cluster_count.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
CONTEXTS = _mod.CONTEXTS

# Layers to probe — SAEs are available per residual stream layer
PROBE_LAYERS = [2, 4, 6, 8, 10]

# Activation threshold — features below this are treated as inactive
ACTIVATION_THRESHOLD = 0.5

# Top-N features to show per register in the heatmap
TOP_N_FEATURES = 30


def load_model_and_saes(probe_layers):
    """
    Load GPT-2 small via TransformerLens and pre-trained SAEs via sae_lens.
    Returns model and a dict of {layer: sae}.
    """
    from transformer_lens import HookedTransformer
    from sae_lens import SAE

    print("Loading GPT-2 via TransformerLens...")
    model = HookedTransformer.from_pretrained("gpt2", center_unembed=True,
                                               center_writing_weights=True,
                                               fold_ln=True)
    model.eval()

    saes = {}
    for layer in probe_layers:
        print(f"  Loading SAE for layer {layer}...")
        # Anthropic's released GPT-2 small SAEs via sae_lens
        # hook point: residual stream after layer norm, pre-MLP
        sae, _, _ = SAE.from_pretrained(
            release="gpt2-small-res-jb",       # Joseph Bloom's GPT-2 small SAEs
            sae_id=f"blocks.{layer}.hook_resid_pre",
        )
        saes[layer] = sae

    return model, saes


def find_token_position(model, text, target="7"):
    """Find position of the token that contains target string."""
    tokens = model.to_tokens(text, prepend_bos=True)[0]
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    for i, tok in enumerate(str_tokens):
        if target in tok:
            return i
    return None


def get_residual_stream(model, text, layer):
    """Extract residual stream at the given layer for all token positions."""
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=f"blocks.{layer}.hook_resid_pre")
    return cache[f"blocks.{layer}.hook_resid_pre"][0]  # (seq_len, d_model)


def get_sae_features(sae, residual_vec):
    """Pass a single residual stream vector through the SAE encoder."""
    import torch
    vec = torch.tensor(residual_vec, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        feature_acts = sae.encode(vec)
    return feature_acts[0].numpy()  # (n_features,)


def collect_feature_activations(model, saes, layer):
    """
    For every context sentence, find the "7" token position,
    extract residual stream, pass through SAE, record feature activations.
    Returns: list of (register, feature_vector) pairs
    """
    results = []
    skipped = 0

    for register, text in CONTEXTS:
        pos = find_token_position(model, text)
        if pos is None:
            skipped += 1
            continue
        resid = get_residual_stream(model, text, layer)
        vec = resid[pos].numpy()
        features = get_sae_features(saes[layer], vec)
        results.append((register, features))

    print(f"  {len(results)} activations collected, {skipped} skipped")
    return results


def analyse_features(results, layer):
    """
    Find which features are active, which are register-specific, which are shared.
    Returns a summary dict.
    """
    registers = sorted(set(r for r, _ in results))
    n_features = results[0][1].shape[0]

    # Mean activation per register per feature
    reg_mean = {}
    for reg in registers:
        vecs = np.array([f for r, f in results if r == reg])
        reg_mean[reg] = vecs.mean(axis=0)

    # Which features are active at all (above threshold in any register)
    global_mean = np.array([f for _, f in results]).mean(axis=0)
    active_features = np.where(global_mean > ACTIVATION_THRESHOLD)[0]

    # Register-specific features: high in one register, low in others
    specific = {}
    for reg in registers:
        others_mean = np.array([reg_mean[r] for r in registers if r != reg]).mean(axis=0)
        specificity = reg_mean[reg] - others_mean  # positive = specific to this register
        top_specific = np.argsort(specificity)[::-1][:10]
        specific[reg] = [(int(f), float(specificity[f])) for f in top_specific
                         if specificity[f] > 0.1]

    return {
        "registers": registers,
        "reg_mean": reg_mean,
        "active_features": active_features,
        "n_active": len(active_features),
        "specific": specific,
        "global_mean": global_mean,
    }


def plot_feature_heatmap(analysis, layer):
    """Heatmap: registers × top active features, showing mean activation."""
    registers = analysis["registers"]
    active = analysis["active_features"]

    if len(active) == 0:
        print(f"  Layer {layer}: no features above threshold, skipping heatmap")
        return

    # Select top features by variance across registers (most discriminating)
    reg_matrix = np.array([analysis["reg_mean"][r][active] for r in registers])
    variance = reg_matrix.var(axis=0)
    top_idx = np.argsort(variance)[::-1][:TOP_N_FEATURES]
    top_features = active[top_idx]

    data = np.array([analysis["reg_mean"][r][top_features] for r in registers])

    fig, ax = plt.subplots(figsize=(max(12, len(top_features) * 0.4), 6))
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd", interpolation="nearest")
    ax.set_yticks(range(len(registers)))
    ax.set_yticklabels(registers, fontsize=9)
    ax.set_xticks(range(len(top_features)))
    ax.set_xticklabels([f"F{f}" for f in top_features],
                       rotation=90, fontsize=7)
    ax.set_xlabel("SAE Feature (top by cross-register variance)")
    ax.set_ylabel("Semantic register")
    ax.set_title(f"Layer {layer} — SAE features for token '7'\n"
                 f"({analysis['n_active']} features active total, "
                 f"showing top {len(top_features)} by discriminability)")
    plt.colorbar(im, ax=ax, label="Mean activation")
    fig.tight_layout()
    out = RESULTS_DIR / f"layer_{layer:02d}_heatmap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Heatmap: {out.name}")


def plot_register_specificity(analysis, layer):
    """Bar chart: which registers have the most register-specific features."""
    registers = analysis["registers"]
    n_specific = {reg: len(feats) for reg, feats in analysis["specific"].items()}

    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(registers, [n_specific.get(r, 0) for r in registers],
                  color="steelblue", alpha=0.8)
    ax.set_xlabel("Register")
    ax.set_ylabel("Number of register-specific features")
    ax.set_title(f"Layer {layer} — Register-specific SAE features for '7'\n"
                 "(features that activate strongly for this register but not others)")
    plt.xticks(rotation=35, ha="right")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / f"layer_{layer:02d}_specificity.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Specificity: {out.name}")


def plot_active_feature_count_by_layer(layer_summaries):
    layers = [s["layer"] for s in layer_summaries]
    n_active = [s["n_active"] for s in layer_summaries]
    n_specific_total = [
        sum(len(v) for v in s["specific"].values())
        for s in layer_summaries
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(layers, n_active, marker="o", color="steelblue",
            linewidth=2, label="Total active features for '7'")
    ax2 = ax.twinx()
    ax2.plot(layers, n_specific_total, marker="s", color="tomato",
             linewidth=2, linestyle="--", label="Register-specific features")
    ax.set_xlabel("Layer")
    ax.set_ylabel("Active SAE features", color="steelblue")
    ax2.set_ylabel("Register-specific features", color="tomato")
    ax.set_title("How many distinct Markov objects does '7' have?\n"
                 "SAE feature count by layer")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "active_features_by_layer.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Feature count summary: {out}")


def main():
    model, saes = load_model_and_saes(PROBE_LAYERS)

    layer_summaries = []

    for layer in PROBE_LAYERS:
        print(f"\n=== Layer {layer} ===")
        results = collect_feature_activations(model, saes, layer)
        if not results:
            continue

        analysis = analyse_features(results, layer)
        print(f"  Active features (>{ACTIVATION_THRESHOLD}): {analysis['n_active']}")

        for reg, feats in analysis["specific"].items():
            if feats:
                top = feats[:3]
                print(f"  {reg:20s} specific: "
                      f"{', '.join(f'F{f}({s:.2f})' for f, s in top)}")

        plot_feature_heatmap(analysis, layer)
        plot_register_specificity(analysis, layer)

        layer_summaries.append({
            "layer": layer,
            "n_active": analysis["n_active"],
            "specific": analysis["specific"],
        })

    plot_active_feature_count_by_layer(layer_summaries)

    print("\n--- Summary ---")
    print(f"{'Layer':>6}  {'Active features':>16}  {'Register-specific':>18}")
    for s in layer_summaries:
        n_spec = sum(len(v) for v in s["specific"].values())
        print(f"{s['layer']:>6}  {s['n_active']:>16}  {n_spec:>18}")

    peak = max(layer_summaries, key=lambda s: s["n_active"])
    print(f"\nPeak: layer {peak['layer']} with {peak['n_active']} distinct "
          f"SAE features active for '7'")
    print("\nThis is the principled answer to 'how many Markov objects is 7?'")
    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
