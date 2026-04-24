"""
Experiment 09: Context-Conditional Markov Objects

The paper's central claim is that a concept's Markov object is context-selected,
not fixed. Experiment 08 showed numbers have rich feature signatures under one
context ("The number N"). This experiment tests whether those signatures *shift*
when the context changes.

Method:
  - Pick culturally-loaded numbers: 666, 999, 7, 42, 100
  - Probe each across 8 structured contexts (referential, page, currency,
    quantity, address, temporal, arithmetic, symbolic)
  - Extract SAE features at the target-number token, layer 8
  - Decompose active features per number into:
      invariant_core       — active in ALL contexts   (the skeleton)
      shared_pool          — active in ≥2 but not all (partial selectivity)
      context_specific     — active in exactly ONE context (the coat)
  - Compute 8×8 context similarity matrix per number
  - Compare invariant/specific ratios across numbers (is 666's coat fatter?)

Predictions if context-conditional blanketing holds:
  - Invariant core is small relative to total features
  - Context-specific coat is large
  - Similarity matrix shows context clustering (e.g. cultural ∼ symbolic,
    currency ∼ quantity, temporal ∼ address)
  - Heavy cultural numbers (666, 999) have richer context-specific coats
"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
from itertools import combinations
import urllib.request

RESULTS_DIR = Path(__file__).parent.parent / "results" / "09_context_conditional"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Reuse Neuronpedia cache from experiment 08
CACHE_FILE_08 = Path(__file__).parent.parent / "results" / "08_feature_identity" / "neuronpedia_cache.json"
CACHE_FILE    = RESULTS_DIR / "neuronpedia_cache.json"

PROBE_LAYER = 8
ACTIVATION_THRESHOLD = 0.5

NUMBERS = [666, 999, 7, 42, 100]

# Contexts — crafted to keep the target number as its own token
CONTEXTS = {
    "referential":  "The number {n} is",
    "page":         "Page {n} of the book",
    "currency":     "The price was {n} dollars",
    "quantity":     "There were {n} people",
    "address":      "They live at {n} Main Street",
    "temporal":     "In the year {n}",
    "arithmetic":   "When you calculate {n} plus one",
    "symbolic":     "The sacred number {n} means",
}


# ---------------------------------------------------------------------------
# Model / SAE / caching
# ---------------------------------------------------------------------------

def load_cache():
    cache = {}
    if CACHE_FILE_08.exists():
        cache.update(json.loads(CACHE_FILE_08.read_text()))
    if CACHE_FILE.exists():
        cache.update(json.loads(CACHE_FILE.read_text()))
    return cache


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def fetch_feature_label(feature_id, cache, delay=0.25):
    key = f"gpt2-small/{PROBE_LAYER}-res-jb/{feature_id}"
    if key in cache:
        return cache[key]
    url = f"https://www.neuronpedia.org/api/feature/gpt2-small/{PROBE_LAYER}-res-jb/{feature_id}"
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


def load_model_and_sae():
    from transformer_lens import HookedTransformer
    from sae_lens import SAE
    print("Loading GPT-2 + SAE...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()
    sae = SAE.from_pretrained(
        release="gpt2-small-res-jb",
        sae_id=f"blocks.{PROBE_LAYER}.hook_resid_pre",
    )
    print(f"  Layer {PROBE_LAYER} SAE: {sae.cfg.d_sae} features")
    return model, sae


def get_features(model, sae, text, n):
    import torch
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    target = str(n)
    pos = None
    for i, tok in enumerate(str_tokens):
        if tok.strip() == target:        # exact match preferred
            pos = i
            break
    if pos is None:
        for i, tok in enumerate(str_tokens):
            if target in tok.strip():    # fallback: containment
                pos = i
                break
    if pos is None:
        return None, None
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{PROBE_LAYER}.hook_resid_pre"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    resid = cache[hook_name][0, pos, :]
    with torch.no_grad():
        acts = sae.encode(resid.unsqueeze(0))[0]
    return acts.numpy(), pos


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def decompose_features(feature_vectors_by_context, threshold=ACTIVATION_THRESHOLD):
    """
    Given {context_name: feature_vector}, return:
      invariant_core  — fids active in ALL contexts
      shared_pool     — fids active in ≥2 contexts (but not all)
      context_specific — {context: fids active ONLY in that context}
      all_active       — union of fids active in any context
    """
    contexts = list(feature_vectors_by_context.keys())
    active_sets = {c: set(np.where(v > threshold)[0].tolist())
                   for c, v in feature_vectors_by_context.items()}
    all_active = set().union(*active_sets.values())
    invariant_core = set.intersection(*active_sets.values()) if active_sets else set()

    context_specific = {}
    for c in contexts:
        others = set().union(*[s for cc, s in active_sets.items() if cc != c])
        context_specific[c] = active_sets[c] - others

    shared_pool = all_active - invariant_core - set().union(*context_specific.values())
    return {
        "active_sets":      active_sets,
        "all_active":       all_active,
        "invariant_core":   invariant_core,
        "shared_pool":      shared_pool,
        "context_specific": context_specific,
    }


def context_similarity_matrix(feature_vectors_by_context):
    contexts = list(feature_vectors_by_context.keys())
    n = len(contexts)
    mat = np.zeros((n, n))
    for i, a in enumerate(contexts):
        for j, b in enumerate(contexts):
            va, vb = feature_vectors_by_context[a], feature_vectors_by_context[b]
            na, nb = np.linalg.norm(va), np.linalg.norm(vb)
            mat[i, j] = float(np.dot(va, vb) / (na * nb)) if na and nb else 0.0
    return mat, contexts


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_decomposition_bar(all_data):
    """
    Per-number stacked bar: invariant core / shared pool / context-specific.
    """
    numbers = list(all_data.keys())
    cores = [len(all_data[n]["decomp"]["invariant_core"])   for n in numbers]
    shared = [len(all_data[n]["decomp"]["shared_pool"])     for n in numbers]
    specific = [sum(len(s) for s in all_data[n]["decomp"]["context_specific"].values())
                for n in numbers]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(numbers))
    ax.bar(x, cores,   label="Invariant core (all contexts)",    color="steelblue")
    ax.bar(x, shared,  bottom=cores, label="Shared pool (≥2 contexts)", color="gold")
    ax.bar(x, specific, bottom=[c+s for c,s in zip(cores, shared)],
           label="Context-specific (exactly 1)", color="tomato")

    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in numbers])
    ax.set_xlabel("Number")
    ax.set_ylabel("SAE feature count")
    ax.set_title(f"Feature decomposition by number — layer {PROBE_LAYER}\n"
                 "Does the coat (tomato) dominate the skeleton (blue)?")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")

    # Annotate ratios
    for xi, (c, s, sp) in enumerate(zip(cores, shared, specific)):
        total = c + s + sp
        if total:
            ax.text(xi, total + 2, f"core={c}\ncoat={sp}\ntotal={total}",
                    ha="center", fontsize=7)

    fig.tight_layout()
    out = RESULTS_DIR / "feature_decomposition.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Decomposition plot: {out.name}")


def plot_similarity_matrices(all_data):
    """Grid of per-number context-similarity matrices."""
    numbers = list(all_data.keys())
    n_num = len(numbers)
    cols = min(3, n_num)
    rows = (n_num + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4.3*rows), squeeze=False)
    for idx, n in enumerate(numbers):
        r, c = divmod(idx, cols)
        ax = axes[r][c]
        mat = all_data[n]["sim_matrix"]
        contexts = all_data[n]["contexts"]
        im = ax.imshow(mat, cmap="YlOrRd", vmin=0.2, vmax=1.0)
        ax.set_xticks(range(len(contexts)))
        ax.set_yticks(range(len(contexts)))
        ax.set_xticklabels(contexts, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(contexts, fontsize=7)
        ax.set_title(f"n = {n}", fontsize=10, fontweight="bold")
        for i in range(len(contexts)):
            for j in range(len(contexts)):
                v = mat[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                        fontsize=6, color="black" if v < 0.65 else "white")
        plt.colorbar(im, ax=ax, fraction=0.045)

    # Hide any trailing empty subplots
    for idx in range(n_num, rows * cols):
        r, c = divmod(idx, cols)
        axes[r][c].axis("off")

    fig.suptitle(f"Context similarity matrices — layer {PROBE_LAYER}\n"
                 "High = same object presented; low = different object selected",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    out = RESULTS_DIR / "context_similarity_matrices.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Similarity matrices: {out.name}")


def plot_context_specific_heatmap(all_data):
    """
    For each number, how many context-specific features per context?
    Heatmap: rows = numbers, cols = contexts, value = count.
    """
    numbers = list(all_data.keys())
    context_names = list(CONTEXTS.keys())
    mat = np.zeros((len(numbers), len(context_names)))
    for i, n in enumerate(numbers):
        for j, c in enumerate(context_names):
            mat[i, j] = len(all_data[n]["decomp"]["context_specific"].get(c, set()))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    im = ax.imshow(mat, cmap="Purples", aspect="auto")
    ax.set_xticks(range(len(context_names)))
    ax.set_xticklabels(context_names, rotation=30, ha="right")
    ax.set_yticks(range(len(numbers)))
    ax.set_yticklabels([str(n) for n in numbers])
    ax.set_title(f"Context-specific features per (number × context) — layer {PROBE_LAYER}")
    for i in range(len(numbers)):
        for j in range(len(context_names)):
            v = int(mat[i, j])
            if v > 0:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=9,
                        color="white" if v > mat.max() * 0.5 else "black")
    plt.colorbar(im, ax=ax, label="Features unique to this context")
    fig.tight_layout()
    out = RESULTS_DIR / "context_specific_heatmap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Context-specific heatmap: {out.name}")


def write_annotated_report(all_data, model, sae, cache):
    """Text report with top features per number, annotated with Neuronpedia labels."""
    out = RESULTS_DIR / "annotated_report.txt"
    lines = [f"Context-Conditional Markov Objects — layer {PROBE_LAYER}", "=" * 70, ""]

    for n, data in all_data.items():
        decomp = data["decomp"]
        lines.append(f"\n### n = {n}")
        lines.append("-" * 50)
        lines.append(f"Total active features (any context): {len(decomp['all_active'])}")
        lines.append(f"Invariant core (all contexts):       {len(decomp['invariant_core'])}")
        lines.append(f"Shared pool (≥2):                    {len(decomp['shared_pool'])}")
        total_specific = sum(len(s) for s in decomp['context_specific'].values())
        lines.append(f"Context-specific total:              {total_specific}")

        # Invariant core with labels
        lines.append("\n  INVARIANT CORE (the skeleton — always on):")
        core_list = sorted(decomp["invariant_core"],
                           key=lambda f: -np.mean([data["feats"][c][f] for c in data["contexts"]]))
        for fid in core_list[:10]:
            lbl = fetch_feature_label(int(fid), cache) or "—"
            mean_strength = np.mean([data["feats"][c][fid] for c in data["contexts"]])
            lines.append(f"    F{int(fid):5d}  μ={mean_strength:5.2f}  {lbl}")

        # Top context-specific per context
        lines.append("\n  CONTEXT-SPECIFIC (the coat — selected by context):")
        for ctx in data["contexts"]:
            specific = decomp["context_specific"].get(ctx, set())
            if not specific:
                continue
            # sort by strength in this context
            spec_list = sorted(specific, key=lambda f: -data["feats"][ctx][f])
            lines.append(f"\n    [{ctx}]")
            for fid in spec_list[:5]:
                lbl = fetch_feature_label(int(fid), cache) or "—"
                strength = data["feats"][ctx][fid]
                lines.append(f"      F{int(fid):5d}  {strength:5.2f}  {lbl}")

    out.write_text("\n".join(lines))
    save_cache(cache)
    print(f"Annotated report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()
    cache = load_cache()

    all_data = {}

    for n in NUMBERS:
        print(f"\n=== n = {n} ===")
        feats = {}
        used_contexts = []
        for ctx_name, template in CONTEXTS.items():
            text = template.format(n=n)
            vec, pos = get_features(model, sae, text, n)
            if vec is None:
                print(f"  [{ctx_name}] skipped — token not found in: '{text}'")
                continue
            feats[ctx_name] = vec
            used_contexts.append(ctx_name)
            n_active = int((vec > ACTIVATION_THRESHOLD).sum())
            print(f"  [{ctx_name:12s}] pos={pos}  active={n_active}  '{text}'")

        if len(feats) < 3:
            print(f"  too few contexts survived, skipping")
            continue

        decomp = decompose_features(feats)
        sim_matrix, contexts = context_similarity_matrix(feats)

        all_data[n] = {
            "feats":      feats,
            "contexts":   contexts,
            "decomp":     decomp,
            "sim_matrix": sim_matrix,
        }

        print(f"  -> core={len(decomp['invariant_core'])}  "
              f"shared={len(decomp['shared_pool'])}  "
              f"specific_total={sum(len(s) for s in decomp['context_specific'].values())}")

    print("\nGenerating plots...")
    plot_decomposition_bar(all_data)
    plot_similarity_matrices(all_data)
    plot_context_specific_heatmap(all_data)

    print("\nWriting annotated report (querying Neuronpedia for labels)...")
    write_annotated_report(all_data, model, sae, cache)

    # Summary statistics
    print("\n--- Summary: coat / skeleton ratio ---")
    for n, data in all_data.items():
        core = len(data["decomp"]["invariant_core"])
        specific = sum(len(s) for s in data["decomp"]["context_specific"].values())
        total = len(data["decomp"]["all_active"])
        ratio = specific / max(core, 1)
        print(f"  n={n:>4}: core={core:>3}  coat={specific:>3}  "
              f"total={total:>3}  coat/core={ratio:.2f}")

    print("\n--- Cross-context diversity ---")
    for n, data in all_data.items():
        mat = data["sim_matrix"]
        off_diag = mat[~np.eye(mat.shape[0], dtype=bool)]
        print(f"  n={n:>4}: mean off-diag cosine = {off_diag.mean():.3f}  "
              f"(lower = more context-selectivity)")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
