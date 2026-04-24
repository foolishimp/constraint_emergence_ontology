"""
Experiment 21: Multi-layer Identity Direction

Exp 10 established layered assembly of SAE features for cultural
tokens: features present from layer 2, strengthening to layer 8. The
identity direction reading (exp 18) was anchored at layer 8. Whether
the direction is a layer-8 artifact or a representation-spanning
invariant is an open question in §13.4.

Protocol:
  1. For each L ∈ LAYERS, collect paired (target, reference) residuals
     on train templates; extract d_L = μ(R_tgt_L) − μ(R_ref_L).
  2. Compute the pairwise cosine matrix C[L, L'] over all layer pairs.
  3. Same-layer transfer: α-sweep with d_L applied at layer L on held-out
     prompts; record transfer at α = 1.
  4. Cross-layer transfer: apply d_L at layer L' ≠ L and record
     transfer — tests whether the direction survives residual-stream
     rotation.

Pre-registered expectation:
  - cos(d_L, d_{L+2}) ≥ 0.6 for ≥ 2 adjacent pairs with L ≥ 4.
  - Same-layer transfer ≥ 0.15 at L ∈ {6, 10}.
  - Cross-layer transfer degrades monotonically with |L − L'|.

Outcome interpretation:
  PASS     identity direction is layer-continuous; cross-layer mean
           direction is a lawful abstraction.
  PARTIAL  critical-layer emergence: direction noisy below some L_c,
           stable above.
  FAIL     direction rotates layer-by-layer; cuts must pin layer.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "21_multi_layer_direction"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LAYERS = [2, 4, 6, 8, 10, 11]
REFERENCE = 5
TARGETS = [999, 666, 137]

TEMPLATE_POOL = [
    "The number {n} is",
    "The number {n} is most associated with",
    "Call {n} immediately",
    "In {n} AD the Vikings",
    "Price was ${n} only",
    "There were {n} people",
    "Page {n} of the book",
    "Line {n}: error",
    "She whispered {n}",
    "Yesterday we saw {n}",
    "We had {n} choices",
    "The sacred number {n} means",
    "Pick number {n}",
    "Room {n} is empty",
    "{n} is the answer",
    "My code is {n}",
    "Try {n} next time",
    "They sang song {n}",
    "Box {n} contains",
    "Apartment {n} on the third floor",
    "Channel {n} is broadcasting",
    "Version {n} released today",
    "The tribe numbered {n}",
    "He lived {n} years",
    "Mission {n} begins now",
    "Only {n} remain standing",
    "Flight {n} is boarding",
    "Gate {n} closes soon",
    "Problem {n} is solved",
    "The clock struck {n}",
]

TRAIN_TEMPLATES   = TEMPLATE_POOL[:-10]
HELDOUT_TEMPLATES = TEMPLATE_POOL[-10:]

ALPHAS = [0.0, 0.5, 1.0, 1.5, 2.0]

# Pre-reg thresholds
COS_PASS       = 0.60
TRANSFER_FLOOR = 0.15


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


def capture_resid(model, text, pos, layer):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    captured = {}

    def capture(value, hook):
        captured["resid"] = value[0, pos, :].detach().clone()
        return value

    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=[(hook_name, capture)])
    return captured["resid"]


def collect_residuals_at_layer(model, n, templates, layer):
    import torch
    resids = []
    used = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        r = capture_resid(model, text, pos, layer)
        resids.append(r)
        used.append(t)
    return torch.stack(resids), used


def baseline_logits(model, text):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def logits_with_direction_at_layer(model, text, pos, direction, alpha, layer):
    """Subtract α*direction from residual at (pos, layer.hook_resid_pre)."""
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"

    def patch(value, hook):
        resid = value[0, pos, :].clone()
        resid = resid - alpha * direction
        value[0, pos, :] = resid
        return value

    with torch.no_grad():
        logits = model.run_with_hooks(tokens, fwd_hooks=[(hook_name, patch)])
    return logits[0, -1, :]


def kl_div(p_logits, q_logits):
    import torch
    p = torch.softmax(p_logits, dim=-1)
    q = torch.softmax(q_logits, dim=-1)
    return float((p * (torch.log(p + 1e-12) - torch.log(q + 1e-12))).sum())


# ---------------------------------------------------------------------------
# Direction extraction per layer
# ---------------------------------------------------------------------------

def direction_mean_diff(R_tgt, R_ref):
    return R_tgt.mean(0) - R_ref.mean(0)


def extract_directions_all_layers(model, target, layers):
    """Return dict L -> (d_L, ref_norm_L, n_paired)."""
    import torch
    result = {}
    for L in layers:
        print(f"    layer {L}: collecting residuals...")
        R_tgt, used_tgt = collect_residuals_at_layer(
            model, target, TRAIN_TEMPLATES, L,
        )
        R_ref, used_ref = collect_residuals_at_layer(
            model, REFERENCE, TRAIN_TEMPLATES, L,
        )
        shared = [t for t in used_tgt if t in used_ref]
        tgt_idx = [used_tgt.index(t) for t in shared]
        ref_idx = [used_ref.index(t) for t in shared]
        R_tgt = R_tgt[tgt_idx].float()
        R_ref = R_ref[ref_idx].float()
        d = direction_mean_diff(R_tgt, R_ref)
        result[L] = {
            "direction": d,
            "norm":      float(d.norm()),
            "n_paired":  len(shared),
        }
    return result


# ---------------------------------------------------------------------------
# Cosine matrix
# ---------------------------------------------------------------------------

def cosine_matrix(directions_by_layer):
    import torch
    layers = sorted(directions_by_layer.keys())
    n = len(layers)
    C = np.zeros((n, n))
    for i, Li in enumerate(layers):
        di = directions_by_layer[Li]["direction"]
        di_n = di / (di.norm() + 1e-9)
        for j, Lj in enumerate(layers):
            dj = directions_by_layer[Lj]["direction"]
            dj_n = dj / (dj.norm() + 1e-9)
            C[i, j] = float((di_n @ dj_n).item())
    return layers, C


# ---------------------------------------------------------------------------
# Transfer at layer (same-layer and cross-layer)
# ---------------------------------------------------------------------------

def alpha_sweep_at_layer(model, target, template, direction, intervene_layer,
                         alphas=ALPHAS):
    text_target = template.format(n=target)
    text_ref    = template.format(n=REFERENCE)
    pos_t = last_token_of_span(model, text_target, str(target))
    if pos_t is None:
        return None

    logits_tgt = baseline_logits(model, text_target)
    logits_ref = baseline_logits(model, text_ref)
    kl_baseline = kl_div(logits_tgt, logits_ref)

    result = {"template": template, "kl_baseline": kl_baseline, "alphas": {}}
    for a in alphas:
        li = logits_with_direction_at_layer(
            model, text_target, pos_t, direction, a, intervene_layer,
        )
        kl_ref = kl_div(li, logits_ref)
        transfer = 1.0 - (kl_ref / max(kl_baseline, 1e-9))
        result["alphas"][a] = {"kl_ref": kl_ref, "transfer": transfer}
    return result


def aggregate_at_layer(model, target, direction, intervene_layer, templates):
    per_alpha = {a: [] for a in ALPHAS}
    kl_baseline_all = []
    for t in templates:
        res = alpha_sweep_at_layer(model, target, t, direction, intervene_layer)
        if res is None:
            continue
        kl_baseline_all.append(res["kl_baseline"])
        for a in ALPHAS:
            per_alpha[a].append(res["alphas"][a]["transfer"])
    return {
        "kl_baseline": float(np.mean(kl_baseline_all)) if kl_baseline_all else 0.0,
        "mean":        {a: float(np.mean(per_alpha[a])) if per_alpha[a] else 0.0 for a in ALPHAS},
        "n":           len(per_alpha[ALPHAS[0]]),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def adjacent_cosines(layers, C):
    pairs = []
    for i, L in enumerate(layers[:-1]):
        if layers[i+1] - L <= 2:
            pairs.append((L, layers[i+1], float(C[i, i+1])))
    return pairs


def monotonic_degradation(cross_transfer, center_layer):
    """
    cross_transfer[L'] = transfer when d_{center_layer} applied at L'.
    Returns True if |L' - center_layer| increasing implies transfer
    non-increasing (up to noise).
    """
    sorted_lprimes = sorted(cross_transfer.keys(),
                            key=lambda lp: abs(lp - center_layer))
    prev = None
    for lp in sorted_lprimes:
        t = cross_transfer[lp]
        if prev is not None and t > prev + 0.05:
            return False
        prev = t
    return True


def score_outcome(all_cosines_per_target, same_layer_transfer_per_target,
                  cross_layer_per_target):
    passes_cos = []
    passes_transfer = []
    passes_monotonic = []
    for target in TARGETS:
        layers, C = all_cosines_per_target[target]
        adj = adjacent_cosines(layers, C)
        adj_pass = [p for p in adj if p[0] >= 4 and p[2] >= COS_PASS]
        passes_cos.append(len(adj_pass) >= 2)

        same = same_layer_transfer_per_target[target]
        passes_transfer.append(
            same.get(6, {}).get("alpha_1", 0.0) >= TRANSFER_FLOOR and
            same.get(10, {}).get("alpha_1", 0.0) >= TRANSFER_FLOOR
        )

        for L_center, cross in cross_layer_per_target[target].items():
            passes_monotonic.append(monotonic_degradation(cross, L_center))

    all_cos_pass = all(passes_cos)
    all_transfer_pass = all(passes_transfer)
    most_monotonic = sum(passes_monotonic) >= int(0.7 * len(passes_monotonic))

    if all_cos_pass and all_transfer_pass and most_monotonic:
        return "PASS"
    if all_cos_pass or (all_transfer_pass and most_monotonic):
        return "PARTIAL"
    return "FAIL"


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_cosine_heatmap(target, layers, C):
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(C, vmin=-0.2, vmax=1.0, cmap="RdBu_r")
    ax.set_xticks(range(len(layers)))
    ax.set_yticks(range(len(layers)))
    ax.set_xticklabels([str(L) for L in layers])
    ax.set_yticklabels([str(L) for L in layers])
    for i in range(len(layers)):
        for j in range(len(layers)):
            ax.text(j, i, f"{C[i,j]:.2f}", ha="center", va="center",
                    fontsize=8,
                    color="white" if abs(C[i,j]) > 0.6 else "black")
    ax.set_xlabel("layer L'")
    ax.set_ylabel("layer L")
    ax.set_title(f"cos(d_L, d_L') — target {target}")
    fig.colorbar(im, ax=ax, label="cosine")
    fig.tight_layout()
    out = RESULTS_DIR / f"cosine_{target}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_same_layer_transfer(same_layer_transfer_per_target):
    fig, ax = plt.subplots(figsize=(9, 5))
    for target, by_layer in same_layer_transfer_per_target.items():
        xs = sorted(by_layer.keys())
        ys = [by_layer[L]["alpha_1"] for L in xs]
        ax.plot(xs, ys, marker="o", linewidth=2, label=f"n={target}")
    ax.axhline(TRANSFER_FLOOR, color="orange", linestyle="--", alpha=0.5,
               label=f"floor ({TRANSFER_FLOOR})")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xlabel("layer L (d_L applied at L)")
    ax.set_ylabel("transfer at α = 1")
    ax.set_title("Same-layer transfer across layers")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "same_layer_transfer.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_cross_layer_heatmap(target, cross_layer):
    """
    cross_layer[L_center][L_apply] = transfer at α=1.
    """
    L_centers = sorted(cross_layer.keys())
    L_applies = sorted({lp for v in cross_layer.values() for lp in v.keys()})
    M = np.zeros((len(L_centers), len(L_applies)))
    for i, Lc in enumerate(L_centers):
        for j, La in enumerate(L_applies):
            M[i, j] = cross_layer[Lc].get(La, 0.0)
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(M, cmap="viridis", vmin=-0.1, vmax=0.4)
    ax.set_xticks(range(len(L_applies)))
    ax.set_yticks(range(len(L_centers)))
    ax.set_xticklabels([str(L) for L in L_applies])
    ax.set_yticklabels([str(L) for L in L_centers])
    for i in range(len(L_centers)):
        for j in range(len(L_applies)):
            ax.text(j, i, f"{M[i,j]:+.2f}", ha="center", va="center",
                    fontsize=8,
                    color="white" if M[i,j] < 0.2 else "black")
    ax.set_xlabel("apply at layer L'")
    ax.set_ylabel("direction from layer L")
    ax.set_title(f"Cross-layer transfer at α=1 — target {target}")
    fig.colorbar(im, ax=ax, label="transfer")
    fig.tight_layout()
    out = RESULTS_DIR / f"cross_layer_{target}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(all_directions, cosines_per_target,
                 same_layer_transfer_per_target, cross_layer_per_target,
                 aggregate):
    lines = [
        "Exp 21 — Multi-layer Identity Direction",
        "=" * 72,
        "",
        f"Reference: n = {REFERENCE}",
        f"Targets:   {TARGETS}",
        f"Layers:    {LAYERS}",
        f"Train templates: {len(TRAIN_TEMPLATES)}",
        f"Held-out templates: {len(HELDOUT_TEMPLATES)}",
        "",
        "Pre-registered rules:",
        f"  cos(d_L, d_{{L+2}}) ≥ {COS_PASS} for ≥ 2 adjacent pairs (L ≥ 4)",
        f"  Same-layer transfer ≥ {TRANSFER_FLOOR} at L ∈ {{6, 10}}",
        f"  Cross-layer transfer monotonically degrades with |L − L'|",
        "",
        f"AGGREGATE OUTCOME: {aggregate}",
        "",
    ]
    for target in TARGETS:
        lines.append(f"\n### target = {target}")
        layers, C = cosines_per_target[target]

        lines.append("")
        lines.append("  Direction norms per layer:")
        for L in layers:
            d_info = all_directions[target][L]
            lines.append(f"    L = {L:2d}  "
                         f"||d|| = {d_info['norm']:.3f}  "
                         f"n_paired = {d_info['n_paired']}")

        lines.append("")
        lines.append("  Cosine matrix:")
        header = "    L\\L' | " + " | ".join(f"{L:>6d}" for L in layers)
        lines.append(header)
        for i, L in enumerate(layers):
            row = [f"    {L:>4d}"]
            for j in range(len(layers)):
                row.append(f"{C[i,j]:>+6.3f}")
            lines.append(" | ".join(row))

        adj = adjacent_cosines(layers, C)
        lines.append("")
        lines.append(f"  Adjacent cosines (|ΔL| ≤ 2):")
        for a, b, c in adj:
            lines.append(f"    cos(d_{a}, d_{b}) = {c:+.3f}  "
                         f"({'pass' if c >= COS_PASS else 'below'})")

        lines.append("")
        lines.append("  Same-layer transfer (α = 1):")
        for L in layers:
            t1 = same_layer_transfer_per_target[target].get(L, {}).get("alpha_1", 0.0)
            lines.append(f"    L = {L:2d}  transfer(α=1) = {t1:+.3f}")

        lines.append("")
        lines.append("  Cross-layer transfer (d_L applied at L', α = 1):")
        for Lc in cross_layer_per_target[target]:
            row = [f"    d_{Lc:>2d} →"]
            for La in layers:
                v = cross_layer_per_target[target][Lc].get(La, 0.0)
                row.append(f"L'={La}:{v:+.3f}")
            lines.append("  ".join(row))

    out = RESULTS_DIR / "multi_layer_report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")

    json_summary = {
        "aggregate": aggregate,
        "targets": {
            str(t): {
                "layers":   list(cosines_per_target[t][0]),
                "cosines":  cosines_per_target[t][1].tolist(),
                "same_layer_transfer": {
                    int(L): float(same_layer_transfer_per_target[t][L]["alpha_1"])
                    for L in same_layer_transfer_per_target[t]
                },
                "cross_layer": {
                    int(Lc): {int(La): float(v)
                              for La, v in cross.items()}
                    for Lc, cross in cross_layer_per_target[t].items()
                },
                "direction_norms": {
                    int(L): float(all_directions[t][L]["norm"])
                    for L in all_directions[t]
                },
            } for t in TARGETS
        },
    }
    (RESULTS_DIR / "multi_layer_summary.json").write_text(
        json.dumps(json_summary, indent=2))
    print("Summary JSON: multi_layer_summary.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import torch

    model = load_model()

    all_directions = {}
    cosines_per_target = {}
    same_layer_transfer_per_target = {}
    cross_layer_per_target = {}

    for target in TARGETS:
        print(f"\n=== target = {target} ===")

        directions_by_layer = extract_directions_all_layers(
            model, target, LAYERS,
        )
        all_directions[target] = directions_by_layer

        layers, C = cosine_matrix(directions_by_layer)
        cosines_per_target[target] = (layers, C)
        print(f"  cosine matrix computed ({len(layers)}×{len(layers)})")

        # Same-layer transfer
        same_transfer = {}
        for L in layers:
            print(f"  same-layer transfer at L={L}...")
            d_L = directions_by_layer[L]["direction"]
            # Normalise to exp-18 convention: use raw mean-diff vector (no renorm)
            agg = aggregate_at_layer(
                model, target, d_L, L, HELDOUT_TEMPLATES,
            )
            same_transfer[L] = {
                "alpha_1":  agg["mean"][1.0],
                "alpha_2":  agg["mean"][2.0],
                "full":     agg["mean"],
                "n":        agg["n"],
            }
            print(f"    L={L:2d}  transfer α=1 = {agg['mean'][1.0]:+.3f}")
        same_layer_transfer_per_target[target] = same_transfer

        # Cross-layer transfer: d_L applied at L' ≠ L
        cross = {}
        for L_center in layers:
            d_center = directions_by_layer[L_center]["direction"]
            per_apply = {}
            for L_apply in layers:
                agg = aggregate_at_layer(
                    model, target, d_center, L_apply, HELDOUT_TEMPLATES,
                )
                per_apply[L_apply] = agg["mean"][1.0]
            cross[L_center] = per_apply
            row = "  ".join(f"L'={la}:{per_apply[la]:+.3f}"
                            for la in layers)
            print(f"  d_{L_center:>2d} → {row}")
        cross_layer_per_target[target] = cross

        plot_cosine_heatmap(target, layers, C)
        plot_cross_layer_heatmap(target, cross)

    plot_same_layer_transfer(same_layer_transfer_per_target)

    aggregate = score_outcome(
        cosines_per_target,
        same_layer_transfer_per_target,
        cross_layer_per_target,
    )
    print(f"\n=== AGGREGATE OUTCOME: {aggregate} ===")

    write_report(
        all_directions, cosines_per_target,
        same_layer_transfer_per_target, cross_layer_per_target,
        aggregate,
    )

    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
