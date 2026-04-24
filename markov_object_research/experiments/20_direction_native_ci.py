"""
Experiment 20: Direction-native Conditional Independence
                 (The Promotion Gate)

Given the rank-k* identity subspace extracted in exp 19, test whether
the residual component orthogonal to that subspace is conditionally
independent of target identity. This is the named promotion gate: a
pass moves the Markov-object construct from candidate to established
at the representation depth tested.

Protocol:
  1. Load exp 19's rank-k* projector per target.
  2. Collect residuals at held-out positions for (target, reference).
  3. For each residual r, compute r_perp = r − P_k(r − μ_null).
  4. Train a cross-validated logistic probe on r_perp → target-vs-ref
     label. Report mean AUC.
  5. Train the same probe on full r. Report ΔAUC.
  6. HSIC independence between r_perp and label with a permutation
     null (secondary test).

Pre-registered expectation:
  AUC(r_perp) ∈ [0.47, 0.53] over 5-fold CV
  ΔAUC = AUC(r) − AUC(r_perp) ≥ 0.20
  HSIC(r_perp, label) not significant at p > 0.05

Outcome interpretation:
  PASS     AUC(r_perp) ∈ [0.47, 0.53] AND HSIC n.s.
           → Construct promoted to established at this rank & layer.
  PARTIAL  AUC(r_perp) ∈ [0.53, 0.60], or HSIC p ∈ [0.01, 0.05]
           → Residual still carries some identity info; not a formal
             blanket but near one. Publish cuts with a leak tag.
  FAIL     AUC(r_perp) > 0.60 OR HSIC highly significant
           → Construct is not a formal blanket at rank k* in the
             representation depth tested.
             Candidate status continues; revise §15.1 and method's
             epistemic-status subsection.

Note on estimator validity: a probe-based test gives a lower bound on
mutual information. A probe that can't predict establishes that
*this probe class* finds no signal. HSIC with a Gaussian kernel
complements with a non-parametric independence measure. Neither is a
formal CI proof, but their joint result is the best practical proxy
at residual-space dimensionality.
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DEFAULT_PROBE_LAYER = 8


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the direction-native CI gate at a chosen probe layer.",
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

RESULTS_19_ROOT = Path(__file__).parent.parent / "results" / "19_rank_k_saturation"
RESULTS_19_DIR = (RESULTS_19_ROOT if PROBE_LAYER == DEFAULT_PROBE_LAYER
                  else RESULTS_19_ROOT / f"layer_{PROBE_LAYER}")
RESULTS_ROOT = Path(__file__).parent.parent / "results" / "20_direction_native_ci"
RESULTS_DIR = (RESULTS_ROOT if PROBE_LAYER == DEFAULT_PROBE_LAYER
               else RESULTS_ROOT / f"layer_{PROBE_LAYER}")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE = 5
TARGETS = [999, 666, 137]

# A larger template pool than exp 18/19, so the probe has enough
# samples for meaningful CV. First 20 templates overlap with exp 19's
# training templates for direction extraction; we use only templates
# 20+ for the probe to avoid leakage between direction-fitting and
# probe-fitting.
TEMPLATE_POOL = [
    # --- overlap with exp 19 TRAIN (not used for probe) ---
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
    # --- exp 19 HELDOUT (ok to reuse for probe; disjoint from extraction) ---
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
    # --- fresh eval templates (exp 20 only) ---
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

# Templates used for probe training / CV. 30 non-direction-extraction ones.
PROBE_TEMPLATES = TEMPLATE_POOL[20:]

N_CV_FOLDS = 5
HSIC_N_PERM = 200
RNG_SEED = 42

PASS_AUC_LO  = 0.47
PASS_AUC_HI  = 0.53
PARTIAL_AUC_HI = 0.60
DELTA_AUC_PASS = 0.20


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


# ---------------------------------------------------------------------------
# Load exp 19 projector
# ---------------------------------------------------------------------------

def load_projector(target, method="meandiff"):
    path = RESULTS_19_DIR / f"projector_{method}_{target}.npz"
    if not path.exists():
        raise FileNotFoundError(
            f"Exp 19 projector not found: {path}\n"
            "Run 19_rank_k_saturation.py first."
        )
    z = np.load(path, allow_pickle=True)
    return {
        "directions": z["directions"],      # (k_max, d_model)
        "mu_null":    z["mu_null"],         # (d_model,)
        "k_star":     int(z["k_star"]),
        "target":     int(z["target"]),
        "method":     str(z["method"]),
    }


def project_out_identity(R, directions, k, mu_null):
    """
    r_perp = r − P_k (r − μ_null)
    where P_k = Σ_{i<k} d_i d_iᵀ for orthonormal d_i.

    R: (n, d_model) tensor or np.ndarray.
    """
    import torch
    if isinstance(R, np.ndarray):
        R_t = torch.tensor(R, dtype=torch.float32)
    else:
        R_t = R.float()
    D = torch.tensor(directions[:k], dtype=torch.float32)     # (k, d_model)
    mu = torch.tensor(mu_null, dtype=torch.float32)
    diff = R_t - mu                                           # (n, d_model)
    # projection: for each row, project onto span(D)
    coeffs = diff @ D.t()                                     # (n, k)
    proj = coeffs @ D                                         # (n, d_model)
    R_perp = R_t - proj
    return R_perp


# ---------------------------------------------------------------------------
# Probe: cross-validated logistic regression
# ---------------------------------------------------------------------------

def probe_auc_cv(X, y, groups, n_splits=N_CV_FOLDS, C=0.1, seed=RNG_SEED):
    """
    X: (n, d) features
    y: (n,) binary labels (0/1)
    groups: (n,) template ids, so each fold holds out whole templates
    Returns: per-fold AUC list, mean AUC.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    gkf = GroupKFold(n_splits=n_splits)
    aucs = []
    for fold, (train_idx, test_idx) in enumerate(
            gkf.split(X, y, groups=groups)):
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_idx])
        X_te = scaler.transform(X[test_idx])
        clf = LogisticRegression(
            C=C, penalty="l2", solver="lbfgs", max_iter=2000,
            random_state=seed,
        )
        clf.fit(X_tr, y[train_idx])
        scores = clf.decision_function(X_te)
        try:
            auc = roc_auc_score(y[test_idx], scores)
        except ValueError:
            # single-class in test fold
            auc = 0.5
        aucs.append(auc)
    return aucs, float(np.mean(aucs))


# ---------------------------------------------------------------------------
# HSIC
# ---------------------------------------------------------------------------

def gauss_kernel(X, sigma=None):
    """Gaussian kernel with median-heuristic bandwidth."""
    sq = np.sum(X ** 2, axis=1, keepdims=True)
    D2 = sq + sq.T - 2 * X @ X.T
    D2 = np.maximum(D2, 0)
    if sigma is None:
        sigma = np.sqrt(np.median(D2[D2 > 0])) if (D2 > 0).any() else 1.0
    sigma = max(sigma, 1e-6)
    return np.exp(-D2 / (2 * sigma ** 2))


def label_kernel(y):
    """Kernel L[i,j] = 1 if y_i == y_j else 0. Centered automatically by H."""
    y = y.reshape(-1, 1)
    return (y == y.T).astype(np.float64)


def hsic(X, y):
    """Biased HSIC with Gaussian kernel on X and label kernel on y."""
    n = len(y)
    K = gauss_kernel(X)
    L = label_kernel(y)
    H = np.eye(n) - np.ones((n, n)) / n
    Kc = H @ K @ H
    return float(np.trace(Kc @ L) / max((n - 1) ** 2, 1))


def hsic_permutation_p(X, y, n_perm=HSIC_N_PERM, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    observed = hsic(X, y)
    count_ge = 0
    nulls = []
    for _ in range(n_perm):
        y_perm = rng.permutation(y)
        null_val = hsic(X, y_perm)
        nulls.append(null_val)
        if null_val >= observed:
            count_ge += 1
    p = (count_ge + 1) / (n_perm + 1)
    return {
        "observed": observed,
        "p":        float(p),
        "null_mean": float(np.mean(nulls)),
        "null_std":  float(np.std(nulls)),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_target(target, auc_perp_mean, auc_full_mean, hsic_result):
    delta_auc = auc_full_mean - auc_perp_mean

    if (PASS_AUC_LO <= auc_perp_mean <= PASS_AUC_HI
            and hsic_result["p"] >= 0.05):
        outcome = "PASS"
    elif (auc_perp_mean <= PARTIAL_AUC_HI
          or 0.01 <= hsic_result["p"] < 0.05):
        outcome = "PARTIAL"
    else:
        outcome = "FAIL"

    return {
        "target":         target,
        "auc_perp":       auc_perp_mean,
        "auc_full":       auc_full_mean,
        "delta_auc":      delta_auc,
        "hsic_observed":  hsic_result["observed"],
        "hsic_p":         hsic_result["p"],
        "outcome":        outcome,
    }


def aggregate_outcome(per_target):
    outcomes = [s["outcome"] for s in per_target]
    if all(o == "PASS" for o in outcomes):
        return "PASS"
    if any(o == "FAIL" for o in outcomes):
        return "FAIL"
    return "PARTIAL"


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_auc_bars(per_target):
    targets = [s["target"] for s in per_target]
    auc_perp = [s["auc_perp"] for s in per_target]
    auc_full = [s["auc_full"] for s in per_target]
    x = np.arange(len(targets))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width/2, auc_full, width, color="tomato",
           label="AUC(full r)")
    ax.bar(x + width/2, auc_perp, width, color="steelblue",
           label="AUC(r_perp)")
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5,
               label="chance")
    ax.axhspan(PASS_AUC_LO, PASS_AUC_HI, color="green", alpha=0.15,
               label=f"pass band [{PASS_AUC_LO}, {PASS_AUC_HI}]")
    ax.axhline(PARTIAL_AUC_HI, color="orange", linestyle=":",
               label=f"partial ceiling ({PARTIAL_AUC_HI})")
    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in targets])
    ax.set_ylabel("AUC (target vs reference probe)")
    ax.set_ylim(0.4, 1.0)
    ax.set_title("Probe AUC — before and after identity-subspace projection")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "auc_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_hsic_permutation(target, hsic_result, nulls=None):
    fig, ax = plt.subplots(figsize=(7, 4))
    if nulls is not None:
        ax.hist(nulls, bins=30, color="lightgray", edgecolor="gray",
                label="permutation null")
    ax.axvline(hsic_result["observed"], color="tomato", linewidth=2,
               label=f"observed = {hsic_result['observed']:.4f}")
    ax.set_title(f"HSIC(r_perp, label) — target {target}\n"
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


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(per_target_scores, aggregate, k_stars, probe_meta):
    lines = [
        f"Exp 20 — Direction-native Conditional Independence (The Gate)",
        f"              layer {PROBE_LAYER}",
        "=" * 72,
        "",
        f"Reference: n = {REFERENCE}",
        f"Targets:   {TARGETS}",
        f"Probe templates: {len(probe_meta['templates'])} "
            f"(disjoint from direction-extraction pool)",
        f"CV folds:  {N_CV_FOLDS}  (GroupKFold over templates)",
        f"HSIC permutations: {HSIC_N_PERM}",
        "",
        "Pre-registered outcome rules (per target):",
        f"  PASS     AUC(r_perp) ∈ [{PASS_AUC_LO}, {PASS_AUC_HI}]  "
            f"AND HSIC p ≥ 0.05",
        f"  PARTIAL  AUC(r_perp) ≤ {PARTIAL_AUC_HI}  OR HSIC p ∈ [0.01, 0.05]",
        f"  FAIL     AUC(r_perp) > {PARTIAL_AUC_HI}  OR HSIC highly significant",
        "",
        f"AGGREGATE OUTCOME: {aggregate}",
        "",
    ]

    for s in per_target_scores:
        lines.append(f"\n### target = {s['target']}  "
                     f"(k* = {k_stars[s['target']]})")
        lines.append(f"  AUC(full r):   {s['auc_full']:.3f}")
        lines.append(f"  AUC(r_perp):   {s['auc_perp']:.3f}")
        lines.append(f"  ΔAUC:          {s['delta_auc']:+.3f}   "
                     f"(pass needs ≥ {DELTA_AUC_PASS})")
        lines.append(f"  HSIC observed: {s['hsic_observed']:.5f}")
        lines.append(f"  HSIC p:        {s['hsic_p']:.3f}")
        lines.append(f"  outcome:       {s['outcome']}")

    out = RESULTS_DIR / "ci_report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")

    json_summary = {
        "aggregate":    aggregate,
        "per_target":   per_target_scores,
        "k_stars":      k_stars,
        "probe_meta":   probe_meta,
        "thresholds": {
            "pass_auc_lo":   PASS_AUC_LO,
            "pass_auc_hi":   PASS_AUC_HI,
            "partial_auc_hi": PARTIAL_AUC_HI,
            "delta_auc_pass": DELTA_AUC_PASS,
            "hsic_n_perm":    HSIC_N_PERM,
        },
    }
    (RESULTS_DIR / "ci_summary.json").write_text(
        json.dumps(json_summary, indent=2))
    print("Summary JSON: ci_summary.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import torch

    model = load_model()

    per_target_scores = []
    k_stars = {}
    probe_meta = {
        "templates":  PROBE_TEMPLATES,
        "n_templates": len(PROBE_TEMPLATES),
    }
    hsic_nulls_per_target = {}

    for target in TARGETS:
        print(f"\n=== target = {target} ===")

        projector_info = load_projector(target, method="meandiff")
        k_star = projector_info["k_star"]
        k_stars[target] = int(k_star)
        print(f"  loaded exp 19 projector: k* = {k_star}")

        print("  collecting probe residuals (target and reference)...")
        R_tgt, used_tgt = collect_residuals(model, target, PROBE_TEMPLATES)
        R_ref, used_ref = collect_residuals(model, REFERENCE, PROBE_TEMPLATES)
        shared = [t for t in used_tgt if t in used_ref]
        tgt_idx = [used_tgt.index(t) for t in shared]
        ref_idx = [used_ref.index(t) for t in shared]
        R_tgt_m = R_tgt[tgt_idx].float().cpu().numpy()
        R_ref_m = R_ref[ref_idx].float().cpu().numpy()
        print(f"  {len(shared)} paired probe residuals")

        X_full = np.concatenate([R_tgt_m, R_ref_m], axis=0)
        y      = np.concatenate([np.ones(len(R_tgt_m), dtype=int),
                                 np.zeros(len(R_ref_m), dtype=int)])
        groups = np.concatenate([np.arange(len(shared)),
                                 np.arange(len(shared))])  # pair-templates

        print("  projecting out identity subspace (P_k*)...")
        R_tgt_perp = project_out_identity(
            R_tgt_m, projector_info["directions"], k_star,
            projector_info["mu_null"],
        ).cpu().numpy()
        R_ref_perp = project_out_identity(
            R_ref_m, projector_info["directions"], k_star,
            projector_info["mu_null"],
        ).cpu().numpy()
        X_perp = np.concatenate([R_tgt_perp, R_ref_perp], axis=0)

        print("  CV logistic probe on full r...")
        aucs_full, auc_full = probe_auc_cv(X_full, y, groups)
        print(f"    folds: {[f'{a:.3f}' for a in aucs_full]}  "
              f"mean = {auc_full:.3f}")

        print("  CV logistic probe on r_perp...")
        aucs_perp, auc_perp = probe_auc_cv(X_perp, y, groups)
        print(f"    folds: {[f'{a:.3f}' for a in aucs_perp]}  "
              f"mean = {auc_perp:.3f}")

        print(f"  ΔAUC = {auc_full - auc_perp:+.3f}")

        print("  HSIC on r_perp (permutation null)...")
        # Cache nulls by running permutation manually so we can plot them.
        observed = hsic(X_perp, y)
        rng = np.random.default_rng(RNG_SEED)
        nulls = []
        for _ in range(HSIC_N_PERM):
            nulls.append(hsic(X_perp, rng.permutation(y)))
        nulls = np.array(nulls)
        p = ((nulls >= observed).sum() + 1) / (HSIC_N_PERM + 1)
        hsic_result = {
            "observed":  float(observed),
            "p":         float(p),
            "null_mean": float(nulls.mean()),
            "null_std":  float(nulls.std()),
        }
        hsic_nulls_per_target[target] = nulls
        print(f"    observed = {hsic_result['observed']:.5f}   "
              f"p = {hsic_result['p']:.3f}")

        s = score_target(target, auc_perp, auc_full, hsic_result)
        print(f"  outcome: {s['outcome']}")
        per_target_scores.append(s)

        plot_hsic_permutation(target, hsic_result, nulls=nulls)

    plot_auc_bars(per_target_scores)

    aggregate = aggregate_outcome(per_target_scores)
    print(f"\n=== AGGREGATE OUTCOME: {aggregate} ===")

    write_report(per_target_scores, aggregate, k_stars, probe_meta)

    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
