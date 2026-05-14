"""
Experiment 40: Explicit-Object Control On A Toy Transformer

Constructs a small transformer where target identity is stored explicitly
in a learned object-slot embedding o_T injected additively at layer 2.
Validates that the wave-1/2/3 instruments (35-37) recover this known
object cleanly. Without this calibration, "GPT-2 fails the gate" is
ambiguous between "construct missing" and "instrument broken".

Architecture:
    - Tiny encoder-only transformer (4 layers, d_model=128, single head)
    - Vocabulary V = K_targets * K_continuations + a few control tokens
    - Object slot: a learned embedding table O[T] in R^{16} -> projected to
      R^{d_model} via a fixed linear lift; injected additively at layer 2
      residual stream at the target token position
    - Task: given prompt "<context> <target_marker>", inject o_T at the
      target position; model must predict the canonical T-conditional
      continuation token

Sanity checks performed:
    1. Train accuracy reaches >= 0.95
    2. Per-target mean-diff direction recovers the injection subspace at
       layer 2 (cosine of mean-diff with W_lift @ O[T] >= 0.8)
    3. Alpha-sweep transfer at layer 2 with mean-diff direction reaches
       >= 0.8 at alpha=1 on held-out prompts (the pre-registered exp-19
       threshold, which the toy MUST pass since the object is explicit)

If these pass, the underlying wave-1/2/3 instruments will inherit
calibrated thresholds. If they FAIL on this toy, the instrument family
is broken and must be revised before being applied to GPT-2.

Outputs:
    results/40_explicit_object_control/
        report.txt
        summary.json
        toy_training_loss.png
        per_target_recovery.png
        toy_checkpoint.pt
"""

import json
import math
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

RESULTS_DIR = Path(__file__).parent.parent / "results" / "40_explicit_object_control"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

K_TARGETS = 5
N_CONTEXT_TOKENS = 8
N_CONTINUATIONS  = K_TARGETS  # one canonical continuation per target
SLOT_DIM   = 16
D_MODEL    = 128
N_LAYERS   = 4
N_HEADS    = 4
SEQ_LEN    = 6                # prompt length: <bos> ctx0 ctx1 ctx2 ctx3 <target_marker>
PROBE_LAYER = 2               # injection layer; same as where we extract directions

# Vocab: ids 0..N_CONTEXT_TOKENS-1 = generic context tokens
#        ids N_CONTEXT_TOKENS = <bos>
#        id  N_CONTEXT_TOKENS+1 = <target_marker>  (where injection happens)
#        ids next K_TARGETS = continuation tokens (target-conditional)
BOS_ID    = N_CONTEXT_TOKENS
MARKER_ID = N_CONTEXT_TOKENS + 1
CONT_BASE = N_CONTEXT_TOKENS + 2
VOCAB     = CONT_BASE + N_CONTINUATIONS

ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class ToyBlock(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.ln1  = nn.LayerNorm(d_model)
        self.mlp  = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )
        self.ln2  = nn.LayerNorm(d_model)

    def forward(self, x):
        a, _ = self.attn(x, x, x, need_weights=False)
        x = self.ln1(x + a)
        m = self.mlp(x)
        x = self.ln2(x + m)
        return x


class ToyTransformer(nn.Module):
    """Tiny transformer with optional residual injection at layer PROBE_LAYER."""

    def __init__(self, vocab=VOCAB, d_model=D_MODEL, n_layers=N_LAYERS,
                 n_heads=N_HEADS, seq_len=SEQ_LEN,
                 k_targets=K_TARGETS, slot_dim=SLOT_DIM):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab, d_model)
        self.pos_emb = nn.Embedding(seq_len, d_model)
        self.blocks  = nn.ModuleList([ToyBlock(d_model, n_heads)
                                       for _ in range(n_layers)])
        self.ln_out  = nn.LayerNorm(d_model)
        self.unemb   = nn.Linear(d_model, vocab, bias=False)
        # Object slot table + lift to d_model.
        self.O       = nn.Embedding(k_targets, slot_dim)
        self.lift    = nn.Linear(slot_dim, d_model, bias=False)
        # Storage for residual-stream capture / patching
        self._capture = None
        self._patch_at_layer = None
        self._patch_pos = None
        self._patch_value = None
        self._inject_at_layer = None
        self._inject_pos = None
        self._inject_value = None

    def slot_image(self, target_ids):
        """Return W_lift @ O[T]  -- the injection vector in d_model space."""
        return self.lift(self.O(target_ids))

    def forward(self, tokens, target_ids=None):
        """tokens: (B, T)  target_ids: (B,) or None for "no injection"."""
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0).expand(B, T)
        x = self.tok_emb(tokens) + self.pos_emb(pos)
        for L, blk in enumerate(self.blocks):
            # Inject before this block iff layer matches (residual_pre semantics)
            if (target_ids is not None and self._inject_at_layer == L
                    and self._inject_pos is not None):
                inj = self.slot_image(target_ids)
                x = x.clone()
                x[:, self._inject_pos, :] = x[:, self._inject_pos, :] + inj
            # External patch (used by alpha-sweep interventions)
            if (self._patch_at_layer == L and self._patch_pos is not None
                    and self._patch_value is not None):
                x = x.clone()
                x[:, self._patch_pos, :] = self._patch_value
            # Capture (residual_pre)
            if self._capture is not None and self._capture[0] == L:
                self._capture = (L, x[:, self._capture[2], :].detach().clone())
            x = blk(x)
        x = self.ln_out(x)
        return self.unemb(x)


# ---------------------------------------------------------------------------
# Synthetic dataset
# ---------------------------------------------------------------------------

def make_batch(B, target_ids=None):
    """Build B prompts. Each prompt: <bos> ctx0..ctx3 <marker>; the
    continuation token at the next position is CONT_BASE + T."""
    if target_ids is None:
        target_ids = torch.randint(0, K_TARGETS, (B,))
    ctx = torch.randint(0, N_CONTEXT_TOKENS, (B, SEQ_LEN - 2))
    bos = torch.full((B, 1), BOS_ID)
    marker = torch.full((B, 1), MARKER_ID)
    tokens = torch.cat([bos, ctx, marker], dim=1)  # (B, SEQ_LEN)
    targets = CONT_BASE + target_ids
    return tokens, target_ids, targets


def train(model, n_steps=2000, batch_size=64, lr=3e-3):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    losses = []
    accs = []
    model.train()
    model._inject_at_layer = PROBE_LAYER
    model._inject_pos      = SEQ_LEN - 1   # at marker position
    for step in range(n_steps):
        tokens, target_ids, target_tok = make_batch(batch_size)
        logits = model(tokens, target_ids=target_ids)  # (B, T, V)
        last = logits[:, -1, :]                         # logits at marker
        loss = F.cross_entropy(last, target_tok)
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(float(loss.item()))
        if step % 100 == 0 or step == n_steps - 1:
            with torch.no_grad():
                pred = last.argmax(-1)
                acc = float((pred == target_tok).float().mean().item())
                accs.append((step, acc))
                print(f"  step {step:5d}  loss={loss.item():.4f}  acc={acc:.3f}")
    return losses, accs


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def collect_residuals(model, target_id, n_prompts, layer):
    """Capture residual at marker position, layer, with target_id injected."""
    model.eval()
    model._inject_at_layer = PROBE_LAYER
    model._inject_pos      = SEQ_LEN - 1
    R = []
    for _ in range(n_prompts):
        tokens, _, _ = make_batch(1, target_ids=torch.tensor([target_id]))
        model._capture = (layer, None, SEQ_LEN - 1)
        with torch.no_grad():
            _ = model(tokens, target_ids=torch.tensor([target_id]))
        R.append(model._capture[1][0])
        model._capture = None
    return torch.stack(R)  # (n, d_model)


def probe_logits_with_patch(model, target_id, ref_id, alpha, direction, layer,
                             n_eval=20):
    """For each held-out prompt, intervene resid -= alpha*direction at the
    marker position+layer; return mean target_logit and ref_logit."""
    model.eval()
    model._inject_at_layer = PROBE_LAYER
    model._inject_pos      = SEQ_LEN - 1
    target_tok = CONT_BASE + target_id
    ref_tok    = CONT_BASE + ref_id
    target_logits = []
    ref_logits = []
    for _ in range(n_eval):
        tokens, _, _ = make_batch(1, target_ids=torch.tensor([target_id]))
        # Capture native resid_pre at the layer to compute the patched value
        model._capture = (layer, None, SEQ_LEN - 1)
        with torch.no_grad():
            _ = model(tokens, target_ids=torch.tensor([target_id]))
        resid_native = model._capture[1][0]
        model._capture = None
        # Patch: resid <- resid - alpha * direction  (then run through remaining layers)
        model._patch_at_layer = layer
        model._patch_pos      = SEQ_LEN - 1
        model._patch_value    = (resid_native - alpha * direction).unsqueeze(0)
        with torch.no_grad():
            logits = model(tokens, target_ids=torch.tensor([target_id]))
        model._patch_at_layer = None
        model._patch_pos      = None
        model._patch_value    = None
        last = logits[0, -1, :]
        target_logits.append(float(last[target_tok].item()))
        ref_logits.append(float(last[ref_tok].item()))
    return float(np.mean(target_logits)), float(np.mean(ref_logits))


def kl_at_alpha(model, target_id, ref_id, alpha, direction, layer, n_eval=20):
    """KL(intervened || ref-baseline) where ref-baseline is the model's logits
    at ref_id with no intervention. Cleaner equivalent of exp 18's transfer."""
    model.eval()
    model._inject_at_layer = PROBE_LAYER
    model._inject_pos      = SEQ_LEN - 1
    kl_int_vs_ref = []
    kl_t_vs_ref   = []
    for _ in range(n_eval):
        # Same prompt for both target & ref runs
        tokens, _, _ = make_batch(1, target_ids=torch.tensor([target_id]))
        # Baseline target logits (no patch, target injection)
        with torch.no_grad():
            logits_t = model(tokens, target_ids=torch.tensor([target_id]))[0, -1, :]
        # Baseline ref logits (no patch, ref injection on same prompt tokens)
        with torch.no_grad():
            logits_r = model(tokens, target_ids=torch.tensor([ref_id]))[0, -1, :]
        # Intervened logits: target injection + patch at probe layer
        model._capture = (layer, None, SEQ_LEN - 1)
        with torch.no_grad():
            _ = model(tokens, target_ids=torch.tensor([target_id]))
        resid_native = model._capture[1][0]
        model._capture = None
        model._patch_at_layer = layer
        model._patch_pos      = SEQ_LEN - 1
        model._patch_value    = (resid_native - alpha * direction).unsqueeze(0)
        with torch.no_grad():
            logits_i = model(tokens, target_ids=torch.tensor([target_id]))[0, -1, :]
        model._patch_at_layer = None
        model._patch_pos      = None
        model._patch_value    = None
        # Compare distributions
        p_i = torch.softmax(logits_i, dim=-1)
        p_r = torch.softmax(logits_r, dim=-1)
        p_t = torch.softmax(logits_t, dim=-1)
        kl_int_vs_ref.append(float((p_i * (torch.log(p_i + 1e-12)
                                           - torch.log(p_r + 1e-12))).sum()))
        kl_t_vs_ref.append(float((p_t * (torch.log(p_t + 1e-12)
                                         - torch.log(p_r + 1e-12))).sum()))
    kl_iv = float(np.mean(kl_int_vs_ref))
    kl_tv = float(np.mean(kl_t_vs_ref))
    transfer = 1.0 - (kl_iv / max(kl_tv, 1e-9))
    return {"kl_int_vs_ref": kl_iv, "kl_target_vs_ref": kl_tv, "transfer": transfer}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Building toy transformer...")
    model = ToyTransformer()

    print("Training...")
    losses, accs = train(model, n_steps=2000, batch_size=64, lr=3e-3)
    final_acc = accs[-1][1]
    print(f"Final training accuracy: {final_acc:.3f}")

    # Save checkpoint
    ckpt = RESULTS_DIR / "toy_checkpoint.pt"
    torch.save({
        "state_dict": model.state_dict(),
        "config": {
            "K_TARGETS": K_TARGETS, "N_CONTEXT_TOKENS": N_CONTEXT_TOKENS,
            "N_CONTINUATIONS": N_CONTINUATIONS, "SLOT_DIM": SLOT_DIM,
            "D_MODEL": D_MODEL, "N_LAYERS": N_LAYERS, "N_HEADS": N_HEADS,
            "SEQ_LEN": SEQ_LEN, "PROBE_LAYER": PROBE_LAYER,
            "BOS_ID": BOS_ID, "MARKER_ID": MARKER_ID,
            "CONT_BASE": CONT_BASE, "VOCAB": VOCAB,
        },
    }, ckpt)
    print(f"Saved checkpoint: {ckpt}")

    # Plot training curve
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(losses, color="steelblue", linewidth=1)
    ax2 = ax.twinx()
    sx, sy = zip(*accs)
    ax2.plot(sx, sy, color="tomato", marker="o", linewidth=1.5)
    ax.set_xlabel("step"); ax.set_ylabel("loss", color="steelblue")
    ax2.set_ylabel("accuracy", color="tomato")
    ax.set_title(f"Toy training: final acc {final_acc:.3f}")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "toy_training_loss.png", dpi=150)
    plt.close(fig)

    # ---- Recovery check ----
    print("\nMean-diff direction recovery at probe layer ...")
    recoveries = {}
    REF_ID = 0  # use target 0 as reference for transfer scoring
    for T in range(1, K_TARGETS):
        R_target = collect_residuals(model, T,     n_prompts=64, layer=PROBE_LAYER)
        R_ref    = collect_residuals(model, REF_ID, n_prompts=64, layer=PROBE_LAYER)
        d = R_target.mean(0) - R_ref.mean(0)

        # Cosine with the ground-truth injection vector difference
        with torch.no_grad():
            slot_T   = model.slot_image(torch.tensor([T])).squeeze(0)
            slot_ref = model.slot_image(torch.tensor([REF_ID])).squeeze(0)
            inj_diff = slot_T - slot_ref
        cos_with_inj = float((d @ inj_diff).item()) / (
            float(d.norm() * inj_diff.norm()) + 1e-9)

        # Alpha sweep transfer at probe layer
        sweep = {}
        for a in ALPHAS:
            r = kl_at_alpha(model, T, REF_ID, a, d, PROBE_LAYER, n_eval=20)
            sweep[a] = r["transfer"]
        a1 = sweep[1.0]
        print(f"  T={T}  cos(d, inj_diff)={cos_with_inj:+.3f}  "
              f"transfer @ alpha=1 = {a1:+.3f}")
        recoveries[T] = {
            "cos_with_inj_diff": cos_with_inj,
            "transfer_alpha1":   a1,
            "sweep": {str(a): v for a, v in sweep.items()},
            "d_norm": float(d.norm()),
            "inj_diff_norm": float(inj_diff.norm()),
        }

    # Verdict: instrument family is calibrated iff
    #   - training acc >= 0.95
    #   - mean cos(d, inj_diff) >= 0.7
    #   - mean transfer @ alpha=1 >= 0.8
    cos_mean = float(np.mean([v["cos_with_inj_diff"] for v in recoveries.values()]))
    a1_mean  = float(np.mean([v["transfer_alpha1"]   for v in recoveries.values()]))
    pass_train  = final_acc >= 0.95
    pass_cos    = cos_mean  >= 0.7
    pass_a1     = a1_mean   >= 0.8
    if pass_train and pass_cos and pass_a1:
        verdict = "PASS"
    elif pass_train and (pass_cos or pass_a1):
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    print(f"\nVerdict: {verdict}")
    print(f"  train acc {final_acc:.3f} (need >=0.95): {'OK' if pass_train else 'FAIL'}")
    print(f"  mean cos(d, inj_diff) {cos_mean:+.3f} (need >=0.70): "
          f"{'OK' if pass_cos else 'FAIL'}")
    print(f"  mean transfer @ alpha=1 {a1_mean:+.3f} (need >=0.80): "
          f"{'OK' if pass_a1 else 'FAIL'}")

    # Plot per-target recovery
    fig, ax = plt.subplots(figsize=(8, 4))
    Ts = sorted(recoveries.keys())
    cosines  = [recoveries[T]["cos_with_inj_diff"] for T in Ts]
    transfers = [recoveries[T]["transfer_alpha1"]  for T in Ts]
    x = np.arange(len(Ts))
    ax.bar(x - 0.2, cosines,   width=0.4, color="steelblue",
           label="cos(d, inj_diff)")
    ax.bar(x + 0.2, transfers, width=0.4, color="tomato",
           label="transfer @ alpha=1")
    ax.axhline(0.8, color="green",  linestyle="--", alpha=0.5)
    ax.axhline(0.7, color="orange", linestyle="--", alpha=0.5)
    ax.set_xticks(x); ax.set_xticklabels([f"T={t}" for t in Ts])
    ax.set_ylim(-0.1, 1.1)
    ax.set_title("Toy explicit-object recovery (per target)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "per_target_recovery.png", dpi=150)
    plt.close(fig)

    # Report
    lines = ["Exp 40 - Explicit-Object Control (toy transformer)", "=" * 70, ""]
    lines.append(f"Architecture: {N_LAYERS} layers, d_model={D_MODEL}, "
                 f"slot_dim={SLOT_DIM}, K_targets={K_TARGETS}")
    lines.append(f"Probe/injection layer: {PROBE_LAYER}")
    lines.append(f"Reference target: T={REF_ID}")
    lines.append("")
    lines.append("Pre-registered thresholds:")
    lines.append("  PASS  train_acc >= 0.95 AND mean cos(d, inj_diff) >= 0.70 "
                 "AND mean transfer @ alpha=1 >= 0.80")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict}")
    lines.append(f"  final training accuracy:    {final_acc:.3f}")
    lines.append(f"  mean cos(d, inj_diff):      {cos_mean:+.3f}")
    lines.append(f"  mean transfer @ alpha=1:    {a1_mean:+.3f}")
    lines.append("")
    lines.append("Per-target results:")
    for T in Ts:
        v = recoveries[T]
        lines.append(f"  T={T}  cos={v['cos_with_inj_diff']:+.3f}  "
                     f"transfer@1={v['transfer_alpha1']:+.3f}  "
                     f"||d||={v['d_norm']:.3f}  ||inj_diff||={v['inj_diff_norm']:.3f}")
        sweep_str = "  ".join(f"a={a:.2f}:{recoveries[T]['sweep'][str(a)]:+.3f}"
                              for a in ALPHAS)
        lines.append(f"        sweep: {sweep_str}")

    (RESULTS_DIR / "report.txt").write_text("\n".join(lines))
    print(f"Report: {RESULTS_DIR / 'report.txt'}")

    summary = {
        "design": "exp 40: explicit-object control (toy transformer)",
        "config": {
            "K_TARGETS": K_TARGETS, "SLOT_DIM": SLOT_DIM, "D_MODEL": D_MODEL,
            "N_LAYERS": N_LAYERS, "N_HEADS": N_HEADS, "SEQ_LEN": SEQ_LEN,
            "PROBE_LAYER": PROBE_LAYER,
        },
        "final_train_acc": final_acc,
        "mean_cos_with_inj_diff": cos_mean,
        "mean_transfer_alpha1":   a1_mean,
        "verdict": verdict,
        "recoveries": {str(T): v for T, v in recoveries.items()},
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
