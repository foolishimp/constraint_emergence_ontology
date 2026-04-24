"""
Experiment 10: Layer-by-Layer Markov Object Assembly

Exp 09 showed the Markov object is overwhelmingly context-selected — tiny
invariant core (1-9 features), large context-specific coat (150-180 features).
This experiment asks WHEN and HOW those features are built across depth.

Method:
  - Pick key numbers: 999, 666, 42, 100, 7
  - For each, run the neutral template "The number N is"
  - Extract SAE features at layers 0, 2, 4, 6, 8, 10
  - Track which features are active at each layer
  - Identify feature "birth layer" — the first layer where the feature exceeds
    ACTIVATION_THRESHOLD

Plots:
  - Feature count trajectory per number across depth
  - Feature birth-layer distribution: early (0-2) vs mid (4-6) vs late (8-10)
  - Top-feature trajectories: does 999's emergency/911 feature rise early or late?

Prediction:
  - Early layers: token-level / pattern features (sees the literal digits)
  - Mid layers: category features (sees "this is a number", "this is a quantity")
  - Late layers: cultural/semantic features (sees "911", "demon", "42nd president")
"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import urllib.request

RESULTS_DIR = Path(__file__).parent.parent / "results" / "10_layer_assembly"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Reuse Neuronpedia caches from previous experiments
CACHE_FILES_READ = [
    Path(__file__).parent.parent / "results" / "08_feature_identity" / "neuronpedia_cache.json",
    Path(__file__).parent.parent / "results" / "09_context_conditional" / "neuronpedia_cache.json",
]
CACHE_FILE = RESULTS_DIR / "neuronpedia_cache.json"

PROBE_LAYERS = [0, 2, 4, 6, 8, 10]
ACTIVATION_THRESHOLD = 0.5
TOP_K = 5  # top features per number per layer to inspect

TEMPLATE = "The number {n} is"
NUMBERS = [7, 42, 100, 666, 999]


# ---------------------------------------------------------------------------
# Cache + Neuronpedia
# ---------------------------------------------------------------------------

def load_cache():
    cache = {}
    for p in CACHE_FILES_READ:
        if p.exists():
            cache.update(json.loads(p.read_text()))
    if CACHE_FILE.exists():
        cache.update(json.loads(CACHE_FILE.read_text()))
    return cache


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def fetch_feature_label(feature_id, layer, cache, delay=0.2):
    """Note: labels are per-layer — each layer has its own 24576 SAE features."""
    key = f"gpt2-small/{layer}-res-jb/{feature_id}"
    if key in cache:
        return cache[key]
    url = f"https://www.neuronpedia.org/api/feature/gpt2-small/{layer}-res-jb/{feature_id}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        exps = data.get("explanations") or []
        label = exps[0].get("description") if exps else None
        cache[key] = label
        time.sleep(delay)
        return label
    except Exception:
        cache[key] = None
        return None


# ---------------------------------------------------------------------------
# Model + multi-layer SAE
# ---------------------------------------------------------------------------

def load_model_and_saes():
    from transformer_lens import HookedTransformer
    from sae_lens import SAE

    print("Loading GPT-2...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()

    saes = {}
    for L in PROBE_LAYERS:
        print(f"  Loading SAE for layer {L}...")
        saes[L] = SAE.from_pretrained(
            release="gpt2-small-res-jb",
            sae_id=f"blocks.{L}.hook_resid_pre",
        )
    return model, saes


def get_features_all_layers(model, saes, n):
    """Returns {layer: feature_vector} for the target-number token position."""
    import torch

    text = TEMPLATE.format(n=n)
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    target = str(n)
    pos = None
    for i, tok in enumerate(str_tokens):
        if tok.strip() == target:
            pos = i
            break
    if pos is None:
        for i, tok in enumerate(str_tokens):
            if target in tok.strip():
                pos = i
                break
    if pos is None:
        return None, text

    tokens = model.to_tokens(text, prepend_bos=True)
    hook_names = [f"blocks.{L}.hook_resid_pre" for L in PROBE_LAYERS]
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_names)

    out = {}
    for L in PROBE_LAYERS:
        resid = cache[f"blocks.{L}.hook_resid_pre"][0, pos, :]
        with torch.no_grad():
            feats = saes[L].encode(resid.unsqueeze(0))[0]
        out[L] = feats.numpy()
    return out, text


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def birth_layers(feats_by_layer, threshold=ACTIVATION_THRESHOLD):
    """
    For each feature, the earliest layer at which it becomes active.
    Returns dict {(feature_id): birth_layer}.  Features never active are omitted.
    """
    layers = sorted(feats_by_layer.keys())
    birth = {}
    for L in layers:
        active = np.where(feats_by_layer[L] > threshold)[0]
        for fid in active:
            key = (int(L), int(fid))
            # We want the earliest, so only record if not seen
            fid_int = int(fid)
            if fid_int not in birth:
                birth[fid_int] = L
    return birth


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_feature_count_trajectory(all_data):
    fig, ax = plt.subplots(figsize=(9, 5))
    for n, data in all_data.items():
        layers = sorted(data["feats_by_layer"].keys())
        counts = [int((data["feats_by_layer"][L] > ACTIVATION_THRESHOLD).sum())
                  for L in layers]
        ax.plot(layers, counts, marker="o", linewidth=2, label=f"n={n}")
    ax.set_xlabel("Layer")
    ax.set_ylabel("Active SAE features (>0.5)")
    ax.set_title("Markov object assembly across depth\n"
                 "How does feature count grow for each number?")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "feature_count_trajectory.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Count trajectory: {out.name}")


def plot_birth_layer_distribution(all_data):
    """Histogram of feature birth layers per number."""
    fig, axes = plt.subplots(1, len(all_data), figsize=(3.5 * len(all_data), 4), sharey=True)
    if len(all_data) == 1:
        axes = [axes]
    for ax, (n, data) in zip(axes, all_data.items()):
        births = list(data["birth"].values())
        counts_per_layer = {L: births.count(L) for L in PROBE_LAYERS}
        colors = plt.cm.viridis(np.linspace(0.15, 0.9, len(PROBE_LAYERS)))
        ax.bar(PROBE_LAYERS, [counts_per_layer[L] for L in PROBE_LAYERS],
               color=colors, alpha=0.9)
        ax.set_title(f"n = {n}\n{len(births)} features total", fontsize=10)
        ax.set_xlabel("Birth layer")
        ax.grid(True, alpha=0.3, axis="y")
    axes[0].set_ylabel("Features born at this layer")
    fig.suptitle("Feature birth-layer distribution: when is each feature first active?",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    out = RESULTS_DIR / "birth_layer_distribution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Birth distribution: {out.name}")


def plot_top_feature_strength_trajectories(all_data):
    """
    For each number, trace the top 5 features of the final layer BACK through
    earlier layers — does their activation strength rise early or late?
    (Features are layer-specific, so we trace their activation in each layer
    by feature_id — this only makes sense within a single number's panel.)
    """
    n_numbers = len(all_data)
    fig, axes = plt.subplots(1, n_numbers, figsize=(4 * n_numbers, 4.5), sharey=False)
    if n_numbers == 1:
        axes = [axes]
    for ax, (n, data) in zip(axes, all_data.items()):
        final_layer = max(data["feats_by_layer"].keys())
        final_vec = data["feats_by_layer"][final_layer]
        top_fids = np.argsort(final_vec)[::-1][:TOP_K]

        colors = plt.cm.tab10(np.linspace(0, 1, len(top_fids)))
        for fid, color in zip(top_fids, colors):
            strengths = [data["feats_by_layer"][L][fid] for L in PROBE_LAYERS]
            ax.plot(PROBE_LAYERS, strengths, marker="o", color=color,
                    label=f"F{fid}", linewidth=1.7)
        ax.set_title(f"n = {n}\ntop {TOP_K} features at final layer", fontsize=9)
        ax.set_xlabel("Layer")
        ax.set_ylabel("Feature activation")
        ax.legend(fontsize=6, loc="upper left")
        ax.grid(True, alpha=0.3)

    fig.suptitle("Top feature strength trajectories across depth\n"
                 "(features are layer-specific — same ID ≠ same meaning across layers, "
                 "but trajectory reveals when a number's 'signature' features emerge)",
                 fontsize=9, fontweight="bold")
    fig.tight_layout()
    out = RESULTS_DIR / "top_feature_trajectories.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Top trajectories: {out.name}")


def write_layer_report(all_data, cache):
    out = RESULTS_DIR / "layer_report.txt"
    lines = [f"Layer Assembly Report — template '{TEMPLATE}'", "=" * 70, ""]
    for n, data in all_data.items():
        lines.append(f"\n### n = {n}")
        lines.append("-" * 50)
        for L in sorted(data["feats_by_layer"].keys()):
            vec = data["feats_by_layer"][L]
            active = int((vec > ACTIVATION_THRESHOLD).sum())
            top = np.argsort(vec)[::-1][:TOP_K]
            lines.append(f"\n  Layer {L}  —  {active} active features")
            for fid in top:
                if vec[fid] < ACTIVATION_THRESHOLD:
                    continue
                label = fetch_feature_label(int(fid), L, cache) or "—"
                lines.append(f"    F{int(fid):5d}  {vec[fid]:6.2f}  {label}")
            save_cache(cache)
    out.write_text("\n".join(lines))
    print(f"Layer report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, saes = load_model_and_saes()
    cache = load_cache()

    all_data = {}
    for n in NUMBERS:
        print(f"\n=== n = {n} ===")
        feats_by_layer, text = get_features_all_layers(model, saes, n)
        if feats_by_layer is None:
            print(f"  token not found in '{text}', skipping")
            continue
        print(f"  text: '{text}'")
        for L in sorted(feats_by_layer.keys()):
            n_active = int((feats_by_layer[L] > ACTIVATION_THRESHOLD).sum())
            top_strength = float(feats_by_layer[L].max())
            print(f"    layer {L:>2}: {n_active:>3} active,  max strength = {top_strength:.2f}")

        birth = birth_layers(feats_by_layer)
        all_data[n] = {
            "feats_by_layer": feats_by_layer,
            "birth": birth,
        }

    print("\nGenerating plots...")
    plot_feature_count_trajectory(all_data)
    plot_birth_layer_distribution(all_data)
    plot_top_feature_strength_trajectories(all_data)

    print("\nWriting layer report (this queries Neuronpedia for 6 layers × 5 numbers × 5 features)...")
    write_layer_report(all_data, cache)

    # Summary: early vs late feature ratios
    print("\n--- Early vs late feature distribution ---")
    for n, data in all_data.items():
        births = list(data["birth"].values())
        early = sum(1 for L in births if L <= 2)
        mid = sum(1 for L in births if 4 <= L <= 6)
        late = sum(1 for L in births if L >= 8)
        total = len(births)
        if total:
            print(f"  n={n:>4}: total={total:>3}  "
                  f"early({early:>3} = {100*early/total:.0f}%)  "
                  f"mid({mid:>3} = {100*mid/total:.0f}%)  "
                  f"late({late:>3} = {100*late/total:.0f}%)")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
