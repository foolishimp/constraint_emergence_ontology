"""
Experiment 19: Rank-k Identity Saturation

Exp 18 showed that a single mean-diff residual direction transfers
identity at α=1 transfer ≈ 0.24–0.28, well below the pre-registered
≥ 0.8 threshold. Two readings of the shortfall are consistent with the
evidence:

  (a) the construct is low-rank linear at some k > 1; rank-1 captures a
      fraction of the identity subspace proportional to its largest
      principal axis.
  (b) the construct is not purely linear in residual space; additional
      rank does not close the gap.

This experiment discriminates them. Iteratively extract K_MAX orthogonal
identity directions by residualized mean-diff, form a rank-k projector
P_k, and α-sweep on held-out prompts. Secondary method: regularized LDA
in residual space, iterated by the same residualization.

Pre-registered expectation: at k = 5, α = 1, transfer ≥ 0.8 for at least
two of {666, 999, 137} using mean-diff iteration.

Outcome interpretation:
  Pass     ≥ 2 targets meet threshold at k ≤ 5
  Partial  1 target at k ≤ 10, or ≥ 2 in [0.5, 0.8) at k = 5
  Fail     transfer plateaus below 0.5 at k = 10 for all targets

Exp 19 persists the rank-k* projector per target to `results/19_rank_k_saturation/`
so exp 20 can load it for the conditional-independence promotion-gate
test.
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DEFAULT_PROBE_LAYER = 8


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run rank-k identity saturation at a chosen probe layer.",
    )
    parser.add_argument(
        "--layer",
        type=int,
        default=DEFAULT_PROBE_LAYER,
        help=f"Residual stream layer to probe (default: {DEFAULT_PROBE_LAYER})",
    )
    return parser.parse_args()


ARGS = parse_args()
PROBE_LAYER = ARGS.layer

RESULTS_ROOT = Path(__file__).parent.parent / "results" / "19_rank_k_saturation"
RESULTS_DIR = (RESULTS_ROOT if PROBE_LAYER == DEFAULT_PROBE_LAYER
               else RESULTS_ROOT / f"layer_{PROBE_LAYER}")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE = 5
TARGETS = [999, 666, 137]

K_MAX = 10

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

HELDOUT_TEMPLATES = TEMPLATE_POOL[-10:]
TRAIN_TEMPLATES   = TEMPLATE_POOL[:-10]

ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

PASS_TRANSFER = 0.80
PARTIAL_TRANSFER = 0.50


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


def capture_resid(model, text, pos, layer=PROBE_LAYER):
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
    import torch
    resids = []
    used = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        r = capture_resid(model, text, pos)
        resids.append(r)
        used.append(t)
    return torch.stack(resids), used


def baseline_logits(model, text):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def logits_with_projector(model, text, pos, projector, mu_null, alpha,
                          layer=PROBE_LAYER):
    """
    Intervention: r_new = r - α * P(r - μ_null)
    where P is a rank-k projector built from orthonormal identity
    directions and μ_null is the reference-mean residual.
    """
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"

    def patch(value, hook):
        resid = value[0, pos, :].clone()
        offset = projector @ (resid - mu_null)
        value[0, pos, :] = resid - alpha * offset
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
# Direction extraction
# ---------------------------------------------------------------------------

def iterated_mean_diff_directions(R_tgt, R_ref, k_max=K_MAX):
    """
    Return k_max orthonormal directions by iterated residualized mean-diff.

    For k = 1..k_max:
      d_k = μ(R_tgt_perp) − μ(R_ref_perp), normalise.
      R_tgt_perp, R_ref_perp = residuals with span(d_1..d_{k-1}) removed.
    """
    import torch
    R_t = R_tgt.clone().float()
    R_r = R_ref.clone().float()
    directions = []
    for k in range(k_max):
        d = R_t.mean(0) - R_r.mean(0)
        norm = d.norm()
        if norm < 1e-8:
            # subspace exhausted
            break
        d = d / norm
        directions.append(d)
        # residualise both sets: r - (r·d) d
        R_t = R_t - (R_t @ d).unsqueeze(-1) * d.unsqueeze(0)
        R_r = R_r - (R_r @ d).unsqueeze(-1) * d.unsqueeze(0)
    return torch.stack(directions, dim=0)  # (k, d_model)


def iterated_lda_directions(R_tgt, R_ref, k_max=K_MAX, shrinkage=0.5):
    """
    Return k_max orthonormal directions by iterated regularised LDA
    followed by residualisation.

    Each iteration: fit binary LDA (target vs ref) on the residualised
    pair; extract the decision normal; normalise and residualise out.
    """
    import torch
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

    R_t = R_tgt.clone().float()
    R_r = R_ref.clone().float()
    directions = []
    for k in range(k_max):
        X = torch.cat([R_t, R_r], dim=0).numpy()
        y = np.concatenate([
            np.ones(len(R_t), dtype=int),
            np.zeros(len(R_r), dtype=int),
        ])
        try:
            lda = LinearDiscriminantAnalysis(
                solver="lsqr", shrinkage=shrinkage
            )
            lda.fit(X, y)
            w = lda.coef_[0]  # (d_model,)
        except Exception as e:
            print(f"    LDA k={k+1} failed: {e}")
            break
        d = torch.tensor(w, dtype=torch.float32)
        norm = d.norm()
        if norm < 1e-8:
            break
        d = d / norm
        directions.append(d)
        R_t = R_t - (R_t @ d).unsqueeze(-1) * d.unsqueeze(0)
        R_r = R_r - (R_r @ d).unsqueeze(-1) * d.unsqueeze(0)
    if not directions:
        return None
    return torch.stack(directions, dim=0)


def build_projector(directions, k):
    """
    P_k = Σ_{i < k} d_i d_iᵀ for orthonormal directions (d_model,).
    """
    import torch
    D = directions[:k]                           # (k, d_model)
    return D.t() @ D                             # (d_model, d_model)


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

def alpha_sweep_projector(model, target, template, projector, mu_null,
                          alphas=ALPHAS):
    text_target = template.format(n=target)
    text_ref    = template.format(n=REFERENCE)
    pos_t = last_token_of_span(model, text_target, str(target))
    if pos_t is None:
        return None

    logits_tgt = baseline_logits(model, text_target)
    logits_ref = baseline_logits(model, text_ref)
    kl_baseline = kl_div(logits_tgt, logits_ref)

    out = {"template": template, "kl_baseline": kl_baseline, "alphas": {}}
    for a in alphas:
        li = logits_with_projector(model, text_target, pos_t, projector,
                                   mu_null, a)
        kl_ref = kl_div(li, logits_ref)
        kl_tgt = kl_div(li, logits_tgt)
        transfer = 1.0 - (kl_ref / max(kl_baseline, 1e-9))
        out["alphas"][a] = {
            "kl_ref": kl_ref, "kl_tgt": kl_tgt, "transfer": transfer,
        }
    return out


def aggregate_sweep(model, target, projector, mu_null, templates):
    per_alpha = {a: [] for a in ALPHAS}
    kl_baseline_all = []
    for t in templates:
        res = alpha_sweep_projector(model, target, t, projector, mu_null)
        if res is None:
            continue
        kl_baseline_all.append(res["kl_baseline"])
        for a in ALPHAS:
            per_alpha[a].append(res["alphas"][a]["transfer"])
    return {
        "kl_baseline": float(np.mean(kl_baseline_all)) if kl_baseline_all else 0.0,
        "mean":        {a: float(np.mean(per_alpha[a])) if per_alpha[a] else 0.0 for a in ALPHAS},
        "std":         {a: float(np.std(per_alpha[a]))  if per_alpha[a] else 0.0 for a in ALPHAS},
        "n_templates": len(per_alpha[ALPHAS[0]]),
    }


def rank_k_saturation(model, target, directions, mu_null, templates,
                      k_values, method_label):
    """Run α-sweep for each k in k_values, return {k: summary}."""
    import torch
    results = {}
    for k in k_values:
        P_k = build_projector(directions, k)
        s = aggregate_sweep(model, target, P_k, mu_null, templates)
        s["k"] = k
        results[k] = s
        print(f"    {method_label}  k={k:2d}  α=1 transfer = "
              f"{s['mean'][1.0]:+.3f}  α=2 = {s['mean'][2.0]:+.3f}")
    return results


def pick_k_star(curve, threshold=PASS_TRANSFER):
    """Smallest k with α=1 transfer ≥ threshold; else K_MAX."""
    for k in sorted(curve.keys()):
        if curve[k]["mean"][1.0] >= threshold:
            return k
    return max(curve.keys())


# ---------------------------------------------------------------------------
# Persistence — write projectors for exp 20
# ---------------------------------------------------------------------------

def persist_projector(target, directions, mu_null, k_star, method_label):
    import torch
    path = RESULTS_DIR / f"projector_{method_label}_{target}.npz"
    np.savez(
        path,
        directions=directions.cpu().numpy(),        # (k_max, d_model)
        mu_null=mu_null.cpu().numpy(),              # (d_model,)
        k_star=np.array(k_star, dtype=np.int64),
        target=np.array(target, dtype=np.int64),
        method=method_label,
    )
    return path


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_saturation_curves(per_target_results, method_label):
    fig, axes = plt.subplots(1, len(per_target_results), figsize=(14, 5),
                             sharey=True)
    if len(per_target_results) == 1:
        axes = [axes]
    for ax, (target, curves) in zip(axes, per_target_results.items()):
        ks = sorted(curves.keys())
        for a in [0.5, 1.0, 1.5, 2.0]:
            ys = [curves[k]["mean"][a] for k in ks]
            ax.plot(ks, ys, marker="o", linewidth=2, label=f"α={a}")
        ax.axhline(PASS_TRANSFER, color="green", linestyle="--", alpha=0.4,
                   label=f"pass ({PASS_TRANSFER})")
        ax.axhline(PARTIAL_TRANSFER, color="orange", linestyle="--", alpha=0.4,
                   label=f"partial ({PARTIAL_TRANSFER})")
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.set_xlabel("k (rank of identity projector)")
        ax.set_title(f"n = {target}")
        ax.grid(True, alpha=0.3)
        if target == list(per_target_results.keys())[0]:
            ax.set_ylabel("transfer (1 − KL(intervened‖ref) / KL(tgt‖ref))")
            ax.legend(fontsize=8)
    fig.suptitle(f"Rank-k saturation — {method_label}")
    fig.tight_layout()
    out = RESULTS_DIR / f"saturation_{method_label}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_method_compare(meandiff_results, lda_results):
    """Overlay mean-diff vs LDA α=1 transfer per target, per k."""
    targets = list(meandiff_results.keys())
    fig, axes = plt.subplots(1, len(targets), figsize=(14, 5), sharey=True)
    if len(targets) == 1:
        axes = [axes]
    for ax, target in zip(axes, targets):
        ks_md = sorted(meandiff_results[target].keys())
        ys_md = [meandiff_results[target][k]["mean"][1.0] for k in ks_md]
        ax.plot(ks_md, ys_md, marker="o", linewidth=2, color="tomato",
                label="mean-diff α=1")
        if target in lda_results:
            ks_lda = sorted(lda_results[target].keys())
            ys_lda = [lda_results[target][k]["mean"][1.0] for k in ks_lda]
            ax.plot(ks_lda, ys_lda, marker="s", linewidth=2, color="steelblue",
                    label="LDA α=1")
        ax.axhline(PASS_TRANSFER, color="green", linestyle="--", alpha=0.4)
        ax.axhline(PARTIAL_TRANSFER, color="orange", linestyle="--", alpha=0.4)
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.set_xlabel("k")
        ax.set_title(f"n = {target}")
        ax.grid(True, alpha=0.3)
        if target == targets[0]:
            ax.set_ylabel("transfer at α=1")
            ax.legend(fontsize=8)
    fig.suptitle("Method comparison — mean-diff vs LDA")
    fig.tight_layout()
    out = RESULTS_DIR / "method_compare.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def score_outcome(meandiff_results):
    """
    Pass:    ≥ 2 targets meet PASS_TRANSFER at k ≤ 5
    Partial: 1 target meets PASS_TRANSFER at k ≤ 10, or ≥ 2 in [0.5, 0.8) at k = 5
    Fail:    transfer plateaus below PARTIAL_TRANSFER at k = 10 for all targets
    """
    targets_pass_5  = [t for t, c in meandiff_results.items()
                       if any(c[k]["mean"][1.0] >= PASS_TRANSFER
                              for k in c if k <= 5)]
    targets_pass_10 = [t for t, c in meandiff_results.items()
                       if any(c[k]["mean"][1.0] >= PASS_TRANSFER
                              for k in c if k <= 10)]
    targets_partial_5 = [t for t, c in meandiff_results.items()
                         if max(c[k]["mean"][1.0] for k in c if k <= 5)
                            in range_incl(PARTIAL_TRANSFER, PASS_TRANSFER)]
    max_at_k10 = {t: max(c[k]["mean"][1.0] for k in c)
                  for t, c in meandiff_results.items()}

    if len(targets_pass_5) >= 2:
        outcome = "PASS"
    elif len(targets_pass_10) >= 1 or len(targets_partial_5) >= 2:
        outcome = "PARTIAL"
    elif all(v < PARTIAL_TRANSFER for v in max_at_k10.values()):
        outcome = "FAIL"
    else:
        outcome = "PARTIAL"

    return {
        "outcome":          outcome,
        "targets_pass_k5":  targets_pass_5,
        "targets_pass_k10": targets_pass_10,
        "max_transfer":     max_at_k10,
    }


def range_incl(lo, hi):
    class _R:
        def __contains__(self, x):
            return lo <= x < hi
    return _R()


def write_report(meandiff_results, lda_results, k_star_per_target, outcome):
    lines = [
        f"Exp 19 — Rank-k Identity Saturation  (layer {PROBE_LAYER})",
        "=" * 72,
        "",
        f"Reference: n = {REFERENCE}",
        f"Targets:   {TARGETS}",
        f"k_max:     {K_MAX}",
        f"Train templates:   {len(TRAIN_TEMPLATES)}",
        f"Held-out templates: {len(HELDOUT_TEMPLATES)}",
        "",
        f"Pre-registered outcome rules:",
        f"  PASS     ≥ 2 targets meet transfer ≥ {PASS_TRANSFER} at k ≤ 5",
        f"  PARTIAL  1 target at k ≤ 10, or ≥ 2 in [{PARTIAL_TRANSFER}, {PASS_TRANSFER}) at k = 5",
        f"  FAIL     all targets plateau < {PARTIAL_TRANSFER} at k = {K_MAX}",
        "",
        f"OUTCOME: {outcome['outcome']}",
        f"  targets meeting pass at k ≤ 5:  {outcome['targets_pass_k5']}",
        f"  targets meeting pass at k ≤ {K_MAX}: {outcome['targets_pass_k10']}",
        f"  max-over-k transfer per target:  {outcome['max_transfer']}",
        "",
    ]

    for target in TARGETS:
        lines.append(f"\n### target = {target}")
        md = meandiff_results[target]
        lines.append(f"  mean KL(target‖ref) over held-out = "
                     f"{md[1]['kl_baseline']:.4f}")
        lines.append(f"  k* (mean-diff, threshold {PASS_TRANSFER}) = "
                     f"{k_star_per_target[target]}")
        lines.append("")
        lines.append(f"  Mean-diff transfer curve:")
        lines.append(f"    {'k':>3s} | " + " | ".join(f"{a:>7s}" for a in
                     [f"α={a}" for a in ALPHAS]))
        for k in sorted(md.keys()):
            row = [f"{k:>3d}"]
            for a in ALPHAS:
                row.append(f"{md[k]['mean'][a]:>+7.3f}")
            lines.append("    " + " | ".join(row))

        if target in lda_results:
            ld = lda_results[target]
            lines.append("")
            lines.append(f"  LDA transfer curve:")
            lines.append(f"    {'k':>3s} | " + " | ".join(f"{a:>7s}" for a in
                         [f"α={a}" for a in ALPHAS]))
            for k in sorted(ld.keys()):
                row = [f"{k:>3d}"]
                for a in ALPHAS:
                    row.append(f"{ld[k]['mean'][a]:>+7.3f}")
                lines.append("    " + " | ".join(row))

    out = RESULTS_DIR / "rank_k_report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")

    # Also write machine-readable summary for exp 20 consumption.
    json_summary = {
        "outcome":   outcome,
        "k_star":    {str(t): int(k_star_per_target[t]) for t in TARGETS},
        "meandiff":  {str(t): {k: {a: meandiff_results[t][k]["mean"][a]
                                   for a in ALPHAS}
                               for k in meandiff_results[t]}
                      for t in TARGETS},
        "lda":       {str(t): {k: {a: lda_results[t][k]["mean"][a]
                                   for a in ALPHAS}
                               for k in lda_results[t]}
                      for t in lda_results},
    }
    (RESULTS_DIR / "rank_k_summary.json").write_text(
        json.dumps(json_summary, indent=2))
    print(f"Summary JSON: rank_k_summary.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import torch

    model = load_model()

    print("\nCollecting reference residuals (n=5) on train templates...")
    R_ref_train, used_ref = collect_residuals(model, REFERENCE, TRAIN_TEMPLATES)
    print(f"  {R_ref_train.shape[0]} residuals")

    meandiff_results = {}
    lda_results = {}
    k_star_per_target = {}
    projector_paths = []

    k_values = list(range(1, K_MAX + 1))

    for target in TARGETS:
        print(f"\n=== target = {target} ===")

        R_tgt_train, used_tgt = collect_residuals(model, target, TRAIN_TEMPLATES)
        shared = [t for t in used_tgt if t in used_ref]
        tgt_idx = [used_tgt.index(t) for t in shared]
        ref_idx = [used_ref.index(t) for t in shared]
        R_tgt = R_tgt_train[tgt_idx].float()
        R_ref = R_ref_train[ref_idx].float()
        mu_null = R_ref.mean(0)
        print(f"  {len(shared)} paired prompts for direction extraction")

        print("  Extracting orthogonal mean-diff directions...")
        D_md = iterated_mean_diff_directions(R_tgt, R_ref, k_max=K_MAX)
        print(f"    {D_md.shape[0]} directions extracted")

        print("  α-sweeping rank-k projectors on held-out...")
        md_curves = rank_k_saturation(
            model, target, D_md, mu_null, HELDOUT_TEMPLATES,
            k_values, "mean-diff",
        )
        meandiff_results[target] = md_curves

        k_star = pick_k_star(md_curves, PASS_TRANSFER)
        k_star_per_target[target] = k_star
        print(f"  k* (pass threshold {PASS_TRANSFER}): {k_star}")

        p = persist_projector(target, D_md, mu_null, k_star, "meandiff")
        projector_paths.append(p)
        print(f"  persisted projector: {p.name}")

        print("  Extracting LDA directions (secondary)...")
        D_lda = iterated_lda_directions(R_tgt, R_ref, k_max=K_MAX)
        if D_lda is not None:
            print(f"    {D_lda.shape[0]} LDA directions extracted")
            print("  α-sweeping LDA rank-k projectors on held-out...")
            lda_curves = rank_k_saturation(
                model, target, D_lda, mu_null, HELDOUT_TEMPLATES,
                k_values[:D_lda.shape[0]], "LDA",
            )
            lda_results[target] = lda_curves
            p2 = persist_projector(target, D_lda, mu_null,
                                   pick_k_star(lda_curves, PASS_TRANSFER),
                                   "lda")
            projector_paths.append(p2)
            print(f"  persisted LDA projector: {p2.name}")
        else:
            print("    LDA extraction failed; skipping.")

        plot_saturation_curves({target: md_curves}, f"meandiff_{target}")
        if target in lda_results:
            plot_saturation_curves({target: lda_results[target]},
                                   f"lda_{target}")

    plot_saturation_curves(meandiff_results, "meandiff_all")
    if lda_results:
        plot_method_compare(meandiff_results, lda_results)

    outcome = score_outcome(meandiff_results)
    print(f"\n=== OUTCOME: {outcome['outcome']} ===")
    print(f"  targets passing at k ≤ 5:  {outcome['targets_pass_k5']}")
    print(f"  targets passing at k ≤ {K_MAX}: {outcome['targets_pass_k10']}")

    write_report(meandiff_results, lda_results, k_star_per_target, outcome)

    print(f"\nPersisted projectors for exp 20:")
    for p in projector_paths:
        print(f"  {p}")
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
