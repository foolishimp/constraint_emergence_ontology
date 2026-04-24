"""
Experiment 16: Permutation / Shuffle Baselines for the Invariant Core

Critics' objection to exp 09: the "invariant core" could be a pipeline
artifact — just whatever features happen to fire on the number token,
independent of context. This experiment tests three null models:

  Null-1  TARGET-SHUFFLE: for each context, insert a *randomly chosen*
          number instead of the real target. Features-in-all-contexts
          then measures 'what fires on random numbers in this template'
          — nothing about the target.

  Null-2  CONTEXT-SHUFFLE: keep target fixed, but replace each context
          template with a *random GPT-2 prompt* (no numerical meaning).
          Features-in-all-contexts measures 'what fires on the target
          regardless of any prompt'.

  Null-3  BOOTSTRAP: draw 8 random (target, template) pairs — different
          numbers in different templates — and measure intersection.
          This is the full random-prompt null.

For each target and each null, run N_ITER iterations and build an
empirical distribution of |intersection|. Compare to the observed
invariant core size from exp 15/09.

If the observed core size is indistinguishable from any null, the
invariant-core result is not load-bearing.
"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import urllib.request

RESULTS_DIR = Path(__file__).parent.parent / "results" / "16_permutation_baseline"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 8
ACTIVATION_THRESHOLD = 0.5
N_ITER = 30  # bootstrap iterations per null per target

CULTURAL = [666, 999, 7, 42, 100]
RANDOM_NUMBERS_POOL = list(range(2, 1000))  # for shuffling

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

# Non-numerical templates (for context-shuffle null) — each has a {n} slot
# that will be filled but the surrounding meaning has no number-specific role
RANDOM_TEMPLATES = [
    "She walked into the room and said {n}",
    "The old book mentioned {n}",
    "Yesterday we saw {n}",
    "In the garden there was {n}",
    "Nobody expected {n}",
    "The cat looked at {n}",
    "Far away in the forest {n}",
    "Under the bridge we found {n}",
    "The song began with {n}",
    "A letter arrived containing {n}",
    "The weather report said {n}",
    "In silence they heard {n}",
]


# ---------------------------------------------------------------------------
# Model + SAE
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
    return model, sae


def get_features(model, sae, text, n_token):
    """Find last-token of the numeric span and return SAE features there."""
    import torch
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    target = str(n_token)
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
        return None
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{PROBE_LAYER}.hook_resid_pre"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    resid = cache[hook_name][0, pos, :]
    with torch.no_grad():
        acts = sae.encode(resid.unsqueeze(0))[0]
    return acts.numpy()


def active_set(vec, threshold=ACTIVATION_THRESHOLD):
    return set(np.where(vec > threshold)[0].tolist())


# ---------------------------------------------------------------------------
# Observed core + the three nulls
# ---------------------------------------------------------------------------

def observed_core(model, sae, target):
    """Invariant core size for target across the 8 exp-09 contexts."""
    sets = []
    for template in CONTEXTS.values():
        vec = get_features(model, sae, template.format(n=target), target)
        if vec is None:
            return None
        sets.append(active_set(vec))
    return set.intersection(*sets)


def null_target_shuffle(model, sae, rng, n_iter=N_ITER):
    """
    Null-1: for each of the 8 exp-09 contexts, plug in a DIFFERENT random
    number. Intersection = size of the 'typical' invariant feature set
    when the target is not held constant.
    """
    sizes = []
    for _ in range(n_iter):
        sets = []
        for template in CONTEXTS.values():
            n = int(rng.choice(RANDOM_NUMBERS_POOL))
            vec = get_features(model, sae, template.format(n=n), n)
            if vec is None:
                continue
            sets.append(active_set(vec))
        if sets:
            sizes.append(len(set.intersection(*sets)))
    return np.array(sizes)


def null_context_shuffle(model, sae, target, rng, n_iter=N_ITER):
    """
    Null-2: keep target fixed; use random non-numerical templates.
    Intersection = 'what fires on target regardless of prompt'.
    """
    sizes = []
    for _ in range(n_iter):
        picks = rng.choice(len(RANDOM_TEMPLATES),
                           size=len(CONTEXTS), replace=False)
        sets = []
        for idx in picks:
            template = RANDOM_TEMPLATES[idx]
            vec = get_features(model, sae, template.format(n=target), target)
            if vec is None:
                continue
            sets.append(active_set(vec))
        if sets:
            sizes.append(len(set.intersection(*sets)))
    return np.array(sizes)


def null_full_random(model, sae, rng, n_iter=N_ITER):
    """
    Null-3: 8 random (target, template) pairs where templates are random and
    numbers are random.  Gives the purest prompt-agnostic intersection null.
    """
    sizes = []
    for _ in range(n_iter):
        sets = []
        for _ in range(len(CONTEXTS)):
            n = int(rng.choice(RANDOM_NUMBERS_POOL))
            template = RANDOM_TEMPLATES[int(rng.integers(len(RANDOM_TEMPLATES)))]
            vec = get_features(model, sae, template.format(n=n), n)
            if vec is None:
                continue
            sets.append(active_set(vec))
        if sets:
            sizes.append(len(set.intersection(*sets)))
    return np.array(sizes)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_null_distributions(observed, nulls):
    """
    Per-target row: histogram of each null, red line = observed core size.
    """
    targets = list(observed.keys())
    null_names = ["target_shuffle", "context_shuffle_per_target", "full_random"]
    nrows = len(targets)
    ncols = 3

    fig, axes = plt.subplots(nrows, ncols, figsize=(13, 3 * nrows),
                             squeeze=False)
    for i, t in enumerate(targets):
        obs = observed[t]
        for j, nn in enumerate(null_names):
            ax = axes[i][j]
            if nn == "target_shuffle":
                dist = nulls["target_shuffle"]  # shared across targets
                title = "Null-1: target-shuffle"
            elif nn == "context_shuffle_per_target":
                dist = nulls["context_shuffle"][t]
                title = "Null-2: context-shuffle"
            else:
                dist = nulls["full_random"]
                title = "Null-3: full random"
            ax.hist(dist, bins=max(10, int(max(dist)+1)), color="gray",
                    alpha=0.7, edgecolor="black")
            ax.axvline(obs, color="tomato", linewidth=2,
                       label=f"obs = {obs}")
            ax.set_title(f"n={t}  {title}\nmean={dist.mean():.2f}  "
                         f"max={dist.max()}", fontsize=8)
            ax.set_xlabel("|intersection|")
            ax.set_ylabel("count")
            ax.legend(fontsize=8)
    fig.tight_layout()
    out = RESULTS_DIR / "null_distributions.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_summary_comparison(observed, nulls):
    """Bar: observed vs each null mean ± std, per target."""
    targets = list(observed.keys())
    x = np.arange(len(targets))
    width = 0.22

    fig, ax = plt.subplots(figsize=(12, 5))
    obs_vals = [observed[t] for t in targets]
    n1 = nulls["target_shuffle"]
    n3 = nulls["full_random"]
    n2_means = [nulls["context_shuffle"][t].mean() for t in targets]
    n2_stds  = [nulls["context_shuffle"][t].std()  for t in targets]

    ax.bar(x - 1.5*width, obs_vals, width, color="tomato",
           label="observed (exp 09 core)")
    ax.bar(x - 0.5*width, [n1.mean()] * len(targets), width,
           yerr=[n1.std()] * len(targets),
           color="gray", alpha=0.85, label=f"null-1 target shuffle  μ={n1.mean():.1f}")
    ax.bar(x + 0.5*width, n2_means, width, yerr=n2_stds,
           color="orange", alpha=0.85, label="null-2 context shuffle")
    ax.bar(x + 1.5*width, [n3.mean()] * len(targets), width,
           yerr=[n3.std()] * len(targets),
           color="darkblue", alpha=0.7, label=f"null-3 full random  μ={n3.mean():.1f}")

    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in targets])
    ax.set_ylabel("|invariant core|")
    ax.set_title("Invariant core: observed vs three null baselines")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "null_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def write_report(observed, nulls):
    out = RESULTS_DIR / "permutation_report.txt"
    lines = [f"Permutation / Null-Baseline Report — layer {PROBE_LAYER}",
             "=" * 70, ""]
    n1 = nulls["target_shuffle"]
    n3 = nulls["full_random"]
    lines.append(f"N_ITER per null = {N_ITER}\n")
    lines.append(f"Null-1 (target-shuffle): |core| over {len(n1)} iters")
    lines.append(f"   mean={n1.mean():.3f}  std={n1.std():.3f}  "
                 f"max={int(n1.max())}  min={int(n1.min())}")
    lines.append(f"Null-3 (full random):    |core| over {len(n3)} iters")
    lines.append(f"   mean={n3.mean():.3f}  std={n3.std():.3f}  "
                 f"max={int(n3.max())}  min={int(n3.min())}")
    lines.append("")

    lines.append("Observed core sizes vs nulls:")
    lines.append(f"{'target':>6}  {'observed':>8}  {'p(null1)':>9}  {'p(null2)':>9}  {'p(null3)':>9}")
    for t in observed:
        obs = observed[t]
        n2 = nulls["context_shuffle"][t]
        p1 = float((n1 >= obs).mean())
        p2 = float((n2 >= obs).mean())
        p3 = float((n3 >= obs).mean())
        lines.append(f"{str(t):>6}  {obs:>8}  {p1:>9.3f}  {p2:>9.3f}  {p3:>9.3f}")

    lines.append("\np-value ≡ fraction of null iters with |core| >= observed")
    lines.append("Low p ⇒ observed core is real; high p ⇒ could be null artifact")

    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()
    rng = np.random.default_rng(seed=17)

    print("\n--- Computing observed invariant cores ---")
    observed = {}
    for t in CULTURAL:
        core = observed_core(model, sae, t)
        observed[t] = len(core) if core is not None else 0
        print(f"   target={t}  core_size={observed[t]}")

    print(f"\n--- Null-1: target shuffle ({N_ITER} iters) ---")
    n1 = null_target_shuffle(model, sae, rng)
    print(f"   mean |core|={n1.mean():.2f}  max={n1.max()}  "
          f"distribution over {len(n1)} iters")

    print(f"\n--- Null-3: full random ({N_ITER} iters) ---")
    n3 = null_full_random(model, sae, rng)
    print(f"   mean |core|={n3.mean():.2f}  max={n3.max()}")

    context_shuffle = {}
    print(f"\n--- Null-2: context shuffle per target ({N_ITER} iters each) ---")
    for t in CULTURAL:
        cs = null_context_shuffle(model, sae, t, rng)
        context_shuffle[t] = cs
        print(f"   target={t}  mean |core|={cs.mean():.2f}  max={cs.max()}")

    nulls = {
        "target_shuffle": n1,
        "full_random":    n3,
        "context_shuffle": context_shuffle,
    }

    print("\nGenerating plots...")
    plot_null_distributions(observed, nulls)
    plot_summary_comparison(observed, nulls)
    write_report(observed, nulls)

    # Save raw
    raw = {
        "observed": observed,
        "null_target_shuffle": n1.tolist(),
        "null_full_random":    n3.tolist(),
        "null_context_shuffle": {str(k): v.tolist() for k, v in context_shuffle.items()},
    }
    (RESULTS_DIR / "null_raw.json").write_text(json.dumps(raw, indent=2))

    print("\n--- Summary ---")
    print(f"Null-1 target-shuffle   μ={n1.mean():.2f}  σ={n1.std():.2f}")
    print(f"Null-3 full-random      μ={n3.mean():.2f}  σ={n3.std():.2f}")
    print(f"{'target':>6}  observed  null-2 μ  p(null1)  p(null2)  p(null3)")
    for t in CULTURAL:
        obs = observed[t]
        n2 = context_shuffle[t]
        p1 = float((n1 >= obs).mean())
        p2 = float((n2 >= obs).mean())
        p3 = float((n3 >= obs).mean())
        print(f"{str(t):>6}  {obs:>8}  {n2.mean():>8.2f}  "
              f"{p1:>8.3f}  {p2:>8.3f}  {p3:>8.3f}")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
