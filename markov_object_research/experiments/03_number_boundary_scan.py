"""
Experiment 03: Number Boundary Scan

Is the tipping point between adjacent integers constant, frequency-driven,
or algorithmically structured?

Hypotheses:
  H1 Constant   — blanket width flat across all n → n+1 pairs (uniform number line)
  H2 Frequency  — width grows with magnitude (common numbers = tighter objects)
  H3 Algorithmic — flat within digit-count, discontinuity at 9→10, 99→100, 999→1000

Method:
  - Fix template: "{n} + 1 ="  →  next token should be "{n+1}"
  - Interpolate activations between prompt_n and prompt_{n+1} at mid-network layer
  - Measure crossing α and blanket width for each pair
  - Plot width and crossing vs magnitude (log scale)
  - Mark digit-count boundaries

Pairs tested:
  Adjacent singles:  1→2, 2→3, ..., 8→9
  Boundary:          9→10
  Adjacent doubles:  10→11, 11→12, ..., 19→20, 49→50, 98→99
  Boundary:          99→100
  Adjacent triples:  100→101, 499→500, 998→999
  Boundary:          999→1000
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "03_number_boundary_scan"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

N_STEPS = 30
PROBE_LAYER = 6  # mid-network; also do a quick layer scan for one pair

# Number pairs to probe: (n, n+1)
# Chosen to cover digit-count transitions and sample within each range
NUMBER_PAIRS = (
    # single digits
    list(range(1, 10)) +
    # double digits — sample
    [10, 11, 12, 15, 19, 20, 25, 49, 50, 89, 98, 99] +
    # triple digits — sample
    [100, 101, 199, 200, 499, 500, 899, 998, 999]
)

# Digit-count boundaries for annotation
BOUNDARIES = {9: "9→10", 99: "99→100", 999: "999→1000"}


def load_model():
    from transformer_lens import HookedTransformer
    print("Loading GPT-2 via TransformerLens...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()
    return model


def prompt_for(n):
    return f"{n} + 1 ="


def get_last_token_resid(model, text, layer):
    import torch
    tokens = model.to_tokens(text)
    hook_name = f"blocks.{layer}.hook_resid_post"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    return cache[hook_name][0, -1, :].clone()


def patch_and_get_probs(model, base_prompt, layer, patched_vec):
    import torch

    def hook_fn(value, hook):
        value[0, -1, :] = patched_vec
        return value

    tokens = model.to_tokens(base_prompt)
    with torch.no_grad():
        logits = model.run_with_hooks(
            tokens,
            fwd_hooks=[(f"blocks.{layer}.hook_resid_post", hook_fn)]
        )
    return logits[0, -1, :].softmax(dim=-1)


def probe_pair(model, n, layer):
    """
    Interpolate activations between prompt_n and prompt_{n+1}.
    Returns crossing α, blanket width, and whether tokenisation is clean.
    """
    pa_text = prompt_for(n)
    pb_text = prompt_for(n + 1)

    answer_a = f" {n + 1}"
    answer_b = f" {n + 2}"

    try:
        id_a = model.to_single_token(answer_a)
        id_b = model.to_single_token(answer_b)
    except Exception:
        return None

    vec_a = get_last_token_resid(model, pa_text, layer)
    vec_b = get_last_token_resid(model, pb_text, layer)

    alphas = np.linspace(0, 1, N_STEPS)
    prob_a_arr, prob_b_arr = [], []

    for alpha in alphas:
        interp = (1 - alpha) * vec_a + alpha * vec_b
        probs = patch_and_get_probs(model, pa_text, layer, interp)
        prob_a_arr.append(probs[id_a].item())
        prob_b_arr.append(probs[id_b].item())

    pa = np.array(prob_a_arr)
    pb = np.array(prob_b_arr)

    crossing = _find_crossing(alphas, pa, pb)
    width = _blanket_width(pa, pb)

    return {
        "n": n,
        "crossing": crossing,
        "width": width,
        "prob_a": pa,
        "prob_b": pb,
        "alphas": alphas,
    }


def _find_crossing(alphas, pa, pb):
    diff = pa - pb
    for i in range(len(diff) - 1):
        if diff[i] * diff[i + 1] <= 0:
            t = diff[i] / (diff[i] - diff[i + 1] + 1e-12)
            return alphas[i] + t * (alphas[i + 1] - alphas[i])
    return None


def _blanket_width(pa, pb, threshold=0.1):
    return (np.abs(pa - pb) < threshold).sum() / len(pa)


def plot_summary(results):
    ns = [r["n"] for r in results]
    widths = [r["width"] for r in results]
    crossings = [r["crossing"] if r["crossing"] is not None else float("nan")
                 for r in results]

    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    fig.suptitle("Number Boundary Scan — Is the Markov blanket constant?",
                 fontsize=12, fontweight="bold")

    # Top: blanket width
    ax = axes[0]
    ax.plot(ns, widths, marker="o", color="mediumpurple", linewidth=1.5,
            markersize=5, label="Blanket width")
    ax.axhline(np.nanmean(widths), color="gray", linestyle="--",
               linewidth=0.8, label=f"Mean {np.nanmean(widths):.2f}")
    for boundary_n, label in BOUNDARIES.items():
        if boundary_n in ns:
            ax.axvline(boundary_n, color="tomato", linestyle=":", linewidth=1.2)
            ax.text(boundary_n, ax.get_ylim()[1] * 0.95 if ax.get_ylim()[1] > 0 else 0.95,
                    label, color="tomato", fontsize=7, ha="center")
    ax.set_ylabel("Blanket width\n(fraction uncertain)")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Bottom: crossing point
    ax = axes[1]
    ax.plot(ns, crossings, marker="o", color="steelblue", linewidth=1.5, markersize=5)
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, label="α=0.5 (symmetric)")
    for boundary_n in BOUNDARIES:
        if boundary_n in ns:
            ax.axvline(boundary_n, color="tomato", linestyle=":", linewidth=1.2)
    ax.set_ylabel("Crossing α\n(0=A side, 1=B side)")
    ax.set_xlabel("n  (pair: n → n+1)")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax.set_xscale("symlog", linthresh=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: str(int(x))))

    fig.tight_layout()
    out = RESULTS_DIR / "boundary_scan_summary.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\nSummary plot: {out}")


def plot_digit_boundary_detail(results):
    """
    Close-up of the 9→10 boundary — the most structurally interesting.
    Show individual probability curves for pairs around the boundary.
    """
    boundary_pairs = [r for r in results if r["n"] in range(6, 14)]
    if not boundary_pairs:
        return

    n_pairs = len(boundary_pairs)
    fig, axes = plt.subplots(1, n_pairs, figsize=(3 * n_pairs, 4), sharey=True)
    fig.suptitle("9→10 boundary detail: individual tipping curves", fontsize=10)

    for ax, r in zip(axes, boundary_pairs):
        ax.plot(r["alphas"], r["prob_a"], color="steelblue", linewidth=1.5,
                label=f"P({r['n']+1})")
        ax.plot(r["alphas"], r["prob_b"], color="tomato", linewidth=1.5,
                label=f"P({r['n']+2})")
        if r["crossing"] is not None:
            ax.axvline(r["crossing"], color="purple", linestyle="--", linewidth=1)
        ax.set_title(f"{r['n']}→{r['n']+1}", fontsize=9)
        ax.set_xlabel("α", fontsize=8)
        if r == boundary_pairs[0]:
            ax.set_ylabel("P(next token)")
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    out = RESULTS_DIR / "digit_boundary_detail.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Digit boundary detail: {out}")


def main():
    model = load_model()

    results = []
    skipped = []

    print(f"\nProbing {len(NUMBER_PAIRS)} number pairs at layer {PROBE_LAYER}...")
    for n in NUMBER_PAIRS:
        result = probe_pair(model, n, PROBE_LAYER)
        if result is None:
            skipped.append(n)
            print(f"  n={n:>5}  skipped (multi-token answer)")
            continue
        results.append(result)
        c = f"{result['crossing']:.3f}" if result["crossing"] is not None else "none "
        print(f"  n={n:>5}  crossing={c}  width={result['width']:.2%}")

    if skipped:
        print(f"\nSkipped (multi-token): {skipped}")

    print("\nGenerating plots...")
    plot_summary(results)
    plot_digit_boundary_detail(results)

    # Print hypothesis verdict
    widths = [r["width"] for r in results]
    cv = np.std(widths) / (np.mean(widths) + 1e-9)  # coefficient of variation

    print("\n--- Hypothesis check ---")
    print(f"Mean blanket width: {np.mean(widths):.3f}")
    print(f"Std dev:            {np.std(widths):.3f}")
    print(f"Coefficient of variation: {cv:.3f}")

    boundary_ns = [9, 99, 999]
    for bn in boundary_ns:
        before = [r["width"] for r in results if r["n"] == bn - 1]
        after  = [r["width"] for r in results if r["n"] == bn + 1]
        if before and after:
            print(f"Width jump at {bn}→{bn+1}: {before[0]:.3f} → {after[0]:.3f}  "
                  f"(Δ={after[0]-before[0]:+.3f})")

    if cv < 0.2:
        verdict = "H1 SUPPORTED — blanket width approximately constant (uniform number line)"
    elif any(
        abs(r["width"] - results[0]["width"]) > 0.3
        for r in results if r["n"] > 50
    ):
        verdict = "H2 SUPPORTED — width grows with magnitude (frequency-driven encoding)"
    else:
        verdict = "H3 CANDIDATE — check digit-boundary jumps in plot"

    print(f"\nVerdict: {verdict}")
    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
