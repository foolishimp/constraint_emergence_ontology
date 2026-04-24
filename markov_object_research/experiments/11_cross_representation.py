"""
Experiment 11: Cross-Representation Invariance

Does a Markov object for a number exist above the token level?
Or is each surface form (7, seven, VII) its own local object?

Method:
  - For each integer, probe multiple surface forms:
      digit form   ("7")
      word form    ("seven")
      roman form   ("VII")
  - Template stays neutral: "The number {form} is"
  - Extract SAE features at the LAST token of the number's surface form
  - Compute feature overlap and cosine similarity between forms

Key test:
  Is similarity(7, seven) > similarity(7, 8)?
  If yes → quantity transcends symbol (form-invariant Markov object exists).
  If no  → each form is its own local object (identity bound to surface).

Probe numbers: 3, 7, 42, 100
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import urllib.request
import time

RESULTS_DIR = Path(__file__).parent.parent / "results" / "11_cross_representation"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 8
ACTIVATION_THRESHOLD = 0.5

# Reuse caches from earlier experiments
CACHE_FILES_READ = [
    Path(__file__).parent.parent / "results" / "08_feature_identity" / "neuronpedia_cache.json",
    Path(__file__).parent.parent / "results" / "09_context_conditional" / "neuronpedia_cache.json",
    Path(__file__).parent.parent / "results" / "10_layer_assembly" / "neuronpedia_cache.json",
]
CACHE_FILE = RESULTS_DIR / "neuronpedia_cache.json"

# Surface forms for each number
FORMS = {
    3:   [("digit", "3"),   ("word", "three"), ("roman", "III")],
    7:   [("digit", "7"),   ("word", "seven"), ("roman", "VII")],
    42:  [("digit", "42"),  ("word", "forty-two"), ("roman", "XLII")],
    100: [("digit", "100"), ("word", "hundred"),   ("roman", "C")],
}

TEMPLATE = "The number {form} is"

# For cross-number comparisons
OTHER_NUMBERS_FOR_NEIGHBOR_TEST = [2, 4, 6, 8, 40, 41, 43, 44, 99, 101]


# ---------------------------------------------------------------------------
# Cache
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


def fetch_feature_label(fid, cache, delay=0.2):
    key = f"gpt2-small/{PROBE_LAYER}-res-jb/{fid}"
    if key in cache:
        return cache[key]
    url = f"https://www.neuronpedia.org/api/feature/gpt2-small/{PROBE_LAYER}-res-jb/{fid}"
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
# Model
# ---------------------------------------------------------------------------

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
    print(f"  Layer {PROBE_LAYER} SAE loaded")
    return model, sae


def last_token_of_span(model, text, span):
    """Return the token index that covers the END of the span in text."""
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    # Walk through and find where the span sits in the reconstructed string
    # Simpler approach: iterate, keep char count, find first token whose end >= span_end
    reconstructed = ""
    span_start = text.find(span)
    if span_start < 0:
        return None
    span_end = span_start + len(span)

    # str_tokens starts with BOS. Reconstruct by stripping BOS.
    # Convert tokens to their string form and accumulate lengths.
    acc = 0
    # str_tokens[0] is BOS with empty string in HookedTransformer
    for i, tok in enumerate(str_tokens):
        if i == 0 and tok in ("<|endoftext|>", ""):
            continue
        acc += len(tok)
        if acc >= span_end:
            return i
    return None


def get_features(model, sae, text, span):
    import torch
    pos = last_token_of_span(model, text, span)
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


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def collect_form_features(model, sae):
    """For each (number, form), extract feature vector."""
    data = {}  # data[number][form_name] = vector
    for n, form_list in FORMS.items():
        data[n] = {}
        print(f"\n  n = {n}")
        for form_name, form_text in form_list:
            sentence = TEMPLATE.format(form=form_text)
            vec, pos = get_features(model, sae, sentence, form_text)
            if vec is None:
                print(f"    [{form_name:5s}] '{sentence}' — span not found")
                continue
            n_active = int((vec > ACTIVATION_THRESHOLD).sum())
            print(f"    [{form_name:5s}] '{sentence}' → pos={pos}, active={n_active}")
            data[n][form_name] = vec
    return data


def collect_digit_neighbors(model, sae, numbers):
    """Digit-form features for neighbor numbers (for within-form similarity)."""
    out = {}
    for n in numbers:
        text = TEMPLATE.format(form=str(n))
        vec, pos = get_features(model, sae, text, str(n))
        if vec is not None:
            out[n] = vec
    return out


def plot_within_number_overlap(data):
    """
    For each number, show the form-pair similarities:
    (digit,word), (digit,roman), (word,roman).
    Bar chart grouped by number.
    """
    numbers = list(data.keys())
    pairs = [("digit", "word"), ("digit", "roman"), ("word", "roman")]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(numbers))
    width = 0.25
    colors = ["steelblue", "mediumpurple", "tomato"]

    for i, (a, b) in enumerate(pairs):
        sims = []
        for n in numbers:
            if a in data[n] and b in data[n]:
                sims.append(cosine(data[n][a], data[n][b]))
            else:
                sims.append(float("nan"))
        ax.bar(x + i * width, sims, width, label=f"{a} ↔ {b}", color=colors[i])
        for xi, s in zip(x + i * width, sims):
            if not np.isnan(s):
                ax.text(xi, s + 0.01, f"{s:.2f}", ha="center", fontsize=7)

    ax.set_xticks(x + width)
    ax.set_xticklabels([str(n) for n in numbers])
    ax.set_xlabel("Number")
    ax.set_ylabel("Cosine similarity (feature vectors)")
    ax.set_title(f"Within-number form similarity — layer {PROBE_LAYER}\n"
                 "High = forms share an object; low = forms are distinct objects")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(fontsize=9)
    fig.tight_layout()
    out = RESULTS_DIR / "within_number_form_similarity.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Within-number overlap: {out.name}")


def plot_form_vs_neighbor(data, neighbor_data):
    """
    The KEY plot:
    For each target number (digit form) and form variant,
    compute similarity(target_digit, form_variant) vs
    compute similarity(target_digit, neighbor_digit)

    If form similarity > neighbor similarity → form-invariant object
    If neighbor similarity > form similarity → symbol-bound object
    """
    rows = []
    for n in data.keys():
        if "digit" not in data[n]:
            continue
        target = data[n]["digit"]

        # form variants
        for form_name in ("word", "roman"):
            if form_name not in data[n]:
                continue
            sim = cosine(target, data[n][form_name])
            rows.append({"n": n, "type": f"same n, {form_name}", "sim": sim})

        # neighbor digits
        for m in neighbor_data:
            if m == n:
                continue
            sim = cosine(target, neighbor_data[m])
            rows.append({"n": n, "type": f"digit {m}", "sim": sim, "neighbor": m})

    # Plot: for each target n, scatter showing form-sim vs neighbor-sim distribution
    fig, axes = plt.subplots(1, len(data), figsize=(4 * len(data), 4.5), sharey=True)
    if len(data) == 1:
        axes = [axes]

    for ax, n in zip(axes, data.keys()):
        n_rows = [r for r in rows if r["n"] == n]
        form_points = [r for r in n_rows if "same n" in r["type"]]
        neigh_points = [r for r in n_rows if "digit" in r["type"]]

        # Scatter neighbor similarities as blue dots
        if neigh_points:
            neigh_vals = [r["sim"] for r in neigh_points]
            ax.scatter([0] * len(neigh_vals), neigh_vals,
                       color="steelblue", alpha=0.6, s=50,
                       label="digit(other n) ↔ digit(this n)")
            mean_n = np.mean(neigh_vals)
            ax.axhline(mean_n, color="steelblue", linestyle="--", linewidth=1,
                       label=f"neighbor mean = {mean_n:.2f}")

        # Form points as red/purple triangles
        for r in form_points:
            color = "tomato" if "word" in r["type"] else "mediumpurple"
            marker = "^" if "word" in r["type"] else "s"
            ax.scatter([1], [r["sim"]], color=color, s=150, marker=marker,
                       label=r["type"], zorder=5)

        ax.set_title(f"n = {n}")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["other digits", "same-n forms"])
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="lower right")

    axes[0].set_ylabel("Cosine similarity to digit form")
    fig.suptitle(f"Form-invariance vs numeric-neighborhood — layer {PROBE_LAYER}\n"
                 "Does '7' cluster closer to 'seven' or to '8'?", fontweight="bold")
    fig.tight_layout()
    out = RESULTS_DIR / "form_vs_neighbor.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Form vs neighbor: {out.name}")


def save_feature_comparison_report(data, cache):
    """For each number, list invariant core across forms and unique-to-form features."""
    out = RESULTS_DIR / "form_feature_report.txt"
    lines = [f"Cross-Representation Feature Report — layer {PROBE_LAYER}", "=" * 70, ""]

    for n, forms in data.items():
        if len(forms) < 2:
            continue
        lines.append(f"\n### n = {n}  —  forms: {list(forms.keys())}")
        lines.append("-" * 50)

        # active sets per form
        active_sets = {
            fname: set(np.where(vec > ACTIVATION_THRESHOLD)[0].tolist())
            for fname, vec in forms.items()
        }
        all_union = set().union(*active_sets.values())
        invariant = set.intersection(*active_sets.values())

        lines.append(f"  Active counts: " +
                     "  ".join(f"{f}={len(s)}" for f, s in active_sets.items()))
        lines.append(f"  Union: {len(all_union)}")
        lines.append(f"  Invariant across all forms: {len(invariant)}")

        if invariant:
            lines.append("\n  Cross-form invariant features:")
            # sort by mean strength
            sorted_inv = sorted(invariant,
                                key=lambda f: -np.mean([forms[fn][f] for fn in forms]))
            for fid in sorted_inv[:10]:
                label = fetch_feature_label(int(fid), cache) or "—"
                strengths = {fn: forms[fn][fid] for fn in forms}
                sstr = "  ".join(f"{fn}={v:.1f}" for fn, v in strengths.items())
                lines.append(f"    F{int(fid):5d}  [{sstr}]  {label}")

        # form-specific
        for fname, fset in active_sets.items():
            others = set().union(*[s for fn, s in active_sets.items() if fn != fname])
            unique = fset - others
            if unique:
                lines.append(f"\n  Unique to {fname} ({len(unique)} features):")
                unique_sorted = sorted(unique, key=lambda f: -forms[fname][f])
                for fid in unique_sorted[:5]:
                    label = fetch_feature_label(int(fid), cache) or "—"
                    lines.append(f"    F{int(fid):5d}  {forms[fname][fid]:5.2f}  {label}")
        save_cache(cache)

    out.write_text("\n".join(lines))
    print(f"Form feature report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()
    cache = load_cache()

    print("Collecting form features...")
    data = collect_form_features(model, sae)

    print("\nCollecting digit-form features for neighbor numbers...")
    neighbor_data = collect_digit_neighbors(model, sae, OTHER_NUMBERS_FOR_NEIGHBOR_TEST)
    print(f"  Got features for {len(neighbor_data)} neighbors")

    print("\nGenerating plots...")
    plot_within_number_overlap(data)
    plot_form_vs_neighbor(data, neighbor_data)

    print("\nWriting feature comparison report...")
    save_feature_comparison_report(data, cache)

    # Summary: is form-invariance larger than numeric-neighbor similarity?
    print("\n--- Form-invariance vs numeric neighborhood ---")
    for n in data.keys():
        if "digit" not in data[n]:
            continue
        target = data[n]["digit"]
        form_sims = []
        for form_name in ("word", "roman"):
            if form_name in data[n]:
                form_sims.append(cosine(target, data[n][form_name]))
        neigh_sims = [cosine(target, neighbor_data[m])
                      for m in neighbor_data if m != n]
        if form_sims and neigh_sims:
            msf = np.mean(form_sims)
            mns = np.mean(neigh_sims)
            verdict = "FORM-INVARIANT" if msf > mns + 0.02 else \
                      "SYMBOL-BOUND" if mns > msf + 0.02 else "TIE"
            print(f"  n={n:>3}:  same-n mean form sim = {msf:.3f}   "
                  f"other-n mean digit sim = {mns:.3f}   → {verdict}")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
