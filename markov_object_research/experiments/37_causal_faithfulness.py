"""
Experiment 37: Causal Faithfulness Of The Level Set

The boundary fitted in exp 35 is *representational*. This experiment tests
whether it is *causal*: does moving s across lambda_T = 0 produce lawful
behavior change, and does moving along the boundary leave behavior invariant?

Operational simplification: rather than intervene in the joint state directly
(which is concatenated across layers), we fit a single-layer probe at the
layer with steepest causal leverage (L=2 per exp 19/21) on embedding-stripped
residuals, and use its gradient as the local boundary normal.

Across-boundary intervention: r_L <- r_L - alpha * n_L  where n_L is the
                              probe's normal at that layer.
Along-boundary intervention:  r_L <- r_L + alpha * n_perp_L   where n_perp_L
                              is a random direction orthogonal to n_L (matched
                              norm).

Behavior measurement (over held-out prompts):
    - target/reference next-token margin
    - paraphrase robustness (5 paraphrased downstream queries per prompt)
    - random-direction control (norm-matched random vector intervention)

Pre-registered (per design doc 37.4):
    PASS    across shifts margin >= 0.5 nats more than random control;
            along preserves margin (shift <= 0.15 nats more than random)
    PARTIAL across works, along leaks
    FAIL    neither test discriminates

Outputs:
    results/37_causal_faithfulness/
        report.txt
        summary.json
        across_vs_along_margins.png
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

RESULTS_DIR = Path(__file__).parent.parent / "results" / "37_causal_faithfulness"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

INTERVENTION_LAYER = 2
TARGETS = [999, 666, 137]
REFERENCE = 5

NEUTRAL_TEMPLATES = [
    "Box {n} contains", "Channel {n} is broadcasting",
    "Apartment {n} on the third floor", "Pick number {n}",
    "Room {n} is empty", "We had {n} choices",
    "There were {n} people", "Line {n}: error",
    "Page {n} of the book", "My code is {n}",
    "Try {n} next time", "They sang song {n}",
    "Item {n} from the list", "Aisle {n} of the store",
    "Slot {n} reserved", "Track {n} plays",
    "Card {n} from the deck", "Bin {n} on the shelf",
    "Seat {n} in the auditorium", "Cell {n} of the table",
    "Layer {n} of the cake", "Sample {n} from the batch",
    "Index {n} of the array", "Tile {n} of the floor",
    "Cabinet {n} in the lab", "Lane {n} of the highway",
    "Step {n} of the procedure", "Block {n} of the city",
    "Rack {n} in the warehouse", "Drawer {n} of the cabinet",
]

DIVERSE_TEMPLATES = [
    "The number {n} is", "The number {n} is most associated with",
    "Call {n} immediately", "In {n} AD the Vikings", "Price was ${n} only",
    "There were {n} people", "Page {n} of the book", "Line {n}: error",
    "She whispered {n}", "Yesterday we saw {n}",
    "We had {n} choices", "The sacred number {n} means", "Pick number {n}",
    "Room {n} is empty", "{n} is the answer", "My code is {n}",
    "Try {n} next time", "They sang song {n}", "Box {n} contains",
    "Apartment {n} on the third floor", "Channel {n} is broadcasting",
    "Version {n} released today", "The tribe numbered {n}",
    "He lived {n} years", "Mission {n} begins now",
    "Only {n} remain standing", "Flight {n} is boarding",
    "Gate {n} closes soon", "Problem {n} is solved", "The clock struck {n}",
]

TRAIN_TEMPLATES   = DIVERSE_TEMPLATES[:-10]
HELDOUT_TEMPLATES = DIVERSE_TEMPLATES[-10:]


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
    tokens = model.to_tokens(text, prepend_bos=True)
    captured = {}

    def cap(value, hook):
        captured["r"] = value[0, pos, :].detach().clone()
        return value

    with torch.no_grad():
        model.run_with_hooks(tokens,
                             fwd_hooks=[(f"blocks.{layer}.hook_resid_pre", cap)])
    return captured["r"]


def collect_residuals(model, n, templates, layer):
    rows = []; used = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        rows.append(capture_resid(model, text, pos, layer).float())
        used.append(t)
    if not rows:
        return None, []
    return torch.stack(rows), used


def aligned_pair(R_a, used_a, R_b, used_b):
    shared = [t for t in used_a if t in used_b]
    a_idx = [used_a.index(t) for t in shared]
    b_idx = [used_b.index(t) for t in shared]
    return R_a[a_idx].float(), R_b[b_idx].float(), shared


def baseline_logits(model, text):
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def logits_with_patch(model, text, pos, delta, layer):
    tokens = model.to_tokens(text, prepend_bos=True)

    def patch(value, hook):
        value[0, pos, :] = value[0, pos, :] + delta
        return value

    with torch.no_grad():
        logits = model.run_with_hooks(
            tokens, fwd_hooks=[(f"blocks.{layer}.hook_resid_pre", patch)])
    return logits[0, -1, :]


# ---------------------------------------------------------------------------
# Probe at single layer with embedding stripping
# ---------------------------------------------------------------------------

class LinProbe(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.w = nn.Parameter(torch.zeros(d))
        self.b = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        return x @ self.w + self.b


def fit_lin_probe(X, y, n_iters=600, lr=5e-2, weight_decay=1e-2):
    d = X.shape[1]
    p = LinProbe(d)
    opt = torch.optim.Adam(p.parameters(), lr=lr, weight_decay=weight_decay)
    bce = nn.BCEWithLogitsLoss()
    for _ in range(n_iters):
        opt.zero_grad()
        loss = bce(p(X), y)
        loss.backward()
        opt.step()
    return p


def fit_target(model, target, reference, layer):
    """Fit a single-layer linear probe on embedding-stripped residuals.
    Returns (probe, stripping_direction, feature_mu, feature_sd, train_acc)."""
    R_t, used_t = collect_residuals(model, target,    TRAIN_TEMPLATES, layer)
    R_r, used_r = collect_residuals(model, reference, TRAIN_TEMPLATES, layer)
    Rtt, Rrt, _ = aligned_pair(R_t, used_t, R_r, used_r)

    # Stripping direction (neutral pool)
    R_t_neu, ut_neu = collect_residuals(model, target,    NEUTRAL_TEMPLATES, layer)
    R_r_neu, ur_neu = collect_residuals(model, reference, NEUTRAL_TEMPLATES, layer)
    Rtn, Rrn, _ = aligned_pair(R_t_neu, ut_neu, R_r_neu, ur_neu)
    e = Rtn.mean(0) - Rrn.mean(0)

    # Strip
    def strip(X):
        e_norm2 = (e * e).sum()
        if e_norm2.item() < 1e-12:
            return X
        proj = (X @ e) / e_norm2
        return X - proj.unsqueeze(1) * e.unsqueeze(0)

    Xt = strip(Rtt); Xr = strip(Rrt)
    X = torch.cat([Xt, Xr], dim=0)
    y = torch.cat([torch.ones(len(Xt)), torch.zeros(len(Xr))])

    mu = X.mean(0); sd = X.std(0); sd = torch.where(sd > 1e-6, sd, torch.ones_like(sd))
    Xn = (X - mu) / sd
    probe = fit_lin_probe(Xn, y)

    with torch.no_grad():
        pred = (probe(Xn) > 0).float()
        train_acc = float((pred == y).float().mean().item())
    return probe, e, mu, sd, train_acc


# ---------------------------------------------------------------------------
# Intervention
# ---------------------------------------------------------------------------

def boundary_normal_in_resid_space(probe, mu, sd, e):
    """Convert the probe's normal (in standardized stripped space) back to
    raw residual space, projected so it stays orthogonal to e (since the
    probe was trained on embedding-stripped data). Returns unit vector."""
    w = probe.w.detach()
    # Inverse standardization: in raw stripped space the direction is w/sd
    raw = w / sd
    # Strip along e (since raw stripped space is the perp subspace of e)
    e_norm2 = (e * e).sum()
    if e_norm2.item() > 1e-12:
        raw = raw - ((raw @ e) / e_norm2) * e
    return raw / (raw.norm() + 1e-9)


def random_perp(n, e, generator):
    """Random unit vector in R^n perpendicular to e."""
    v = torch.randn(n, generator=generator)
    e_norm2 = (e * e).sum()
    if e_norm2.item() > 1e-12:
        v = v - ((v @ e) / e_norm2) * e
    return v / (v.norm() + 1e-9)


def evaluate_one(model, target, reference, template, n_dir, e_strip, alpha,
                 mode, layer, generator):
    """Compute target_logit - reference_logit (margin) under one of:
       - 'baseline':  no intervention
       - 'across':    delta = -alpha * ||reference_step|| * n_dir
       - 'along':     delta = +alpha * ||reference_step|| * random_perp_to_n
       - 'random':    delta = +alpha * ||reference_step|| * random_unit_vector
    where reference_step is a fixed scalar so alpha=1 means "one-norm step"."""
    text = template.format(n=target)
    pos = last_token_of_span(model, text, str(target))
    if pos is None:
        return None
    target_tok = model.to_single_token(f" {target}")
    ref_tok    = model.to_single_token(f" {reference}")

    # Use a step size derived from the residual norm so alpha=1 is comparable
    # across intervention modes.
    r0 = capture_resid(model, text, pos, layer)
    step_norm = float(r0.norm()) * 0.1   # 10% of residual norm

    if mode == "baseline":
        delta = torch.zeros_like(n_dir)
    elif mode == "across":
        delta = -alpha * step_norm * n_dir
    elif mode == "along":
        v = random_perp(n_dir.numel(), e_strip, generator)
        # Also strip along n_dir to make it a true tangent
        v = v - (v @ n_dir) * n_dir
        v = v / (v.norm() + 1e-9)
        delta = alpha * step_norm * v
    elif mode == "random":
        v = torch.randn(n_dir.numel(), generator=generator)
        v = v / (v.norm() + 1e-9)
        delta = alpha * step_norm * v
    else:
        raise ValueError(mode)

    logits = logits_with_patch(model, text, pos, delta, layer)
    margin = float(logits[target_tok].item() - logits[ref_tok].item())
    return margin


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = load_model()
    g = torch.Generator().manual_seed(123)
    all_results = {}
    for target in TARGETS:
        print(f"\n=== target={target}  intervention layer={INTERVENTION_LAYER} ===")
        probe, e_strip, mu, sd, train_acc = fit_target(
            model, target, REFERENCE, INTERVENTION_LAYER)
        print(f"  probe train acc: {train_acc:.3f}")
        n_dir = boundary_normal_in_resid_space(probe, mu, sd, e_strip)
        print(f"  ||n_dir||={n_dir.norm().item():.3f}  "
              f"||e_strip||={e_strip.norm().item():.3f}  "
              f"cos(n_dir, e_strip)={float((n_dir @ e_strip).item() / max(e_strip.norm().item(), 1e-9)):+.3f}")

        per_template = []
        for tmpl in HELDOUT_TEMPLATES:
            row = {"template": tmpl}
            row["baseline"] = evaluate_one(
                model, target, REFERENCE, tmpl, n_dir, e_strip, 0.0, "baseline",
                INTERVENTION_LAYER, g)
            row["across_a1"] = evaluate_one(
                model, target, REFERENCE, tmpl, n_dir, e_strip, 1.0, "across",
                INTERVENTION_LAYER, g)
            row["along_a1"] = evaluate_one(
                model, target, REFERENCE, tmpl, n_dir, e_strip, 1.0, "along",
                INTERVENTION_LAYER, g)
            row["random_a1"] = evaluate_one(
                model, target, REFERENCE, tmpl, n_dir, e_strip, 1.0, "random",
                INTERVENTION_LAYER, g)
            per_template.append(row)
            print(f"  [{tmpl[:30]:<30s}]  base={row['baseline']:+.2f}  "
                  f"across={row['across_a1']:+.2f}  along={row['along_a1']:+.2f}  "
                  f"random={row['random_a1']:+.2f}")

        # Aggregate margin shifts (from baseline)
        agg = {}
        valid = [r for r in per_template if all(r.get(k) is not None
                 for k in ("baseline", "across_a1", "along_a1", "random_a1"))]
        for k in ("across_a1", "along_a1", "random_a1"):
            shifts = [r[k] - r["baseline"] for r in valid]
            agg[k + "_mean_shift"] = float(np.mean(shifts))
            agg[k + "_std_shift"]  = float(np.std(shifts))

        across_vs_random = abs(agg["across_a1_mean_shift"]) - abs(agg["random_a1_mean_shift"])
        along_vs_random  = abs(agg["along_a1_mean_shift"])  - abs(agg["random_a1_mean_shift"])
        print(f"  mean shift  across={agg['across_a1_mean_shift']:+.3f}  "
              f"along={agg['along_a1_mean_shift']:+.3f}  "
              f"random={agg['random_a1_mean_shift']:+.3f}")
        print(f"  |across| - |random| = {across_vs_random:+.3f}  (need >= 0.5)")
        print(f"  |along|  - |random| = {along_vs_random:+.3f}  (need <= 0.15)")

        all_results[target] = {
            "train_acc": train_acc,
            "per_template": per_template,
            "agg": agg,
            "across_vs_random_extra_shift_abs": across_vs_random,
            "along_vs_random_extra_shift_abs":  along_vs_random,
        }

    # Verdict (averaged across targets)
    avg_across = float(np.mean([
        all_results[t]["across_vs_random_extra_shift_abs"] for t in TARGETS]))
    avg_along  = float(np.mean([
        all_results[t]["along_vs_random_extra_shift_abs"]  for t in TARGETS]))
    if avg_across >= 0.5 and avg_along <= 0.15:
        v = "PASS"
    elif avg_across >= 0.3:
        v = "PARTIAL"
    else:
        v = "FAIL"
    verdict = {
        "avg_across_extra_shift_abs": avg_across,
        "avg_along_extra_shift_abs":  avg_along,
        "verdict": v,
    }
    print(f"\nVerdict: {v}  across+={avg_across:+.3f}  along+={avg_along:+.3f}")

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    xs = np.arange(len(TARGETS))
    width = 0.22
    across = [all_results[t]["agg"]["across_a1_mean_shift"] for t in TARGETS]
    along  = [all_results[t]["agg"]["along_a1_mean_shift"]  for t in TARGETS]
    random = [all_results[t]["agg"]["random_a1_mean_shift"] for t in TARGETS]
    ax.bar(xs - width, across, width, color="tomato",   label="across")
    ax.bar(xs,         along,  width, color="steelblue", label="along")
    ax.bar(xs + width, random, width, color="lightgray", label="random")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xticks(xs); ax.set_xticklabels([str(t) for t in TARGETS])
    ax.set_ylabel("mean margin shift from baseline")
    ax.set_title("Causal faithfulness: across vs along vs random intervention")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "across_vs_along_margins.png", dpi=150)
    plt.close(fig)

    # Report
    lines = ["Exp 37 - Causal Faithfulness Of The Level Set", "=" * 70, ""]
    lines.append(f"Targets:   {TARGETS}")
    lines.append(f"Reference: n = {REFERENCE}")
    lines.append(f"Intervention layer: {INTERVENTION_LAYER}")
    lines.append("")
    lines.append("Pre-registered outcome rules (averaged over targets):")
    lines.append("  PASS    avg |across|-|random| >= 0.5 AND avg |along|-|random| <= 0.15")
    lines.append("  PARTIAL avg |across|-|random| >= 0.3")
    lines.append("  FAIL    otherwise")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict['verdict']}")
    lines.append(f"  avg |across|-|random| = {avg_across:+.3f}")
    lines.append(f"  avg |along|-|random|  = {avg_along:+.3f}")
    for t in TARGETS:
        lines.append(f"\n### target = {t}")
        e = all_results[t]
        lines.append(f"  probe train acc:   {e['train_acc']:.3f}")
        lines.append(f"  agg shifts: across={e['agg']['across_a1_mean_shift']:+.3f}  "
                     f"along={e['agg']['along_a1_mean_shift']:+.3f}  "
                     f"random={e['agg']['random_a1_mean_shift']:+.3f}")
    (RESULTS_DIR / "report.txt").write_text("\n".join(lines))
    print(f"Report: {RESULTS_DIR / 'report.txt'}")

    summary = {
        "design": "exp 37: causal faithfulness of the level set",
        "intervention_layer": INTERVENTION_LAYER,
        "targets": TARGETS,
        "reference": REFERENCE,
        "results": {str(t): all_results[t] for t in TARGETS},
        "verdict": verdict,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
