"""
Experiment 34: Multi-Null Direction Stability

All identity directions to date are mu(target) - mu(5). The "identity" claim
requires that the direction be stable across the choice of null.

Construct:
    For each target T and null N_i in a null battery, layer L:
        d_{T,N_i}^(L) = mu(R_target^(L)) - mu(R_N_i^(L))
    Compute pairwise cosine matrix C[i, j] = cos(d_{T,N_i}, d_{T,N_j}).
    Compute PC1 of the d_{T,N_i} stack as the "target-stable component".
    Test alpha=1 transfer of the PC1 direction vs each per-null direction.

Optional cultural-null arm:
    Repeat with cultural nulls {42, 100} to discriminate
        "target identity" (stable across all nulls)
    from
        "target-vs-generic"  (stable across generic, varies vs cultural).

Pre-registered thresholds (per design doc 34.4):
    layer 2:  mean cross-null cosine >= 0.6  AND  PC1 explained variance >= 0.60
    layer 8:  mean cross-null cosine >= 0.4  AND  PC1 explained variance >= 0.50
    PC1 transfer within +/- 20% of best per-null direction.

Verdict (averaged over targets, layer 2 dominant):
    PASS     PC1 explained variance >= 0.60 AND mean cross-null cosine >= 0.6 at L=2
    PARTIAL  EV >= 0.40 OR mean cosine >= 0.4
    FAIL     otherwise
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "34_multinull_stability"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYERS = [2, 8]
TARGETS = [999, 666, 137]

GENERIC_NULLS  = [5, 2, 50, 250, 800, 41, 7, 11]
CULTURAL_NULLS = [42, 100]

ALL_NULLS = GENERIC_NULLS + CULTURAL_NULLS

DIVERSE_TEMPLATES = [
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

HELDOUT_TEMPLATES = DIVERSE_TEMPLATES[-10:]
TRAIN_TEMPLATES   = DIVERSE_TEMPLATES[:-10]

ALPHAS = [0.0, 0.5, 1.0, 1.5]


# ---------------------------------------------------------------------------
# Model + capture (matches exp 18 / 33 conventions)
# ---------------------------------------------------------------------------

def load_model():
    from transformer_lens import HookedTransformer
    print("Loading GPT-2...")
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
    used_templates = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        r = capture_resid(model, text, pos, layer)
        resids.append(r)
        used_templates.append(t)
    if not resids:
        return None, []
    return torch.stack(resids), used_templates


def aligned_pair(R_a, used_a, R_b, used_b):
    shared = [t for t in used_a if t in used_b]
    a_idx = [used_a.index(t) for t in shared]
    b_idx = [used_b.index(t) for t in shared]
    return R_a[a_idx].float(), R_b[b_idx].float(), shared


def baseline_logits(model, text):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def logits_with_direction(model, text, pos, direction, alpha, layer):
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
# Core measurements
# ---------------------------------------------------------------------------

def direction_for_null(model, target, null, layer):
    """d = mu(R_target) - mu(R_null) computed across diverse templates,
    paired by template."""
    R_t, used_t = collect_residuals_at_layer(model, target, TRAIN_TEMPLATES, layer)
    R_n, used_n = collect_residuals_at_layer(model, null,   TRAIN_TEMPLATES, layer)
    if R_t is None or R_n is None:
        return None, 0
    Rt, Rn, shared = aligned_pair(R_t, used_t, R_n, used_n)
    d = Rt.mean(0) - Rn.mean(0)
    return d, len(shared)


def pairwise_cosine(directions):
    """directions: list of (d_model,) tensors -> ndarray (k, k)."""
    import torch
    K = len(directions)
    M = np.zeros((K, K))
    for i in range(K):
        for j in range(K):
            ni = directions[i].norm() + 1e-9
            nj = directions[j].norm() + 1e-9
            M[i, j] = float((directions[i] @ directions[j]).item()) / float(ni * nj)
    return M


def pc1_and_explained_variance(directions):
    """Return (pc1 vector (d_model,), explained variance ratio)."""
    import torch
    D = torch.stack(directions)              # (k, d_model)
    D_centered = D - D.mean(0, keepdim=True)
    U, S, V = torch.linalg.svd(D_centered, full_matrices=False)
    var_total = float((S * S).sum())
    var_pc1   = float((S[0] * S[0]).item()) if S.numel() > 0 else 0.0
    explained = var_pc1 / max(var_total, 1e-12)
    pc1 = V[0]                                # already unit vector
    return pc1, explained


def alpha_sweep(model, target, ref_null, template, direction, layer, alphas=ALPHAS):
    """Transfer = 1 - KL(intervened || ref) / KL(target || ref) on this template,
    with reference being one chosen null token (we use 5 for transfer scoring,
    matching exp 18 conventions)."""
    text_target = template.format(n=target)
    text_ref    = template.format(n=ref_null)
    pos_t = last_token_of_span(model, text_target, str(target))
    pos_r = last_token_of_span(model, text_ref, str(ref_null))
    if pos_t is None or pos_r is None:
        return None

    logits_tgt = baseline_logits(model, text_target)
    logits_ref = baseline_logits(model, text_ref)
    kl_baseline = kl_div(logits_tgt, logits_ref)

    out = {"alphas": {}}
    for a in alphas:
        li = logits_with_direction(model, text_target, pos_t, direction, a, layer)
        kl_ref = kl_div(li, logits_ref)
        transfer = 1.0 - (kl_ref / max(kl_baseline, 1e-9))
        out["alphas"][a] = transfer
    return out


def aggregate_sweep(model, target, ref_null, direction, layer, templates):
    per_alpha = {a: [] for a in ALPHAS}
    for t in templates:
        res = alpha_sweep(model, target, ref_null, t, direction, layer)
        if res is None:
            continue
        for a in ALPHAS:
            per_alpha[a].append(res["alphas"][a])
    return {a: float(np.mean(per_alpha[a])) if per_alpha[a] else 0.0
            for a in ALPHAS}


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def classify_verdict(per_target_layer):
    """per_target_layer[target][layer] = {mean_cosine_generic, ev_generic, ...}.
    Verdict averaged over targets at L=2."""
    cos_at_L2, ev_at_L2 = [], []
    for target, by_layer in per_target_layer.items():
        e = by_layer.get(2)
        if e:
            cos_at_L2.append(e["mean_cosine_generic_offdiag"])
            ev_at_L2.append(e["pc1_explained_var_generic"])
    if not cos_at_L2:
        return {"verdict": "UNKNOWN"}
    mean_cos_l2 = float(np.mean(cos_at_L2))
    mean_ev_l2  = float(np.mean(ev_at_L2))
    if mean_cos_l2 >= 0.6 and mean_ev_l2 >= 0.60:
        v = "PASS"
    elif mean_cos_l2 >= 0.4 or mean_ev_l2 >= 0.40:
        v = "PARTIAL"
    else:
        v = "FAIL"
    return {
        "mean_cross_null_cosine_L2_generic": mean_cos_l2,
        "mean_pc1_explained_var_L2_generic": mean_ev_l2,
        "verdict": v,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_cosine_matrix(M, labels, title, outpath):
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(M, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center",
                    color="black" if abs(M[i,j]) < 0.5 else "white",
                    fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def plot_pc1_vs_pernull_transfer(all_results):
    fig, axes = plt.subplots(1, len(TARGETS), figsize=(5 * len(TARGETS), 5),
                              sharey=True)
    if len(TARGETS) == 1:
        axes = [axes]
    for ax, target in zip(axes, TARGETS):
        e = all_results[target].get(2)
        if not e:
            continue
        nulls = e["per_null"]["nulls"]
        xs = np.arange(len(nulls))
        per_null = e["per_null"]["transfer_alpha1"]
        pc1_t   = e["pc1_transfer_alpha1_generic"]
        ax.bar(xs, per_null, color="steelblue", alpha=0.85,
               label="per-null d (alpha=1)")
        ax.axhline(pc1_t, color="tomato", linestyle="--", linewidth=2,
                   label=f"PC1 transfer = {pc1_t:+.3f}")
        ax.set_xticks(xs)
        ax.set_xticklabels([str(n) for n in nulls], rotation=45)
        ax.set_xlabel("null")
        ax.set_title(f"target = {target}, layer 2")
        ax.grid(True, alpha=0.3, axis="y")
    axes[0].set_ylabel("transfer at alpha=1 (held-out)")
    axes[0].legend(fontsize=9, loc="best")
    fig.suptitle("Per-null vs PC1 transfer (target-stable component)")
    fig.tight_layout()
    out = RESULTS_DIR / "pc1_vs_pernull_transfer.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(all_results, verdict):
    lines = ["Exp 34 - Multi-Null Direction Stability", "=" * 70, ""]
    lines.append(f"Targets:        {TARGETS}")
    lines.append(f"Generic nulls:  {GENERIC_NULLS}")
    lines.append(f"Cultural nulls: {CULTURAL_NULLS}")
    lines.append(f"Probe layers:   {PROBE_LAYERS}")
    lines.append(f"Diverse templates: {len(TRAIN_TEMPLATES)}  Held-out: {len(HELDOUT_TEMPLATES)}")
    lines.append("")
    lines.append("Pre-registered outcome rules (averaged over targets, at layer 2):")
    lines.append("  PASS     mean cross-null cosine >= 0.6 AND PC1 EV >= 0.60")
    lines.append("  PARTIAL  cosine >= 0.4 OR EV >= 0.40")
    lines.append("  FAIL     otherwise")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict['verdict']}")
    if "mean_cross_null_cosine_L2_generic" in verdict:
        lines.append(f"  mean cross-null cosine  (L=2, generic): "
                     f"{verdict['mean_cross_null_cosine_L2_generic']:+.3f}")
        lines.append(f"  mean PC1 explained var (L=2, generic): "
                     f"{verdict['mean_pc1_explained_var_L2_generic']:.3f}")
    lines.append("")

    for target in TARGETS:
        for L in PROBE_LAYERS:
            e = all_results.get(target, {}).get(L)
            if not e:
                continue
            lines.append(f"\n### target = {target}  layer = {L}")
            lines.append(f"  generic-nulls: {e['per_null']['nulls']}")
            lines.append(f"  mean off-diag cosine (generic): "
                         f"{e['mean_cosine_generic_offdiag']:+.3f}")
            lines.append(f"  PC1 explained variance (generic): "
                         f"{e['pc1_explained_var_generic']:.3f}")
            lines.append(f"  PC1 transfer @ alpha=1: {e['pc1_transfer_alpha1_generic']:+.3f}")
            best_per_null = max(e['per_null']['transfer_alpha1'])
            lines.append(f"  best per-null transfer @ alpha=1: {best_per_null:+.3f}")
            if "mean_cosine_with_cultural" in e:
                lines.append(f"  mean cosine generic-vs-cultural nulls: "
                             f"{e['mean_cosine_with_cultural']:+.3f}")

    out = RESULTS_DIR / "report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import torch
    model = load_model()
    all_results = {}

    for target in TARGETS:
        all_results[target] = {}
        for layer in PROBE_LAYERS:
            print(f"\n=== target={target}  layer={layer} ===")

            # Per-null directions (generic)
            generic_dirs = []
            generic_nulls_used = []
            for n in GENERIC_NULLS:
                d, k = direction_for_null(model, target, n, layer)
                if d is None or k < 5:
                    continue
                generic_dirs.append(d)
                generic_nulls_used.append(n)
            print(f"  generic nulls used: {generic_nulls_used}")

            # Cosine matrix + PC1 over generic
            M_gen = pairwise_cosine(generic_dirs)
            offdiag = M_gen[~np.eye(len(M_gen), dtype=bool)]
            mean_cos_gen = float(offdiag.mean()) if len(offdiag) else 0.0
            pc1_gen, ev_gen = pc1_and_explained_variance(generic_dirs)
            print(f"  mean off-diag cosine (generic): {mean_cos_gen:+.3f}")
            print(f"  PC1 explained variance (generic): {ev_gen:.3f}")

            # Rescale PC1 to typical d-norm for fair alpha=1 comparison
            mean_d_norm = float(torch.stack([d.norm() for d in generic_dirs]).mean())
            pc1_scaled  = pc1_gen / (pc1_gen.norm() + 1e-9) * mean_d_norm

            # Per-null transfer at alpha=1, scoring against a fixed transfer
            # reference (n=5) so directions are comparable.
            ref_for_scoring = 5
            per_null_alpha1 = []
            for d, n in zip(generic_dirs, generic_nulls_used):
                sw = aggregate_sweep(model, target, ref_for_scoring,
                                     d, layer, HELDOUT_TEMPLATES)
                per_null_alpha1.append(sw[1.0])
            print(f"  per-null transfer @ alpha=1 (vs ref={ref_for_scoring}): "
                  f"{[round(x, 3) for x in per_null_alpha1]}")

            sw_pc1 = aggregate_sweep(model, target, ref_for_scoring,
                                     pc1_scaled, layer, HELDOUT_TEMPLATES)
            pc1_transfer_a1 = sw_pc1[1.0]
            print(f"  PC1 transfer @ alpha=1 (vs ref={ref_for_scoring}): "
                  f"{pc1_transfer_a1:+.3f}")

            # Plot generic cosine matrix
            plot_cosine_matrix(
                M_gen, [str(n) for n in generic_nulls_used],
                f"target={target}, layer={layer}: cosine across generic nulls",
                RESULTS_DIR / f"cosine_matrix_{target}_L{layer}.png",
            )

            # Optional cultural-null arm
            cultural_dirs = []
            cultural_used = []
            for n in CULTURAL_NULLS:
                d, k = direction_for_null(model, target, n, layer)
                if d is None or k < 5:
                    continue
                cultural_dirs.append(d)
                cultural_used.append(n)
            mean_cos_with_cultural = None
            if cultural_dirs:
                cross = []
                for dg in generic_dirs:
                    for dc in cultural_dirs:
                        cs = float((dg @ dc).item()) / (
                            float(dg.norm()) * float(dc.norm()) + 1e-9)
                        cross.append(cs)
                mean_cos_with_cultural = float(np.mean(cross)) if cross else None
                print(f"  mean cosine generic-vs-cultural: "
                      f"{mean_cos_with_cultural:+.3f}")

            entry = {
                "per_null": {
                    "nulls": generic_nulls_used,
                    "transfer_alpha1": per_null_alpha1,
                },
                "cosine_matrix_generic": M_gen.tolist(),
                "mean_cosine_generic_offdiag": mean_cos_gen,
                "pc1_explained_var_generic":   ev_gen,
                "pc1_transfer_alpha1_generic": pc1_transfer_a1,
                "mean_d_norm": mean_d_norm,
            }
            if mean_cos_with_cultural is not None:
                entry["cultural_nulls_used"] = cultural_used
                entry["mean_cosine_with_cultural"] = mean_cos_with_cultural
            all_results[target][layer] = entry

    verdict = classify_verdict(all_results)
    print(f"\nVerdict: {verdict['verdict']}")
    plot_pc1_vs_pernull_transfer(all_results)
    write_report(all_results, verdict)

    summary = {
        "design": "exp 34: multi-null direction stability",
        "probe_layers": PROBE_LAYERS,
        "targets": TARGETS,
        "generic_nulls":  GENERIC_NULLS,
        "cultural_nulls": CULTURAL_NULLS,
        "results": {
            str(t): {str(L): entry for L, entry in by_layer.items()}
            for t, by_layer in all_results.items()
        },
        "verdict": verdict,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
