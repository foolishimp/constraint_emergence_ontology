"""
Experiment 17: Markov Boundary Tightness — The Definitional Test

The defining property of a Markov blanket is conditional independence:
given the boundary, internal states are independent of external states.
Translated to LLM terms:

  At a target token position, the features of the token's Markov object
  should be sufficient to determine the token's contribution to downstream
  predictions. If we SWAP the target's features for those of a reference
  token (same prompt template), the downstream prediction should converge
  to the reference's behaviour.

This experiment measures *how much* of the target's identity passes
through the SAE-identified boundary by overwriting progressively larger
subsets of the target's features with a reference target's values and
tracking convergence to the reference's logit distribution.

Design.
  Fixed template:  "The number {n} is most associated with"
  Reference:       n = 5  (structurally neutral)
  Targets:         n in {999 (cultural), 666 (cultural), 137 (boring)}

  For each target n:
    1) baseline logits at final position  →  L_target
    2) reference logits with the reference prompt  →  L_ref
    3) At target position, overwrite SAE features progressively:
         Tier-1  invariant core  (from exp 15 output)
         Tier-2  core + context-specific coat for this prompt
         Tier-3  top-20 firing features at target position
         Tier-4  top-50 firing features
    4) for each tier, compute:
         KL(intervened || ref)      — how far from reference?
         KL(intervened || target)   — how far from baseline?
         transfer ratio = 1 - KL(intervened || ref) / KL(target || ref)

A transfer ratio near 1.0 means the SAE boundary captured the identity
fully (intervention = swap target for reference). A ratio near 0 means
the SAE basis doesn't carry the identity-bearing degrees of freedom.

The curve of transfer-ratio vs intervention-tier tests whether the
Markov object is diffuse (gradually transfers as more features are
swapped) or localised to the core (transfers sharply with the core
alone).
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "17_boundary_tightness"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 8
ACTIVATION_THRESHOLD = 0.5

REFERENCE = 5
TARGETS = [999, 666, 137]

TEMPLATE = "The number {n} is most associated with"

# Invariant cores from exp 09 / 15
CORES = {
    999: [2269, 12604, 10744, 5567, 2747, 17244],
    666: [17244, 13585, 12604, 20061, 20951, 11917, 10439, 17855, 9551],
    137: [9497, 1608, 7702, 19680, 23723, 6863],
}


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


def encode_at(model, sae, text, pos, layer=PROBE_LAYER):
    """Return (resid_vec, feature_vec) at target pos."""
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    captured = {}

    def capture(value, hook):
        captured["resid"] = value[0, pos, :].detach().clone()
        return value

    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=[(hook_name, capture)])
    resid = captured["resid"]
    features = sae.encode(resid.unsqueeze(0))[0]
    return resid, features


def baseline_logits(model, text):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def intervene_and_logits(model, sae, text, pos, feature_overrides,
                         layer=PROBE_LAYER):
    """
    feature_overrides: dict {feature_id: new_value}.
    At `pos` in text, rewrite each feature to new_value via decoder delta.
    """
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"

    def hook_fn(value, hook):
        resid = value[0, pos, :].clone()
        features = sae.encode(resid.unsqueeze(0))[0]
        for fid, new_val in feature_overrides.items():
            delta = new_val - features[fid].item()
            resid = resid + delta * sae.W_dec[fid]
        value[0, pos, :] = resid
        return value

    with torch.no_grad():
        logits = model.run_with_hooks(tokens, fwd_hooks=[(hook_name, hook_fn)])
    return logits[0, -1, :]


def kl_div(logits_p, logits_q):
    import torch
    p = torch.softmax(logits_p, dim=-1)
    q = torch.softmax(logits_q, dim=-1)
    return float((p * (torch.log(p + 1e-12) - torch.log(q + 1e-12))).sum())


def top_k_tokens(model, logits, k=10):
    import torch
    probs = torch.softmax(logits, dim=-1)
    tp, ti = probs.topk(k)
    return [(model.to_single_str_token(int(i)), float(p)) for p, i in zip(tp, ti)]


# ---------------------------------------------------------------------------
# Compute tiers of features for a target
# ---------------------------------------------------------------------------

def build_tiers(features_target, target, k_top=50):
    """
    Return dict tier_name -> list of feature_ids to override.

    Tier-1: invariant core
    Tier-2: core + top-active features in THIS prompt (coat-analogue)
    Tier-3: top-20 features at target position (by activation)
    Tier-4: top-50 features at target position
    """
    feats_np = features_target.detach().cpu().numpy()
    active = np.where(feats_np > ACTIVATION_THRESHOLD)[0]
    sorted_active = active[np.argsort(-feats_np[active])]

    tiers = {}
    if target in CORES:
        tiers["core"] = list(CORES[target])
        coat_like = [int(f) for f in sorted_active[:20] if int(f) not in set(CORES[target])]
        tiers["core+coat(20)"] = list(CORES[target]) + coat_like
    tiers["top20"] = [int(f) for f in sorted_active[:20]]
    tiers["top50"] = [int(f) for f in sorted_active[:k_top]]
    tiers["top100"] = [int(f) for f in sorted_active[:min(100, len(sorted_active))]]
    return tiers, feats_np


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_for_target(model, sae, target):
    import torch
    text_target = TEMPLATE.format(n=target)
    text_ref    = TEMPLATE.format(n=REFERENCE)

    pos_t = last_token_of_span(model, text_target, str(target))
    pos_r = last_token_of_span(model, text_ref, str(REFERENCE))
    if pos_t is None or pos_r is None:
        return None

    # Features at reference position — these are the values we'll inject
    _, features_ref    = encode_at(model, sae, text_ref, pos_r)
    _, features_target = encode_at(model, sae, text_target, pos_t)

    logits_target = baseline_logits(model, text_target)
    logits_ref    = baseline_logits(model, text_ref)

    kl_target_vs_ref = kl_div(logits_target, logits_ref)
    print(f"\n=== target {target} ===")
    print(f"   KL(target || ref) baseline = {kl_target_vs_ref:.3f}")

    tiers, feats_np = build_tiers(features_target, target)

    results = {
        "target":          target,
        "pos_target":      pos_t,
        "pos_ref":         pos_r,
        "kl_baseline":     kl_target_vs_ref,
        "logits_target":   logits_target,
        "logits_ref":      logits_ref,
        "tier_results":    {},
    }

    for tier_name, fids in tiers.items():
        # Build overrides: set each feature to its value at the reference position
        overrides = {int(fid): float(features_ref[int(fid)].item()) for fid in fids}
        logits_i = intervene_and_logits(model, sae, text_target, pos_t, overrides)
        kl_vs_ref    = kl_div(logits_i, logits_ref)
        kl_vs_target = kl_div(logits_i, logits_target)
        transfer = 1.0 - (kl_vs_ref / max(kl_target_vs_ref, 1e-9))
        results["tier_results"][tier_name] = {
            "n_features":  len(overrides),
            "kl_vs_ref":    kl_vs_ref,
            "kl_vs_target": kl_vs_target,
            "transfer":     transfer,
            "top_tokens":   top_k_tokens(model, logits_i),
        }
        print(f"   tier={tier_name:<15s}  n={len(overrides):>4}   "
              f"KL→ref={kl_vs_ref:.4f}   KL→tgt={kl_vs_target:.4f}   "
              f"transfer={transfer:.3f}")

    results["top_tokens_target"] = top_k_tokens(model, logits_target)
    results["top_tokens_ref"]    = top_k_tokens(model, logits_ref)
    return results


# ---------------------------------------------------------------------------
# Additional analysis: bypass test — overwrite features OUTSIDE the object
# ---------------------------------------------------------------------------

def bypass_test(model, sae, target):
    """
    If SAE features form a tight Markov boundary, overwriting features
    OUTSIDE the boundary should not transfer identity.
    We pick the ~top-50 non-object features (low-activation features) at
    the target, and overwrite them with reference values. Transfer ratio
    should be near 0 if boundary is tight.
    """
    text_target = TEMPLATE.format(n=target)
    text_ref    = TEMPLATE.format(n=REFERENCE)
    pos_t = last_token_of_span(model, text_target, str(target))
    pos_r = last_token_of_span(model, text_ref, str(REFERENCE))
    if pos_t is None or pos_r is None:
        return None

    _, features_ref = encode_at(model, sae, text_ref, pos_r)
    _, features_tgt = encode_at(model, sae, text_target, pos_t)

    feats_np = features_tgt.detach().cpu().numpy()
    # Active features in target (would be the object boundary)
    active = set(np.where(feats_np > ACTIVATION_THRESHOLD)[0].tolist())
    n_active = len(active)

    # Non-object: features that are ACTIVE at the reference but NOT at target.
    # Overwriting these mimics "handing target the features it lacks but
    # reference has" from outside the target's own object.
    ref_np = features_ref.detach().cpu().numpy()
    ref_active = set(np.where(ref_np > ACTIVATION_THRESHOLD)[0].tolist())
    outside = list(ref_active - active)[:n_active]  # match cardinality

    logits_target = baseline_logits(model, text_target)
    logits_ref    = baseline_logits(model, text_ref)
    kl_baseline = kl_div(logits_target, logits_ref)

    overrides = {int(fid): float(features_ref[int(fid)].item()) for fid in outside}
    logits_i = intervene_and_logits(model, sae, text_target, pos_t, overrides)
    kl_vs_ref    = kl_div(logits_i, logits_ref)
    transfer = 1.0 - (kl_vs_ref / max(kl_baseline, 1e-9))
    return {
        "n_outside_features": len(outside),
        "kl_baseline":        kl_baseline,
        "kl_vs_ref_after":    kl_vs_ref,
        "transfer":           transfer,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_transfer_curves(all_results):
    """For each target, line plot of transfer-ratio vs tier."""
    fig, ax = plt.subplots(figsize=(11, 6))
    tier_order = ["core", "core+coat(20)", "top20", "top50", "top100"]
    colors = {999: "tomato", 666: "purple", 137: "steelblue"}

    for target, r in all_results.items():
        xs, ys, ns = [], [], []
        for tn in tier_order:
            if tn in r["tier_results"]:
                xs.append(tn)
                ys.append(r["tier_results"][tn]["transfer"])
                ns.append(r["tier_results"][tn]["n_features"])
        ax.plot(xs, ys, "o-", label=f"n={target}", color=colors.get(target, "gray"),
                linewidth=2, markersize=8)
        for xi, yi, ni in zip(xs, ys, ns):
            ax.text(xi, yi + 0.02, f"{ni}", ha="center", fontsize=7)

    ax.axhline(0.0, color="gray", linewidth=0.5)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.4,
               label="full transfer (= become reference)")
    ax.set_ylabel("transfer ratio = 1 - KL(intervened||ref) / KL(target||ref)")
    ax.set_xlabel("intervention tier")
    ax.set_title("Markov boundary tightness: how much identity transfers "
                 "when SAE features are overwritten with reference values")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = RESULTS_DIR / "transfer_curves.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_kl_bars(all_results):
    tier_order = ["core", "core+coat(20)", "top20", "top50", "top100"]
    n_t = len(all_results)
    fig, axes = plt.subplots(1, n_t, figsize=(5.5 * n_t, 4.5), squeeze=False)
    for i, (target, r) in enumerate(all_results.items()):
        ax = axes[0][i]
        xs = [tn for tn in tier_order if tn in r["tier_results"]]
        kl_ref = [r["tier_results"][tn]["kl_vs_ref"] for tn in xs]
        kl_tgt = [r["tier_results"][tn]["kl_vs_target"] for tn in xs]
        x = np.arange(len(xs))
        w = 0.4
        ax.bar(x - w/2, kl_ref, w, color="steelblue", label="KL(intervened || ref)", alpha=0.85)
        ax.bar(x + w/2, kl_tgt, w, color="tomato",    label="KL(intervened || target)", alpha=0.85)
        ax.axhline(r["kl_baseline"], color="gray", linestyle="--",
                   label=f"baseline KL(target||ref) = {r['kl_baseline']:.3f}")
        ax.set_xticks(x)
        ax.set_xticklabels(xs, rotation=15, fontsize=8)
        ax.set_ylabel("KL")
        ax.set_title(f"target = {target}")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "kl_bars.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(all_results, bypass_results):
    out = RESULTS_DIR / "boundary_report.txt"
    lines = [f"Markov Boundary Tightness Report — layer {PROBE_LAYER}",
             "=" * 70, ""]
    lines.append("Template: " + TEMPLATE)
    lines.append(f"Reference: n = {REFERENCE}")
    lines.append("")
    for target, r in all_results.items():
        lines.append(f"\n### target = {target}")
        lines.append(f"  baseline KL(target || ref) = {r['kl_baseline']:.4f}")
        lines.append("\n  BASELINE top tokens — target:")
        for tok, p in r["top_tokens_target"][:8]:
            lines.append(f"    {repr(tok):>15}  {p:.4f}")
        lines.append("\n  BASELINE top tokens — ref:")
        for tok, p in r["top_tokens_ref"][:8]:
            lines.append(f"    {repr(tok):>15}  {p:.4f}")
        lines.append("\n  TIER RESULTS:")
        lines.append(f"  {'tier':<18s} {'n':>4s} {'KL→ref':>10s} {'KL→tgt':>10s} {'transfer':>10s}")
        for tn, tr in r["tier_results"].items():
            lines.append(f"  {tn:<18s} {tr['n_features']:>4d} "
                         f"{tr['kl_vs_ref']:>10.4f} {tr['kl_vs_target']:>10.4f} "
                         f"{tr['transfer']:>10.3f}")
            lines.append(f"     top tokens after: " +
                         "  ".join(f"{repr(t)}={p:.3f}" for t, p in tr["top_tokens"][:5]))
        if target in bypass_results:
            b = bypass_results[target]
            lines.append(f"\n  BYPASS (overwrite {b['n_outside_features']} features "
                         f"OUTSIDE target's active set with ref values):")
            lines.append(f"     KL→ref after  = {b['kl_vs_ref_after']:.4f}")
            lines.append(f"     transfer      = {b['transfer']:.3f}")
            lines.append(f"     (compare to tiers above — should be close to 0 if "
                         f"boundary is tight)")
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()

    all_results = {}
    for t in TARGETS:
        r = run_for_target(model, sae, t)
        if r is not None:
            all_results[t] = r

    print("\n--- Bypass test (overwrite non-object features) ---")
    bypass_results = {}
    for t in TARGETS:
        b = bypass_test(model, sae, t)
        if b is not None:
            bypass_results[t] = b
            print(f"  n={t}  bypass transfer = {b['transfer']:.3f}  "
                  f"(using {b['n_outside_features']} outside features)")

    print("\nGenerating plots...")
    plot_transfer_curves(all_results)
    plot_kl_bars(all_results)
    write_report(all_results, bypass_results)

    print("\n--- Summary ---")
    print(f"{'target':>6}  {'tier':<16s} {'n':>4s} {'transfer':>10s}")
    for target, r in all_results.items():
        for tn, tr in r["tier_results"].items():
            print(f"{target:>6}  {tn:<16s} {tr['n_features']:>4d} "
                  f"{tr['transfer']:>10.3f}")
    print(f"\nBypass (non-object) transfers:")
    for t, b in bypass_results.items():
        print(f"  n={t}  {b['transfer']:.3f}")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
