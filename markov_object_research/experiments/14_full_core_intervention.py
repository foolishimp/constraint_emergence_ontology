"""
Experiment 14: Full Core Intervention — Markov Object Transplant

Exp 13 showed single-feature interventions produce directionally correct but
small effects (~1% probability mass). The theory predicts this: a Markov
object is an *ensemble* of ~80 features, so ablating one feature removes
~1/80 of the skeleton. The load-bearing structure should be the *invariant
core* (exp 09), not any single feature.

This experiment tests the ensemble hypothesis directly:

  Test A — ABLATE the full 6-feature invariant core of 999.
           Prediction: KL >> 0.027 (exp 13's single-feature KL); 999 loses
           emergency identity entirely and collapses toward generic number.

  Test B — INJECT 999's full core into 500.
           Prediction: 500 inherits emergency-themed continuations.

  Test C — ABLATE the full 9-feature invariant core of 666.
           Prediction: 666 loses its specific structural signature.

  Test D — INJECT 666's full core into 7.
           Prediction: 7 takes on 666-like continuations.

  Test E — NUCLEAR: ablate the top-20 active features of 999.
           Prediction: 999's Markov object is destroyed — distribution
           becomes indistinguishable from a generic number.

Source of truth for cores: results/09_context_conditional/annotated_report.txt
Intervention pattern is identical to exp 13 but now with lists of (fid, val).
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "14_full_core_intervention"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 8
TOP_K = 15


# ---------------------------------------------------------------------------
# Invariant cores from exp 09 (annotated_report.txt)
# Format: (feature_id, mean_firing_across_8_contexts, label)
# ---------------------------------------------------------------------------

INVARIANT_CORES = {
    "999": [
        (2269,  15.93, "emergency numbers '911'"),
        (12604, 13.89, "tech specifications / quantities"),
        (10744,  9.13, "references to date '9/11'"),
        (5567,   7.89, "numerical values"),
        (2747,   7.86, "numerical with percentage / CI"),
        (17244,  5.65, "legal/organizational codes"),
    ],
    "666": [
        (17244, 12.45, "legal/organizational codes"),
        (13585,  9.31, "measurements and numerical values"),
        (12604,  7.13, "tech specifications / quantities"),
        (20061,  5.80, "measurements / dimensions"),
        (20951,  4.72, "numbers"),
        (11917,  4.19, "proper nouns / names"),
        (10439,  3.90, "gentrification"),
        (17855,  2.55, "specific numerical patterns"),
        (9551,   1.84, "patronage / support"),
    ],
}


# ---------------------------------------------------------------------------
# Model + SAE
# ---------------------------------------------------------------------------

def load_model_and_sae():
    from transformer_lens import HookedTransformer
    from sae_lens import SAE
    print("Loading GPT-2 + SAE...")
    model = HookedTransformer.from_pretrained("gpt2")
    model.eval()
    sae = SAE.from_pretrained(
        release="gpt2-small-res-jb",
        sae_id=f"blocks.{PROBE_LAYER}.hook_resid_pre",
    )
    return model, sae


def last_token_of_span(model, text, span):
    span_start = text.find(span)
    if span_start < 0:
        return None
    span_end = span_start + len(span)
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    acc = 0
    for i, tok in enumerate(str_tokens):
        if i == 0 and tok in ("<|endoftext|>", ""):
            continue
        acc += len(tok)
        if acc >= span_end:
            return i
    return None


# ---------------------------------------------------------------------------
# Intervention machinery (identical pattern to exp 13, generalized to lists)
# ---------------------------------------------------------------------------

def run_baseline(model, text):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def encode_features_at(model, sae, text, target_pos, layer=PROBE_LAYER):
    """Return SAE feature activations at target position."""
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    captured = {}

    def capture(value, hook):
        captured["resid"] = value[0, target_pos, :].detach().clone()
        return value

    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=[(hook_name, capture)])
    features = sae.encode(captured["resid"].unsqueeze(0))[0]
    return features


def run_with_intervention(model, sae, text, target_pos, interventions,
                          layer=PROBE_LAYER):
    """
    interventions : list of (feature_id, new_value)
      new_value = 0.0 → ablate
      new_value > 0  → inject / boost
    """
    import torch

    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"

    def hook_fn(value, hook):
        resid = value[0, target_pos, :].clone()
        features = sae.encode(resid.unsqueeze(0))[0]
        for fid, new_val in interventions:
            delta = new_val - features[fid].item()
            resid = resid + delta * sae.W_dec[fid]
        value[0, target_pos, :] = resid
        return value

    with torch.no_grad():
        logits = model.run_with_hooks(tokens, fwd_hooks=[(hook_name, hook_fn)])
    return logits[0, -1, :]


def top_k_tokens(model, logits, k=TOP_K):
    import torch
    probs = torch.softmax(logits, dim=-1)
    top_probs, top_ids = probs.topk(k)
    return [(model.to_single_str_token(int(i)), float(p))
            for p, i in zip(top_probs, top_ids)]


def kl_divergence(logits_p, logits_q):
    import torch
    p = torch.softmax(logits_p, dim=-1)
    q = torch.softmax(logits_q, dim=-1)
    return float((p * (torch.log(p + 1e-12) - torch.log(q + 1e-12))).sum())


def measure_token_prob_shift(model, logits_before, logits_after, tokens_of_interest):
    import torch
    p_before = torch.softmax(logits_before, dim=-1)
    p_after  = torch.softmax(logits_after,  dim=-1)
    out = {}
    for tok in tokens_of_interest:
        try:
            tid = model.to_single_token(tok)
        except Exception:
            continue
        b = float(p_before[tid])
        a = float(p_after[tid])
        out[tok] = (b, a, a - b)
    return out


def greedy_continuation(model, text, max_new_tokens=12):
    """Greedy decode; no intervention. For baseline display."""
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    out_tokens = tokens.clone()
    with torch.no_grad():
        for _ in range(max_new_tokens):
            logits = model(out_tokens)
            next_id = int(logits[0, -1, :].argmax())
            out_tokens = torch.cat(
                [out_tokens, torch.tensor([[next_id]], device=out_tokens.device)],
                dim=1,
            )
    return model.to_string(out_tokens[0])


def greedy_continuation_with_intervention(model, sae, text, target_pos,
                                          interventions, max_new_tokens=12,
                                          layer=PROBE_LAYER):
    """Greedy decode while re-applying the intervention at every forward pass."""
    import torch

    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    out_tokens = tokens.clone()

    def hook_fn(value, hook):
        resid = value[0, target_pos, :].clone()
        features = sae.encode(resid.unsqueeze(0))[0]
        for fid, new_val in interventions:
            delta = new_val - features[fid].item()
            resid = resid + delta * sae.W_dec[fid]
        value[0, target_pos, :] = resid
        return value

    with torch.no_grad():
        for _ in range(max_new_tokens):
            logits = model.run_with_hooks(
                out_tokens, fwd_hooks=[(hook_name, hook_fn)]
            )
            next_id = int(logits[0, -1, :].argmax())
            out_tokens = torch.cat(
                [out_tokens, torch.tensor([[next_id]], device=out_tokens.device)],
                dim=1,
            )
    return model.to_string(out_tokens[0])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def build_tests():
    tests = []

    # --- A: Ablate 999's full invariant core ---
    tests.append({
        "name":        "A_ablate_999_full_core",
        "text":        "The number 999 is most associated with",
        "span":        "999",
        "description": "Ablate all 6 invariant-core features of 999 "
                       "(emergency/911, 9/11 date, tech spec, numerical, %, legal code)",
        "mode":        "ablate",
        "interventions": [(fid, 0.0) for fid, _, _ in INVARIANT_CORES["999"]],
        "feature_labels": INVARIANT_CORES["999"],
        "probes": [" emergency", " police", " fire", " call", " 911",
                   " number", " song", " year", " God", " phone",
                   " code", " people"],
    })

    # --- B: Inject 999's core into 500 ---
    tests.append({
        "name":        "B_inject_999_core_into_500",
        "text":        "The number 500 is most associated with",
        "span":        "500",
        "description": "Transplant 999's full invariant core into 500",
        "mode":        "inject",
        "interventions": [(fid, mu) for fid, mu, _ in INVARIANT_CORES["999"]],
        "feature_labels": INVARIANT_CORES["999"],
        "probes": [" emergency", " police", " fire", " call", " 911",
                   " money", " dollars", " people", " Fortune",
                   " years", " miles"],
    })

    # --- C: Ablate 666's full invariant core ---
    tests.append({
        "name":        "C_ablate_666_full_core",
        "text":        "The number 666 is most associated with",
        "span":        "666",
        "description": "Ablate all 9 invariant-core features of 666",
        "mode":        "ablate",
        "interventions": [(fid, 0.0) for fid, _, _ in INVARIANT_CORES["666"]],
        "feature_labels": INVARIANT_CORES["666"],
        "probes": [" beast", " devil", " demon", " Satan", " God",
                   " number", " code", " year", " Antichrist", " mark"],
    })

    # --- D: Inject 666's core into 7 ---
    tests.append({
        "name":        "D_inject_666_core_into_7",
        "text":        "The number 7 is the mark of the",
        "span":        "7",
        "description": "Transplant 666's full invariant core into 7",
        "mode":        "inject",
        "interventions": [(fid, mu) for fid, mu, _ in INVARIANT_CORES["666"]],
        "feature_labels": INVARIANT_CORES["666"],
        "probes": [" beast", " devil", " demon", " Satan", " Antichrist",
                   " seven", " day", " week", " sacred", " lucky",
                   " God", " Lord"],
    })

    # --- E: Top-20 ablation of 999 (nuclear option) ---
    # Built at runtime: encode 999's residual, take top-20 firing features,
    # ablate them all.
    tests.append({
        "name":        "E_ablate_top20_of_999",
        "text":        "The number 999 is most associated with",
        "span":        "999",
        "description": "Nuclear: ablate top-20 firing features at 999's position",
        "mode":        "ablate_top_k",
        "top_k_ablate": 20,
        "probes": [" emergency", " 911", " the", " a", " an", " number",
                   " God", " code", " one", " nine", " 1"],
    })

    return tests


def run_test(test, model, sae):
    text = test["text"]
    pos = last_token_of_span(model, text, test["span"])
    if pos is None:
        print(f"  [{test['name']}] span '{test['span']}' not found")
        return None

    # Top-k ablation needs to encode features first to pick targets
    if test["mode"] == "ablate_top_k":
        feats = encode_features_at(model, sae, text, pos)
        feats_np = feats.detach().cpu().numpy()
        top_ids = np.argsort(-feats_np)[:test["top_k_ablate"]]
        interventions = [(int(fid), 0.0) for fid in top_ids]
        test["resolved_interventions"] = [
            (int(fid), float(feats_np[fid])) for fid in top_ids
        ]
    else:
        interventions = test["interventions"]
        test["resolved_interventions"] = interventions

    logits_b = run_baseline(model, text)
    logits_i = run_with_intervention(model, sae, text, pos, interventions)

    top_b = top_k_tokens(model, logits_b)
    top_i = top_k_tokens(model, logits_i)
    kl = kl_divergence(logits_b, logits_i)
    probe_shifts = measure_token_prob_shift(model, logits_b, logits_i, test["probes"])

    # Greedy continuation (sentence-level behavioral probe)
    cont_b = greedy_continuation(model, text, max_new_tokens=12)
    cont_i = greedy_continuation_with_intervention(
        model, sae, text, pos, interventions, max_new_tokens=12
    )

    return {
        "test":                 test,
        "span_pos":             pos,
        "top_baseline":         top_b,
        "top_after":            top_i,
        "kl":                   kl,
        "probe_shifts":         probe_shifts,
        "continuation_before":  cont_b,
        "continuation_after":   cont_i,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_test_result(result):
    t = result["test"]
    print(f"\n### {t['name']}")
    print(f"    prompt : {t['text']!r}")
    print(f"    span   : {t['span']!r}  (pos={result['span_pos']})")
    print(f"    mode   : {t['mode']}")
    print(f"    desc   : {t['description']}")
    print(f"    #feats intervened: {len(t['resolved_interventions'])}")
    print(f"    KL(baseline || intervened) = {result['kl']:.4f}")

    print("\n    continuation:")
    print(f"      baseline   → {result['continuation_before']!r}")
    print(f"      intervened → {result['continuation_after']!r}")

    print("\n    top next-token shift:")
    print(f"    {'rank':>4}  {'BASELINE':>25}    {'INTERVENED':>25}")
    for i, ((tb, pb), (ta, pa)) in enumerate(zip(result["top_baseline"],
                                                 result["top_after"])):
        marker = "   " if tb == ta else "→"
        print(f"    {i+1:>4}  {repr(tb):>18} {pb:6.3f}  {marker}  "
              f"{repr(ta):>18} {pa:6.3f}")

    print("\n    probe token probabilities (before → after):")
    for tok, (b, a, d) in sorted(result["probe_shifts"].items(),
                                 key=lambda x: -abs(x[1][2])):
        arrow = "↑" if d > 0 else "↓" if d < 0 else "="
        ratio = (a / b) if b > 1e-9 else float("inf")
        print(f"      {repr(tok):>15}  {b:.5f} → {a:.5f}  "
              f"({d:+.5f} {arrow}, ×{ratio:.2f})")


def plot_probe_shifts(all_results):
    n_tests = len(all_results)
    fig, axes = plt.subplots(n_tests, 1, figsize=(13, 3.2 * n_tests))
    if n_tests == 1:
        axes = [axes]
    for ax, r in zip(axes, all_results):
        tokens_sorted = sorted(r["probe_shifts"].items(),
                               key=lambda x: -abs(x[1][2]))
        tokens = [k for k, _ in tokens_sorted]
        before = [v[0] for _, v in tokens_sorted]
        after  = [v[1] for _, v in tokens_sorted]
        x = np.arange(len(tokens))
        w = 0.4
        ax.bar(x - w/2, before, w, label="baseline", color="steelblue", alpha=0.85)
        ax.bar(x + w/2, after,  w, label="intervened", color="tomato", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels([t.strip() or "∅" for t in tokens],
                           rotation=30, fontsize=8)
        ax.set_ylabel("P(next token)")
        ax.set_title(f"{r['test']['name']}  —  KL={r['kl']:.3f}  —  "
                     f"{len(r['test']['resolved_interventions'])} features\n"
                     f"prompt: {r['test']['text']!r}", fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "probe_shifts.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\nProbe-shift plot: {out.name}")


def plot_top_token_comparison(all_results):
    n_tests = len(all_results)
    fig, axes = plt.subplots(n_tests, 2, figsize=(15, 3.2 * n_tests))
    if n_tests == 1:
        axes = axes.reshape(1, -1)
    for i, r in enumerate(all_results):
        for j, (title, ranked) in enumerate(
            [("baseline", r["top_baseline"]),
             ("intervened", r["top_after"])]
        ):
            ax = axes[i][j]
            toks = [t.strip() or "∅" for t, _ in ranked]
            probs = [p for _, p in ranked]
            color = "steelblue" if j == 0 else "tomato"
            ax.barh(range(len(toks)), probs, color=color, alpha=0.85)
            ax.set_yticks(range(len(toks)))
            ax.set_yticklabels(toks, fontsize=7)
            ax.invert_yaxis()
            ax.set_xlabel("P(token)")
            ax.set_title(f"{r['test']['name']} — {title}", fontsize=8)
            ax.grid(True, alpha=0.3, axis="x")
    fig.tight_layout()
    out = RESULTS_DIR / "top_token_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Top-token plot: {out.name}")


def plot_kl_comparison(all_results, exp13_kl_reference=None):
    """Bar plot comparing KL across the battery; annotate vs exp 13 baselines."""
    names = [r["test"]["name"] for r in all_results]
    kls   = [r["kl"] for r in all_results]
    n_feats = [len(r["test"]["resolved_interventions"]) for r in all_results]

    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(range(len(names)), kls, color="tomato", alpha=0.85)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([n.replace("_", "\n") for n in names],
                       rotation=0, fontsize=7)
    ax.set_ylabel("KL(baseline || intervened)")
    ax.set_title("Exp 14 — KL impact of full-core vs single-feature interventions")

    # Annotate each bar with feature count
    for b, nf, k in zip(bars, n_feats, kls):
        ax.text(b.get_x() + b.get_width() / 2, k,
                f"{k:.3f}\n({nf} feats)", ha="center", va="bottom", fontsize=8)

    # Reference line for exp 13 single-feature baseline
    if exp13_kl_reference is not None:
        ax.axhline(exp13_kl_reference, color="steelblue", linestyle="--",
                   label=f"exp13 single-feature typical ≈ {exp13_kl_reference}")
        ax.legend()

    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "kl_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"KL comparison plot: {out.name}")


def write_report(all_results):
    out = RESULTS_DIR / "intervention_report.txt"
    lines = [f"Full Core Intervention Report — layer {PROBE_LAYER}",
             "=" * 70]
    for r in all_results:
        t = r["test"]
        lines.append(f"\n### {t['name']}")
        lines.append(f"  prompt     : {t['text']!r}")
        lines.append(f"  span       : {t['span']!r}  (pos={r['span_pos']})")
        lines.append(f"  mode       : {t['mode']}")
        lines.append(f"  description: {t['description']}")
        lines.append(f"  KL(baseline || intervened) = {r['kl']:.4f}")
        lines.append(f"  #features intervened: {len(t['resolved_interventions'])}")
        lines.append("\n  FEATURES INTERVENED:")
        if t["mode"] == "ablate_top_k":
            for fid, val in t["resolved_interventions"]:
                lines.append(f"    F{fid:<6d}  orig_act={val:.3f}  →  ablated")
        elif t["mode"] == "ablate":
            for (fid, _), (_, mu, label) in zip(t["resolved_interventions"],
                                                t["feature_labels"]):
                lines.append(f"    F{fid:<6d}  μ_in_core={mu:.2f}  →  ablated"
                             f"   ({label})")
        else:  # inject
            for (fid, val), (_, mu, label) in zip(t["resolved_interventions"],
                                                  t["feature_labels"]):
                lines.append(f"    F{fid:<6d}  injected@{val:.2f}  "
                             f"(core μ={mu:.2f})   ({label})")
        lines.append("\n  CONTINUATION:")
        lines.append(f"    baseline   → {r['continuation_before']!r}")
        lines.append(f"    intervened → {r['continuation_after']!r}")
        lines.append("\n  TOP BASELINE:")
        for i, (tok, p) in enumerate(r["top_baseline"]):
            lines.append(f"    {i+1:>2}. {repr(tok):>15}  {p:.4f}")
        lines.append("\n  TOP INTERVENED:")
        for i, (tok, p) in enumerate(r["top_after"]):
            lines.append(f"    {i+1:>2}. {repr(tok):>15}  {p:.4f}")
        lines.append("\n  PROBE SHIFTS (sorted by |Δ|):")
        for tok, (b, a, d) in sorted(r["probe_shifts"].items(),
                                     key=lambda x: -abs(x[1][2])):
            ratio = (a / b) if b > 1e-9 else float("inf")
            lines.append(f"    {repr(tok):>15}  {b:.5f} → {a:.5f}  "
                         f"({d:+.5f}, ×{ratio:.2f})")
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()
    tests = build_tests()

    all_results = []
    for test in tests:
        print(f"\nRunning {test['name']}...")
        result = run_test(test, model, sae)
        if result is None:
            continue
        all_results.append(result)
        print_test_result(result)

    print("\nGenerating plots...")
    plot_probe_shifts(all_results)
    plot_top_token_comparison(all_results)
    # Exp 13's single-feature KL for 999 emergency ablation was ~0.027
    plot_kl_comparison(all_results, exp13_kl_reference=0.027)
    write_report(all_results)

    # Summary
    print("\n--- Full Core Intervention Summary ---")
    print(f"{'test':<38s}  #feats  KL       biggest probe shift")
    for r in all_results:
        nf = len(r["test"]["resolved_interventions"])
        if r["probe_shifts"]:
            max_shift = max(r["probe_shifts"].items(),
                            key=lambda x: abs(x[1][2]))
            tok = repr(max_shift[0])
            d = max_shift[1][2]
        else:
            tok = "—"; d = 0.0
        print(f"  {r['test']['name']:<36s}  {nf:>5d}   {r['kl']:.4f}   "
              f"{tok:>15s}  ({d:+.4f})")

    print(f"\nAll results → {RESULTS_DIR}")


if __name__ == "__main__":
    main()
