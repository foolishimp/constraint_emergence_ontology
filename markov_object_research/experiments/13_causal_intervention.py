"""
Experiment 13: Causal Intervention — Ablating and Injecting Markov Object Features

Exp 08–12 showed SAE features correlate with interpretable object structure.
This experiment moves from correlation to causation:
  - If F2269 ("911 emergency") is a genuine component of 999's Markov object,
    ablating it should shift the model's downstream predictions away from
    emergency-themed continuations.
  - If the same feature is *injected* into 500's representation, 500 should
    behave (in next-token predictions) as if it inherited an emergency role.

This is the gold-standard test for mechanistic interpretability: does the
feature do causal work, or is it a bystander?

Method:
  - Hook the residual stream at layer 8 (where SAEs live)
  - At the target token's position, decompose resid = features @ W_dec + error
  - Modify the coefficient of a chosen feature (ablate→0, or inject→value)
  - Reconstruct modified resid = resid_orig + delta * W_dec[f]
  - Run forward pass with this hook
  - Measure next-token logits at a chosen readout position
  - Compare baseline vs intervention: top-k shifts, KL divergence

Battery:
  Test A — ABLATE 999's F2269 (emergency) → does emergency flavor drop out?
  Test B — INJECT F2269 into 500 → does 500 become emergency-colored?
  Test C — ABLATE 666's F5480 (demon) → does demonic flavor drop out?
  Test D — INJECT demon feature into 7 → does 7 become demonic?
  Test E — TRANSPLANT currency coat onto 7 → does 7 get priced?
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "13_causal_intervention"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 8
TOP_K = 12  # top next-tokens to display per condition


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
# Intervention machinery
# ---------------------------------------------------------------------------

def run_baseline(model, text):
    """Return next-token logits at the final position."""
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def run_with_intervention(model, sae, text, target_pos, interventions, layer=PROBE_LAYER):
    """
    interventions: list of (feature_id, new_value).
      new_value = 0.0 means ablate
      new_value > 0.0 means inject/boost
    Modifies residual at (target_pos, layer, hook_resid_pre).
    Returns next-token logits at FINAL position.
    """
    import torch

    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"

    def hook_fn(value, hook):
        # value: (batch, seq, d_model)
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
    """Return dict {token: (p_before, p_after, delta)}."""
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

TESTS = [
    {
        "name":   "A_ablate_999_emergency",
        "text":   "The number 999 is most associated with",
        "span":   "999",
        "feature_id": 2269,
        "feature_label": "emergency numbers '911'",
        "mode":   "ablate",
        "target_value": 0.0,
        "probes": [" emergency", " police", " fire", " call", " number",
                   " code", " god", " phone", " year", " song"],
    },
    {
        "name":   "B_inject_500_emergency",
        "text":   "The number 500 is most associated with",
        "span":   "500",
        "feature_id": 2269,
        "feature_label": "emergency numbers '911'  (INJECTED)",
        "mode":   "inject",
        "target_value": 20.0,
        "probes": [" emergency", " police", " fire", " call", " money",
                   " dollars", " years", " people", " miles", " Fortune"],
    },
    {
        "name":   "C_ablate_666_demon",
        "text":   "The number 666 is the mark of the",
        "span":   "666",
        "feature_id": 5480,
        "feature_label": "demon variations",
        "mode":   "ablate",
        "target_value": 0.0,
        "probes": [" beast", " devil", " demon", " God", " Lord", " king",
                   " number", " Antichrist", " Church", " Cross"],
    },
    {
        "name":   "D_inject_7_demon",
        "text":   "The number 7 is the mark of the",
        "span":   "7",
        "feature_id": 5480,
        "feature_label": "demon variations  (INJECTED)",
        "mode":   "inject",
        "target_value": 6.0,  # matches typical 666 firing strength
        "probes": [" beast", " devil", " demon", " God", " Lord",
                   " seven", " week", " day", " sacred", " lucky"],
    },
    {
        "name":   "E_transplant_currency_onto_7",
        "text":   "The number 7 means",
        "span":   "7",
        # A cluster of currency-context features from exp 09
        "multi_feature": [
            (14198, 10.0, "financial transactions / monetary"),
            (3785,  8.0,  "numerical quantities with units"),
            (20169, 8.0,  "price and economic factors"),
            (20799, 5.0,  "product prices, various currencies"),
        ],
        "feature_label": "CURRENCY CLUSTER (INJECTED)",
        "mode":   "inject_cluster",
        "probes": [" dollars", " cents", " pounds", " euros", " money",
                   " price", " years", " lucky", " God", " digits"],
    },
]


def run_test(test, model, sae):
    text = test["text"]
    pos = last_token_of_span(model, text, test["span"])
    if pos is None:
        print(f"  [{test['name']}] span '{test['span']}' not found in '{text}'")
        return None

    # Baseline
    logits_b = run_baseline(model, text)

    # Intervention
    if test["mode"] == "inject_cluster":
        interventions = [(fid, val) for fid, val, _ in test["multi_feature"]]
    else:
        interventions = [(test["feature_id"], test["target_value"])]

    logits_i = run_with_intervention(model, sae, text, pos, interventions)

    top_b = top_k_tokens(model, logits_b)
    top_i = top_k_tokens(model, logits_i)

    kl = kl_divergence(logits_b, logits_i)
    probe_shifts = measure_token_prob_shift(model, logits_b, logits_i, test["probes"])

    return {
        "test":         test,
        "span_pos":     pos,
        "top_baseline": top_b,
        "top_after":    top_i,
        "kl":           kl,
        "probe_shifts": probe_shifts,
    }


# ---------------------------------------------------------------------------
# Reporting / plots
# ---------------------------------------------------------------------------

def print_test_result(result):
    t = result["test"]
    print(f"\n### {t['name']}")
    print(f"    prompt : '{t['text']}'")
    print(f"    span   : '{t['span']}' (pos={result['span_pos']})")
    print(f"    feature: {t['feature_label']}")
    print(f"    mode   : {t['mode']}  target={t.get('target_value','cluster')}")
    print(f"    KL(baseline || intervened) = {result['kl']:.3f}")
    print("\n    top next-token shift:")
    print(f"    {'rank':>4}  {'BASELINE':>20}  {'INTERVENED':>20}")
    for i, ((tb, pb), (ta, pa)) in enumerate(zip(result["top_baseline"], result["top_after"])):
        marker = "   " if tb == ta else "-->"
        print(f"    {i+1:>4}  {repr(tb):>15} {pb:6.3f}  {marker}  {repr(ta):>15} {pa:6.3f}")
    print("\n    probe token probabilities (before → after):")
    for tok, (b, a, d) in sorted(result["probe_shifts"].items(), key=lambda x: -abs(x[1][2])):
        arrow = "↑" if d > 0 else "↓" if d < 0 else "="
        print(f"      {repr(tok):>15}  {b:.4f} → {a:.4f}  ({d:+.4f} {arrow})")


def plot_probe_shifts(all_results):
    """Grouped bar: for each test, probe-token prob before vs after."""
    n_tests = len(all_results)
    fig, axes = plt.subplots(n_tests, 1, figsize=(12, 3.2 * n_tests))
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
        ax.bar(x - w/2, before, w, label="baseline", color="steelblue", alpha=0.8)
        ax.bar(x + w/2, after,  w, label="intervened", color="tomato", alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([t.strip() or "∅" for t in tokens], rotation=30, fontsize=8)
        ax.set_ylabel("Next-token probability")
        ax.set_title(f"{r['test']['name']}  —  "
                     f"KL={r['kl']:.3f}  —  {r['test']['feature_label']}\n"
                     f"prompt: '{r['test']['text']}'",
                     fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "probe_shifts.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\nProbe-shift plot: {out.name}")


def plot_top_token_comparison(all_results):
    """Side-by-side top-k bars per test."""
    n_tests = len(all_results)
    fig, axes = plt.subplots(n_tests, 2, figsize=(14, 3 * n_tests))
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
            ax.barh(range(len(toks)), probs, color=color, alpha=0.8)
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
    print(f"Top-token comparison: {out.name}")


def write_report(all_results):
    out = RESULTS_DIR / "intervention_report.txt"
    lines = [f"Causal Intervention Report — layer {PROBE_LAYER}", "=" * 70]
    for r in all_results:
        t = r["test"]
        lines.append(f"\n### {t['name']}")
        lines.append(f"  prompt : '{t['text']}'")
        lines.append(f"  span   : '{t['span']}' (pos={r['span_pos']})")
        lines.append(f"  feature: {t['feature_label']}")
        lines.append(f"  mode   : {t['mode']}  target={t.get('target_value','cluster')}")
        lines.append(f"  KL(baseline || intervened) = {r['kl']:.3f}")
        lines.append("\n  TOP BASELINE:")
        for i, (tok, p) in enumerate(r["top_baseline"]):
            lines.append(f"    {i+1:>2}. {repr(tok):>15}  {p:.4f}")
        lines.append("\n  TOP INTERVENED:")
        for i, (tok, p) in enumerate(r["top_after"]):
            lines.append(f"    {i+1:>2}. {repr(tok):>15}  {p:.4f}")
        lines.append("\n  PROBE SHIFTS (sorted by |Δ|):")
        for tok, (b, a, d) in sorted(r["probe_shifts"].items(), key=lambda x: -abs(x[1][2])):
            lines.append(f"    {repr(tok):>15}  {b:.4f} → {a:.4f}  ({d:+.4f})")
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()

    all_results = []
    for test in TESTS:
        print(f"\nRunning {test['name']}...")
        result = run_test(test, model, sae)
        if result is None:
            continue
        all_results.append(result)
        print_test_result(result)

    print("\nGenerating plots...")
    plot_probe_shifts(all_results)
    plot_top_token_comparison(all_results)
    write_report(all_results)

    # Summary
    print("\n--- Causal Intervention Summary ---")
    print(f"{'test':<35s}  KL     max |Δ|  probe shifted (biggest)")
    for r in all_results:
        max_shift = max(r["probe_shifts"].items(), key=lambda x: abs(x[1][2]))
        print(f"  {r['test']['name']:<33s}  {r['kl']:.3f}   "
              f"{abs(max_shift[1][2]):.4f}  {repr(max_shift[0])}")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
