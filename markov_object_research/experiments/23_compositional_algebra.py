"""
Experiment 23: Compositional Algebra of Identity Directions

If identity directions compose via vector arithmetic, the construct has
algebra — a Newtonian-level property. §13.4 names this as "object
composition". This experiment tests whether compound-object directions
are linearly reconstructible from component directions.

For each compound (context, number) pair, a 2×2 grid yields four cells:
    (ctx,    n)   (ctx,    null)
    (neutral, n)  (neutral, null)

Directions are extracted at the number-token position in the residual
stream (layer 8), averaged across a shared template pool:

    d_compound = μ(ctx, n)      − μ(neutral, null)
    d_A        = μ(ctx, null)   − μ(neutral, null)   # context effect
    d_B        = μ(neutral, n)  − μ(neutral, null)   # number effect

Test whether d_compound ≈ d_A + d_B by cosine, compared against a
permutation null built from (A, B) pairs drawn from other triples.

Pre-registered expectation:
  Mean cos(d_compound, d_A + d_B) ≥ 0.5 over 20 triples.
  Mean true-pair cosine exceeds mean random-pair cosine by ≥ 0.3,
  permutation p < 0.01.

Outcome interpretation:
  PASS     compound directions are approximately linear combinations
           of component directions; identity composes by vector
           addition.
  PARTIAL  compound-to-sum cosine in [0.3, 0.5] and exceeds random;
           composition is partly linear, partly non-linear.
  FAIL     compound-to-sum cosine ≈ random; composition is not linear
           at the direction level at this scale.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "23_compositional_algebra"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LAYER          = 8
NEUTRAL        = "number"
NULL_NUMBER    = 5

# 20 (context, number) compound pairs.
# Targets drawn from {999, 666, 137, 42} — same pool used in exps 08–18.
TRIPLES = [
    {"context": "page",      "number": 666},
    {"context": "page",      "number": 137},
    {"context": "page",      "number": 999},
    {"context": "room",      "number": 137},
    {"context": "room",      "number": 666},
    {"context": "room",      "number": 999},
    {"context": "line",      "number": 666},
    {"context": "line",      "number": 137},
    {"context": "line",      "number": 999},
    {"context": "chapter",   "number": 666},
    {"context": "chapter",   "number": 137},
    {"context": "chapter",   "number": 42},
    {"context": "floor",     "number": 137},
    {"context": "floor",     "number": 666},
    {"context": "flight",    "number": 999},
    {"context": "flight",    "number": 42},
    {"context": "section",   "number": 666},
    {"context": "section",   "number": 137},
    {"context": "mission",   "number": 42},
    {"context": "mission",   "number": 999},
]

TEMPLATES = [
    "The {ctx} {n} is here",
    "{ctx} {n} of the book",
    "I saw {ctx} {n} yesterday",
    "She mentioned {ctx} {n} earlier",
    "He called out {ctx} {n}",
    "Find {ctx} {n} immediately",
    "{ctx} {n} is important",
    "{ctx} {n} has meaning",
]

N_RANDOM_PAIRS = 100

# Pre-registered thresholds
COS_PASS_MEAN        = 0.50
COS_EXCESS_OVER_NULL = 0.30
PERM_ALPHA           = 0.01


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def load_model():
    from transformer_lens import HookedTransformer
    print("Loading GPT-2 small...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()
    return model


def last_token_of_span(model, text, span):
    start = text.find(span)
    if start < 0:
        return None
    end = start + len(span)
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    acc = 0
    for i, tok in enumerate(str_tokens):
        if i == 0 and tok in ("<|endoftext|>", ""):
            continue
        acc += len(tok)
        if acc >= end:
            return i
    return None


def capture_resid_at_number(model, text, n, layer=LAYER):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    pos = last_token_of_span(model, text, str(n))
    if pos is None:
        return None
    hook_name = f"blocks.{layer}.hook_resid_pre"
    captured = {}

    def capture(value, hook):
        captured["resid"] = value[0, pos, :].detach().clone().float()
        return value

    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=[(hook_name, capture)])
    return captured["resid"]


# ---------------------------------------------------------------------------
# Cell residual collection
# ---------------------------------------------------------------------------

def collect_cell(model, ctx, n):
    """
    Average residual at the number-token position across all templates
    for the given (ctx, n) cell.
    """
    import torch
    residuals = []
    for t in TEMPLATES:
        text = t.format(ctx=ctx, n=n)
        r = capture_resid_at_number(model, text, n)
        if r is None:
            continue
        residuals.append(r)
    if not residuals:
        return None, 0
    return torch.stack(residuals).mean(0), len(residuals)


def extract_triple_directions(model, triple):
    """
    For one (context, number) triple, extract:
      mu_compound  = μ(context, number)
      mu_A_side    = μ(context, null_number)    # for d_A
      mu_B_side    = μ(neutral_context, number) # for d_B
      mu_null      = μ(neutral_context, null_number)

    Returns directions (d_compound, d_A, d_B) and counts.
    """
    ctx = triple["context"]
    n   = triple["number"]

    mu_compound, n_c = collect_cell(model, ctx,     n)
    mu_a,        n_a = collect_cell(model, ctx,     NULL_NUMBER)
    mu_b,        n_b = collect_cell(model, NEUTRAL, n)
    mu_null,     n_0 = collect_cell(model, NEUTRAL, NULL_NUMBER)

    if any(x is None for x in (mu_compound, mu_a, mu_b, mu_null)):
        return None

    d_compound = mu_compound - mu_null
    d_A        = mu_a        - mu_null
    d_B        = mu_b        - mu_null

    return {
        "triple":       triple,
        "d_compound":   d_compound,
        "d_A":          d_A,
        "d_B":          d_B,
        "counts":       {"compound": n_c, "A": n_a, "B": n_b, "null": n_0},
        "norms":        {
            "compound": float(d_compound.norm()),
            "A":        float(d_A.norm()),
            "B":        float(d_B.norm()),
        },
    }


# ---------------------------------------------------------------------------
# Cosine geometry
# ---------------------------------------------------------------------------

def cos_sim(u, v):
    import torch
    nu = u.norm()
    nv = v.norm()
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    return float((u @ v / (nu * nv)).item())


def cos_compound_to_sum(d_compound, d_A, d_B):
    return cos_sim(d_compound, d_A + d_B)


# ---------------------------------------------------------------------------
# Random-pair permutation null
# ---------------------------------------------------------------------------

def random_pair_nulls(extracted, rng, n_draws=N_RANDOM_PAIRS):
    """
    For each triple i, sample n_draws random (A', B') pairs where A' and
    B' come from triples other than i. Return per-triple list of null
    cosines cos(d_compound_i, d_A' + d_B').
    """
    n = len(extracted)
    null_by_triple = []
    for i in range(n):
        other_idx = [j for j in range(n) if j != i]
        draws = []
        for _ in range(n_draws):
            ja = rng.choice(other_idx)
            jb = rng.choice(other_idx)
            while jb == ja:
                jb = rng.choice(other_idx)
            d_A_rand = extracted[ja]["d_A"]
            d_B_rand = extracted[jb]["d_B"]
            c = cos_compound_to_sum(
                extracted[i]["d_compound"], d_A_rand, d_B_rand,
            )
            draws.append(c)
        null_by_triple.append(draws)
    return null_by_triple


def permutation_p_value(true_mean, null_means_per_draw):
    """
    null_means_per_draw[d] = mean over triples of cosine at draw d of
    random-pair cosines. We ask: how often does the null mean match or
    exceed the true mean?
    """
    n = len(null_means_per_draw)
    hits = sum(1 for m in null_means_per_draw if m >= true_mean)
    return (hits + 1) / (n + 1)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_outcome(true_mean, null_mean, p_value):
    excess = true_mean - null_mean
    pass_mean   = true_mean  >= COS_PASS_MEAN
    pass_excess = excess     >= COS_EXCESS_OVER_NULL
    pass_p      = p_value    <  PERM_ALPHA

    if pass_mean and pass_excess and pass_p:
        return "PASS"
    if true_mean >= 0.30 and excess >= 0.15 and p_value < 0.05:
        return "PARTIAL"
    return "FAIL"


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_cosine_bars(true_cosines, null_means_per_triple, triples):
    labels = [f"{t['context']}/{t['number']}" for t in triples]
    x = np.arange(len(labels))
    width = 0.4
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width/2, true_cosines,           width,
           label="cos(d_compound, d_A + d_B)", color="#2563eb")
    ax.bar(x + width/2, null_means_per_triple,  width,
           label="random-pair null mean",       color="#9ca3af")
    ax.axhline(COS_PASS_MEAN, color="green", linestyle="--", alpha=0.6,
               label=f"threshold ({COS_PASS_MEAN})")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("cosine")
    ax.set_title("Per-triple: true (compound ↔ A+B) vs random-pair null")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "compound_vs_random.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_null_histogram(true_mean, null_means_per_draw):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(null_means_per_draw, bins=30, color="#9ca3af", alpha=0.85,
            edgecolor="white")
    ax.axvline(true_mean, color="#2563eb", linewidth=2,
               label=f"true mean = {true_mean:.3f}")
    ax.set_xlabel("mean cosine across triples")
    ax.set_ylabel("count")
    ax.set_title(f"Permutation null ({N_RANDOM_PAIRS} draws)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "null_histogram.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_component_contributions(extracted):
    """
    For each triple, show cos(d_compound, d_A) and cos(d_compound, d_B)
    alongside cos(d_compound, d_A + d_B).
    """
    labels     = [f"{e['triple']['context']}/{e['triple']['number']}"
                  for e in extracted]
    c_a        = [cos_sim(e["d_compound"], e["d_A"])             for e in extracted]
    c_b        = [cos_sim(e["d_compound"], e["d_B"])             for e in extracted]
    c_sum      = [cos_compound_to_sum(e["d_compound"], e["d_A"], e["d_B"])
                  for e in extracted]
    x     = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width, c_a,   width, label="cos(d_c, d_A)", color="#ef4444")
    ax.bar(x,         c_b,   width, label="cos(d_c, d_B)", color="#10b981")
    ax.bar(x + width, c_sum, width, label="cos(d_c, d_A+d_B)", color="#2563eb")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("cosine")
    ax.set_title("Per-triple: compound vs A, B, and A+B")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "component_contributions.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(extracted, true_cosines, null_by_triple,
                 true_mean, null_mean, p_value, outcome):
    lines = [
        "Exp 23 — Compositional Algebra of Identity Directions",
        "=" * 72,
        "",
        f"Layer:             {LAYER} (hook_resid_pre)",
        f"Neutral context:   '{NEUTRAL}'",
        f"Null number:       {NULL_NUMBER}",
        f"Triples:           {len(extracted)}",
        f"Templates per cell: {len(TEMPLATES)}",
        f"Random draws per triple: {N_RANDOM_PAIRS}",
        "",
        "Pre-registered rules:",
        f"  mean cos(d_compound, d_A + d_B) ≥ {COS_PASS_MEAN}",
        f"  excess over random-pair null     ≥ {COS_EXCESS_OVER_NULL}",
        f"  permutation p-value              <  {PERM_ALPHA}",
        "",
        f"AGGREGATE OUTCOME: {outcome}",
        "",
        "Summary statistics:",
        f"  mean true cosine:           {true_mean:+.3f}",
        f"  mean random-pair cosine:    {null_mean:+.3f}",
        f"  excess:                     {true_mean - null_mean:+.3f}",
        f"  permutation p-value:        {p_value:.4f}",
        "",
        "Per-triple:",
    ]
    for i, e in enumerate(extracted):
        t = e["triple"]
        c_sum = true_cosines[i]
        c_a   = cos_sim(e["d_compound"], e["d_A"])
        c_b   = cos_sim(e["d_compound"], e["d_B"])
        null_mean_i = float(np.mean(null_by_triple[i]))
        null_std_i  = float(np.std(null_by_triple[i]))
        norms = e["norms"]
        lines.append(
            f"  {t['context']:>8s}/{t['number']:<4d}  "
            f"cos(A+B)={c_sum:+.3f}  "
            f"cos(A)={c_a:+.3f}  "
            f"cos(B)={c_b:+.3f}  "
            f"null={null_mean_i:+.3f}±{null_std_i:.3f}  "
            f"||d_c||={norms['compound']:.2f} "
            f"||d_A||={norms['A']:.2f} "
            f"||d_B||={norms['B']:.2f}"
        )

    out = RESULTS_DIR / "compositional_report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")

    summary = {
        "outcome":    outcome,
        "true_mean":  true_mean,
        "null_mean":  null_mean,
        "excess":     true_mean - null_mean,
        "p_value":    p_value,
        "layer":      LAYER,
        "n_triples":  len(extracted),
        "per_triple": [
            {
                "context":     e["triple"]["context"],
                "number":      e["triple"]["number"],
                "cos_compound_sum": true_cosines[i],
                "cos_compound_A":   cos_sim(e["d_compound"], e["d_A"]),
                "cos_compound_B":   cos_sim(e["d_compound"], e["d_B"]),
                "null_mean":        float(np.mean(null_by_triple[i])),
                "null_std":         float(np.std(null_by_triple[i])),
                "norms":            e["norms"],
            }
            for i, e in enumerate(extracted)
        ],
    }
    (RESULTS_DIR / "compositional_summary.json").write_text(
        json.dumps(summary, indent=2))
    print("Summary JSON: compositional_summary.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    rng = np.random.default_rng(seed=0)
    model = load_model()

    print(f"\n=== Extracting directions for {len(TRIPLES)} triples ===")
    extracted = []
    for i, triple in enumerate(TRIPLES):
        e = extract_triple_directions(model, triple)
        if e is None:
            print(f"  [{i+1}/{len(TRIPLES)}] "
                  f"{triple['context']}/{triple['number']}  SKIPPED")
            continue
        extracted.append(e)
        print(f"  [{i+1}/{len(TRIPLES)}] "
              f"{triple['context']:>8s}/{triple['number']:<4d}  "
              f"||d_c||={e['norms']['compound']:.2f} "
              f"||d_A||={e['norms']['A']:.2f} "
              f"||d_B||={e['norms']['B']:.2f}")

    if len(extracted) < 3:
        print("Too few triples extracted; aborting.")
        return

    print(f"\n=== Computing compound-to-sum cosines ===")
    true_cosines = [
        cos_compound_to_sum(e["d_compound"], e["d_A"], e["d_B"])
        for e in extracted
    ]
    true_mean = float(np.mean(true_cosines))
    print(f"  mean true cosine = {true_mean:+.3f}")

    print(f"\n=== Random-pair permutation null ({N_RANDOM_PAIRS} draws) ===")
    null_by_triple = random_pair_nulls(extracted, rng, n_draws=N_RANDOM_PAIRS)
    null_means_per_triple = [float(np.mean(n)) for n in null_by_triple]
    null_mean = float(np.mean(null_means_per_triple))

    # Per-draw aggregate: at each draw d, take the mean across triples
    # of the d-th random cosine. Gives a distribution of mean-cosines
    # under the null, against which the true mean is tested.
    null_means_per_draw = []
    for d in range(N_RANDOM_PAIRS):
        vals = [null_by_triple[i][d] for i in range(len(extracted))]
        null_means_per_draw.append(float(np.mean(vals)))
    p_value = permutation_p_value(true_mean, null_means_per_draw)
    print(f"  mean null cosine = {null_mean:+.3f}")
    print(f"  permutation p    = {p_value:.4f}")

    outcome = score_outcome(true_mean, null_mean, p_value)
    print(f"\n=== AGGREGATE OUTCOME: {outcome} ===")

    print("\n=== Plots ===")
    plot_cosine_bars(true_cosines, null_means_per_triple,
                     [e["triple"] for e in extracted])
    plot_null_histogram(true_mean, null_means_per_draw)
    plot_component_contributions(extracted)

    write_report(extracted, true_cosines, null_by_triple,
                 true_mean, null_mean, p_value, outcome)

    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
