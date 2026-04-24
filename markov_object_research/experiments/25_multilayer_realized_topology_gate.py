"""
Experiment 25: Multi-layer Realized-topology Gate

Exp 20 failed the single-chart conditional-independence gate at layer 8
and layer 2. After subtracting the selected identity projection, a probe
still predicts target-vs-reference identity perfectly. Exp 21 showed that
identity directions are highly coherent across layers while intervention
leverage is sharply layer-sensitive.

This experiment tests the direct successor hypothesis: the failed gate
conditioned on one local chart rather than the realized topology. Build a
joint chart over layers 2/4/6/8, condition the concatenated residual on
that chart, and test whether held-out residual identity signal weakens
more than under the best single-layer chart.

Pre-registered support threshold:
  PASS     at least two targets satisfy:
             AUC_joint <= 0.70
             AUC_joint <= AUC_best_single - 0.15
             AUC_full - AUC_joint >= 0.25
             HSIC p >= 0.05
  PARTIAL  joint conditioning improves over best single chart, but does
           not close the gate.
  FAIL     joint conditioning adds little, or residual AUC remains high.

Candidate status continues unless a gate actually closes.
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


RESULTS_DIR = (
    Path(__file__).parent.parent / "results" / "25_multilayer_gate"
)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LAYERS = [2, 4, 6, 8]
REFERENCE = 5
TARGETS = [999, 666, 137]

TEMPLATE_POOL = [
    # Direction and residualizer calibration templates.
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
    # Probe templates, disjoint from direction extraction.
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
    "Dial {n} for service",
    "Section {n} has been updated",
    "Serial {n} expired yesterday",
    "Chapter {n} begins with",
    "Ticket {n} was rejected",
    "Process id {n} terminated",
    "Badge {n} entered the room",
    "Order {n} shipped today",
    "Reading {n} on the scale",
    "Scene {n} opens with",
    "Quota {n} exceeded limit",
    "Row {n} contains errors",
    "Track {n} starts playing",
    "Warehouse slot {n} empty",
    "Exit {n} is closed",
    "Report {n} was filed",
    "Document {n} is classified",
    "Batch {n} completed successfully",
    "Prompt {n} needs review",
    "Zone {n} is secured",
]

CALIBRATION_TEMPLATES = TEMPLATE_POOL[:20]
PROBE_TEMPLATES = TEMPLATE_POOL[20:]

N_CV_FOLDS = 5
HSIC_N_PERM_DEFAULT = 200
RNG_SEED = 42
RIDGE_LAMBDA = 1e-3

PASS_AUC_JOINT = 0.70
PASS_JOINT_VS_SINGLE = 0.15
PASS_DELTA_FULL = 0.25
PASS_HSIC_P = 0.05

PARTIAL_AUC_JOINT = 0.85
PARTIAL_JOINT_VS_SINGLE = 0.05


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Exp 25 multi-layer realized-topology gate.",
    )
    parser.add_argument(
        "--hsic-perm",
        type=int,
        default=HSIC_N_PERM_DEFAULT,
        help=f"HSIC permutation count (default: {HSIC_N_PERM_DEFAULT})",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Model / residual capture
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


def capture_resids_at_layers(model, text, pos, layers=LAYERS):
    import torch

    tokens = model.to_tokens(text, prepend_bos=True)
    captured = {}

    def make_capture(layer):
        def capture(value, hook):
            captured[layer] = value[0, pos, :].detach().clone()
            return value
        return capture

    hooks = [
        (f"blocks.{layer}.hook_resid_pre", make_capture(layer))
        for layer in layers
    ]
    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=hooks)
    return captured


def collect_multilayer_residuals(model, n, templates, layers=LAYERS):
    import torch

    rows = []
    used = []
    for template in templates:
        text = template.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        captured = capture_resids_at_layers(model, text, pos, layers)
        if not all(layer in captured for layer in layers):
            continue
        rows.append(torch.stack([captured[layer] for layer in layers], dim=0))
        used.append(template)
    if not rows:
        raise RuntimeError(f"No residuals collected for n={n}")
    return torch.stack(rows, dim=0), used  # (n_templates, n_layers, d_model)


def paired_multilayer_residuals(model, target, reference, templates):
    R_tgt, used_tgt = collect_multilayer_residuals(model, target, templates)
    R_ref, used_ref = collect_multilayer_residuals(model, reference, templates)
    shared = [t for t in used_tgt if t in used_ref]
    tgt_idx = [used_tgt.index(t) for t in shared]
    ref_idx = [used_ref.index(t) for t in shared]
    return R_tgt[tgt_idx].float(), R_ref[ref_idx].float(), shared


# ---------------------------------------------------------------------------
# Chart construction and residualization
# ---------------------------------------------------------------------------

def extract_layer_directions(R_tgt, R_ref):
    """Return unit mean-diff directions and reference means per layer."""
    import torch

    directions = []
    mu_ref = []
    for i in range(len(LAYERS)):
        R_t = R_tgt[:, i, :]
        R_r = R_ref[:, i, :]
        d = R_t.mean(0) - R_r.mean(0)
        d = d / (d.norm() + 1e-9)
        directions.append(d)
        mu_ref.append(R_r.mean(0))
    return torch.stack(directions, dim=0), torch.stack(mu_ref, dim=0)


def flatten_multilayer(R):
    """(n, n_layers, d_model) -> (n, n_layers*d_model)."""
    return R.reshape(R.shape[0], R.shape[1] * R.shape[2])


def chart_coordinates(R, directions, mu_ref):
    """
    Coordinates along each layer-local identity direction:
    z_L = <r_L - mu_ref_L, d_L>.
    """
    centered = R - mu_ref.unsqueeze(0)
    return (centered * directions.unsqueeze(0)).sum(dim=-1)


def fit_chart_residualizer(X_cal, Z_cal, ridge=RIDGE_LAMBDA):
    """
    Fit X ~= [1, Z] B on calibration rows. Returns B.

    The intercept is not regularized. The chart coefficients are lightly
    regularized because X is high-dimensional and calibration is small.
    """
    Z_aug = np.concatenate([np.ones((len(Z_cal), 1)), Z_cal], axis=1)
    gram = Z_aug.T @ Z_aug
    penalty = np.eye(gram.shape[0]) * ridge
    penalty[0, 0] = 0.0
    return np.linalg.solve(gram + penalty, Z_aug.T @ X_cal)


def apply_chart_residualizer(X, Z, beta):
    Z_aug = np.concatenate([np.ones((len(Z), 1)), Z], axis=1)
    return X - Z_aug @ beta


def prepare_conditioned_surfaces(R_cal_t, R_cal_r, R_probe_t, R_probe_r,
                                 directions, mu_ref):
    X_cal = np.concatenate([
        flatten_multilayer(R_cal_t).cpu().numpy(),
        flatten_multilayer(R_cal_r).cpu().numpy(),
    ], axis=0)
    X_probe = np.concatenate([
        flatten_multilayer(R_probe_t).cpu().numpy(),
        flatten_multilayer(R_probe_r).cpu().numpy(),
    ], axis=0)

    Z_cal = np.concatenate([
        chart_coordinates(R_cal_t, directions, mu_ref).cpu().numpy(),
        chart_coordinates(R_cal_r, directions, mu_ref).cpu().numpy(),
    ], axis=0)
    Z_probe = np.concatenate([
        chart_coordinates(R_probe_t, directions, mu_ref).cpu().numpy(),
        chart_coordinates(R_probe_r, directions, mu_ref).cpu().numpy(),
    ], axis=0)

    beta_joint = fit_chart_residualizer(X_cal, Z_cal)
    X_joint = apply_chart_residualizer(X_probe, Z_probe, beta_joint)

    single_surfaces = {}
    single_betas = {}
    for i, layer in enumerate(LAYERS):
        z_cal_i = Z_cal[:, [i]]
        z_probe_i = Z_probe[:, [i]]
        beta_i = fit_chart_residualizer(X_cal, z_cal_i)
        single_surfaces[layer] = apply_chart_residualizer(
            X_probe, z_probe_i, beta_i,
        )
        single_betas[layer] = beta_i

    return {
        "X_full": X_probe,
        "X_joint": X_joint,
        "single_surfaces": single_surfaces,
        "beta_joint": beta_joint,
        "single_betas": single_betas,
        "Z_probe": Z_probe,
    }


# ---------------------------------------------------------------------------
# Probe and HSIC
# ---------------------------------------------------------------------------

def probe_auc_cv(X, y, groups, n_splits=N_CV_FOLDS, C=0.1, seed=RNG_SEED):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler

    gkf = GroupKFold(n_splits=n_splits)
    aucs = []
    for train_idx, test_idx in gkf.split(X, y, groups=groups):
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_idx])
        X_te = scaler.transform(X[test_idx])
        clf = LogisticRegression(
            C=C,
            penalty="l2",
            solver="lbfgs",
            max_iter=2000,
            random_state=seed,
        )
        clf.fit(X_tr, y[train_idx])
        scores = clf.decision_function(X_te)
        try:
            auc = roc_auc_score(y[test_idx], scores)
        except ValueError:
            auc = 0.5
        aucs.append(float(auc))
    return aucs, float(np.mean(aucs))


def gauss_kernel(X, sigma=None):
    sq = np.sum(X ** 2, axis=1, keepdims=True)
    D2 = sq + sq.T - 2 * X @ X.T
    D2 = np.maximum(D2, 0)
    if sigma is None:
        sigma = np.sqrt(np.median(D2[D2 > 0])) if (D2 > 0).any() else 1.0
    sigma = max(sigma, 1e-6)
    return np.exp(-D2 / (2 * sigma ** 2))


def label_kernel(y):
    y = y.reshape(-1, 1)
    return (y == y.T).astype(np.float64)


def hsic(X, y):
    n = len(y)
    K = gauss_kernel(X)
    L = label_kernel(y)
    H = np.eye(n) - np.ones((n, n)) / n
    Kc = H @ K @ H
    return float(np.trace(Kc @ L) / max((n - 1) ** 2, 1))


def hsic_permutation(X, y, n_perm, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    observed = hsic(X, y)
    nulls = []
    for _ in range(n_perm):
        nulls.append(hsic(X, rng.permutation(y)))
    nulls = np.array(nulls)
    p = ((nulls >= observed).sum() + 1) / (n_perm + 1)
    return {
        "observed": float(observed),
        "p": float(p),
        "null_mean": float(nulls.mean()),
        "null_std": float(nulls.std()),
        "nulls": nulls,
    }


# ---------------------------------------------------------------------------
# Scoring and plots
# ---------------------------------------------------------------------------

def score_target(target, auc_full, auc_single_by_layer, auc_joint, hsic_joint):
    best_single_layer = min(auc_single_by_layer, key=auc_single_by_layer.get)
    auc_best_single = auc_single_by_layer[best_single_layer]
    joint_vs_single = auc_best_single - auc_joint
    delta_full = auc_full - auc_joint

    passes = (
        auc_joint <= PASS_AUC_JOINT
        and joint_vs_single >= PASS_JOINT_VS_SINGLE
        and delta_full >= PASS_DELTA_FULL
        and hsic_joint["p"] >= PASS_HSIC_P
    )
    partial = (
        auc_joint <= PARTIAL_AUC_JOINT
        or joint_vs_single >= PARTIAL_JOINT_VS_SINGLE
        or delta_full >= 0.10
    )

    if passes:
        outcome = "PASS"
    elif partial:
        outcome = "PARTIAL"
    else:
        outcome = "FAIL"

    return {
        "target": int(target),
        "auc_full": float(auc_full),
        "auc_best_single": float(auc_best_single),
        "best_single_layer": int(best_single_layer),
        "auc_joint": float(auc_joint),
        "joint_vs_single": float(joint_vs_single),
        "delta_full": float(delta_full),
        "hsic_joint_observed": float(hsic_joint["observed"]),
        "hsic_joint_p": float(hsic_joint["p"]),
        "outcome": outcome,
    }


def aggregate_outcome(per_target):
    n_pass = sum(1 for s in per_target if s["outcome"] == "PASS")
    n_partial = sum(1 for s in per_target if s["outcome"] == "PARTIAL")
    if n_pass >= 2:
        return "PASS"
    if n_pass + n_partial >= 2:
        return "PARTIAL"
    return "FAIL"


def plot_auc_comparison(per_target, auc_single_by_target):
    targets = [s["target"] for s in per_target]
    x = np.arange(len(targets))
    width = 0.25

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(
        x - width,
        [s["auc_full"] for s in per_target],
        width,
        color="tomato",
        label="full residual",
    )
    ax.bar(
        x,
        [s["auc_best_single"] for s in per_target],
        width,
        color="orange",
        label="best single chart",
    )
    ax.bar(
        x + width,
        [s["auc_joint"] for s in per_target],
        width,
        color="steelblue",
        label="joint chart",
    )
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, label="chance")
    ax.axhline(
        PASS_AUC_JOINT,
        color="green",
        linestyle=":",
        linewidth=1,
        label=f"joint pass ceiling ({PASS_AUC_JOINT})",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in targets])
    ax.set_ylim(0.4, 1.02)
    ax.set_ylabel("AUC (target vs reference)")
    ax.set_title("Exp 25 probe AUC after chart conditioning")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "auc_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")

    fig, ax = plt.subplots(figsize=(9, 5))
    for target, by_layer in auc_single_by_target.items():
        ax.plot(
            list(by_layer.keys()),
            list(by_layer.values()),
            marker="o",
            linewidth=2,
            label=f"n={target}",
        )
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("single conditioned layer")
    ax.set_ylabel("AUC")
    ax.set_title("Single-chart residual AUC by conditioned layer")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "single_layer_auc.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_hsic_permutation(target, hsic_result):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(
        hsic_result["nulls"],
        bins=30,
        color="lightgray",
        edgecolor="gray",
        label="permutation null",
    )
    ax.axvline(
        hsic_result["observed"],
        color="tomato",
        linewidth=2,
        label=f"observed = {hsic_result['observed']:.4f}",
    )
    ax.set_title(f"HSIC(joint residual, label) - target {target}\n"
                 f"p = {hsic_result['p']:.3f}")
    ax.set_xlabel("HSIC value")
    ax.set_ylabel("permutation count")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / f"hsic_perm_{target}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_chart_coefficients(chart_norms):
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(LAYERS))
    width = 0.22
    for i, target in enumerate(TARGETS):
        ys = [chart_norms[target][layer] for layer in LAYERS]
        ax.bar(x + (i - 1) * width, ys, width, label=f"n={target}")
    ax.set_xticks(x)
    ax.set_xticklabels([str(layer) for layer in LAYERS])
    ax.set_xlabel("joint chart coordinate layer")
    ax.set_ylabel("||B_layer||")
    ax.set_title("Joint residualizer coefficient norms")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "chart_coefficients.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(per_target, auc_single_by_target, chart_norms, aggregate,
                 probe_meta):
    lines = [
        "Exp 25 - Multi-layer Realized-topology Gate",
        "=" * 72,
        "",
        f"Reference: n = {REFERENCE}",
        f"Targets:   {TARGETS}",
        f"Layers:    {LAYERS}",
        f"Calibration templates: {len(CALIBRATION_TEMPLATES)}",
        f"Probe templates:       {len(PROBE_TEMPLATES)}",
        f"CV folds: {N_CV_FOLDS} (GroupKFold over templates)",
        f"HSIC permutations: {probe_meta['hsic_perm']}",
        "",
        "Pre-registered aggregate support:",
        f"  PASS     >=2 targets meet AUC_joint <= {PASS_AUC_JOINT}, "
        f"joint beats best single by >= {PASS_JOINT_VS_SINGLE}, "
        f"full-to-joint drop >= {PASS_DELTA_FULL}, and HSIC p >= {PASS_HSIC_P}",
        f"  PARTIAL  joint conditioning improves but does not close the gate",
        f"  FAIL     joint conditioning adds little or residual AUC remains high",
        "",
        f"AGGREGATE OUTCOME: {aggregate}",
        "",
    ]

    for s in per_target:
        target = s["target"]
        lines.append(f"\n### target = {target}")
        lines.append(f"  AUC(full residual):       {s['auc_full']:.3f}")
        lines.append(
            f"  AUC(best single chart):   {s['auc_best_single']:.3f} "
            f"(layer {s['best_single_layer']})"
        )
        lines.append(f"  AUC(joint chart):         {s['auc_joint']:.3f}")
        lines.append(
            f"  joint improvement over best single: {s['joint_vs_single']:+.3f}"
        )
        lines.append(f"  full-to-joint AUC drop:   {s['delta_full']:+.3f}")
        lines.append(
            f"  HSIC joint residual:      {s['hsic_joint_observed']:.5f}"
        )
        lines.append(f"  HSIC p:                   {s['hsic_joint_p']:.3f}")
        lines.append(f"  outcome:                  {s['outcome']}")
        lines.append("")
        lines.append("  single-chart residual AUC by layer:")
        for layer, auc in auc_single_by_target[target].items():
            lines.append(f"    layer {layer}: {auc:.3f}")
        lines.append("")
        lines.append("  joint residualizer coefficient norms:")
        for layer, norm in chart_norms[target].items():
            lines.append(f"    layer {layer}: {norm:.3f}")

    out = RESULTS_DIR / "gate_report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")

    summary = {
        "aggregate": aggregate,
        "per_target": per_target,
        "single_layer_auc": {
            str(target): {str(layer): float(auc)
                          for layer, auc in by_layer.items()}
            for target, by_layer in auc_single_by_target.items()
        },
        "chart_coefficient_norms": {
            str(target): {str(layer): float(norm)
                          for layer, norm in by_layer.items()}
            for target, by_layer in chart_norms.items()
        },
        "probe_meta": probe_meta,
        "thresholds": {
            "pass_auc_joint": PASS_AUC_JOINT,
            "pass_joint_vs_single": PASS_JOINT_VS_SINGLE,
            "pass_delta_full": PASS_DELTA_FULL,
            "pass_hsic_p": PASS_HSIC_P,
            "partial_auc_joint": PARTIAL_AUC_JOINT,
            "partial_joint_vs_single": PARTIAL_JOINT_VS_SINGLE,
        },
    }
    (RESULTS_DIR / "gate_summary.json").write_text(
        json.dumps(summary, indent=2),
    )
    print("Summary JSON: gate_summary.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    model = load_model()

    per_target = []
    auc_single_by_target = {}
    chart_norms = {}

    for target in TARGETS:
        print(f"\n=== target = {target} ===")
        print("  collecting calibration residuals...")
        R_cal_t, R_cal_r, shared_cal = paired_multilayer_residuals(
            model, target, REFERENCE, CALIBRATION_TEMPLATES,
        )
        print(f"    calibration pairs: {len(shared_cal)}")

        print("  extracting layer-local chart directions...")
        directions, mu_ref = extract_layer_directions(R_cal_t, R_cal_r)

        print("  collecting probe residuals...")
        R_probe_t, R_probe_r, shared_probe = paired_multilayer_residuals(
            model, target, REFERENCE, PROBE_TEMPLATES,
        )
        print(f"    probe pairs: {len(shared_probe)}")

        surfaces = prepare_conditioned_surfaces(
            R_cal_t, R_cal_r, R_probe_t, R_probe_r, directions, mu_ref,
        )
        n_probe = R_probe_t.shape[0]
        y = np.concatenate([
            np.ones(n_probe, dtype=int),
            np.zeros(n_probe, dtype=int),
        ])
        groups = np.concatenate([np.arange(n_probe), np.arange(n_probe)])

        print("  CV logistic probe on full residual...")
        aucs_full, auc_full = probe_auc_cv(surfaces["X_full"], y, groups)
        print(f"    folds: {[f'{a:.3f}' for a in aucs_full]}  "
              f"mean = {auc_full:.3f}")

        auc_single = {}
        for layer, X_single in surfaces["single_surfaces"].items():
            print(f"  CV logistic probe after single-chart conditioning L={layer}...")
            aucs_s, auc_s = probe_auc_cv(X_single, y, groups)
            auc_single[layer] = auc_s
            print(f"    folds: {[f'{a:.3f}' for a in aucs_s]}  "
                  f"mean = {auc_s:.3f}")

        print("  CV logistic probe after joint-chart conditioning...")
        aucs_joint, auc_joint = probe_auc_cv(surfaces["X_joint"], y, groups)
        print(f"    folds: {[f'{a:.3f}' for a in aucs_joint]}  "
              f"mean = {auc_joint:.3f}")

        print("  HSIC on joint-chart residual...")
        hsic_joint = hsic_permutation(
            surfaces["X_joint"], y, n_perm=args.hsic_perm,
        )
        print(f"    observed = {hsic_joint['observed']:.5f}  "
              f"p = {hsic_joint['p']:.3f}")
        plot_hsic_permutation(target, hsic_joint)

        s = score_target(target, auc_full, auc_single, auc_joint, hsic_joint)
        print(f"  outcome: {s['outcome']}")
        per_target.append(s)
        auc_single_by_target[target] = auc_single

        beta_joint = surfaces["beta_joint"]
        # beta row 0 is intercept; row i+1 corresponds to LAYERS[i].
        chart_norms[target] = {
            layer: float(np.linalg.norm(beta_joint[i + 1]))
            for i, layer in enumerate(LAYERS)
        }

    aggregate = aggregate_outcome(per_target)
    print(f"\n=== AGGREGATE OUTCOME: {aggregate} ===")

    plot_auc_comparison(per_target, auc_single_by_target)
    plot_chart_coefficients(chart_norms)

    probe_meta = {
        "calibration_templates": CALIBRATION_TEMPLATES,
        "probe_templates": PROBE_TEMPLATES,
        "hsic_perm": args.hsic_perm,
        "ridge_lambda": RIDGE_LAMBDA,
        "layers": LAYERS,
    }
    write_report(
        per_target,
        auc_single_by_target,
        chart_norms,
        aggregate,
        probe_meta,
    )

    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
