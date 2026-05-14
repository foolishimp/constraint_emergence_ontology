"""
Experiment 33 (Llama-3 8B port): Embedding-Decomposition Audit

Same protocol as 33_embedding_decomposition.py but runs on Llama-3 8B via
transformer_lens with MPS backend. Probe layers chosen at proportional depth:
{2, 8, 16, 24, 30} (32-layer model).

Pre-registered question (unchanged):
    Does scale alone (124M -> 8B) move the verdict?

Pre-registered thresholds (unchanged):
    layers L >= 16 (proportional to L>=6 in GPT-2 small):
        PASS     mean retention(perp/full) >= 0.50
        PARTIAL  0.25 <= mean < 0.50
        FAIL     mean < 0.25

Outputs:
    results/33_embedding_decomposition_llama3/
        report.txt
        summary.json
        transfer_by_layer.png
        parallel_perp_decomposition.png
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch

RESULTS_DIR = (Path(__file__).parent.parent
               / "results" / "33_embedding_decomposition_llama3")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME    = "meta-llama/Meta-Llama-3-8B"
DEVICE        = "mps"
DTYPE         = torch.float16
PROBE_LAYERS  = [2, 8, 16, 24, 30]
LAYER_THRESHOLD = 16        # equivalent of L>=6 in 12-layer GPT-2 (proportional)

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

HELDOUT_TEMPLATES = DIVERSE_TEMPLATES[-10:]
TRAIN_TEMPLATES   = DIVERSE_TEMPLATES[:-10]

ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def load_model():
    from transformer_lens import HookedTransformer
    print(f"Loading {MODEL_NAME} on {DEVICE} ({DTYPE})...")
    token = os.environ.get("HF_TOKEN")
    if token:
        os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    model = HookedTransformer.from_pretrained(
        MODEL_NAME,
        device=DEVICE,
        dtype=DTYPE,
    )
    model.eval()
    print(f"  loaded: n_layers={model.cfg.n_layers}, "
          f"d_model={model.cfg.d_model}, n_heads={model.cfg.n_heads}")
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
    hook_name = f"blocks.{layer}.hook_resid_pre"
    captured = {}

    def cap(value, hook):
        captured["resid"] = value[0, pos, :].detach().clone().to("cpu").float()
        return value

    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=[(hook_name, cap)])
    return captured["resid"]


def collect_residuals_at_layer(model, n, templates, layer):
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
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :].to("cpu").float()


def logits_with_direction(model, text, pos, direction, alpha, layer):
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    direction_dev = direction.to(DEVICE).to(DTYPE)

    def patch(value, hook):
        resid = value[0, pos, :].clone()
        resid = resid - alpha * direction_dev
        value[0, pos, :] = resid
        return value

    with torch.no_grad():
        logits = model.run_with_hooks(tokens, fwd_hooks=[(hook_name, patch)])
    return logits[0, -1, :].to("cpu").float()


def kl_div(p_logits, q_logits):
    p = torch.softmax(p_logits, dim=-1)
    q = torch.softmax(q_logits, dim=-1)
    return float((p * (torch.log(p + 1e-12) - torch.log(q + 1e-12))).sum())


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

def alpha_sweep(model, target, template, direction, layer, alphas=ALPHAS):
    text_target = template.format(n=target)
    text_ref    = template.format(n=REFERENCE)
    pos_t = last_token_of_span(model, text_target, str(target))
    pos_r = last_token_of_span(model, text_ref, str(REFERENCE))
    if pos_t is None or pos_r is None:
        return None

    logits_tgt = baseline_logits(model, text_target)
    logits_ref = baseline_logits(model, text_ref)
    kl_baseline = kl_div(logits_tgt, logits_ref)

    out = {"kl_baseline": kl_baseline, "alphas": {}}
    for a in alphas:
        li = logits_with_direction(model, text_target, pos_t, direction, a, layer)
        kl_ref = kl_div(li, logits_ref)
        kl_tgt = kl_div(li, logits_tgt)
        transfer = 1.0 - (kl_ref / max(kl_baseline, 1e-9))
        out["alphas"][a] = {"kl_ref": kl_ref, "kl_tgt": kl_tgt,
                            "transfer": transfer}
    return out


def aggregate_sweep(model, target, direction, layer, templates):
    per_alpha = {a: [] for a in ALPHAS}
    kl_baseline_all = []
    for t in templates:
        res = alpha_sweep(model, target, t, direction, layer)
        if res is None:
            continue
        kl_baseline_all.append(res["kl_baseline"])
        for a in ALPHAS:
            per_alpha[a].append(res["alphas"][a]["transfer"])
    return {
        "kl_baseline": float(np.mean(kl_baseline_all)) if kl_baseline_all else 0.0,
        "mean": {a: float(np.mean(per_alpha[a])) if per_alpha[a] else 0.0
                 for a in ALPHAS},
        "std":  {a: float(np.std(per_alpha[a]))  if per_alpha[a] else 0.0
                 for a in ALPHAS},
        "n_templates": len(per_alpha[ALPHAS[0]]),
    }


def decompose(d, e):
    e_norm2 = float((e * e).sum())
    if e_norm2 < 1e-12:
        return 0.0, d * 0.0, d.clone()
    alpha_e = float((d * e).sum()) / e_norm2
    d_par = alpha_e * e
    d_perp = d - d_par
    return alpha_e, d_par, d_perp


def classify_verdict(all_results, layer_threshold=LAYER_THRESHOLD):
    retentions = []
    for target, by_layer in all_results.items():
        for L, entry in by_layer.items():
            if int(L) >= layer_threshold:
                retentions.append(entry["retention_perp_over_full"])
    if not retentions:
        return {"mean_retention_at_L_ge_threshold": None, "verdict": "UNKNOWN"}
    mean_ret = float(np.mean(retentions))
    if mean_ret >= 0.50:
        v = "PASS"
    elif mean_ret >= 0.25:
        v = "PARTIAL"
    else:
        v = "FAIL"
    return {
        "layer_threshold": layer_threshold,
        "mean_retention_at_L_ge_threshold": mean_ret,
        "verdict": v,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_transfer_by_layer(all_results):
    fig, axes = plt.subplots(1, len(TARGETS), figsize=(5 * len(TARGETS), 5),
                              sharey=True)
    if len(TARGETS) == 1:
        axes = [axes]
    for ax, target in zip(axes, TARGETS):
        by_layer = all_results.get(target, {})
        if not by_layer:
            continue
        layers = sorted(by_layer.keys())
        full = [by_layer[L]["transfer_full"] for L in layers]
        perp = [by_layer[L]["transfer_perp"] for L in layers]
        emb  = [by_layer[L]["transfer_emb"]  for L in layers]
        ax.plot(layers, full, marker="o", linewidth=2, label="d_full",
                color="tomato")
        ax.plot(layers, perp, marker="s", linewidth=2, label="d_perp (stripped)",
                color="steelblue")
        ax.plot(layers, emb,  marker="^", linewidth=2, label="e_emb (neutral)",
                color="goldenrod")
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.set_xlabel("layer")
        ax.set_title(f"target = {target}")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("transfer at alpha=1 (held-out)")
    axes[0].legend(loc="best", fontsize=9)
    fig.suptitle(f"Embedding-decomposition on {MODEL_NAME}: full vs perp vs emb")
    fig.tight_layout()
    out = RESULTS_DIR / "transfer_by_layer.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_decomposition_by_layer(all_results):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for target in TARGETS:
        by_layer = all_results.get(target, {})
        if not by_layer:
            continue
        layers = sorted(by_layer.keys())
        cos_de = [by_layer[L]["cos_d_e"] for L in layers]
        frac_par = [by_layer[L]["frac_par_var"] for L in layers]
        axes[0].plot(layers, cos_de, marker="o", linewidth=2,
                     label=f"target={target}")
        axes[1].plot(layers, frac_par, marker="o", linewidth=2,
                     label=f"target={target}")
    for ax, ylabel, title in zip(
        axes, ["cos(d_full, e_emb)", "||d_par||^2 / ||d_full||^2"],
        ["Direction-embedding alignment", "Embedding-attributable variance"]):
        ax.set_xlabel("layer")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=9)
    axes[0].set_ylim(-0.1, 1.1)
    axes[1].set_ylim(-0.05, 1.1)
    fig.suptitle(f"{MODEL_NAME}: cosine and variance share by layer")
    fig.tight_layout()
    out = RESULTS_DIR / "parallel_perp_decomposition.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(all_results, verdict):
    lines = [f"Exp 33 - Embedding-Decomposition Audit  ({MODEL_NAME})",
             "=" * 70, ""]
    lines.append(f"Reference: n = {REFERENCE}")
    lines.append(f"Targets:   {TARGETS}")
    lines.append(f"Layers:    {PROBE_LAYERS}")
    lines.append(f"Train (diverse): {len(TRAIN_TEMPLATES)}  "
                 f"Neutral: {len(NEUTRAL_TEMPLATES)}  "
                 f"Held-out: {len(HELDOUT_TEMPLATES)}")
    lines.append("")
    lines.append(f"Pre-registered outcome rules (averaged, layers L>={LAYER_THRESHOLD}):")
    lines.append("  PASS     mean retention(perp/full) >= 0.50")
    lines.append("  PARTIAL  0.25 <= mean retention < 0.50")
    lines.append("  FAIL     mean retention < 0.25")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict['verdict']}")
    if verdict.get("mean_retention_at_L_ge_threshold") is not None:
        lines.append(f"  mean retention at L >= {verdict['layer_threshold']}: "
                     f"{verdict['mean_retention_at_L_ge_threshold']:+.3f}")
    lines.append("")
    for target in TARGETS:
        by_layer = all_results.get(target, {})
        if not by_layer:
            continue
        lines.append(f"\n### target = {target}")
        header = (f"  {'layer':>5s} | {'||d_full||':>11s} | {'||e_emb||':>11s} | "
                  f"{'cos(d,e)':>9s} | {'frac_par':>9s} | "
                  f"{'tr_full':>9s} | {'tr_perp':>9s} | {'tr_emb':>9s} | "
                  f"{'ret':>7s}")
        lines.append(header)
        lines.append("  " + "-" * (len(header) - 2))
        for L in sorted(by_layer.keys()):
            e = by_layer[L]
            lines.append(
                f"  {int(L):>5d} | {e['d_full_norm']:>11.3f} | "
                f"{e['e_emb_norm']:>11.3f} | {e['cos_d_e']:>+9.3f} | "
                f"{e['frac_par_var']:>9.3f} | "
                f"{e['transfer_full']:>+9.3f} | {e['transfer_perp']:>+9.3f} | "
                f"{e['transfer_emb']:>+9.3f} | "
                f"{e['retention_perp_over_full']:>+7.3f}")
    out = RESULTS_DIR / "report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = load_model()

    all_results = {}
    for target in TARGETS:
        all_results[target] = {}
        for layer in PROBE_LAYERS:
            print(f"\n=== target={target}  layer={layer} ===")

            R_t_div, used_t_div = collect_residuals_at_layer(
                model, target, TRAIN_TEMPLATES, layer)
            R_r_div, used_r_div = collect_residuals_at_layer(
                model, REFERENCE, TRAIN_TEMPLATES, layer)
            if R_t_div is None or R_r_div is None:
                print("  skip: no usable templates")
                continue
            R_t, R_r, shared_div = aligned_pair(R_t_div, used_t_div,
                                                 R_r_div, used_r_div)
            d_full = R_t.mean(0) - R_r.mean(0)

            R_t_neu, used_t_neu = collect_residuals_at_layer(
                model, target, NEUTRAL_TEMPLATES, layer)
            R_r_neu, used_r_neu = collect_residuals_at_layer(
                model, REFERENCE, NEUTRAL_TEMPLATES, layer)
            if R_t_neu is None or R_r_neu is None:
                print("  skip: no usable neutral templates")
                continue
            R_tn, R_rn, shared_neu = aligned_pair(R_t_neu, used_t_neu,
                                                   R_r_neu, used_r_neu)
            e_emb = R_tn.mean(0) - R_rn.mean(0)

            alpha_e, d_par, d_perp = decompose(d_full, e_emb)
            d_full_norm = float(d_full.norm())
            e_emb_norm  = float(e_emb.norm())
            d_par_norm  = float(d_par.norm())
            d_perp_norm = float(d_perp.norm())
            cos_d_e = float((d_full @ e_emb).item()) / max(
                d_full_norm * e_emb_norm, 1e-9)

            print(f"  paired_diverse={len(shared_div)}  paired_neutral={len(shared_neu)}")
            print(f"  ||d_full||={d_full_norm:.3f}  ||e_emb||={e_emb_norm:.3f}")
            print(f"  cos(d_full, e_emb)={cos_d_e:+.3f}  alpha_e={alpha_e:+.3f}")
            print(f"  frac_par_var={d_par_norm**2 / max(d_full_norm**2, 1e-9):.3f}")

            d_perp_resc = d_perp / max(d_perp_norm, 1e-9) * d_full_norm
            e_emb_resc  = e_emb  / max(e_emb_norm,  1e-9) * d_full_norm

            print("  alpha-sweep d_full ...")
            s_full = aggregate_sweep(model, target, d_full,     layer, HELDOUT_TEMPLATES)
            print("  alpha-sweep d_perp (rescaled) ...")
            s_perp = aggregate_sweep(model, target, d_perp_resc, layer, HELDOUT_TEMPLATES)
            print("  alpha-sweep e_emb (rescaled) ...")
            s_emb  = aggregate_sweep(model, target, e_emb_resc,  layer, HELDOUT_TEMPLATES)

            transfer_full = s_full["mean"][1.0]
            transfer_perp = s_perp["mean"][1.0]
            transfer_emb  = s_emb["mean"][1.0]
            retention = (transfer_perp / max(abs(transfer_full), 1e-9)
                         if transfer_full > 0 else 0.0)

            entry = {
                "d_full_norm": d_full_norm,
                "e_emb_norm":  e_emb_norm,
                "d_par_norm":  d_par_norm,
                "d_perp_norm": d_perp_norm,
                "alpha_e":     alpha_e,
                "cos_d_e":     cos_d_e,
                "frac_par_var":  d_par_norm**2  / max(d_full_norm**2, 1e-9),
                "frac_perp_var": d_perp_norm**2 / max(d_full_norm**2, 1e-9),
                "transfer_full": transfer_full,
                "transfer_perp": transfer_perp,
                "transfer_emb":  transfer_emb,
                "retention_perp_over_full": retention,
                "sweep_full": {str(a): v for a, v in s_full["mean"].items()},
                "sweep_perp": {str(a): v for a, v in s_perp["mean"].items()},
                "sweep_emb":  {str(a): v for a, v in s_emb["mean"].items()},
                "n_paired_diverse": len(shared_div),
                "n_paired_neutral": len(shared_neu),
            }
            all_results[target][layer] = entry
            print(f"  transfer @ alpha=1: full={transfer_full:+.3f}  "
                  f"perp={transfer_perp:+.3f}  emb={transfer_emb:+.3f}")
            print(f"  retention(perp/full)={retention:+.3f}")

    verdict = classify_verdict(all_results)
    print(f"\nVerdict: {verdict['verdict']}  "
          f"(mean retention at L>={verdict.get('layer_threshold')} = "
          f"{verdict.get('mean_retention_at_L_ge_threshold')})")

    plot_transfer_by_layer(all_results)
    plot_decomposition_by_layer(all_results)
    write_report(all_results, verdict)

    summary = {
        "design": "exp 33 (Llama-3 8B port)",
        "model": MODEL_NAME,
        "device": DEVICE,
        "probe_layers": PROBE_LAYERS,
        "targets": TARGETS,
        "reference": REFERENCE,
        "alphas": ALPHAS,
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
