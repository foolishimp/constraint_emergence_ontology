"""
Experiment 24: Cross-model Replication — Pythia-160M

All results to date are within GPT-2 small. The construct's claim to
generality over trained representations requires replication in at
least one comparable but distinct model. Pythia-160M is the first
target because it has similar scale (12 layers, ~160M params), a
public residual-stream architecture, and a different tokenizer
(GPT-NeoX). Proportional-depth layer 8 of 12 is used.

First-pass scope (this file): port of exp 18 only.
  - Mean-difference direction in residual space at layer 8
  - α-sweep intervention on held-out prompts
  - Transfer metric = 1 − KL(intervened ‖ ref) / KL(target ‖ ref)

SAE-dependent ports (exp 08 core/coat, exp 13 core-ablation causality,
exp 17 outside-set leak) are out of scope here until an SAE is
selected for Pythia-160M. Design-doc dependency clause 24.6.

Pre-registered expectation (exp 18 port only):
  mean-diff α = 1 transfer ≥ 0.10 for ≥ 2 of {999, 666, 137}
  GPT-2 small baseline was ≈ 0.27; threshold relaxed to 0.10 to
  accept qualitative replication rather than magnitude replication.

Outcome interpretation (within this file's scope):
  PASS     ≥ 2 targets meet threshold → exp 18 qualitatively replicates
           in Pythia; the direction-native object generalises beyond
           GPT-2 small. Promote to full 4-experiment port next.
  PARTIAL  1 target meets threshold → mixed signal; run full port to
           isolate model-specific vs target-specific failure.
  FAIL     0 targets meet threshold → construct is GPT-2-specific at
           candidate status; revisit "LLM" claims in empirical_results.md
           and world_model_project_paper.md.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "24_cross_model_pythia"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME  = "pythia-160m"
PROBE_LAYER = 8
REFERENCE   = 5
TARGETS     = [999, 666, 137]

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

ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

# Pre-registered threshold (relaxed from GPT-2 baseline 0.27)
TRANSFER_THRESHOLD = 0.10
N_PASS_REQUIRED    = 2


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def load_model():
    from transformer_lens import HookedTransformer
    print(f"Loading {MODEL_NAME} via transformer_lens...")
    model = HookedTransformer.from_pretrained(MODEL_NAME)
    model.eval()
    print(f"  n_layers = {model.cfg.n_layers}, "
          f"d_model = {model.cfg.d_model}, "
          f"probe layer = {PROBE_LAYER}")
    return model


def last_token_of_span(model, text, span):
    start = text.find(span)
    if start < 0:
        return None
    end = start + len(span)
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    acc = 0
    for i, tok in enumerate(str_tokens):
        if i == 0 and tok in ("<|endoftext|>", "<|padding|>", ""):
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
        captured["resid"] = value[0, pos, :].detach().clone().float()
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
    if not resids:
        return None, []
    return torch.stack(resids), used


def baseline_logits(model, text):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def logits_with_direction(model, text, pos, direction, alpha,
                          layer=PROBE_LAYER):
    """Subtract α·direction from residual at (pos, layer.hook_resid_pre)."""
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"

    def patch(value, hook):
        resid = value[0, pos, :].clone()
        resid = resid - alpha * direction.to(resid.dtype)
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
# Direction and intervention
# ---------------------------------------------------------------------------

def direction_mean_diff(R_tgt, R_ref):
    return R_tgt.mean(0) - R_ref.mean(0)


def pair_residuals(R_tgt, used_tgt, R_ref, used_ref):
    shared = [t for t in used_tgt if t in used_ref]
    tgt_idx = [used_tgt.index(t) for t in shared]
    ref_idx = [used_ref.index(t) for t in shared]
    return R_tgt[tgt_idx].float(), R_ref[ref_idx].float(), shared


def alpha_sweep(model, target, template, direction, alphas=ALPHAS):
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
        li = logits_with_direction(model, text_target, pos_t, direction, a)
        kl_ref = kl_div(li, logits_ref)
        transfer = 1.0 - (kl_ref / max(kl_baseline, 1e-9))
        result["alphas"][a] = {"kl_ref": kl_ref, "transfer": transfer}
    return result


def aggregate(model, target, direction, templates):
    per_alpha = {a: [] for a in ALPHAS}
    kl_baseline_all = []
    for t in templates:
        res = alpha_sweep(model, target, t, direction)
        if res is None:
            continue
        kl_baseline_all.append(res["kl_baseline"])
        for a in ALPHAS:
            per_alpha[a].append(res["alphas"][a]["transfer"])
    return {
        "kl_baseline": float(np.mean(kl_baseline_all)) if kl_baseline_all else 0.0,
        "per_alpha":   {a: [float(x) for x in per_alpha[a]]
                        for a in ALPHAS},
        "mean":        {a: float(np.mean(per_alpha[a]))
                        if per_alpha[a] else 0.0 for a in ALPHAS},
        "std":         {a: float(np.std(per_alpha[a]))
                        if per_alpha[a] else 0.0 for a in ALPHAS},
        "n":           len(per_alpha[ALPHAS[0]]),
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_alpha_curves(all_results):
    fig, ax = plt.subplots(figsize=(9, 5))
    for target, agg in all_results.items():
        xs = ALPHAS
        ys = [agg["mean"][a] for a in xs]
        es = [agg["std"][a] for a in xs]
        ax.errorbar(xs, ys, yerr=es, marker="o", capsize=3,
                    linewidth=2, label=f"n={target}")
    ax.axhline(TRANSFER_THRESHOLD, color="orange", linestyle="--",
               alpha=0.6,
               label=f"threshold ({TRANSFER_THRESHOLD})")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xlabel("α (intervention strength)")
    ax.set_ylabel("transfer toward reference")
    ax.set_title(f"Pythia-160M — mean-diff direction α-sweep (layer {PROBE_LAYER})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "alpha_sweep.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_gpt2_comparison(all_results):
    """
    Side-by-side α=1 transfer for each target, overlaid with published
    GPT-2 small baselines from exp 18.
    """
    gpt2_baseline = {999: 0.27, 666: 0.28, 137: 0.24}
    targets = sorted(all_results.keys())
    x = np.arange(len(targets))
    width = 0.4
    pythia_vals = [all_results[t]["mean"][1.0]        for t in targets]
    gpt2_vals   = [gpt2_baseline.get(t, float("nan")) for t in targets]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(x - width/2, gpt2_vals,   width, label="GPT-2 small (exp 18)",
           color="#9ca3af")
    ax.bar(x + width/2, pythia_vals, width, label="Pythia-160M (this exp)",
           color="#2563eb")
    ax.axhline(TRANSFER_THRESHOLD, color="orange", linestyle="--",
               alpha=0.6, label=f"threshold ({TRANSFER_THRESHOLD})")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"n={t}" for t in targets])
    ax.set_ylabel("transfer at α = 1")
    ax.set_title("Exp 18 port — Pythia-160M vs GPT-2 small")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "cross_model_bars.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_outcome(all_results):
    n_pass = sum(
        1 for t in TARGETS
        if all_results[t]["mean"].get(1.0, 0.0) >= TRANSFER_THRESHOLD
    )
    if n_pass >= N_PASS_REQUIRED:
        return "PASS", n_pass
    if n_pass == 1:
        return "PARTIAL", n_pass
    return "FAIL", n_pass


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(all_results, outcome, n_pass, direction_norms,
                 paired_counts):
    lines = [
        "Exp 24 — Cross-model Replication (Pythia-160M)",
        "=" * 72,
        "",
        f"Model:             {MODEL_NAME}",
        f"Probe layer:       {PROBE_LAYER} (hook_resid_pre)",
        f"Reference:         n = {REFERENCE}",
        f"Targets:           {TARGETS}",
        f"Train templates:   {len(TRAIN_TEMPLATES)}",
        f"Held-out templates: {len(HELDOUT_TEMPLATES)}",
        "",
        "Scope: exp 18 port (SAE-free). Exps 08/13/17 ports deferred",
        "pending SAE availability for Pythia-160M.",
        "",
        "Pre-registered rule:",
        f"  α = 1 transfer ≥ {TRANSFER_THRESHOLD} for ≥ {N_PASS_REQUIRED} targets",
        f"  (GPT-2 baseline ~0.27; relaxed to 0.10 for qualitative replication)",
        "",
        f"AGGREGATE OUTCOME: {outcome}  ({n_pass}/{len(TARGETS)} targets)",
        "",
    ]
    for target in TARGETS:
        agg = all_results[target]
        lines.append(f"### target = {target}")
        lines.append(f"  paired training templates: {paired_counts[target]}")
        lines.append(f"  direction norm: {direction_norms[target]:.3f}")
        lines.append(f"  mean baseline KL (target ‖ ref): {agg['kl_baseline']:.3f}")
        lines.append(f"  α-sweep (mean ± std over {agg['n']} held-out templates):")
        for a in ALPHAS:
            lines.append(f"    α = {a:>4.2f}   "
                         f"transfer = {agg['mean'][a]:+.3f} "
                         f"± {agg['std'][a]:.3f}")
        a1 = agg["mean"].get(1.0, 0.0)
        pass_flag = "PASS" if a1 >= TRANSFER_THRESHOLD else "below"
        lines.append(f"  α=1 verdict: {pass_flag} (transfer {a1:+.3f} vs "
                     f"threshold {TRANSFER_THRESHOLD})")
        lines.append("")

    out = RESULTS_DIR / "cross_model_report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")

    summary = {
        "outcome":    outcome,
        "n_pass":     n_pass,
        "model":      MODEL_NAME,
        "layer":      PROBE_LAYER,
        "threshold":  TRANSFER_THRESHOLD,
        "targets": {
            str(t): {
                "direction_norm":  direction_norms[t],
                "paired_train":    paired_counts[t],
                "kl_baseline":     all_results[t]["kl_baseline"],
                "mean":            {str(a): all_results[t]["mean"][a]
                                    for a in ALPHAS},
                "std":             {str(a): all_results[t]["std"][a]
                                    for a in ALPHAS},
                "n_heldout":       all_results[t]["n"],
                "alpha_1_transfer": all_results[t]["mean"].get(1.0, 0.0),
                "pass_threshold":   all_results[t]["mean"].get(1.0, 0.0)
                                    >= TRANSFER_THRESHOLD,
            } for t in TARGETS
        },
    }
    (RESULTS_DIR / "cross_model_summary.json").write_text(
        json.dumps(summary, indent=2))
    print("Summary JSON: cross_model_summary.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = load_model()

    all_results     = {}
    direction_norms = {}
    paired_counts   = {}

    print(f"\nCollecting reference residuals for n = {REFERENCE}...")
    R_ref_all, used_ref = collect_residuals(model, REFERENCE, TRAIN_TEMPLATES)
    print(f"  {len(used_ref)} reference residuals captured")

    for target in TARGETS:
        print(f"\n=== target = {target} ===")
        R_tgt, used_tgt = collect_residuals(model, target, TRAIN_TEMPLATES)
        if R_tgt is None:
            print(f"  no residuals captured; skipping")
            all_results[target] = {
                "kl_baseline": 0.0,
                "per_alpha":   {a: [] for a in ALPHAS},
                "mean":        {a: 0.0 for a in ALPHAS},
                "std":         {a: 0.0 for a in ALPHAS},
                "n":           0,
            }
            direction_norms[target] = 0.0
            paired_counts[target]   = 0
            continue

        R_tgt_p, R_ref_p, shared = pair_residuals(
            R_tgt, used_tgt, R_ref_all, used_ref,
        )
        print(f"  paired train templates: {len(shared)}")

        d = direction_mean_diff(R_tgt_p, R_ref_p)
        direction_norms[target] = float(d.norm())
        paired_counts[target]   = len(shared)
        print(f"  direction norm: {direction_norms[target]:.3f}")

        print(f"  α-sweep on {len(HELDOUT_TEMPLATES)} held-out templates...")
        agg = aggregate(model, target, d, HELDOUT_TEMPLATES)
        all_results[target] = agg
        a1 = agg["mean"][1.0]
        print(f"  α = 1 transfer = {a1:+.3f}  "
              f"({'pass' if a1 >= TRANSFER_THRESHOLD else 'below threshold'})")

    outcome, n_pass = score_outcome(all_results)
    print(f"\n=== AGGREGATE OUTCOME: {outcome}  ({n_pass}/{len(TARGETS)}) ===")

    print("\n=== Plots ===")
    plot_alpha_curves(all_results)
    plot_gpt2_comparison(all_results)

    write_report(all_results, outcome, n_pass, direction_norms, paired_counts)

    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
