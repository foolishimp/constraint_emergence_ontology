"""
Experiment 08: Feature Identity Inspection

What do the SAE features on 666, 997, 500 actually encode?

Method:
  - Get top-K active features for key numbers at layer 8
  - Query Neuronpedia API for human-readable feature labels
  - Compare: symbolic (666) vs prime (997) vs round (500) vs small cultural (7) vs power-of-2 (512)
  - Group features by inferred type: arithmetic, symbolic, currency, ordinal, cultural, etc.
  - Show which feature types are shared vs number-specific

Neuronpedia API:
  GET https://www.neuronpedia.org/api/feature/gpt2-small/8-res-jb/{feature_id}
  Returns JSON with 'explanations' list — each has 'description' field.
"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from collections import defaultdict
import urllib.request
import urllib.error

RESULTS_DIR = Path(__file__).parent.parent / "results" / "08_feature_identity"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE = RESULTS_DIR / "neuronpedia_cache.json"

PROBE_LAYER = 8
ACTIVATION_THRESHOLD = 0.5
TOP_K = 20          # top features to inspect per number
TEMPLATE = "The number {n}"

# Numbers to compare — chosen to maximally contrast object types
NUMBERS = {
    "666_cultural":  666,
    "999_cultural":  999,
    "997_prime":     997,
    "500_round":     500,
    "7_cultural":    7,
    "512_pow2":      512,
    "101_prime":     101,
    "100_round":     100,
}

# Neuronpedia model/SAE identifiers for GPT-2 small layer 8 JB SAE
NP_MODEL = "gpt2-small"
NP_SAE   = f"{PROBE_LAYER}-res-jb"


# ---------------------------------------------------------------------------
# Cache + Neuronpedia query
# ---------------------------------------------------------------------------

def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def fetch_feature_label(feature_id, cache, delay=0.3):
    """Query Neuronpedia for a feature description. Returns string or None."""
    key = f"{NP_MODEL}/{NP_SAE}/{feature_id}"
    if key in cache:
        return cache[key]

    url = f"https://www.neuronpedia.org/api/feature/{NP_MODEL}/{NP_SAE}/{feature_id}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        # 'explanations' is a list; take first description if available
        label = None
        exps = data.get("explanations") or []
        if exps:
            label = exps[0].get("description") or exps[0].get("typeName")
        cache[key] = label
        time.sleep(delay)
        return label
    except Exception as e:
        cache[key] = None
        return None


# ---------------------------------------------------------------------------
# Model + SAE
# ---------------------------------------------------------------------------

def load_model_and_sae(layer):
    from transformer_lens import HookedTransformer
    from sae_lens import SAE
    import torch

    print("Loading GPT-2 + SAE...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()
    sae = SAE.from_pretrained(
        release="gpt2-small-res-jb",
        sae_id=f"blocks.{layer}.hook_resid_pre",
    )
    print(f"  SAE: {sae.cfg.d_sae} features at layer {layer}")
    return model, sae


def get_feature_activations(model, sae, n, layer):
    import torch
    text = TEMPLATE.format(n=n)
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    pos = None
    target = str(n)
    for i, tok in enumerate(str_tokens):
        if target in tok.strip():
            pos = i
            break
    if pos is None:
        return None, text

    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    resid = cache[hook_name][0, pos, :]
    with torch.no_grad():
        acts = sae.encode(resid.unsqueeze(0))[0]
    return acts.numpy(), text


# ---------------------------------------------------------------------------
# Decoder-based token inspection (fallback when Neuronpedia label is None)
# ---------------------------------------------------------------------------

def top_decoder_tokens(sae, feature_id, model, k=8):
    """
    Find which output-vocabulary tokens the feature's decoder vector most
    up-weights. This gives a rough sense of what the feature 'says'.
    """
    import torch
    decoder_vec = sae.W_dec[feature_id]          # (d_model,)
    logits = model.unembed.W_U.T @ decoder_vec   # (vocab,)
    top_ids = logits.topk(k).indices.tolist()
    return [model.to_single_str_token(i) for i in top_ids]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def inspect_number(label, n, model, sae, cache):
    acts, text = get_feature_activations(model, sae, n, PROBE_LAYER)
    if acts is None:
        print(f"  {label}: token not found in '{text}'")
        return None

    active_idx = np.where(acts > ACTIVATION_THRESHOLD)[0]
    top_idx = active_idx[np.argsort(acts[active_idx])[::-1]][:TOP_K]

    features = []
    print(f"\n  {label} (n={n}) — {len(active_idx)} active features, showing top {len(top_idx)}")
    for fid in top_idx:
        strength = float(acts[fid])
        label_str = fetch_feature_label(int(fid), cache)
        decoder_toks = top_decoder_tokens(sae, fid, model, k=6)
        decoder_str = " | ".join(t.strip() for t in decoder_toks[:6])
        print(f"    F{fid:5d}  {strength:5.2f}  label={label_str or '—':45s}  decoder=[{decoder_str}]")
        features.append({
            "feature_id": int(fid),
            "strength": strength,
            "label": label_str,
            "decoder_tokens": decoder_toks,
        })
    return {"number": n, "label": label, "active_total": int(len(active_idx)), "top_features": features}


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_feature_overlap(all_results):
    """
    Which features are shared across numbers, which are unique?
    Venn-style: show top-20 features per number as a set, colour by sharing.
    """
    labels = [r["label"] for r in all_results]
    feature_sets = [set(f["feature_id"] for f in r["top_features"]) for r in all_results]

    # Count how many numbers each feature appears in
    from collections import Counter
    counter = Counter(fid for fs in feature_sets for fid in fs)
    shared = {fid for fid, cnt in counter.items() if cnt >= 3}
    unique = {fid for fid, cnt in counter.items() if cnt == 1}

    # Bar chart: shared vs unique feature count per number
    shared_counts = [len(fs & shared) for fs in feature_sets]
    unique_counts  = [len(fs & unique)  for fs in feature_sets]
    other_counts   = [len(fs) - s - u for fs, s, u in
                      zip(feature_sets, shared_counts, unique_counts)]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x, shared_counts, label="Shared (≥3 numbers)", color="steelblue", alpha=0.85)
    ax.bar(x, other_counts,  bottom=shared_counts, label="Partially shared", color="gold", alpha=0.85)
    ax.bar(x, unique_counts, bottom=[s+o for s,o in zip(shared_counts, other_counts)],
           label="Unique to this number", color="tomato", alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Top-20 feature count")
    ax.set_title(f"Feature overlap — layer {PROBE_LAYER}\n"
                 "How many of each number's top features are shared vs unique?")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "feature_overlap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\nOverlap plot: {out.name}")


def plot_strength_profiles(all_results):
    """
    Line plot: activation strength of each number's top-20 features, ranked.
    Cultural numbers should have stronger/more features.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_results)))
    for r, color in zip(all_results, colors):
        strengths = sorted([f["strength"] for f in r["top_features"]], reverse=True)
        ax.plot(range(1, len(strengths)+1), strengths,
                marker="o", markersize=4, color=color,
                label=r["label"], linewidth=1.5)

    ax.set_xlabel("Feature rank")
    ax.set_ylabel("Activation strength")
    ax.set_title(f"Activation strength profiles — layer {PROBE_LAYER}\n"
                 "Cultural numbers: more features AND stronger activations?")
    ax.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "strength_profiles.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Strength profiles: {out.name}")


def save_feature_report(all_results):
    """Save a readable text report of all feature labels."""
    out = RESULTS_DIR / "feature_report.txt"
    lines = [f"Feature Identity Report — layer {PROBE_LAYER}", "=" * 60, ""]
    for r in all_results:
        lines.append(f"{r['label']} (n={r['number']}) — {r['active_total']} total active features")
        lines.append("-" * 50)
        for f in r["top_features"]:
            label = f["label"] or "—"
            decoder = " | ".join(t.strip() for t in f["decoder_tokens"][:5])
            lines.append(f"  F{f['feature_id']:5d}  {f['strength']:5.2f}  {label}")
            lines.append(f"           decoder: [{decoder}]")
        lines.append("")
    out.write_text("\n".join(lines))
    print(f"Feature report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae(PROBE_LAYER)
    cache = load_cache()

    print(f"\nInspecting {len(NUMBERS)} numbers at layer {PROBE_LAYER}...")
    print("Querying Neuronpedia for feature labels (cached after first run)...\n")

    all_results = []
    for label, n in NUMBERS.items():
        result = inspect_number(label, n, model, sae, cache)
        if result:
            all_results.append(result)
        save_cache(cache)   # save after each number in case of interruption

    print("\nGenerating plots...")
    plot_feature_overlap(all_results)
    plot_strength_profiles(all_results)
    save_feature_report(all_results)

    # Print summary: what types of labels appear for cultural vs mathematical?
    print("\n--- Label summary by number type ---")
    for r in all_results:
        labels_found = [f["label"] for f in r["top_features"] if f["label"]]
        print(f"\n{r['label']} ({r['active_total']} features):")
        for lbl in labels_found[:8]:
            print(f"  • {lbl}")
        if not labels_found:
            print("  (no Neuronpedia labels returned — see decoder tokens in report)")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
