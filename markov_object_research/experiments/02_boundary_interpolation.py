"""
Experiment 02: Boundary Interpolation — Finding the Markov Blanket

Uses TransformerLens for activation patching (purpose-built for this).

Hypothesis: the stochastic tipping point between two adjacent Markov objects
is the Markov blanket made visible.

Method:
  - Extract residual stream at layer L for two anchor prompts A and B
  - Linearly interpolate the last-token activation between A and B
  - Patch the interpolated vector back in via run_with_hooks
  - Read next-token probabilities at each step
  - Crossing point = tipping point = Markov blanket boundary
  - Width of uncertain zone = blanket thickness
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "02_boundary_interpolation"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

N_STEPS = 40


ANCHOR_PAIRS = [
    {
        "name": "1_to_2",
        "description": "Arithmetic: 1+1 → 1+2",
        "prompt_a": "1 + 1 =",
        "token_a": " 2",
        "prompt_b": "1 + 2 =",
        "token_b": " 3",
        "layer": 6,
    },
    {
        "name": "hot_to_cold",
        "description": "Temperature: hot → cold",
        "prompt_a": "The coffee was very hot. The temperature was",
        "token_a": " warm",
        "prompt_b": "The ice was very cold. The temperature was",
        "token_b": " cold",
        "layer": 6,
    },
    {
        "name": "true_to_false",
        "description": "Boolean: true → false",
        "prompt_a": "The statement is correct. The answer is",
        "token_a": " true",
        "prompt_b": "The statement is incorrect. The answer is",
        "token_b": " false",
        "layer": 6,
    },
]


def load_model():
    from transformer_lens import HookedTransformer
    print("Loading GPT-2 via TransformerLens...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()
    return model


def get_last_token_resid(model, prompt, layer):
    """Extract residual stream at layer for the last token position."""
    import torch
    tokens = model.to_tokens(prompt)
    hook_name = f"blocks.{layer}.hook_resid_post"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    return cache[hook_name][0, -1, :].clone()  # (d_model,)


def patched_next_token_probs(model, prompt, layer, patch_vec):
    """Run prompt through model with last-token residual stream patched at layer."""
    import torch

    def hook_fn(value, hook):
        value[0, -1, :] = patch_vec
        return value

    tokens = model.to_tokens(prompt)
    with torch.no_grad():
        logits = model.run_with_hooks(
            tokens,
            fwd_hooks=[(f"blocks.{layer}.hook_resid_post", hook_fn)]
        )
    probs = logits[0, -1, :].softmax(dim=-1)
    return probs


def interpolate_and_probe(model, pair):
    import torch
    layer = pair["layer"]
    prompt_a, token_a = pair["prompt_a"], pair["token_a"]
    prompt_b, token_b = pair["prompt_b"], pair["token_b"]

    vec_a = get_last_token_resid(model, prompt_a, layer)
    vec_b = get_last_token_resid(model, prompt_b, layer)

    id_a = model.to_single_token(token_a)
    id_b = model.to_single_token(token_b)

    alphas = np.linspace(0, 1, N_STEPS)
    prob_a_list, prob_b_list, entropy_list = [], [], []

    for alpha in alphas:
        interp = (1 - alpha) * vec_a + alpha * vec_b
        probs = patched_next_token_probs(model, prompt_a, layer, interp)
        prob_a_list.append(probs[id_a].item())
        prob_b_list.append(probs[id_b].item())
        p = probs.detach().numpy()
        p = np.clip(p, 1e-12, 1)
        entropy_list.append(-np.sum(p * np.log(p)))

    return alphas, np.array(prob_a_list), np.array(prob_b_list), np.array(entropy_list)


def find_crossing(alphas, prob_a, prob_b):
    diff = prob_a - prob_b
    for i in range(len(diff) - 1):
        if diff[i] * diff[i + 1] <= 0:
            t = diff[i] / (diff[i] - diff[i + 1] + 1e-12)
            return alphas[i] + t * (alphas[i + 1] - alphas[i])
    return None


def blanket_width(prob_a, prob_b, threshold=0.1):
    return (np.abs(prob_a - prob_b) < threshold).sum() / len(prob_a)


def plot_pair(pair_name, alphas, prob_a, prob_b, entropy, crossing, width, description):
    fig = plt.figure(figsize=(11, 8))
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(alphas, prob_a, label="P(token A)", color="steelblue", linewidth=2)
    ax1.plot(alphas, prob_b, label="P(token B)", color="tomato", linewidth=2)
    if crossing is not None:
        ax1.axvline(crossing, color="purple", linestyle="--", linewidth=1.2,
                    label=f"crossing α={crossing:.2f}")
    ax1.set_xlabel("Interpolation α  (0=A, 1=B)")
    ax1.set_ylabel("Next-token probability")
    ax1.set_title("Probability across interpolation")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(alphas, entropy, color="darkorange", linewidth=2)
    if crossing is not None:
        ax2.axvline(crossing, color="purple", linestyle="--", linewidth=1.2)
    ax2.set_xlabel("Interpolation α")
    ax2.set_ylabel("Shannon entropy (nats)")
    ax2.set_title("Model uncertainty\n(peak = blanket boundary)")
    ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(gs[1, 0])
    diff = prob_a - prob_b
    colors = ["steelblue" if d > 0.1 else "tomato" if d < -0.1 else "mediumpurple"
              for d in diff]
    ax3.bar(alphas, np.abs(diff), width=1.0 / N_STEPS * 0.9, color=colors, alpha=0.8)
    ax3.set_xlabel("Interpolation α")
    ax3.set_ylabel("|P(A) - P(B)|")
    ax3.set_title("Dominance  (purple = uncertain zone)")
    ax3.grid(True, alpha=0.3)

    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    c_str = f"{crossing:.3f}" if crossing is not None else "none"
    summary = (
        f"Pair: {description}\n\n"
        f"Crossing point α:  {c_str}\n"
        f"Blanket width:     {width:.2%} of range\n\n"
        "Interpretation:\n"
        f"  {'Tight blanket' if width < 0.2 else 'Wide blanket'} — "
        f"{'well-defined object' if width < 0.2 else 'diffuse boundary'}\n\n"
        "Entropy peak at crossing =\n"
        "model maximally uncertain =\n"
        "Markov blanket boundary."
    )
    ax4.text(0.05, 0.95, summary, transform=ax4.transAxes,
             verticalalignment="top", fontsize=9, fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    fig.suptitle(f"Markov Blanket Probe: {description}", fontsize=11, fontweight="bold")
    out_path = RESULTS_DIR / f"{pair_name}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  saved: {out_path.name}")


def layer_scan(model, pair, layers=None):
    if layers is None:
        layers = list(range(1, 12))

    widths, crossings = [], []
    for layer in layers:
        pair_copy = dict(pair, layer=layer)
        alphas, pa, pb, _ = interpolate_and_probe(model, pair_copy)
        c = find_crossing(alphas, pa, pb)
        w = blanket_width(pa, pb)
        crossings.append(c)
        widths.append(w)
        print(f"    layer {layer:2d}  crossing={f'{c:.3f}' if c else 'none':>8}  width={w:.2%}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(layers, widths, marker="o", color="mediumpurple")
    ax1.set_xlabel("Layer")
    ax1.set_ylabel("Blanket width (fraction)")
    ax1.set_title("Blanket width by layer")
    ax1.grid(True, alpha=0.3)

    cross_vals = [c if c is not None else float("nan") for c in crossings]
    ax2.plot(layers, cross_vals, marker="o", color="darkorange")
    ax2.axhline(0.5, color="gray", linestyle="--", linewidth=0.8)
    ax2.set_xlabel("Layer")
    ax2.set_ylabel("Crossing α")
    ax2.set_title("Tipping point position by layer")
    ax2.grid(True, alpha=0.3)

    fig.suptitle(f"Layer scan: {pair['description']}", fontsize=10, fontweight="bold")
    fig.tight_layout()
    out_path = RESULTS_DIR / f"{pair['name']}_layer_scan.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  layer scan saved: {out_path.name}")


def main():
    model = load_model()

    for pair in ANCHOR_PAIRS:
        print(f"\n--- {pair['description']} (layer {pair['layer']}) ---")
        alphas, prob_a, prob_b, entropy = interpolate_and_probe(model, pair)
        crossing = find_crossing(alphas, prob_a, prob_b)
        width = blanket_width(prob_a, prob_b)
        print(f"  crossing α = {crossing:.3f}" if crossing else "  no crossing found")
        print(f"  blanket width = {width:.2%}")
        plot_pair(pair["name"], alphas, prob_a, prob_b, entropy,
                  crossing, width, pair["description"])

    print(f"\n--- Layer scan: {ANCHOR_PAIRS[0]['description']} ---")
    layer_scan(model, ANCHOR_PAIRS[0], layers=list(range(1, 12)))

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
