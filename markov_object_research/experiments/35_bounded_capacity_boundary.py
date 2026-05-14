"""
Experiment 35: Bounded-Capacity Level-Set Fitting

A Markov object's image under K is a level set lambda_T(s) = 0 on joint state.
Whether this level set exists *as a real object* — not just as the decision
boundary of an unbounded probe — is determined by whether a capacity-budgeted
estimator can recover it accurately.

Joint state:  s = concat of residuals at layers {2, 4, 6, 8, 10} at the
              target token position. Dim = 5 * 768 = 3840.

Embedding-stripping (per exp 33): each layer's residual is replaced by its
component perpendicular to e_emb^(L) computed on the neutral-template pool.
This forces the boundary fit to use only the learned-residue signal.

Pre-registered thresholds (per design doc 35.4):
    PASS     hidden width h <= 64 reaches >= 90% accuracy on stripped s
    PARTIAL  h in [256, 1024] required for >= 90%
    FAIL     only unbounded capacity works

Outputs:
    results/35_bounded_capacity_boundary/
        report.txt
        summary.json
        capacity_accuracy_curve.png
        brier_calibration.png
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

RESULTS_DIR = Path(__file__).parent.parent / "results" / "35_bounded_capacity_boundary"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYERS = [2, 4, 6, 8, 10]

REFERENCE = 5
TARGETS = [999, 666, 137]

# Same template pools as exp 33
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

CAPACITY_LADDER = [
    ("linear", 0),
    ("mlp_h16",   16),
    ("mlp_h64",   64),
    ("mlp_h256",  256),
    ("mlp_h1024", 1024),
]


# ---------------------------------------------------------------------------
# Model + capture
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
    """Return dict layer -> resid vector. One forward pass."""
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
    """Return (X (k, sum d_per_layer), used_templates) where each row is the
    concat of residuals across `layers` at the n-token position."""
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


# ---------------------------------------------------------------------------
# Embedding-stripping (per exp 33 protocol)
# ---------------------------------------------------------------------------

def compute_neutral_directions(model, target, reference, layers):
    """Return dict layer -> e_T^(L), the neutral-pool mean-diff direction."""
    Rt, used_t = collect_joint_states(model, target,    NEUTRAL_TEMPLATES, layers)
    Rr, used_r = collect_joint_states(model, reference, NEUTRAL_TEMPLATES, layers)
    if Rt is None or Rr is None:
        return None
    shared = [t for t in used_t if t in used_r]
    ti = [used_t.index(t) for t in shared]
    ri = [used_r.index(t) for t in shared]
    Rts = Rt[ti]; Rrs = Rr[ri]
    # Joint diff = concat of per-layer diffs
    e_joint = Rts.mean(0) - Rrs.mean(0)
    return e_joint, len(shared)


def strip_along(s, e):
    """Project out e from s. s: (N, D); e: (D,). Returns s perpendicular to e."""
    e_norm2 = (e * e).sum()
    if e_norm2.item() < 1e-12:
        return s.clone()
    proj = (s @ e) / e_norm2  # (N,)
    return s - proj.unsqueeze(1) * e.unsqueeze(0)


# ---------------------------------------------------------------------------
# MLP probe
# ---------------------------------------------------------------------------

class MLPProbe(nn.Module):
    def __init__(self, d_in, h):
        super().__init__()
        if h == 0:
            self.net = nn.Linear(d_in, 1)
        else:
            self.net = nn.Sequential(
                nn.Linear(d_in, h),
                nn.GELU(),
                nn.Linear(h, 1),
            )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def fit_probe(X_tr, y_tr, h, n_iters=400, lr=1e-2, weight_decay=1e-3):
    d_in = X_tr.shape[1]
    model = MLPProbe(d_in, h)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    bce = nn.BCEWithLogitsLoss()
    for _ in range(n_iters):
        opt.zero_grad()
        logits = model(X_tr)
        loss = bce(logits, y_tr)
        loss.backward()
        opt.step()
    return model


def evaluate_probe(model, X, y):
    model.eval()
    with torch.no_grad():
        logits = model(X)
        probs = torch.sigmoid(logits)
        pred = (probs >= 0.5).float()
        acc = float((pred == y).float().mean().item())
        brier = float(((probs - y) ** 2).mean().item())
    return acc, brier


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_target(model, target, reference, strip_embedding=True):
    print(f"\n=== target={target}  reference={reference}  "
          f"strip_emb={strip_embedding} ===")
    layers = PROBE_LAYERS
    Xt, used_t = collect_joint_states(model, target,    DIVERSE_TEMPLATES, layers)
    Xr, used_r = collect_joint_states(model, reference, DIVERSE_TEMPLATES, layers)
    if Xt is None or Xr is None:
        print("  no usable templates — skip")
        return None

    print(f"  joint state dim = {Xt.shape[1]}, "
          f"n_target={Xt.shape[0]}, n_ref={Xr.shape[0]}")

    e_joint = None
    if strip_embedding:
        e_joint, n_neu = compute_neutral_directions(model, target, reference, layers)
        if e_joint is None:
            print("  failed to compute embedding direction — skip stripping")
        else:
            print(f"  stripping embedding contrast (computed on {n_neu} neutral)")
            Xt_full = Xt.clone()
            Xr_full = Xr.clone()
            Xt = strip_along(Xt, e_joint)
            Xr = strip_along(Xr, e_joint)
            print(f"  pre-strip ||Xt.mean - Xr.mean||  = "
                  f"{(Xt_full.mean(0) - Xr_full.mean(0)).norm().item():.3f}")
            print(f"  post-strip ||Xt.mean - Xr.mean|| = "
                  f"{(Xt.mean(0) - Xr.mean(0)).norm().item():.3f}")

    # Build labelled dataset
    X = torch.cat([Xt, Xr], dim=0)
    y = torch.cat([torch.ones(len(Xt)), torch.zeros(len(Xr))])
    groups = used_t + used_r  # group by template for GroupKFold

    # Standardize features (helps optimization)
    mu = X.mean(0); sd = X.std(0); sd = torch.where(sd > 1e-6, sd, torch.ones_like(sd))
    X = (X - mu) / sd

    results_per_h = {}
    n_splits = min(5, len(set(groups)))
    gkf = GroupKFold(n_splits=n_splits)
    fold_indices = list(gkf.split(X.numpy(), y.numpy(), groups=groups))

    for label, h in CAPACITY_LADDER:
        accs, briers = [], []
        for fold, (tr_idx, te_idx) in enumerate(fold_indices):
            X_tr = X[tr_idx]; y_tr = y[tr_idx]
            X_te = X[te_idx]; y_te = y[te_idx]
            probe = fit_probe(X_tr, y_tr, h, n_iters=400, lr=1e-2, weight_decay=1e-3)
            acc, brier = evaluate_probe(probe, X_te, y_te)
            accs.append(acc); briers.append(brier)
        results_per_h[label] = {
            "h": h,
            "mean_acc":   float(np.mean(accs)),
            "std_acc":    float(np.std(accs)),
            "mean_brier": float(np.mean(briers)),
            "std_brier":  float(np.std(briers)),
            "fold_accs":  accs,
        }
        print(f"  {label:<11s}  acc={np.mean(accs):.3f} +/- {np.std(accs):.3f}  "
              f"brier={np.mean(briers):.3f}")

    # Capacity-to-90%
    cap_to_90 = None
    for label, h in CAPACITY_LADDER:
        if results_per_h[label]["mean_acc"] >= 0.90:
            cap_to_90 = label
            break

    # Refit the best probe on all data and save it (for exp 37).
    best_label = cap_to_90 or CAPACITY_LADDER[-1][0]
    best_h = dict(CAPACITY_LADDER)[best_label]
    best_probe = fit_probe(X, y, best_h, n_iters=600, lr=1e-2, weight_decay=1e-3)
    if strip_embedding and e_joint is not None:
        ckpt_path = RESULTS_DIR / f"probe_target{target}_stripped.pt"
        torch.save({
            "state_dict": best_probe.state_dict(),
            "h": best_h,
            "label": best_label,
            "feature_mu": mu,
            "feature_sd": sd,
            "stripping_direction": e_joint,
            "probe_layers": PROBE_LAYERS,
            "target": target,
            "reference": reference,
        }, ckpt_path)
        print(f"  saved probe -> {ckpt_path.name}")

    return {
        "joint_dim": int(Xt.shape[1]),
        "n_target":  int(Xt.shape[0]),
        "n_ref":     int(Xr.shape[0]),
        "results":   results_per_h,
        "cap_to_90_acc": cap_to_90,
        "best_label_saved": best_label if strip_embedding else None,
        "stripped_embedding": strip_embedding,
    }


def classify_verdict(stripped_results):
    """PASS if h<=64 reaches 90% accuracy across all targets;
       PARTIAL if h<=1024; FAIL otherwise."""
    if not stripped_results:
        return {"verdict": "UNKNOWN"}
    pass_64, partial_1024 = True, True
    for target, e in stripped_results.items():
        if e is None:
            return {"verdict": "INCOMPLETE"}
        cap = e.get("cap_to_90_acc")
        if cap is None or cap not in {"linear", "mlp_h16", "mlp_h64",
                                       "mlp_h256", "mlp_h1024"}:
            partial_1024 = False
            pass_64 = False
            continue
        if cap not in {"linear", "mlp_h16", "mlp_h64"}:
            pass_64 = False
        if cap not in {"linear", "mlp_h16", "mlp_h64", "mlp_h256", "mlp_h1024"}:
            partial_1024 = False
    if pass_64:
        v = "PASS"
    elif partial_1024:
        v = "PARTIAL"
    else:
        v = "FAIL"
    return {"verdict": v}


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_capacity_curves(stripped, raw):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, results, title in [(axes[0], stripped, "embedding-stripped"),
                                (axes[1], raw,      "raw joint state")]:
        for target, e in results.items():
            if e is None:
                continue
            xs = list(range(len(CAPACITY_LADDER)))
            ys = [e["results"][label]["mean_acc"] for label, _ in CAPACITY_LADDER]
            errs = [e["results"][label]["std_acc"] for label, _ in CAPACITY_LADDER]
            ax.errorbar(xs, ys, yerr=errs, marker="o", linewidth=2, capsize=3,
                        label=f"target={target}")
        ax.axhline(0.5, color="gray", linewidth=0.5)
        ax.axhline(0.9, color="green", linestyle="--", alpha=0.5, label="90%")
        ax.set_xticks(range(len(CAPACITY_LADDER)))
        ax.set_xticklabels([lbl for lbl, _ in CAPACITY_LADDER], rotation=30)
        ax.set_xlabel("capacity")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("held-out accuracy (GroupKFold by template)")
    axes[0].legend(loc="best", fontsize=9)
    fig.suptitle("Capacity-accuracy curve: stripped vs raw joint state")
    fig.tight_layout()
    out = RESULTS_DIR / "capacity_accuracy_curve.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_brier(stripped, raw):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, results, title in [(axes[0], stripped, "embedding-stripped"),
                                (axes[1], raw,      "raw joint state")]:
        for target, e in results.items():
            if e is None:
                continue
            xs = list(range(len(CAPACITY_LADDER)))
            ys = [e["results"][label]["mean_brier"] for label, _ in CAPACITY_LADDER]
            ax.plot(xs, ys, marker="o", linewidth=2, label=f"target={target}")
        ax.axhline(0.25, color="gray", linewidth=0.5)
        ax.set_xticks(range(len(CAPACITY_LADDER)))
        ax.set_xticklabels([lbl for lbl, _ in CAPACITY_LADDER], rotation=30)
        ax.set_xlabel("capacity")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("Brier score (lower = better calibrated)")
    axes[0].legend(loc="best", fontsize=9)
    fig.suptitle("Calibration: stripped vs raw joint state")
    fig.tight_layout()
    out = RESULTS_DIR / "brier_calibration.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(stripped, raw, stripped_verdict, raw_verdict):
    lines = ["Exp 35 - Bounded-Capacity Level-Set Fitting", "=" * 70, ""]
    lines.append(f"Targets:   {TARGETS}")
    lines.append(f"Reference: n = {REFERENCE}")
    lines.append(f"Probe layers (joint state): {PROBE_LAYERS}")
    lines.append(f"Capacity ladder: {[lbl for lbl, _ in CAPACITY_LADDER]}")
    lines.append("")
    lines.append("Pre-registered outcome rules (averaged over targets, on stripped state):")
    lines.append("  PASS     hidden width h <= 64 reaches >= 90% accuracy")
    lines.append("  PARTIAL  h in [256, 1024] required")
    lines.append("  FAIL     only unbounded capacity works")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME on STRIPPED joint state: {stripped_verdict['verdict']}")
    lines.append(f"AGGREGATE OUTCOME on RAW      joint state: {raw_verdict['verdict']}")
    lines.append("")

    for label, results in [("STRIPPED", stripped), ("RAW", raw)]:
        lines.append(f"\n--- {label} joint state ---")
        for target in TARGETS:
            e = results.get(target)
            if e is None:
                lines.append(f"\ntarget={target}: no results")
                continue
            lines.append(f"\ntarget={target}  cap_to_90_acc={e['cap_to_90_acc']}")
            lines.append(f"  joint_dim={e['joint_dim']} n_t={e['n_target']} n_r={e['n_ref']}")
            for cap_lbl, _ in CAPACITY_LADDER:
                r = e["results"][cap_lbl]
                lines.append(f"    {cap_lbl:<11s}  acc={r['mean_acc']:.3f} +/- "
                             f"{r['std_acc']:.3f}  brier={r['mean_brier']:.3f}")

    out = RESULTS_DIR / "report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = load_model()
    print("\n========== STRIPPED joint state ==========")
    stripped = {}
    for t in TARGETS:
        stripped[t] = run_target(model, t, REFERENCE, strip_embedding=True)
    print("\n========== RAW joint state (control) ==========")
    raw = {}
    for t in TARGETS:
        raw[t] = run_target(model, t, REFERENCE, strip_embedding=False)

    sv = classify_verdict(stripped)
    rv = classify_verdict(raw)
    print(f"\nVerdict (stripped): {sv['verdict']}")
    print(f"Verdict (raw):      {rv['verdict']}")

    plot_capacity_curves(stripped, raw)
    plot_brier(stripped, raw)
    write_report(stripped, raw, sv, rv)

    summary = {
        "design": "exp 35: bounded-capacity level-set fitting",
        "probe_layers": PROBE_LAYERS,
        "targets": TARGETS,
        "reference": REFERENCE,
        "capacity_ladder": [{"label": lbl, "h": h} for lbl, h in CAPACITY_LADDER],
        "stripped": {str(t): e for t, e in stripped.items()},
        "raw":      {str(t): e for t, e in raw.items()},
        "verdict_stripped": sv,
        "verdict_raw":      rv,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
