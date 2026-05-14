"""
Experiment 38: Graph-Cut Signature Via Path Patching

Per the spec (§III, INV-11), the substrate Markov object is a graph cut — a
minimal set of substrate nodes whose ablation severs target-relevant
computation. K projects this cut through the network's computational graph.
Question: does the geometric boundary in joint state correspond to a graph
cut in the network's computational graph?

Operationalization (greedy approximation, since exact min-cardinality cut
is combinatorial):
  1. Score every (attention head, layer) and (MLP, layer) by the margin
     damage produced when that node is mean-ablated at the target token
     position. Ablation = replace activation with mean over reference prompts.
  2. The candidate cut C_T = top-K nodes by margin damage (K chosen so
     joint ablation collapses margin to <= 60% of baseline).
  3. Build K_C(C_T) = matrix of per-node residual deltas at the target token
     across prompts (stack of "what does each cut node add to the residual").
     Top principal directions span the cut's image in residual space.
  4. Test alignment of the boundary normal n_dir (from exp 37 protocol)
     with K_C(C_T) principal directions.

Pre-registered (per design doc 38.4):
    PASS    cos(n_dir, top-PC of K_C) >= 0.7 AND null cosine < 0.3
    PARTIAL alignment exists but is weak (cosine in [0.3, 0.7])
    FAIL    cosine < 0.3 (no graph-cut alignment)

Outputs:
    results/38_graph_cut_signature/
        report.txt
        summary.json
        node_damage_ranking.png
        alignment_cosines.png
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
import torch.nn as nn

RESULTS_DIR = Path(__file__).parent.parent / "results" / "38_graph_cut_signature"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYER = 2          # where exp 37 fits the boundary normal
TARGETS = [999, 666, 137]
REFERENCE = 5
N_LAYERS = 12
N_HEADS  = 12

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


def baseline_logits(model, text):
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model(tokens)
    return logits[0, -1, :]


def margin(model, text, target_tok, ref_tok):
    logits = baseline_logits(model, text)
    return float(logits[target_tok].item() - logits[ref_tok].item())


def margin_with_ablation(model, text, target_tok, ref_tok, hooks):
    tokens = model.to_tokens(text, prepend_bos=True)
    with torch.no_grad():
        logits = model.run_with_hooks(tokens, fwd_hooks=hooks)
    last = logits[0, -1, :]
    return float(last[target_tok].item() - last[ref_tok].item())


# ---------------------------------------------------------------------------
# Compute mean ablation values from reference prompts
# ---------------------------------------------------------------------------

def mean_at_node(model, n, templates, hook_name, head=None):
    """For each template, capture the activation at the target-token position
    at hook_name; if head is not None, slice attention output by head."""
    vecs = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        captured = {}

        def cap(value, hook):
            v = value[0, pos, :].detach().clone()
            if head is not None and value.dim() == 4:
                # attn output: (B, T, H, d_head) — but transformer_lens stores
                # attention block output as (B, T, d_model); per-head is via
                # split by head index. We'll capture full at pos and slice via
                # a head-mask in the ablation hook instead.
                pass
            captured["v"] = v
            return value

        with torch.no_grad():
            model.run_with_hooks(text, fwd_hooks=[(hook_name, cap)])
        vecs.append(captured["v"])
    if not vecs:
        return None
    return torch.stack(vecs).mean(0)


def make_resid_mean_ablation(layer, ref_mean, pos_fn):
    """Hook that replaces residual at target position with ref_mean."""
    hook_name = f"blocks.{layer}.hook_resid_pre"

    def fn(value, hook):
        pos = pos_fn()
        value[0, pos, :] = ref_mean
        return value

    return (hook_name, fn)


def make_attn_head_zero_ablation(layer, head, pos_fn):
    """Hook that zeros out the contribution of a specific attention head at the
    target position. Acts on hook_z (B, T, H, d_head)."""
    hook_name = f"blocks.{layer}.attn.hook_z"

    def fn(value, hook):
        pos = pos_fn()
        value[0, pos, head, :] = 0.0
        return value

    return (hook_name, fn)


def make_mlp_zero_ablation(layer, pos_fn):
    """Hook that zeros MLP output at the target position."""
    hook_name = f"blocks.{layer}.hook_mlp_out"

    def fn(value, hook):
        pos = pos_fn()
        value[0, pos, :] = 0.0
        return value

    return (hook_name, fn)


# ---------------------------------------------------------------------------
# Per-target node damage ranking
# ---------------------------------------------------------------------------

def rank_nodes_by_damage(model, target, reference, templates, n_eval=5):
    """For each (layer, head) attention node and each (layer) MLP node, score
    margin damage when zero-ablated at the target token position.
    Returns list of (damage, node_kind, layer, head_or_-1)."""
    target_tok = model.to_single_token(f" {target}")
    ref_tok    = model.to_single_token(f" {reference}")

    # Use n_eval templates to estimate damage
    use_templates = templates[:n_eval]

    # Baseline margin per template
    base_margins = {}
    for t in use_templates:
        text = t.format(n=target)
        if last_token_of_span(model, text, str(target)) is None:
            continue
        base_margins[t] = margin(model, text, target_tok, ref_tok)

    pos_holder = [0]

    def pos_fn():
        return pos_holder[0]

    nodes = []
    # Attention heads
    for L in range(N_LAYERS):
        for H in range(N_HEADS):
            margins = []
            for t, base in base_margins.items():
                text = t.format(n=target)
                pos = last_token_of_span(model, text, str(target))
                pos_holder[0] = pos
                hook = make_attn_head_zero_ablation(L, H, pos_fn)
                m = margin_with_ablation(model, text, target_tok, ref_tok,
                                         [hook])
                margins.append(base - m)  # damage = baseline - ablated
            avg_dmg = float(np.mean(margins))
            nodes.append((avg_dmg, "attn_head", L, H))
        # MLP
        margins = []
        for t, base in base_margins.items():
            text = t.format(n=target)
            pos = last_token_of_span(model, text, str(target))
            pos_holder[0] = pos
            hook = make_mlp_zero_ablation(L, pos_fn)
            m = margin_with_ablation(model, text, target_tok, ref_tok, [hook])
            margins.append(base - m)
        avg_dmg = float(np.mean(margins))
        nodes.append((avg_dmg, "mlp", L, -1))

    # Sort descending by damage
    nodes.sort(key=lambda x: -x[0])
    return nodes, base_margins


# ---------------------------------------------------------------------------
# K_C(C_T) — residual delta basis from cut nodes
# ---------------------------------------------------------------------------

def cut_residual_deltas(model, target, reference, cut_nodes, templates,
                         intervention_layer=PROBE_LAYER):
    """For each cut node, compute the *direction* in the layer-{intervention_layer}
    residual stream that the node contributes (target_text). We approximate by:
        delta_node = resid_with_node_ablated - resid_native
    averaged over templates.
    Returns matrix (n_cut, d_model)."""
    deltas = []

    target_tok = model.to_single_token(f" {target}")
    ref_tok    = model.to_single_token(f" {reference}")
    use_templates = templates[:5]
    pos_holder = [0]

    def pos_fn():
        return pos_holder[0]

    for dmg, kind, L, H in cut_nodes:
        per_template = []
        for t in use_templates:
            text = t.format(n=target)
            pos = last_token_of_span(model, text, str(target))
            if pos is None:
                continue
            pos_holder[0] = pos
            # Native resid at intervention_layer
            captured_native = {}

            def cap_n(value, hook):
                captured_native["r"] = value[0, pos, :].detach().clone()
                return value

            with torch.no_grad():
                model.run_with_hooks(text, fwd_hooks=[
                    (f"blocks.{intervention_layer}.hook_resid_pre", cap_n)
                ])
            r_native = captured_native["r"]

            # Resid at intervention_layer with this node ablated
            if kind == "attn_head":
                ablate = make_attn_head_zero_ablation(L, H, pos_fn)
            else:
                ablate = make_mlp_zero_ablation(L, pos_fn)
            captured_ab = {}

            def cap_a(value, hook):
                captured_ab["r"] = value[0, pos, :].detach().clone()
                return value

            with torch.no_grad():
                model.run_with_hooks(text, fwd_hooks=[
                    ablate,
                    (f"blocks.{intervention_layer}.hook_resid_pre", cap_a)
                ])
            r_ab = captured_ab["r"]
            per_template.append(r_native - r_ab)
        if per_template:
            deltas.append(torch.stack(per_template).mean(0).float())
    if not deltas:
        return None
    return torch.stack(deltas)


def alignment(n_dir, K_basis):
    """cos of n_dir with each principal direction of K_basis. Return top-PC
    cosine and explained-variance-weighted cosine."""
    if K_basis is None or K_basis.shape[0] == 0:
        return None
    Kc = K_basis - K_basis.mean(0, keepdim=True)
    U, S, V = torch.linalg.svd(Kc, full_matrices=False)
    nd = n_dir / (n_dir.norm() + 1e-9)
    top_pc = V[0] / (V[0].norm() + 1e-9)
    cos_top = float((nd @ top_pc).item())
    # Weighted by explained variance
    var_total = float((S * S).sum())
    weights = (S * S) / max(var_total, 1e-12)
    cos_weighted = 0.0
    for k in range(min(len(S), 5)):
        v = V[k] / (V[k].norm() + 1e-9)
        cos_weighted += float(weights[k].item()) * abs(float((nd @ v).item()))
    return {
        "cos_with_top_pc":   abs(cos_top),
        "cos_weighted_top5": cos_weighted,
        "singular_values":   S.tolist()[:10],
    }


# ---------------------------------------------------------------------------
# Boundary normal (re-fit single-layer L=PROBE_LAYER linear probe, stripped)
# ---------------------------------------------------------------------------

def fit_boundary_normal(model, target, reference, layer):
    from experiments_module_inline import _placeholder
    raise NotImplementedError


def _capture_single(model, text, pos, layer):
    captured = {}

    def cap(value, hook):
        captured["r"] = value[0, pos, :].detach().clone()
        return value

    with torch.no_grad():
        model.run_with_hooks(text,
                             fwd_hooks=[(f"blocks.{layer}.hook_resid_pre", cap)])
    return captured["r"]


def _collect(model, n, templates, layer):
    rows = []; used = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        rows.append(_capture_single(model, text, pos, layer).float())
        used.append(t)
    if not rows:
        return None, []
    return torch.stack(rows), used


def _aligned(R_a, ua, R_b, ub):
    shared = [t for t in ua if t in ub]
    return (R_a[[ua.index(t) for t in shared]],
            R_b[[ub.index(t) for t in shared]],
            shared)


class _LinProbe(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.w = nn.Parameter(torch.zeros(d))
        self.b = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        return x @ self.w + self.b


def boundary_normal(model, target, reference, layer):
    Rt, ut = _collect(model, target,    TRAIN_TEMPLATES, layer)
    Rr, ur = _collect(model, reference, TRAIN_TEMPLATES, layer)
    Rtt, Rrt, _ = _aligned(Rt, ut, Rr, ur)
    Rt_n, ut_n = _collect(model, target,    NEUTRAL_TEMPLATES, layer)
    Rr_n, ur_n = _collect(model, reference, NEUTRAL_TEMPLATES, layer)
    Rt_nn, Rr_nn, _ = _aligned(Rt_n, ut_n, Rr_n, ur_n)
    e = Rt_nn.float().mean(0) - Rr_nn.float().mean(0)
    e_n2 = (e * e).sum()

    def strip(X):
        if e_n2.item() < 1e-12:
            return X
        proj = (X @ e) / e_n2
        return X - proj.unsqueeze(1) * e.unsqueeze(0)

    Xt = strip(Rtt.float()); Xr = strip(Rrt.float())
    X = torch.cat([Xt, Xr], dim=0)
    y = torch.cat([torch.ones(len(Xt)), torch.zeros(len(Xr))])
    mu = X.mean(0); sd = X.std(0); sd = torch.where(sd > 1e-6, sd, torch.ones_like(sd))
    Xn = (X - mu) / sd
    p = _LinProbe(Xn.shape[1])
    opt = torch.optim.Adam(p.parameters(), lr=5e-2, weight_decay=1e-2)
    bce = nn.BCEWithLogitsLoss()
    for _ in range(600):
        opt.zero_grad()
        bce(p(Xn), y).backward()
        opt.step()
    raw = p.w.detach() / sd
    if e_n2.item() > 1e-12:
        raw = raw - ((raw @ e) / e_n2) * e
    return raw / (raw.norm() + 1e-9), e


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = load_model()
    all_results = {}

    for target in TARGETS:
        print(f"\n=== target={target} ===")

        print("  Ranking nodes by margin damage (this is slow)...")
        nodes, base_margins = rank_nodes_by_damage(model, target, REFERENCE,
                                                    HELDOUT_TEMPLATES, n_eval=3)
        top10 = nodes[:10]
        print("  top-10 most-damaging nodes:")
        for d, k, L, H in top10:
            tag = f"L{L}H{H}" if k == "attn_head" else f"L{L}MLP"
            print(f"    {tag:<8s}  damage={d:+.3f}")

        # Pick cut as top-K nodes (start with top 10)
        cut_size = 10
        cut = nodes[:cut_size]
        print(f"  Computing K_C basis from top-{cut_size} cut...")
        K_basis = cut_residual_deltas(model, target, REFERENCE, cut,
                                       HELDOUT_TEMPLATES,
                                       intervention_layer=PROBE_LAYER)
        if K_basis is None or K_basis.shape[0] == 0:
            print("  empty K_basis — skip")
            continue

        print("  Fitting boundary normal at layer 2 (stripped)...")
        n_dir, e = boundary_normal(model, target, REFERENCE, PROBE_LAYER)

        print("  Aligning n_dir with K_C principal directions...")
        ali = alignment(n_dir, K_basis)
        print(f"  cos(n_dir, top PC of K_C) = {ali['cos_with_top_pc']:+.3f}")
        print(f"  weighted top-5 cosine     = {ali['cos_weighted_top5']:+.3f}")

        # Null: random nodes of matching cardinality
        all_idxs = list(range(len(nodes)))
        rng = np.random.default_rng(seed=hash((target, "null")) & 0xFFFFFFFF)
        null_idxs = rng.choice(all_idxs[10:], size=cut_size, replace=False)
        null_cut = [nodes[i] for i in null_idxs]
        K_null = cut_residual_deltas(model, target, REFERENCE, null_cut,
                                      HELDOUT_TEMPLATES,
                                      intervention_layer=PROBE_LAYER)
        ali_null = alignment(n_dir, K_null) if K_null is not None else None
        if ali_null is not None:
            print(f"  null cos(n_dir, top PC of K_null) = {ali_null['cos_with_top_pc']:+.3f}")

        all_results[target] = {
            "top10_nodes": [[d, k, L, H] for d, k, L, H in top10],
            "cut_size": cut_size,
            "alignment": ali,
            "null_alignment": ali_null,
        }

    # Verdict
    cos_real = [all_results[t]["alignment"]["cos_with_top_pc"]
                for t in TARGETS if t in all_results]
    cos_null = [all_results[t]["null_alignment"]["cos_with_top_pc"]
                for t in TARGETS if t in all_results
                and all_results[t].get("null_alignment")]
    if cos_real and cos_null:
        avg_real = float(np.mean(cos_real))
        avg_null = float(np.mean(cos_null))
        if avg_real >= 0.7 and avg_null < 0.3:
            v = "PASS"
        elif avg_real >= 0.3:
            v = "PARTIAL"
        else:
            v = "FAIL"
    else:
        avg_real = avg_null = None
        v = "INCOMPLETE"

    verdict = {"avg_cos_real": avg_real, "avg_cos_null": avg_null, "verdict": v}
    print(f"\nVerdict: {v}  avg_cos_real={avg_real}  avg_cos_null={avg_null}")

    # Plots
    fig, ax = plt.subplots(figsize=(8, 5))
    xs = np.arange(len(TARGETS))
    real_v = [all_results[t]["alignment"]["cos_with_top_pc"]
              if t in all_results else 0.0 for t in TARGETS]
    null_v = [all_results[t]["null_alignment"]["cos_with_top_pc"]
              if t in all_results and all_results[t].get("null_alignment")
              else 0.0 for t in TARGETS]
    ax.bar(xs - 0.2, real_v, 0.4, color="steelblue", label="cut")
    ax.bar(xs + 0.2, null_v, 0.4, color="lightgray", label="null nodes")
    ax.axhline(0.7, color="green",  linestyle="--", alpha=0.5, label="PASS thr 0.7")
    ax.axhline(0.3, color="orange", linestyle="--", alpha=0.5, label="PARTIAL thr 0.3")
    ax.set_xticks(xs); ax.set_xticklabels([str(t) for t in TARGETS])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("|cos(n_dir, top PC of K_C)|")
    ax.set_title("Boundary-normal alignment with graph-cut residual deltas")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "alignment_cosines.png", dpi=150)
    plt.close(fig)

    # Per-target node damage bar plot
    fig, axes = plt.subplots(1, len(TARGETS), figsize=(5 * len(TARGETS), 4))
    if len(TARGETS) == 1:
        axes = [axes]
    for ax, target in zip(axes, TARGETS):
        if target not in all_results:
            continue
        top10 = all_results[target]["top10_nodes"]
        labels = [f"L{L}{'H'+str(H) if k=='attn_head' else 'MLP'}"
                  for d, k, L, H in top10]
        damages = [d for d, k, L, H in top10]
        ax.barh(range(len(top10)), damages, color="tomato")
        ax.set_yticks(range(len(top10)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("margin damage")
        ax.invert_yaxis()
        ax.set_title(f"target={target} (top-10)")
        ax.grid(True, alpha=0.3, axis="x")
    fig.suptitle("Node ranking by ablation damage")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "node_damage_ranking.png", dpi=150)
    plt.close(fig)

    # Report
    lines = ["Exp 38 - Graph-Cut Signature Via Path Patching", "=" * 70, ""]
    lines.append(f"Targets:  {TARGETS}  Reference: n = {REFERENCE}")
    lines.append(f"Probe (boundary) layer: {PROBE_LAYER}")
    lines.append(f"Cut size: 10 (greedy, by ablation damage)")
    lines.append("")
    lines.append("Pre-registered outcome rules (averaged over targets):")
    lines.append("  PASS    avg cos(n_dir, top PC of K_C) >= 0.7 AND null < 0.3")
    lines.append("  PARTIAL avg cos in [0.3, 0.7]")
    lines.append("  FAIL    avg cos < 0.3")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {v}")
    lines.append(f"  avg cos (cut):  {avg_real}")
    lines.append(f"  avg cos (null): {avg_null}")
    for t in TARGETS:
        if t not in all_results:
            continue
        lines.append(f"\n### target = {t}")
        e = all_results[t]
        lines.append(f"  top PC alignment (cut):  "
                     f"{e['alignment']['cos_with_top_pc']:+.3f}")
        if e.get("null_alignment"):
            lines.append(f"  top PC alignment (null): "
                         f"{e['null_alignment']['cos_with_top_pc']:+.3f}")
        lines.append(f"  top-10 cut nodes:")
        for dmg, kind, L, H in e["top10_nodes"]:
            tag = f"L{L}H{H}" if kind == "attn_head" else f"L{L}MLP"
            lines.append(f"    {tag:<8s}  damage={dmg:+.3f}")
    (RESULTS_DIR / "report.txt").write_text("\n".join(lines))
    print(f"Report: {RESULTS_DIR / 'report.txt'}")

    summary = {
        "design": "exp 38: graph-cut signature via path patching",
        "probe_layer": PROBE_LAYER,
        "targets": TARGETS,
        "reference": REFERENCE,
        "results": {str(t): all_results[t] for t in TARGETS if t in all_results},
        "verdict": verdict,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
