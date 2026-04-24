"""
Experiment 04: Semantic Register Scan

A number is not a single Markov object — it is a family of them, one per
semantic register. "7" in arithmetic has a different boundary than "7" as
ordinal, temporal, or cultural symbol.

Hypothesis:
  The tipping point n → n+1 shifts measurably when the semantic frame changes.
  If true, the blanket is context-conditional — the Markov object for "7" is
  not fixed but selected by the surrounding constraint surface.

Method:
  - Fix number pair (6→7, 7→8) as the probe
  - Vary semantic frame via prompt template
  - Measure crossing α and blanket width per register
  - Plot: do registers produce distinct tipping points?

Registers tested:
  arithmetic    "3 + 4 ="          → 7, 8
  ordinal       "The 7th item"     → 7th, 8th
  temporal      "At 7 o'clock"     → 7, 8
  cardinal_qty  "There were 7 people"
  label         "Room 7"
  cultural      "Lucky number 7"
  negative      "-7 degrees"
  decimal       "3.7 rounded"
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "04_semantic_register_scan"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

N_STEPS = 40
PROBE_LAYER = 6

# Each register: list of (prompt_a, answer_token_a, prompt_b, answer_token_b)
# Pair is always 6→7 and 7→8 so results are comparable across registers
REGISTERS = {
    "arithmetic": [
        ("3 + 4 =", " 7", "4 + 4 =", " 8"),
        ("1 + 6 =", " 7", "1 + 7 =", " 8"),
        ("14 - 7 =", " 7", "16 - 8 =", " 8"),
    ],
    "ordinal": [
        ("She finished in", " 7th", "She finished in", " 8th"),
        ("The", " 7th", "The", " 8th"),
        ("It was the", " 7th", "It was the", " 8th"),
    ],
    "temporal": [
        ("The meeting starts at", " 7", "The meeting starts at", " 8"),
        ("She woke up at", " 7", "She woke up at", " 8"),
        ("It was", " 7", "It was", " 8"),
    ],
    "cardinal_quantity": [
        ("There were", " 7", "There were", " 8"),
        ("He bought", " 7", "He bought", " 8"),
        ("The team had", " 7", "The team had", " 8"),
    ],
    "label_identifier": [
        ("She stayed in Room", " 7", "She stayed in Room", " 8"),
        ("Take bus number", " 7", "Take bus number", " 8"),
        ("Channel", " 7", "Channel", " 8"),
    ],
    "cultural": [
        ("Lucky number", " 7", "Lucky number", " 8"),
        ("The magic number is", " 7", "The magic number is", " 8"),
        ("He always chose", " 7", "He always chose", " 8"),
    ],
    "measurement": [
        ("The temperature was", " 7", "The temperature was", " 8"),
        ("She scored", " 7", "She scored", " 8"),
        ("The rating was", " 7", "The rating was", " 8"),
    ],
}


def load_model():
    from transformer_lens import HookedTransformer
    print("Loading GPT-2 via TransformerLens...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()
    return model


def get_vec(model, text, layer):
    import torch
    tokens = model.to_tokens(text)
    hook_name = f"blocks.{layer}.hook_resid_post"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    return cache[hook_name][0, -1, :].clone()


def patch_probs(model, base_prompt, layer, vec):
    import torch

    def hook_fn(value, hook):
        value[0, -1, :] = vec
        return value

    tokens = model.to_tokens(base_prompt)
    with torch.no_grad():
        logits = model.run_with_hooks(
            tokens,
            fwd_hooks=[(f"blocks.{layer}.hook_resid_post", hook_fn)]
        )
    return logits[0, -1, :].softmax(dim=-1)


def probe_template(model, prompt_a, tok_a, prompt_b, tok_b, layer):
    try:
        id_a = model.to_single_token(tok_a)
        id_b = model.to_single_token(tok_b)
    except Exception:
        return None

    vec_a = get_vec(model, prompt_a, layer)
    vec_b = get_vec(model, prompt_b, layer)

    alphas = np.linspace(0, 1, N_STEPS)
    pa_list, pb_list = [], []
    for alpha in alphas:
        interp = (1 - alpha) * vec_a + alpha * vec_b
        probs = patch_probs(model, prompt_a, layer, interp)
        pa_list.append(probs[id_a].item())
        pb_list.append(probs[id_b].item())

    pa, pb = np.array(pa_list), np.array(pb_list)
    return pa, pb, alphas


def crossing(alphas, pa, pb):
    diff = pa - pb
    for i in range(len(diff) - 1):
        if diff[i] * diff[i + 1] <= 0:
            t = diff[i] / (diff[i] - diff[i + 1] + 1e-12)
            return alphas[i] + t * (alphas[i + 1] - alphas[i])
    return None


def blanket_width(pa, pb, threshold=0.1):
    return (np.abs(pa - pb) < threshold).sum() / len(pa)


def probe_register(model, register_name, templates, layer):
    """Average results across the templates in a register."""
    all_pa, all_pb, all_alphas = [], [], []
    crossings, widths = [], []

    for prompt_a, tok_a, prompt_b, tok_b in templates:
        result = probe_template(model, prompt_a, tok_a, prompt_b, tok_b, layer)
        if result is None:
            continue
        pa, pb, alphas = result
        all_pa.append(pa)
        all_pb.append(pb)
        all_alphas = alphas
        c = crossing(alphas, pa, pb)
        crossings.append(c if c is not None else float("nan"))
        widths.append(blanket_width(pa, pb))

    if not all_pa:
        return None

    mean_pa = np.mean(all_pa, axis=0)
    mean_pb = np.mean(all_pb, axis=0)
    mean_crossing = np.nanmean(crossings)
    mean_width = np.mean(widths)
    std_crossing = np.nanstd(crossings)
    std_width = np.std(widths)

    return {
        "register": register_name,
        "mean_pa": mean_pa,
        "mean_pb": mean_pb,
        "alphas": all_alphas,
        "crossing": mean_crossing,
        "crossing_std": std_crossing,
        "width": mean_width,
        "width_std": std_width,
        "n_templates": len(all_pa),
    }


def plot_register_curves(results):
    """All registers overlaid on one plot."""
    import seaborn as sns
    palette = sns.color_palette("tab10", n_colors=len(results))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Semantic register scan: does context shift the tipping point?",
                 fontsize=11, fontweight="bold")

    for i, r in enumerate(results):
        color = palette[i]
        label = r["register"]
        ax1.plot(r["alphas"], r["mean_pa"] - r["mean_pb"],
                 color=color, linewidth=2, label=label)
        ax1.axhline(0, color="gray", linewidth=0.6, linestyle="--")

    ax1.set_xlabel("Interpolation α  (0=n side, 1=n+1 side)")
    ax1.set_ylabel("P(n+1) - P(n+2)  [A dominates if > 0]")
    ax1.set_title("Probability difference by register\n(crossing = tipping point)")
    ax1.legend(fontsize=8, bbox_to_anchor=(1.02, 1), loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Blanket width comparison
    names = [r["register"] for r in results]
    widths = [r["width"] for r in results]
    width_stds = [r["width_std"] for r in results]
    crossings = [r["crossing"] for r in results]
    cross_stds = [r["crossing_std"] for r in results]

    x = np.arange(len(names))
    bars = ax2.bar(x, widths, yerr=width_stds, color=palette,
                   alpha=0.8, capsize=4)
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax2.set_ylabel("Blanket width")
    ax2.set_title("Blanket width by register\n(lower = tighter object boundary)")
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3, axis="y")

    # Annotate crossing α on bars
    for bar, c, cs in zip(bars, crossings, cross_stds):
        if not np.isnan(c):
            ax2.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.02,
                     f"α={c:.2f}", ha="center", va="bottom", fontsize=7)

    fig.tight_layout()
    out = RESULTS_DIR / "register_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Register comparison: {out}")


def plot_crossing_scatter(results):
    """Crossing α vs blanket width — each register as a point."""
    import seaborn as sns
    palette = sns.color_palette("tab10", n_colors=len(results))

    fig, ax = plt.subplots(figsize=(7, 6))
    for i, r in enumerate(results):
        ax.scatter(r["crossing"], r["width"],
                   color=palette[i], s=120, zorder=3,
                   label=r["register"])
        ax.annotate(r["register"],
                    (r["crossing"], r["width"]),
                    textcoords="offset points", xytext=(6, 3), fontsize=7)

    ax.axvline(0.5, color="gray", linestyle="--", linewidth=0.8, label="α=0.5")
    ax.set_xlabel("Crossing α  (0.5 = symmetric)")
    ax.set_ylabel("Blanket width")
    ax.set_title("Register map\nTop-left = tight + symmetric (strongest object)\n"
                 "Bottom-right = diffuse + asymmetric (weakest boundary)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "register_scatter.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Register scatter: {out}")


def main():
    model = load_model()

    results = []
    for name, templates in REGISTERS.items():
        print(f"\n--- {name} ({len(templates)} templates, layer {PROBE_LAYER}) ---")
        r = probe_register(model, name, templates, PROBE_LAYER)
        if r is None:
            print("  skipped (all templates multi-token)")
            continue
        results.append(r)
        print(f"  crossing α = {r['crossing']:.3f} ± {r['crossing_std']:.3f}")
        print(f"  blanket width = {r['width']:.2%} ± {r['width_std']:.2%}")

    print("\nGenerating plots...")
    plot_register_curves(results)
    plot_crossing_scatter(results)

    # Summary: are registers distinguishable?
    crossings = [r["crossing"] for r in results if not np.isnan(r["crossing"])]
    widths = [r["width"] for r in results]

    spread_crossing = np.std(crossings)
    spread_width = np.std(widths)

    print("\n--- Register separation ---")
    print(f"Crossing α  std across registers: {spread_crossing:.3f}")
    print(f"Width       std across registers: {spread_width:.3f}")

    if spread_crossing > 0.08 or spread_width > 0.1:
        print("\nVerdict: registers produce DISTINGUISHABLE tipping points.")
        print("The number '7' is a family of context-conditional Markov objects,")
        print("not a single fixed boundary.")
    else:
        print("\nVerdict: registers are NOT clearly distinguished at this layer.")
        print("Try layer scan — separation may emerge at different depths.")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
