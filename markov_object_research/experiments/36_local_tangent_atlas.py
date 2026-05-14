"""
Experiment 36: Local-Tangent Atlas And Curl Test

The single most important experiment in the program. Per INV-11 the substrate
boundary projects through K to a possibly-nonlinear, possibly-fuzzy
hypersurface. Whether this hypersurface is *one global object* or merely a
collection of unrelated local effects is the operational question.

Operationalization:
    For each anchor joint-state s_i (a target sample), build a local
    neighborhood N(s_i) of its k nearest neighbors across all classes
    (target + reference battery). Compute a local mean-difference normal:
        n_i = centroid_target_in_N(s_i) - centroid_ref_in_N(s_i)
    Normalize.
    Test integrability:
      - pairwise cosine matrix of {n_i}; mean off-diagonal cosine
      - PC1 explained variance of {n_i}
      - mean angle between adjacent (geographic) normals
    Compare against null model (shuffled labels).

Pre-registered (per design doc 36.4):
    PASS     mean closure-error angle < 30 deg AND
             null-shuffle mean angle > 60 deg AND
             PC1 explained variance >= 0.6
    PARTIAL  PC1 EV in [0.3, 0.6] (sectional gluing)
    FAIL     PC1 EV < 0.3 OR no separation from null

Outputs:
    results/36_local_tangent_atlas/
        report.txt
        summary.json
        normal_field_pca.png
        pairwise_cosine_dist.png
        local_accuracy_dist.png
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch

RESULTS_DIR = Path(__file__).parent.parent / "results" / "36_local_tangent_atlas"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYERS = [2, 4, 6, 8, 10]
TARGETS = [999, 666, 137]

# Reference battery (matches exp 34 generic null pool)
REFERENCE_BATTERY = [5, 2, 50, 250, 800, 41, 7, 11]

K_NBR = 20

# Same template pools as exps 33/35
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


# ---------------------------------------------------------------------------
# Model + capture (same conventions as exp 35)
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


def capture_resid_multi(model, text, pos, layers):
    tokens = model.to_tokens(text, prepend_bos=True)
    captured = {}

    def make_hook(L):
        def cap(value, hook):
            captured[L] = value[0, pos, :].detach().clone()
            return value
        return cap

    fwd_hooks = [(f"blocks.{L}.hook_resid_pre", make_hook(L)) for L in layers]
    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=fwd_hooks)
    return captured


def collect_joint_states(model, n, templates, layers):
    rows = []
    used = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        d = capture_resid_multi(model, text, pos, layers)
        if any(L not in d for L in layers):
            continue
        rows.append(torch.cat([d[L] for L in layers]).float())
        used.append(t)
    if not rows:
        return None, []
    return torch.stack(rows), used


def compute_neutral_direction(model, target, reference, layers):
    Rt, used_t = collect_joint_states(model, target,    NEUTRAL_TEMPLATES, layers)
    Rr, used_r = collect_joint_states(model, reference, NEUTRAL_TEMPLATES, layers)
    if Rt is None or Rr is None:
        return None
    shared = [t for t in used_t if t in used_r]
    ti = [used_t.index(t) for t in shared]
    ri = [used_r.index(t) for t in shared]
    return Rt[ti].mean(0) - Rr[ri].mean(0)


def strip_along(s, e):
    e_norm2 = (e * e).sum()
    if e_norm2.item() < 1e-12:
        return s.clone()
    proj = (s @ e) / e_norm2
    return s - proj.unsqueeze(1) * e.unsqueeze(0)


# ---------------------------------------------------------------------------
# Local-tangent atlas
# ---------------------------------------------------------------------------

def build_dataset(model, target, references, layers, strip_emb=True):
    """Return X (N, D), labels (N,) where 1=target, 0=reference; tags (N,) for
    template/source bookkeeping."""
    X_t, tmpls_t = collect_joint_states(model, target, DIVERSE_TEMPLATES, layers)
    X_list = [X_t]
    y_list = [torch.ones(len(X_t))]
    tag_list = [(target, t) for t in tmpls_t]
    for ref in references:
        X_r, tmpls_r = collect_joint_states(model, ref, DIVERSE_TEMPLATES, layers)
        if X_r is None:
            continue
        X_list.append(X_r)
        y_list.append(torch.zeros(len(X_r)))
        tag_list += [(ref, t) for t in tmpls_r]
    X = torch.cat(X_list, dim=0)
    y = torch.cat(y_list, dim=0)

    if strip_emb:
        # Use the first reference for the stripping direction (matches exp 33
        # convention which used n=5).
        e = compute_neutral_direction(model, target, references[0], layers)
        if e is not None:
            X = strip_along(X, e)

    return X, y, tag_list


def k_nearest(X, anchor_idxs, k):
    """For each anchor index, return indices of k nearest other points
    (excluding self)."""
    N = X.shape[0]
    # Standardize for distance computation
    Xn = X / (X.norm(dim=1, keepdim=True) + 1e-9)
    nn_idxs = []
    for i in anchor_idxs:
        sims = Xn @ Xn[i]
        sims[i] = -2.0
        top = torch.topk(sims, k=min(k, N - 1)).indices
        nn_idxs.append(top.tolist())
    return nn_idxs


def local_normals(X, y, anchor_idxs, k):
    """For each anchor, build neighborhood and compute centroid-difference normal.
       Returns: normals (M, D), local_acc list, anchor_classes list."""
    nn_lists = k_nearest(X, anchor_idxs, k)
    normals = []
    local_acc = []
    for ai, neighbors in zip(anchor_idxs, nn_lists):
        idxs = [ai] + neighbors
        Xn = X[idxs]; yn = y[idxs]
        if (yn == 1).sum() == 0 or (yn == 0).sum() == 0:
            continue
        c_t = Xn[yn == 1].mean(0)
        c_r = Xn[yn == 0].mean(0)
        n = c_t - c_r
        n = n / (n.norm() + 1e-9)
        normals.append(n)
        # Local accuracy of the centroid-diff classifier on its own neighborhood
        scores = (Xn - c_r) @ n - 0.5 * ((c_t - c_r) @ n)
        pred = (scores > 0).float()
        # Pred should be 1 for target, 0 for ref; align orientation
        if pred.eq(yn).float().mean() < 0.5:
            pred = 1.0 - pred
        local_acc.append(float(pred.eq(yn).float().mean().item()))
    return torch.stack(normals) if normals else None, local_acc


def normal_field_stats(N):
    """N: (M, D) tensor of unit normals.
    Returns dict with mean off-diag cosine, PC1 explained variance,
    angle distribution."""
    M = N.shape[0]
    # Pairwise cosine
    C = N @ N.T   # (M, M)
    mask = ~torch.eye(M, dtype=torch.bool)
    cos_offdiag = C[mask].numpy()
    # SVD for PC1 EV
    Nc = N - N.mean(0, keepdim=True)
    U, S, V = torch.linalg.svd(Nc, full_matrices=False)
    var_total = float((S * S).sum())
    var_pc1 = float((S[0] * S[0]).item())
    ev_pc1 = var_pc1 / max(var_total, 1e-12)
    # Pairwise angles in degrees (using full cosine including possible orientation flips)
    # We orient all normals to align with the global mean direction first.
    mean_dir = N.mean(0)
    mean_dir = mean_dir / (mean_dir.norm() + 1e-9)
    sign = torch.sign(N @ mean_dir)
    sign[sign == 0] = 1.0
    N_oriented = N * sign.unsqueeze(1)
    C2 = N_oriented @ N_oriented.T
    C2 = torch.clamp(C2, -1.0, 1.0)
    angles = torch.rad2deg(torch.arccos(C2[mask])).numpy()
    return {
        "mean_cos_offdiag":          float(cos_offdiag.mean()),
        "median_cos_offdiag":        float(np.median(cos_offdiag)),
        "mean_oriented_angle_deg":   float(angles.mean()),
        "median_oriented_angle_deg": float(np.median(angles)),
        "pc1_explained_var":         ev_pc1,
        "n_normals":                 M,
        "cos_offdiag":               cos_offdiag.tolist(),
        "angles_deg":                angles.tolist(),
    }


# ---------------------------------------------------------------------------
# Per-target run
# ---------------------------------------------------------------------------

def run_target(model, target):
    print(f"\n=== target={target} ===")
    layers = PROBE_LAYERS
    X, y, tags = build_dataset(model, target, REFERENCE_BATTERY, layers,
                                 strip_emb=True)
    print(f"  N={X.shape[0]}  joint_dim={X.shape[1]}  "
          f"n_target={int((y == 1).sum())}  n_ref={int((y == 0).sum())}")

    # Anchors: all target samples
    anchor_idxs = (y == 1).nonzero(as_tuple=True)[0].tolist()

    # Real labels
    N_real, acc_real = local_normals(X, y, anchor_idxs, K_NBR)
    if N_real is None:
        print("  no normals computed — skip")
        return None
    real_stats = normal_field_stats(N_real)
    real_stats["mean_local_acc"] = float(np.mean(acc_real))
    print(f"  real:  mean_cos={real_stats['mean_cos_offdiag']:+.3f}  "
          f"PC1_EV={real_stats['pc1_explained_var']:.3f}  "
          f"angle={real_stats['mean_oriented_angle_deg']:.1f}deg  "
          f"local_acc={real_stats['mean_local_acc']:.3f}")

    # Null: shuffle labels, refit
    g = torch.Generator().manual_seed(42)
    perm = torch.randperm(len(y), generator=g)
    y_shuf = y[perm]
    # Re-pick anchors as indices that are now labelled 1 (so neighborhood
    # building works the same)
    anchor_shuf = (y_shuf == 1).nonzero(as_tuple=True)[0].tolist()
    N_null, acc_null = local_normals(X, y_shuf, anchor_shuf, K_NBR)
    null_stats = normal_field_stats(N_null) if N_null is not None else None
    if null_stats is not None:
        null_stats["mean_local_acc"] = float(np.mean(acc_null))
        print(f"  null:  mean_cos={null_stats['mean_cos_offdiag']:+.3f}  "
              f"PC1_EV={null_stats['pc1_explained_var']:.3f}  "
              f"angle={null_stats['mean_oriented_angle_deg']:.1f}deg  "
              f"local_acc={null_stats['mean_local_acc']:.3f}")

    return {"real": real_stats, "null": null_stats}


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def classify_verdict(per_target):
    if not per_target:
        return {"verdict": "UNKNOWN"}
    pc1_evs = []
    angle_real = []
    angle_null = []
    for target, e in per_target.items():
        if e is None:
            continue
        pc1_evs.append(e["real"]["pc1_explained_var"])
        angle_real.append(e["real"]["mean_oriented_angle_deg"])
        if e.get("null"):
            angle_null.append(e["null"]["mean_oriented_angle_deg"])
    if not pc1_evs:
        return {"verdict": "INCOMPLETE"}
    mean_ev = float(np.mean(pc1_evs))
    mean_angle_real = float(np.mean(angle_real))
    mean_angle_null = float(np.mean(angle_null)) if angle_null else None
    sep = (mean_angle_null - mean_angle_real) if mean_angle_null else None
    if (mean_angle_real < 30.0 and mean_angle_null is not None
            and mean_angle_null > 60.0 and mean_ev >= 0.6):
        v = "PASS"
    elif mean_ev >= 0.3:
        v = "PARTIAL"
    else:
        v = "FAIL"
    return {
        "mean_pc1_ev":          mean_ev,
        "mean_angle_real_deg":  mean_angle_real,
        "mean_angle_null_deg":  mean_angle_null,
        "real_minus_null_deg":  -sep if sep is not None else None,
        "verdict":              v,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_pca_ev(per_target):
    fig, ax = plt.subplots(figsize=(7, 5))
    xs = list(per_target.keys())
    real = [per_target[t]["real"]["pc1_explained_var"] for t in xs]
    null = [per_target[t]["null"]["pc1_explained_var"] if per_target[t]["null"]
            else 0.0 for t in xs]
    x = np.arange(len(xs))
    ax.bar(x - 0.2, real, width=0.4, label="real labels",   color="steelblue")
    ax.bar(x + 0.2, null, width=0.4, label="shuffled null", color="lightgray")
    ax.axhline(0.6, color="green",  linestyle="--", alpha=0.5, label="PASS thr 0.6")
    ax.axhline(0.3, color="orange", linestyle="--", alpha=0.5, label="PARTIAL thr 0.3")
    ax.set_xticks(x); ax.set_xticklabels([str(t) for t in xs])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("PC1 explained variance of normal field")
    ax.set_title("Normal-field global alignment (real vs null)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "normal_field_pca.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_cosine_distributions(per_target):
    fig, axes = plt.subplots(1, len(per_target), figsize=(5 * len(per_target), 4),
                              sharey=True)
    if len(per_target) == 1:
        axes = [axes]
    for ax, (target, e) in zip(axes, per_target.items()):
        if e is None:
            continue
        ax.hist(e["real"]["cos_offdiag"], bins=40, alpha=0.6, label="real",
                color="steelblue", density=True)
        if e["null"]:
            ax.hist(e["null"]["cos_offdiag"], bins=40, alpha=0.6, label="null",
                    color="lightgray", density=True)
        ax.axvline(0, color="gray", linewidth=0.5)
        ax.set_xlim(-1, 1)
        ax.set_xlabel("cos(n_i, n_j)")
        ax.set_title(f"target={target}")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("density")
    axes[0].legend(loc="best", fontsize=9)
    fig.suptitle("Pairwise normal-cosine distribution (real vs shuffled)")
    fig.tight_layout()
    out = RESULTS_DIR / "pairwise_cosine_dist.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_local_accuracy(per_target):
    fig, ax = plt.subplots(figsize=(7, 5))
    xs = list(per_target.keys())
    real = [per_target[t]["real"]["mean_local_acc"] for t in xs]
    null = [per_target[t]["null"]["mean_local_acc"] if per_target[t]["null"]
            else 0.0 for t in xs]
    x = np.arange(len(xs))
    ax.bar(x - 0.2, real, width=0.4, label="real",   color="steelblue")
    ax.bar(x + 0.2, null, width=0.4, label="null",   color="lightgray")
    ax.axhline(0.5, color="gray", linewidth=0.5)
    ax.set_xticks(x); ax.set_xticklabels([str(t) for t in xs])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("local centroid-diff accuracy")
    ax.set_title("Local discriminator accuracy (real vs null)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "local_accuracy_dist.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(per_target, verdict):
    lines = ["Exp 36 - Local-Tangent Atlas And Curl Test", "=" * 70, ""]
    lines.append(f"Targets:           {TARGETS}")
    lines.append(f"Reference battery: {REFERENCE_BATTERY}")
    lines.append(f"Probe layers:      {PROBE_LAYERS}")
    lines.append(f"Neighbors per anchor (k): {K_NBR}")
    lines.append(f"Embedding-stripped joint state: yes (per exp 33 protocol)")
    lines.append("")
    lines.append("Pre-registered outcome rules (averaged over targets):")
    lines.append("  PASS     mean angle real < 30 deg AND null > 60 deg AND PC1 EV >= 0.6")
    lines.append("  PARTIAL  PC1 EV in [0.3, 0.6]")
    lines.append("  FAIL     PC1 EV < 0.3 or no real-vs-null separation")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict['verdict']}")
    lines.append(f"  mean PC1 explained variance:  {verdict['mean_pc1_ev']:.3f}")
    lines.append(f"  mean angle (real):  {verdict['mean_angle_real_deg']:.1f} deg")
    if verdict.get('mean_angle_null_deg'):
        lines.append(f"  mean angle (null):  {verdict['mean_angle_null_deg']:.1f} deg")
    lines.append("")
    for target in TARGETS:
        e = per_target.get(target)
        if e is None:
            lines.append(f"\ntarget={target}: skipped")
            continue
        lines.append(f"\n### target = {target}")
        lines.append("  REAL:")
        for k, v in e["real"].items():
            if k in ("cos_offdiag", "angles_deg"):
                continue
            lines.append(f"    {k:<32s} = {v}")
        if e.get("null"):
            lines.append("  NULL:")
            for k, v in e["null"].items():
                if k in ("cos_offdiag", "angles_deg"):
                    continue
                lines.append(f"    {k:<32s} = {v}")

    out = RESULTS_DIR / "report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = load_model()
    per_target = {}
    for t in TARGETS:
        per_target[t] = run_target(model, t)
    v = classify_verdict(per_target)
    print(f"\nVerdict: {v['verdict']}  PC1_EV={v['mean_pc1_ev']:.3f}  "
          f"angle_real={v['mean_angle_real_deg']:.1f}  "
          f"angle_null={v.get('mean_angle_null_deg')}")
    plot_pca_ev(per_target)
    plot_cosine_distributions(per_target)
    plot_local_accuracy(per_target)
    write_report(per_target, v)
    summary = {
        "design": "exp 36: local-tangent atlas + curl test",
        "k_nbr": K_NBR,
        "probe_layers": PROBE_LAYERS,
        "targets": TARGETS,
        "reference_battery": REFERENCE_BATTERY,
        "per_target": {str(t): e for t, e in per_target.items()},
        "verdict": v,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
