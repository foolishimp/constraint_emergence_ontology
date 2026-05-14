"""
Experiment 41: Dynamical Blanket — Identity-Direction Test (Llama-3 8B)

Per Hipolito et al. (2021) Eq. 2: a Markov blanket is a property of the
*equations of motion*, not of static state. A 4-way partition (mu, s, a, eta)
is a blanket iff intervening on eta leaves the mu-trajectory invariant.

For an LLM the layer-to-layer transition is the equation of motion. This
experiment tests the simplest concrete blanket hypothesis:

  mu = the embedding-stripped probed identity-direction n_T^L (1-D)
  e  = the embedding direction (already stripped, treated separately)
  eta = everything orthogonal to mu and e

Test:
  forward native: capture r at L+1..L+K, project onto n_T^L -> mu_native(k)
  intervene at L: replace eta-component with reference-prompt's eta
  forward intervened: capture mu_intervened(k)
  blanket score: mean |Delta_mu(k)| / mu_RMS  (lower = more blanket-like)

Pre-registered:
  PASS    mean |Delta_mu| / mu_RMS < 0.15  AND  random-baseline > 0.4
                                          AND  |Delta_eta|/eta_RMS > 0.5
  PARTIAL probed direction in [0.15, 0.4]; meaningfully better than random
  FAIL    probed direction approx random

Outputs:
  results/41_dynamical_blanket_identity/
    report.txt, summary.json
    mu_trajectory_disturbance.png
    eta_trajectory_disturbance.png
    per_layer_blanket_score.png
"""

import json, os, time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
import torch.nn as nn

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results" / "41_dynamical_blanket_identity"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "meta-llama/Meta-Llama-3-8B"
DEVICE     = "mps"
DTYPE      = torch.float16

BLANKET_LAYERS = [2, 8, 16, 24]
LOOKAHEAD_K    = 8

REFERENCE = 5
TARGETS = [999, 666, 137]

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


# ---------------------------------------------------------------------------
# Model + capture
# ---------------------------------------------------------------------------

def load_model():
    from transformer_lens import HookedTransformer
    print(f"Loading {MODEL_NAME} on {DEVICE} ({DTYPE})...")
    t0 = time.time()
    model = HookedTransformer.from_pretrained(MODEL_NAME, device=DEVICE,
                                                dtype=DTYPE)
    model.eval()
    print(f"  loaded in {time.time()-t0:.1f}s. n_layers={model.cfg.n_layers} "
          f"d_model={model.cfg.d_model}")
    return model


def last_token_of_span(model, text, span):
    start = text.find(span)
    if start < 0:
        return None
    end = start + len(span)
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    acc = 0
    for i, tok in enumerate(str_tokens):
        if i == 0 and tok in ("<|begin_of_text|>", "<|endoftext|>", ""):
            continue
        acc += len(tok)
        if acc >= end:
            return i
    return None


def capture_resid(model, text, pos, layer):
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    captured = {}
    def cap(value, hook):
        captured["r"] = value[0, pos, :].detach().clone().to("cpu").float()
        return value
    with torch.no_grad():
        model.run_with_hooks(tokens,
                             fwd_hooks=[(f"blocks.{layer}.hook_resid_pre", cap)])
    return captured["r"]


def capture_trajectory(model, text, pos, layers):
    """Capture residuals at the target token position at multiple layers in
    one forward pass. Returns dict layer -> (d,) tensor on cpu."""
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    captured = {}
    def make(L):
        def cap(value, hook):
            captured[L] = value[0, pos, :].detach().clone().to("cpu").float()
            return value
        return cap
    fwd = [(f"blocks.{L}.hook_resid_pre", make(L)) for L in layers]
    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=fwd)
    return captured


def capture_trajectory_with_intervention(model, text, pos, layers,
                                          intervention_layer, new_resid):
    """Same as capture_trajectory but the residual at `intervention_layer` is
    replaced by `new_resid` (d_model,) at position `pos` before the layer
    block executes. Captures the resulting residuals at each layer in `layers`
    (which should include layers > intervention_layer)."""
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    new_resid_dev = new_resid.to(DEVICE).to(DTYPE)
    captured = {}
    def make(L):
        def cap(value, hook):
            captured[L] = value[0, pos, :].detach().clone().to("cpu").float()
            return value
        return cap
    def patch(value, hook):
        value[0, pos, :] = new_resid_dev
        return value
    fwd = [(f"blocks.{intervention_layer}.hook_resid_pre", patch)]
    fwd += [(f"blocks.{L}.hook_resid_pre", make(L)) for L in layers]
    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=fwd)
    return captured


# ---------------------------------------------------------------------------
# Probe fitting (single layer, embedding-stripped)
# ---------------------------------------------------------------------------

def collect_resids(model, n, templates, layer):
    rows = []; used = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        rows.append(capture_resid(model, text, pos, layer))
        used.append(t)
    if not rows:
        return None, []
    return torch.stack(rows), used


def aligned_pair(R_a, used_a, R_b, used_b):
    shared = [t for t in used_a if t in used_b]
    a_idx = [used_a.index(t) for t in shared]
    b_idx = [used_b.index(t) for t in shared]
    return R_a[a_idx].float(), R_b[b_idx].float()


class LinProbe(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.w = nn.Parameter(torch.zeros(d))
        self.b = nn.Parameter(torch.zeros(1))
    def forward(self, x):
        return x @ self.w + self.b


def fit_identity_direction(model, target, layer):
    """Fit n_T^L: embedding-stripped linear probe direction, unit norm."""
    Rt, ut = collect_resids(model, target, TRAIN_TEMPLATES, layer)
    Rr, ur = collect_resids(model, REFERENCE, TRAIN_TEMPLATES, layer)
    Rtt, Rrr = aligned_pair(Rt, ut, Rr, ur)

    Rtn, utn = collect_resids(model, target, NEUTRAL_TEMPLATES, layer)
    Rrn, urn = collect_resids(model, REFERENCE, NEUTRAL_TEMPLATES, layer)
    Rttn, Rrrn = aligned_pair(Rtn, utn, Rrn, urn)
    e = Rttn.mean(0) - Rrrn.mean(0)
    e_n2 = (e * e).sum()

    def strip(X):
        if e_n2.item() < 1e-12:
            return X
        return X - ((X @ e) / e_n2).unsqueeze(1) * e.unsqueeze(0)

    X = torch.cat([strip(Rtt), strip(Rrr)], dim=0)
    y = torch.cat([torch.ones(len(Rtt)), torch.zeros(len(Rrr))])
    mu = X.mean(0); sd = X.std(0)
    sd = torch.where(sd > 1e-6, sd, torch.ones_like(sd))
    Xn = (X - mu) / sd
    p = LinProbe(Xn.shape[1])
    opt = torch.optim.Adam(p.parameters(), lr=5e-2, weight_decay=1e-2)
    bce = nn.BCEWithLogitsLoss()
    for _ in range(600):
        opt.zero_grad()
        bce(p(Xn), y).backward()
        opt.step()
    raw = p.w.detach() / sd
    if e_n2.item() > 1e-12:
        raw = raw - ((raw @ e) / e_n2) * e
    return raw / (raw.norm() + 1e-9), e / (e.norm() + 1e-9)


# ---------------------------------------------------------------------------
# Single (target, layer) blanket test
# ---------------------------------------------------------------------------

def project_onto(d_unit, r):
    """Scalar projection onto unit direction d_unit."""
    return float((d_unit @ r).item())


def intervene_eta(r_native_T, r_native_R, mu_unit, e_unit):
    """Replace eta-component of native target residual with that of reference.
    eta-subspace = orthogonal complement of span{mu_unit, e_unit}.
    Returns the intervened residual: keep target's mu and e components,
    replace target's eta-component with reference's eta-component."""
    # Decompose r_native_T = mu_T*mu_unit + e_T*e_unit + eta_T
    mu_T = (mu_unit @ r_native_T).item()
    e_T  = (e_unit  @ r_native_T).item()
    # Adjust e_unit to be orthogonal to mu_unit (make a orthonormal pair)
    # Simpler: compute residual after subtracting the {mu_unit, e_unit} subspace.
    # Use Gram-Schmidt: e_perp = e_unit - (mu_unit @ e_unit) mu_unit; renormalize
    e_perp = e_unit - (mu_unit @ e_unit) * mu_unit
    e_perp_n = e_perp.norm()
    if e_perp_n.item() > 1e-9:
        e_perp = e_perp / e_perp_n
    else:
        e_perp = torch.zeros_like(e_unit)
    # Coefficients in {mu_unit, e_perp} basis
    a_mu_T = (mu_unit @ r_native_T).item()
    a_e_T  = (e_perp  @ r_native_T).item()
    a_mu_R = (mu_unit @ r_native_R).item()
    a_e_R  = (e_perp  @ r_native_R).item()
    eta_T = r_native_T - a_mu_T * mu_unit - a_e_T * e_perp
    eta_R = r_native_R - a_mu_R * mu_unit - a_e_R * e_perp
    # Intervened: keep target's mu+e components, replace eta with reference's
    return a_mu_T * mu_unit + a_e_T * e_perp + eta_R


def evaluate_blanket(model, target, ref, blanket_layer, mu_unit, e_unit,
                      lookahead_layers, templates):
    """For each template, compute mu/eta trajectory disturbance after eta
    intervention. Returns dict of arrays keyed by lookahead step."""
    results = {
        "delta_mu":   {k: [] for k in lookahead_layers},
        "delta_eta_norm": {k: [] for k in lookahead_layers},
        "mu_native_rms":    {k: [] for k in lookahead_layers},
        "eta_native_rms":   {k: [] for k in lookahead_layers},
    }
    for t in templates:
        text_t = t.format(n=target)
        text_r = t.format(n=ref)
        pos_t = last_token_of_span(model, text_t, str(target))
        pos_r = last_token_of_span(model, text_r, str(ref))
        if pos_t is None or pos_r is None:
            continue
        # Native trajectories
        layers = [blanket_layer] + lookahead_layers
        traj_native_t = capture_trajectory(model, text_t, pos_t, layers)
        traj_native_r = capture_trajectory(model, text_r, pos_r, layers)
        if any(L not in traj_native_t for L in layers):
            continue
        if any(L not in traj_native_r for L in layers):
            continue
        # Build intervened residual at blanket_layer
        r_blank_t = traj_native_t[blanket_layer]
        r_blank_r = traj_native_r[blanket_layer]
        r_intv = intervene_eta(r_blank_t, r_blank_r, mu_unit, e_unit)
        # Forward with intervention, capture downstream
        traj_intv = capture_trajectory_with_intervention(
            model, text_t, pos_t, lookahead_layers,
            intervention_layer=blanket_layer, new_resid=r_intv,
        )
        for k in lookahead_layers:
            r_n = traj_native_t[k]
            r_i = traj_intv.get(k)
            if r_i is None:
                continue
            mu_n = float((mu_unit @ r_n).item())
            mu_i = float((mu_unit @ r_i).item())
            results["delta_mu"][k].append(mu_n - mu_i)
            results["mu_native_rms"][k].append(mu_n)
            # eta = residual minus mu-component minus e-component (Gram-Schmidt e)
            e_perp = e_unit - (mu_unit @ e_unit) * mu_unit
            e_perp = e_perp / max(e_perp.norm().item(), 1e-9)
            eta_n = r_n - float((mu_unit @ r_n).item()) * mu_unit \
                        - float((e_perp  @ r_n).item()) * e_perp
            eta_i = r_i - float((mu_unit @ r_i).item()) * mu_unit \
                        - float((e_perp  @ r_i).item()) * e_perp
            results["delta_eta_norm"][k].append(float((eta_n - eta_i).norm()))
            results["eta_native_rms"][k].append(float(eta_n.norm()))
    return results


def aggregate_blanket_score(results):
    """Compute average |Delta_mu| / mu_RMS and |Delta_eta| / eta_RMS across
    lookahead steps."""
    dmu = []; dme = []
    for k in results["delta_mu"]:
        if not results["delta_mu"][k]:
            continue
        d = np.abs(results["delta_mu"][k])
        rms = np.sqrt(np.mean(np.array(results["mu_native_rms"][k])**2)) + 1e-9
        dmu.append((np.mean(d) / rms))
        de = results["delta_eta_norm"][k]
        e_rms = np.sqrt(np.mean(np.array(results["eta_native_rms"][k])**2)) + 1e-9
        dme.append((np.mean(de) / e_rms))
    return float(np.mean(dmu)) if dmu else 0.0, float(np.mean(dme)) if dme else 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = load_model()
    n_layers = model.cfg.n_layers

    all_results = {}
    for target in TARGETS:
        all_results[target] = {}
        for L_blanket in BLANKET_LAYERS:
            print(f"\n=== target={target}  blanket_layer={L_blanket} ===")
            mu_unit, e_unit = fit_identity_direction(model, target, L_blanket)
            lookahead = [L_blanket + k for k in range(1, LOOKAHEAD_K + 1)
                          if L_blanket + k < n_layers]
            print(f"  lookahead layers: {lookahead}")

            print("  evaluating blanket with probed mu_unit ...")
            res_probed = evaluate_blanket(
                model, target, REFERENCE, L_blanket, mu_unit, e_unit,
                lookahead, HELDOUT_TEMPLATES)
            score_mu_p, score_eta_p = aggregate_blanket_score(res_probed)
            print(f"  probed:  mean |dmu|/mu_rms = {score_mu_p:.3f}  "
                  f"|deta|/eta_rms = {score_eta_p:.3f}")

            # Random direction baseline
            torch.manual_seed(int(target) * 1000 + L_blanket)
            rand = torch.randn(model.cfg.d_model)
            rand = rand - (rand @ e_unit) * e_unit
            rand = rand / (rand.norm() + 1e-9)
            print("  evaluating blanket with random mu_unit (control) ...")
            res_random = evaluate_blanket(
                model, target, REFERENCE, L_blanket, rand, e_unit,
                lookahead, HELDOUT_TEMPLATES)
            score_mu_r, score_eta_r = aggregate_blanket_score(res_random)
            print(f"  random:  mean |dmu|/mu_rms = {score_mu_r:.3f}  "
                  f"|deta|/eta_rms = {score_eta_r:.3f}")

            all_results[target][L_blanket] = {
                "lookahead": lookahead,
                "probed": {
                    "score_mu_over_mu_rms":  score_mu_p,
                    "score_eta_over_eta_rms": score_eta_p,
                    "delta_mu_per_k":  {str(k): float(np.mean(np.abs(res_probed["delta_mu"][k])))
                                         if res_probed["delta_mu"][k] else 0.0
                                         for k in lookahead},
                    "delta_eta_per_k": {str(k): float(np.mean(res_probed["delta_eta_norm"][k]))
                                         if res_probed["delta_eta_norm"][k] else 0.0
                                         for k in lookahead},
                },
                "random": {
                    "score_mu_over_mu_rms":  score_mu_r,
                    "score_eta_over_eta_rms": score_eta_r,
                    "delta_mu_per_k":  {str(k): float(np.mean(np.abs(res_random["delta_mu"][k])))
                                         if res_random["delta_mu"][k] else 0.0
                                         for k in lookahead},
                    "delta_eta_per_k": {str(k): float(np.mean(res_random["delta_eta_norm"][k]))
                                         if res_random["delta_eta_norm"][k] else 0.0
                                         for k in lookahead},
                },
            }

    # Verdict: averaged over (target, layer) cells
    probed_scores = []
    random_scores = []
    eta_scores_p  = []
    for tgt, by_L in all_results.items():
        for L, e in by_L.items():
            probed_scores.append(e["probed"]["score_mu_over_mu_rms"])
            random_scores.append(e["random"]["score_mu_over_mu_rms"])
            eta_scores_p.append(e["probed"]["score_eta_over_eta_rms"])
    avg_probed = float(np.mean(probed_scores))
    avg_random = float(np.mean(random_scores))
    avg_eta_p  = float(np.mean(eta_scores_p))

    if avg_probed < 0.15 and avg_random > 0.4 and avg_eta_p > 0.5:
        verdict = "PASS"
    elif avg_probed < 0.4 and avg_probed < avg_random - 0.1:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    print(f"\nVerdict: {verdict}")
    print(f"  avg |dmu|/mu_rms (probed): {avg_probed:.3f}")
    print(f"  avg |dmu|/mu_rms (random): {avg_random:.3f}")
    print(f"  avg |deta|/eta_rms (probed): {avg_eta_p:.3f}")

    # Plots
    fig, ax = plt.subplots(figsize=(8, 5))
    xs = np.arange(len(BLANKET_LAYERS) * len(TARGETS))
    labels = []; probed = []; randv = []
    for L in BLANKET_LAYERS:
        for t in TARGETS:
            e = all_results[t][L]
            labels.append(f"T={t}\nL={L}")
            probed.append(e["probed"]["score_mu_over_mu_rms"])
            randv.append(e["random"]["score_mu_over_mu_rms"])
    width = 0.4
    ax.bar(xs - width/2, probed, width, color="steelblue", label="probed n_T")
    ax.bar(xs + width/2, randv, width, color="lightgray", label="random direction")
    ax.axhline(0.15, color="green", linestyle="--", alpha=0.5, label="PASS thr 0.15")
    ax.axhline(0.4,  color="orange", linestyle="--", alpha=0.5, label="PARTIAL thr 0.4")
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("mean |Delta mu| / mu_RMS  (lower = blanket-like)")
    ax.set_title("Dynamical blanket score: probed direction vs random control")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "per_layer_blanket_score.png", dpi=150)
    plt.close(fig)

    # Trajectory plots: delta_mu vs k for probed and random, per target/layer
    fig, axes = plt.subplots(len(TARGETS), len(BLANKET_LAYERS),
                              figsize=(4 * len(BLANKET_LAYERS),
                                        3 * len(TARGETS)),
                              sharex=False, sharey=False)
    for i, t in enumerate(TARGETS):
        for j, L in enumerate(BLANKET_LAYERS):
            ax = axes[i, j] if len(TARGETS) > 1 else axes[j]
            e = all_results[t][L]
            ks = e["lookahead"]
            dmu_p = [e["probed"]["delta_mu_per_k"][str(k)] for k in ks]
            dmu_r = [e["random"]["delta_mu_per_k"][str(k)] for k in ks]
            ax.plot(ks, dmu_p, marker="o", color="steelblue", label="probed")
            ax.plot(ks, dmu_r, marker="s", color="lightgray", label="random")
            ax.set_title(f"T={t}, L_blanket={L}", fontsize=10)
            ax.set_xlabel("layer (lookahead)")
            ax.set_ylabel("|Delta mu|")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == 0:
                ax.legend(fontsize=8)
    fig.suptitle("mu-trajectory disturbance after eta-intervention "
                 "(probed identity-direction vs random)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "mu_trajectory_disturbance.png", dpi=150)
    plt.close(fig)

    # Eta trajectory disturbance — confirms intervention had effect
    fig, axes = plt.subplots(len(TARGETS), len(BLANKET_LAYERS),
                              figsize=(4 * len(BLANKET_LAYERS),
                                        3 * len(TARGETS)),
                              sharex=False, sharey=False)
    for i, t in enumerate(TARGETS):
        for j, L in enumerate(BLANKET_LAYERS):
            ax = axes[i, j] if len(TARGETS) > 1 else axes[j]
            e = all_results[t][L]
            ks = e["lookahead"]
            dn_p = [e["probed"]["delta_eta_per_k"][str(k)] for k in ks]
            dn_r = [e["random"]["delta_eta_per_k"][str(k)] for k in ks]
            ax.plot(ks, dn_p, marker="o", color="steelblue", label="probed")
            ax.plot(ks, dn_r, marker="s", color="lightgray", label="random")
            ax.set_title(f"T={t}, L_blanket={L}", fontsize=10)
            ax.set_xlabel("layer (lookahead)")
            ax.set_ylabel("|Delta eta|")
            ax.grid(True, alpha=0.3)
            if i == 0 and j == 0:
                ax.legend(fontsize=8)
    fig.suptitle("eta-trajectory disturbance after eta-intervention "
                 "(should be large — confirms intervention was real)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "eta_trajectory_disturbance.png", dpi=150)
    plt.close(fig)

    # Report
    lines = [f"Exp 41 - Dynamical Blanket Identity-Direction Test  ({MODEL_NAME})",
             "=" * 70, ""]
    lines.append(f"Targets:       {TARGETS}")
    lines.append(f"Blanket layers: {BLANKET_LAYERS}")
    lines.append(f"Lookahead K:   {LOOKAHEAD_K}")
    lines.append("")
    lines.append("Pre-registered outcome rules (averaged over (target, layer)):")
    lines.append("  PASS    avg |Δμ|/μ_RMS (probed) < 0.15  AND  random > 0.4")
    lines.append("                                          AND  |Δη|/η_RMS > 0.5")
    lines.append("  PARTIAL avg |Δμ|/μ_RMS (probed) < 0.4   AND  probed < random - 0.1")
    lines.append("  FAIL    otherwise")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict}")
    lines.append(f"  avg |Δμ|/μ_RMS  (probed): {avg_probed:.3f}")
    lines.append(f"  avg |Δμ|/μ_RMS  (random): {avg_random:.3f}")
    lines.append(f"  avg |Δη|/η_RMS  (probed): {avg_eta_p:.3f}")
    lines.append("")
    for t in TARGETS:
        for L in BLANKET_LAYERS:
            e = all_results[t][L]
            lines.append(f"\n### target={t}  blanket_layer={L}")
            lines.append(f"  probed:  μ-disturbance={e['probed']['score_mu_over_mu_rms']:.3f}  "
                         f"η-disturbance={e['probed']['score_eta_over_eta_rms']:.3f}")
            lines.append(f"  random:  μ-disturbance={e['random']['score_mu_over_mu_rms']:.3f}  "
                         f"η-disturbance={e['random']['score_eta_over_eta_rms']:.3f}")
    (RESULTS_DIR / "report.txt").write_text("\n".join(lines))
    print(f"Report: {RESULTS_DIR / 'report.txt'}")

    summary = {
        "design": "exp 41: dynamical blanket identity-direction test",
        "model": MODEL_NAME,
        "blanket_layers": BLANKET_LAYERS,
        "lookahead_K": LOOKAHEAD_K,
        "targets": TARGETS,
        "reference": REFERENCE,
        "results": {str(t): {str(L): e for L, e in by_L.items()}
                     for t, by_L in all_results.items()},
        "verdict": verdict,
        "avg_mu_disturbance_probed": avg_probed,
        "avg_mu_disturbance_random": avg_random,
        "avg_eta_disturbance_probed": avg_eta_p,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
