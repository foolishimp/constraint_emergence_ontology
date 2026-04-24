"""
Experiment 18: Direction-Native Markov Object — Bypassing the SAE Dictionary

Exp 17 showed that overwriting SAE features leaks: ~25% identity transfer
from features OUTSIDE the object's active set. The interpretation was that
the SAE basis is not aligned with the Markov object's natural frame, so
boundary-via-feature-activation is a mapping problem, not evidence against
a Markov object.

This experiment looks for the object in residual space directly, bypassing
the SAE entirely. Three candidate object directions:

  D1  mean-difference     d = μ(resid_target) - μ(resid_ref)
                          across K diverse prompts. If identity is linearly
                          represented, α·d transfers it.

  D2  first PC of differences   PC1 of (resid_target - resid_ref) for
                                paired prompts. Captures dominant variation
                                along the identity axis.

  D3  linear probe normal   Logistic-regression normal vector separating
                            target residuals from reference residuals.

For each direction, do an α-scan intervention on held-out prompts and
compare transfer curves to exp 17's SAE tiers (overlaid on the same axes).

Hypothesis: if a Markov object exists, there should be a low-dimensional
residual-space direction along which α→1 yields ≥ 0.8 transfer with much
smaller perturbation magnitude than SAE top-100 requires. If no direction
works, the object is either non-linearly encoded, or genuinely diffuse
beyond any low-rank decomposition.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "18_direction_native"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 8

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

# Prompts held out for evaluation (subset)
HELDOUT_TEMPLATES = TEMPLATE_POOL[-10:]
TRAIN_TEMPLATES   = TEMPLATE_POOL[:-10]

ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


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


def capture_resid(model, text, pos, layer=PROBE_LAYER):
    """Capture residual vector at (pos, layer.hook_resid_pre)."""
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


def collect_residuals(model, n, templates):
    """For each template, insert n, find span, capture resid at layer 8."""
    import torch
    resids = []
    used_templates = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        r = capture_resid(model, text, pos)
        resids.append(r)
        used_templates.append(t)
    return torch.stack(resids), used_templates


def baseline_logits(model, text):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def logits_with_direction(model, text, pos, direction, alpha,
                          layer=PROBE_LAYER):
    """Subtract alpha*direction from residual at target pos. Direction is (d,)."""
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
# Direction construction
# ---------------------------------------------------------------------------

def direction_mean_diff(R_target, R_ref):
    import torch
    d = R_target.mean(0) - R_ref.mean(0)
    return d


def direction_pca1(R_target, R_ref):
    """First principal component of paired target-ref differences."""
    import torch
    K = min(len(R_target), len(R_ref))
    deltas = R_target[:K] - R_ref[:K]              # (K, d_model)
    deltas_centered = deltas - deltas.mean(0, keepdim=True)
    U, S, V = torch.linalg.svd(deltas_centered, full_matrices=False)
    return V[0]                                    # (d_model,)


def direction_linear_probe(R_target, R_ref, n_iters=2000, lr=0.05,
                           weight_decay=1e-3):
    """Logistic regression direction separating target from reference."""
    import torch
    import torch.nn as nn

    X = torch.cat([R_target, R_ref], dim=0)
    y = torch.cat([torch.ones(len(R_target)), torch.zeros(len(R_ref))])
    X = X.float()
    d = X.shape[1]

    w = torch.zeros(d, requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w, b], lr=lr, weight_decay=weight_decay)
    bce = nn.BCEWithLogitsLoss()

    for _ in range(n_iters):
        opt.zero_grad()
        logit = X @ w + b
        loss = bce(logit, y)
        loss.backward()
        opt.step()

    return w.detach()


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

def alpha_sweep(model, target, template, direction, alphas=ALPHAS):
    """
    For this template: compute baseline target/ref logits, then intervene
    along `direction` at target position with each alpha.
    Returns dict alpha -> metrics.
    """
    text_target = template.format(n=target)
    text_ref    = template.format(n=REFERENCE)
    pos_t = last_token_of_span(model, text_target, str(target))
    pos_r = last_token_of_span(model, text_ref, str(REFERENCE))
    if pos_t is None or pos_r is None:
        return None

    logits_tgt = baseline_logits(model, text_target)
    logits_ref = baseline_logits(model, text_ref)
    kl_baseline = kl_div(logits_tgt, logits_ref)

    out = {
        "template": template,
        "kl_baseline": kl_baseline,
        "alphas": {},
    }
    for a in alphas:
        li = logits_with_direction(model, text_target, pos_t, direction, a)
        kl_ref = kl_div(li, logits_ref)
        kl_tgt = kl_div(li, logits_tgt)
        transfer = 1.0 - (kl_ref / max(kl_baseline, 1e-9))
        out["alphas"][a] = {"kl_ref": kl_ref, "kl_tgt": kl_tgt,
                            "transfer": transfer}
    return out


def aggregate_sweep(model, target, direction, templates, label):
    """Run alpha-sweep over all templates, aggregate transfer per alpha."""
    per_alpha = {a: [] for a in ALPHAS}
    kl_baseline_all = []
    for t in templates:
        res = alpha_sweep(model, target, t, direction)
        if res is None:
            continue
        kl_baseline_all.append(res["kl_baseline"])
        for a in ALPHAS:
            per_alpha[a].append(res["alphas"][a]["transfer"])
    summary = {
        "label":       label,
        "kl_baseline": float(np.mean(kl_baseline_all)),
        "mean":        {a: float(np.mean(per_alpha[a])) for a in ALPHAS},
        "std":         {a: float(np.std(per_alpha[a]))  for a in ALPHAS},
        "n_templates": len(per_alpha[ALPHAS[0]]),
    }
    return summary


# ---------------------------------------------------------------------------
# Compare to SAE: cosine of direction vs SAE core features
# ---------------------------------------------------------------------------

SAE_CORES = {
    999: [2269, 12604, 10744, 5567, 2747, 17244],
    666: [17244, 13585, 12604, 20061, 20951, 11917, 10439, 17855, 9551],
    137: [9497, 1608, 7702, 19680, 23723, 6863],
}


def cosine_with_sae_core(direction, sae, target):
    import torch
    fids = SAE_CORES.get(target, [])
    if not fids:
        return None
    d = direction / (direction.norm() + 1e-9)
    core_vecs = torch.stack([sae.W_dec[f] for f in fids])            # (K, d_model)
    core_sum = core_vecs.sum(0)
    core_sum_n = core_sum / (core_sum.norm() + 1e-9)
    cos_sum = float((d @ core_sum_n).item())

    # Also per-feature cosines
    per_feat = []
    for f, v in zip(fids, core_vecs):
        vn = v / (v.norm() + 1e-9)
        per_feat.append((int(f), float((d @ vn).item())))
    return {"cos_with_sum_of_core": cos_sum, "per_feature": per_feat}


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_transfer_curves(results, target):
    fig, ax = plt.subplots(figsize=(10, 6))
    for label, summary in results.items():
        xs = ALPHAS
        ys = [summary["mean"][a] for a in xs]
        errs = [summary["std"][a] for a in xs]
        ax.errorbar(xs, ys, yerr=errs, marker="o", linewidth=2, capsize=3,
                    label=f"{label} (n_prompts={summary['n_templates']})")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.4,
               label="full transfer")
    ax.set_xlabel("α (intervention magnitude along direction)")
    ax.set_ylabel("transfer = 1 − KL(intervened‖ref) / KL(target‖ref)")
    ax.set_title(f"Direction-native transfer — n = {target}\n"
                 f"(higher = intervention pushed target toward reference)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / f"transfer_{target}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_sae_vs_direction_compare(per_target_summary, sae_tiers):
    """
    For each target: show best alpha=1.0 direction-native transfer next to
    SAE tier transfers (core, top20, top50, top100) from exp 17.
    """
    fig, ax = plt.subplots(figsize=(11, 6))
    targets = list(per_target_summary.keys())
    x = np.arange(len(targets))
    width = 0.15

    # Direction bars at α=1
    for i, (dir_label, color) in enumerate([
        ("mean-diff", "tomato"),
        ("pca1",      "purple"),
        ("probe",     "steelblue"),
    ]):
        vals = []
        for t in targets:
            s = per_target_summary[t].get(dir_label)
            vals.append(s["mean"][1.0] if s is not None else 0.0)
        ax.bar(x + (i - 2.5) * width, vals, width, color=color, alpha=0.85,
               label=f"{dir_label} α=1")

    # SAE tier bars
    for i, (tier, color) in enumerate([
        ("sae_core",    "gold"),
        ("sae_top100",  "darkgreen"),
    ]):
        vals = [sae_tiers.get(t, {}).get(tier, 0.0) for t in targets]
        ax.bar(x + (i + 0.5) * width, vals, width, color=color, alpha=0.85,
               label=tier)

    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in targets])
    ax.set_ylabel("transfer ratio")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.4)
    ax.set_title("Direction-native vs SAE-basis transfer — α=1 per direction, "
                 "matched tiers per SAE")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "direction_vs_sae.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(all_results, cosine_results):
    out = RESULTS_DIR / "direction_report.txt"
    lines = [f"Direction-Native Markov Object Report — layer {PROBE_LAYER}",
             "=" * 70, ""]
    lines.append(f"Reference: n = {REFERENCE}")
    lines.append(f"Train templates: {len(TRAIN_TEMPLATES)}   "
                 f"Held-out templates: {len(HELDOUT_TEMPLATES)}")
    lines.append("")
    for target, by_dir in all_results.items():
        lines.append(f"\n### target = {target}")
        lines.append(f"    mean KL(target||ref) over heldout = "
                     f"{by_dir['mean-diff']['kl_baseline']:.4f}")
        lines.append(f"\n    Transfer at each α (mean over held-out prompts):")
        lines.append(f"    {'α':>6s} | " +
                     " | ".join(f"{k:>12s}" for k in by_dir.keys()))
        for a in ALPHAS:
            row = [f"{a:>6.2f}"]
            for dir_label in by_dir:
                s = by_dir[dir_label]
                row.append(f"{s['mean'][a]:>12.3f}")
            lines.append("    " + " | ".join(row))
        # Cosine to SAE core
        cos = cosine_results.get(target, {})
        for dir_label, cinfo in cos.items():
            if cinfo is None:
                continue
            lines.append(f"\n    Cosine({dir_label}, Σ SAE_core W_dec)  = "
                         f"{cinfo['cos_with_sum_of_core']:.3f}")
            lines.append(f"    Per-feature cosines:")
            for fid, cv in cinfo["per_feature"]:
                lines.append(f"       F{fid:5d}  cos={cv:+.3f}")
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()

    # Collect reference residuals once — shared across target comparisons
    print("\nCollecting residuals for reference n=5...")
    R_ref_train, used_ref = collect_residuals(model, REFERENCE, TRAIN_TEMPLATES)
    print(f"  {R_ref_train.shape[0]} residuals for ref")

    # Exp-17 tier transfers to overlay (pulled from exp 17 summary numbers)
    sae_tiers = {
        999: {"sae_core": 0.250, "sae_top100": 0.785},
        666: {"sae_core": 0.055, "sae_top100": 0.271},
        137: {"sae_core": -0.129, "sae_top100": 0.164},
    }

    all_results = {}
    cosine_results = {}

    for target in TARGETS:
        print(f"\n=== target = {target} ===")

        print(f"  Collecting residuals for target {target}...")
        R_tgt_train, used_tgt = collect_residuals(model, target, TRAIN_TEMPLATES)
        # Align to shared templates
        shared = [t for t in used_tgt if t in used_ref]
        tgt_idx = [used_tgt.index(t) for t in shared]
        ref_idx = [used_ref.index(t) for t in shared]
        R_tgt = R_tgt_train[tgt_idx].float()
        R_ref = R_ref_train[ref_idx].float()
        print(f"  {len(shared)} paired prompts for training direction")

        print("  Constructing directions...")
        d_mean  = direction_mean_diff(R_tgt, R_ref)
        d_pca1  = direction_pca1(R_tgt, R_ref)
        d_probe = direction_linear_probe(R_tgt, R_ref)

        # Normalize for fair α comparison: scale such that ||direction|| equals
        # the norm of the mean-diff vector. This gives α=1 a consistent meaning
        # across directions (a perturbation of that typical magnitude).
        import torch
        ref_norm = d_mean.norm().item()
        d_mean_n  = d_mean                                # already mean-diff
        d_pca1_n  = d_pca1 / (d_pca1.norm() + 1e-9) * ref_norm
        d_probe_n = d_probe / (d_probe.norm() + 1e-9) * ref_norm

        directions = {
            "mean-diff": d_mean_n,
            "pca1":      d_pca1_n,
            "probe":     d_probe_n,
        }

        print("  α-sweeping each direction over held-out prompts...")
        results = {}
        for label, d in directions.items():
            s = aggregate_sweep(model, target, d, HELDOUT_TEMPLATES, label)
            results[label] = s
            print(f"    {label:<10s}  α=1 transfer = {s['mean'][1.0]:+.3f}  "
                  f"α=0.5 = {s['mean'][0.5]:+.3f}  α=2 = {s['mean'][2.0]:+.3f}")
        all_results[target] = results

        cos = {}
        for label, d in directions.items():
            cos[label] = cosine_with_sae_core(d, sae, target)
            if cos[label] is not None:
                print(f"    cos({label}, Σ SAE core W_dec) = "
                      f"{cos[label]['cos_with_sum_of_core']:+.3f}")
        cosine_results[target] = cos

        plot_transfer_curves(results, target)

    plot_sae_vs_direction_compare(all_results, sae_tiers)
    write_report(all_results, cosine_results)

    print("\n--- Summary ---")
    print(f"{'target':>6}  {'direction':<12s} {'α=0.5':>8s} {'α=1.0':>8s} "
          f"{'α=1.5':>8s} {'α=2.0':>8s}")
    for target, by_dir in all_results.items():
        for label, s in by_dir.items():
            print(f"{target:>6}  {label:<12s} "
                  f"{s['mean'][0.5]:>+8.3f} {s['mean'][1.0]:>+8.3f} "
                  f"{s['mean'][1.5]:>+8.3f} {s['mean'][2.0]:>+8.3f}")

    print(f"\nSAE comparison (exp 17): ")
    print(f"{'target':>6}  sae_core     sae_top100")
    for t, s in sae_tiers.items():
        print(f"{t:>6}  {s['sae_core']:>+8.3f}   {s['sae_top100']:>+8.3f}")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
