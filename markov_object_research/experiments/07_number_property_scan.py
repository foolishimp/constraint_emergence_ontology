"""
Experiment 07: Number Property Scan

Do primes have a distinct SAE feature signature from composites?
Does feature count grow with magnitude or follow mathematical structure?
Are culturally special numbers (7, 13, 42) encoded differently?

Method:
  - Fixed neutral template: "The number {n}" — controls for semantic register
  - Extract SAE features at the "n" token position, layer 8 (peak from exp 06)
  - Compare feature profiles across number classes:
      primes, composites, powers of 2, round numbers, cultural, single/double/triple digit
  - Measure: feature count per number, feature overlap between classes,
              cosine similarity within vs across classes

Questions:
  Q1: Do primes cluster together in feature space?
  Q2: Does feature count grow monotonically with magnitude?
  Q3: Do culturally special numbers show extra features?
  Q4: Do powers of 2 / round numbers form their own cluster?
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pathlib import Path
from collections import defaultdict
from itertools import combinations
import importlib.util

RESULTS_DIR = Path(__file__).parent.parent / "results" / "07_number_property_scan"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 8       # peak from experiment 06
ACTIVATION_THRESHOLD = 0.5
TEMPLATE = "The number {n}"   # neutral arithmetic-free frame


# ---------------------------------------------------------------------------
# Number sets
# ---------------------------------------------------------------------------

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


PRIMES = [n for n in range(2, 200) if is_prime(n)]
COMPOSITES = [n for n in range(4, 200) if not is_prime(n)][:len(PRIMES)]
POWERS_OF_2 = [2**i for i in range(1, 11)]          # 2, 4, 8 ... 1024
ROUND_NUMBERS = [10, 20, 25, 50, 100, 200, 250, 500, 1000]
CULTURAL = [7, 13, 21, 42, 69, 77, 99, 100, 111, 123,
            666, 777, 888, 999, 1000, 1001, 1234, 9999]
SINGLE_DIGIT = list(range(1, 10))
DOUBLE_DIGIT = list(range(10, 100, 7))   # sample
TRIPLE_DIGIT = list(range(100, 1000, 47))  # sample

# All numbers to probe (deduplicated)
ALL_NUMBERS = sorted(set(
    PRIMES[:30] + COMPOSITES[:30] +
    POWERS_OF_2 + ROUND_NUMBERS + CULTURAL +
    SINGLE_DIGIT + DOUBLE_DIGIT[:15] + TRIPLE_DIGIT[:15]
))

# Class membership (a number can be in multiple classes)
def classify(n):
    classes = []
    if is_prime(n):
        classes.append("prime")
    else:
        classes.append("composite")
    if n in POWERS_OF_2:
        classes.append("power_of_2")
    if n in ROUND_NUMBERS:
        classes.append("round")
    if n in CULTURAL:
        classes.append("cultural")
    if n < 10:
        classes.append("single_digit")
    elif n < 100:
        classes.append("double_digit")
    elif n < 1000:
        classes.append("triple_digit")
    else:
        classes.append("large")
    return classes


# ---------------------------------------------------------------------------
# Model + SAE loading
# ---------------------------------------------------------------------------

def load_model_and_sae(layer):
    from transformer_lens import HookedTransformer
    from sae_lens import SAE

    print("Loading GPT-2 + SAE...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()

    sae = SAE.from_pretrained(
        release="gpt2-small-res-jb",
        sae_id=f"blocks.{layer}.hook_resid_pre",
    )
    print(f"  SAE loaded for layer {layer}")
    return model, sae


def find_number_position(model, text, n):
    """Find token position of the number n in text."""
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    target = str(n)
    for i, tok in enumerate(str_tokens):
        if target in tok.strip():
            return i
    return None


def get_sae_features(model, sae, text, position, layer):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    resid = cache[hook_name][0, position, :]
    with torch.no_grad():
        acts = sae.encode(resid.unsqueeze(0))[0]
    return acts.numpy()


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def collect(model, sae, numbers, layer):
    results = {}
    skipped = []
    for n in numbers:
        text = TEMPLATE.format(n=n)
        pos = find_number_position(model, text, n)
        if pos is None:
            skipped.append(n)
            continue
        feats = get_sae_features(model, sae, text, pos, layer)
        results[n] = feats
    if skipped:
        print(f"  Skipped (token not found): {skipped}")
    return results


def active_count(feat_vec, threshold=ACTIVATION_THRESHOLD):
    return int((feat_vec > threshold).sum())


def cosine_sim(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def within_class_similarity(results, number_list):
    sims = []
    pairs = list(combinations([n for n in number_list if n in results], 2))
    for a, b in pairs:
        sims.append(cosine_sim(results[a], results[b]))
    return np.mean(sims) if sims else float("nan")


def cross_class_similarity(results, list_a, list_b):
    sims = []
    for a in list_a:
        for b in list_b:
            if a in results and b in results and a != b:
                sims.append(cosine_sim(results[a], results[b]))
    return np.mean(sims) if sims else float("nan")


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_feature_count_by_magnitude(results):
    numbers = sorted(results.keys())
    counts = [active_count(results[n]) for n in numbers]
    classes = [classify(n) for n in numbers]

    color_map = {
        "prime": "tomato", "composite": "steelblue",
        "power_of_2": "gold", "round": "mediumpurple",
        "cultural": "limegreen",
    }

    fig, ax = plt.subplots(figsize=(14, 5))
    for n, count, cls in zip(numbers, counts, classes):
        # pick colour by first "interesting" class
        color = "lightgray"
        for key in ["power_of_2", "cultural", "round", "prime"]:
            if key in cls:
                color = color_map[key]
                break
        ax.scatter(n, count, color=color, s=55, alpha=0.85, zorder=3)

    # Annotate a few special numbers
    for n in [7, 13, 42, 100, 127, 128, 256, 512, 1000]:
        if n in results:
            ax.annotate(str(n), (n, active_count(results[n])),
                        textcoords="offset points", xytext=(0, 5), fontsize=7)

    ax.set_xscale("symlog", linthresh=10)
    ax.set_xlabel("Number (log scale)")
    ax.set_ylabel("Active SAE features")
    ax.set_title(f"Active SAE features by magnitude — layer {PROBE_LAYER}\n"
                 "red=prime  blue=composite  gold=power-of-2  purple=round  green=cultural")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "feature_count_by_magnitude.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Feature count plot: {out.name}")


def plot_class_similarity_matrix(results):
    classes = {
        "prime":      [n for n in PRIMES[:20] if n in results],
        "composite":  [n for n in COMPOSITES[:20] if n in results],
        "power_of_2": [n for n in POWERS_OF_2 if n in results],
        "round":      [n for n in ROUND_NUMBERS if n in results],
        "cultural":   [n for n in CULTURAL if n in results],
        "single":     [n for n in SINGLE_DIGIT if n in results],
        "double":     [n for n in DOUBLE_DIGIT if n in results],
        "triple":     [n for n in TRIPLE_DIGIT if n in results],
    }

    names = list(classes.keys())
    mat = np.zeros((len(names), len(names)))
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i == j:
                mat[i, j] = within_class_similarity(results, classes[a])
            else:
                mat[i, j] = cross_class_similarity(results, classes[a], classes[b])

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(mat, cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    ax.set_xticklabels(names, rotation=40, ha="right")
    ax.set_yticklabels(names)
    plt.colorbar(im, ax=ax, label="Mean cosine similarity")
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center",
                    fontsize=8, color="black" if mat[i,j] < 0.7 else "white")
    ax.set_title(f"Feature similarity between number classes — layer {PROBE_LAYER}\n"
                 "Diagonal = within-class.  High = similar feature profile.")
    fig.tight_layout()
    out = RESULTS_DIR / "class_similarity_matrix.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Similarity matrix: {out.name}")


def plot_prime_vs_composite(results):
    primes_in = [n for n in PRIMES[:25] if n in results]
    composites_in = [n for n in COMPOSITES[:25] if n in results]

    prime_counts = [active_count(results[n]) for n in primes_in]
    comp_counts = [active_count(results[n]) for n in composites_in]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Feature count distributions
    ax = axes[0]
    ax.hist(prime_counts, bins=10, alpha=0.7, color="tomato", label=f"primes (n={len(primes_in)})")
    ax.hist(comp_counts, bins=10, alpha=0.7, color="steelblue", label=f"composites (n={len(composites_in)})")
    ax.axvline(np.mean(prime_counts), color="tomato", linestyle="--", linewidth=2,
               label=f"prime mean={np.mean(prime_counts):.1f}")
    ax.axvline(np.mean(comp_counts), color="steelblue", linestyle="--", linewidth=2,
               label=f"composite mean={np.mean(comp_counts):.1f}")
    ax.set_xlabel("Active SAE features")
    ax.set_ylabel("Count")
    ax.set_title("Feature count: primes vs composites")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Within-class vs cross-class similarity
    ax = axes[1]
    wp = within_class_similarity(results, primes_in)
    wc = within_class_similarity(results, composites_in)
    xp = cross_class_similarity(results, primes_in, composites_in)

    bars = ax.bar(["within primes", "within composites", "prime ↔ composite"],
                  [wp, wc, xp],
                  color=["tomato", "steelblue", "mediumpurple"], alpha=0.8)
    for bar, val in zip(bars, [wp, wc, xp]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", fontsize=9)
    ax.set_ylabel("Mean cosine similarity")
    ax.set_title("Feature similarity: are primes their own cluster?")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3, axis="y")
    ax.axhline(xp, color="gray", linestyle="--", linewidth=0.8)

    fig.suptitle("Primes vs Composites — SAE feature structure", fontweight="bold")
    fig.tight_layout()
    out = RESULTS_DIR / "prime_vs_composite.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Prime vs composite: {out.name}")


def plot_magnitude_bands(results):
    """Feature count and similarity by digit-count band."""
    bands = {
        "1-digit (1–9)":     [n for n in SINGLE_DIGIT if n in results],
        "2-digit (10–99)":   [n for n in DOUBLE_DIGIT if n in results],
        "3-digit (100–999)": [n for n in TRIPLE_DIGIT if n in results],
        "4-digit (1000+)":   [n for n in ALL_NUMBERS if n >= 1000 and n in results],
    }

    labels = [k for k, v in bands.items() if v]
    means = [np.mean([active_count(results[n]) for n in bands[k]]) for k in labels]
    stds  = [np.std ([active_count(results[n]) for n in bands[k]]) for k in labels]
    within = [within_class_similarity(results, bands[k]) for k in labels]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    ax1.bar(labels, means, yerr=stds, color="steelblue", alpha=0.8, capsize=5)
    ax1.set_ylabel("Mean active SAE features")
    ax1.set_title("Feature count by digit-count band\n(do larger numbers have more features?)")
    ax1.grid(True, alpha=0.3, axis="y")
    plt.setp(ax1.get_xticklabels(), rotation=20, ha="right")

    ax2.bar(labels, within, color="mediumpurple", alpha=0.8)
    ax2.set_ylabel("Within-band cosine similarity")
    ax2.set_title("Feature coherence by band\n(do same-magnitude numbers cluster?)")
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3, axis="y")
    plt.setp(ax2.get_xticklabels(), rotation=20, ha="right")

    fig.tight_layout()
    out = RESULTS_DIR / "magnitude_bands.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Magnitude bands: {out.name}")


def print_summary(results):
    print("\n--- Feature counts by number ---")
    print(f"{'n':>6}  {'features':>8}  {'classes'}")
    for n in sorted(results.keys()):
        cls = classify(n)
        print(f"{n:>6}  {active_count(results[n]):>8}  {', '.join(cls)}")

    primes_in = [n for n in PRIMES[:25] if n in results]
    comps_in  = [n for n in COMPOSITES[:25] if n in results]
    if primes_in and comps_in:
        pm = np.mean([active_count(results[n]) for n in primes_in])
        cm = np.mean([active_count(results[n]) for n in comps_in])
        print(f"\nPrime mean features:    {pm:.1f}")
        print(f"Composite mean features: {cm:.1f}")
        print(f"Difference:              {pm - cm:+.1f}")
        wp = within_class_similarity(results, primes_in)
        wc = within_class_similarity(results, comps_in)
        xp = cross_class_similarity(results, primes_in, comps_in)
        print(f"\nWithin-prime similarity:     {wp:.3f}")
        print(f"Within-composite similarity: {wc:.3f}")
        print(f"Cross-class similarity:      {xp:.3f}")
        if wp > xp + 0.02:
            print("\n→ Primes form a tighter cluster than their cross-class similarity — distinct object.")
        else:
            print("\n→ Primes do not form a distinct cluster from composites at this layer.")


def main():
    model, sae = load_model_and_sae(PROBE_LAYER)

    print(f"\nProbing {len(ALL_NUMBERS)} numbers at layer {PROBE_LAYER}...")
    print(f"Template: '{TEMPLATE}'")
    results = collect(model, sae, ALL_NUMBERS, PROBE_LAYER)
    print(f"  {len(results)} numbers processed")

    print("\nGenerating plots...")
    plot_feature_count_by_magnitude(results)
    plot_prime_vs_composite(results)
    plot_class_similarity_matrix(results)
    plot_magnitude_bands(results)
    print_summary(results)

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
