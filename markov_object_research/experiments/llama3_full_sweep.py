"""
Llama-3 8B full sweep: exps 33, 35, 36, 37, 38 in one process.

Loads Llama-3 8B once on MPS, then runs each experiment sequentially with
results written to separate output dirs (suffix _llama3).

Usage:
    HF_TOKEN=... python -u experiments/llama3_full_sweep.py
"""

import json, os, time, traceback
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
import torch.nn as nn
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "results"

MODEL_NAME = "meta-llama/Meta-Llama-3-8B"
DEVICE     = "mps"
DTYPE      = torch.float16
PROBE_LAYERS = [2, 8, 16, 24, 30]
LAYER_THRESHOLD = 16
INTERVENTION_LAYER = 8

REFERENCE = 5
TARGETS = [999, 666, 137]
REFERENCE_BATTERY = [5, 2, 50, 250, 800, 41, 7, 11]

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
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


# ---------------------------------------------------------------------------
# Shared model + capture
# ---------------------------------------------------------------------------

def load_model():
    from transformer_lens import HookedTransformer
    print(f"Loading {MODEL_NAME} on {DEVICE} ({DTYPE})...")
    t0 = time.time()
    model = HookedTransformer.from_pretrained(
        MODEL_NAME, device=DEVICE, dtype=DTYPE)
    model.eval()
    print(f"  loaded in {time.time()-t0:.1f}s. n_layers={model.cfg.n_layers} "
          f"d_model={model.cfg.d_model} n_heads={model.cfg.n_heads}")
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


def capture_resid_multi(model, text, pos, layers):
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    captured = {}
    def make(L):
        def cap(value, hook):
            captured[L] = value[0, pos, :].detach().clone().to("cpu").float()
            return value
        return cap
    fwd_hooks = [(f"blocks.{L}.hook_resid_pre", make(L)) for L in layers]
    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=fwd_hooks)
    return captured


def collect_residuals(model, n, templates, layer):
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


def collect_joint_states(model, n, templates, layers):
    rows = []; used = []
    for t in templates:
        text = t.format(n=n)
        pos = last_token_of_span(model, text, str(n))
        if pos is None:
            continue
        d = capture_resid_multi(model, text, pos, layers)
        if any(L not in d for L in layers):
            continue
        rows.append(torch.cat([d[L] for L in layers]))
        used.append(t)
    if not rows:
        return None, []
    return torch.stack(rows), used


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
    direction_dev = direction.to(DEVICE).to(DTYPE)
    def patch(value, hook):
        value[0, pos, :] = value[0, pos, :] - alpha * direction_dev
        return value
    with torch.no_grad():
        logits = model.run_with_hooks(
            tokens, fwd_hooks=[(f"blocks.{layer}.hook_resid_pre", patch)])
    return logits[0, -1, :].to("cpu").float()


def kl_div(p, q):
    p = torch.softmax(p, dim=-1)
    q = torch.softmax(q, dim=-1)
    return float((p * (torch.log(p + 1e-12) - torch.log(q + 1e-12))).sum())


def alpha_sweep(model, target, template, direction, layer):
    text_t = template.format(n=target)
    text_r = template.format(n=REFERENCE)
    pos_t = last_token_of_span(model, text_t, str(target))
    pos_r = last_token_of_span(model, text_r, str(REFERENCE))
    if pos_t is None or pos_r is None:
        return None
    L_t = baseline_logits(model, text_t)
    L_r = baseline_logits(model, text_r)
    kl_b = kl_div(L_t, L_r)
    out = {}
    for a in ALPHAS:
        Li = logits_with_direction(model, text_t, pos_t, direction, a, layer)
        out[a] = 1.0 - kl_div(Li, L_r) / max(kl_b, 1e-9)
    return {"kl_baseline": kl_b, "alphas": out}


def aggregate_sweep(model, target, direction, layer, templates):
    per = {a: [] for a in ALPHAS}
    bases = []
    for t in templates:
        r = alpha_sweep(model, target, t, direction, layer)
        if r is None:
            continue
        bases.append(r["kl_baseline"])
        for a in ALPHAS:
            per[a].append(r["alphas"][a])
    return {a: float(np.mean(per[a])) if per[a] else 0.0 for a in ALPHAS}


def decompose(d, e):
    e_n2 = float((e * e).sum())
    if e_n2 < 1e-12:
        return 0.0, d * 0.0, d.clone()
    a = float((d * e).sum()) / e_n2
    return a, a * e, d - a * e


def strip_along(s, e):
    e_n2 = (e * e).sum()
    if e_n2.item() < 1e-12:
        return s.clone()
    proj = (s @ e) / e_n2
    return s - proj.unsqueeze(1) * e.unsqueeze(0)


# ---------------------------------------------------------------------------
# Exp 33: embedding-decomposition audit
# ---------------------------------------------------------------------------

def run_exp33(model, out_dir):
    print("\n\n========== EXP 33: embedding-decomposition (Llama-3 8B) ==========")
    out_dir.mkdir(parents=True, exist_ok=True)
    all_results = {}
    for tgt in TARGETS:
        all_results[tgt] = {}
        for L in PROBE_LAYERS:
            print(f"\n[33] target={tgt} layer={L}")
            R_t, ut = collect_residuals(model, tgt, TRAIN_TEMPLATES, L)
            R_r, ur = collect_residuals(model, REFERENCE, TRAIN_TEMPLATES, L)
            if R_t is None or R_r is None:
                continue
            Rt, Rr, _ = aligned_pair(R_t, ut, R_r, ur)
            d = Rt.mean(0) - Rr.mean(0)
            R_tn, utn = collect_residuals(model, tgt, NEUTRAL_TEMPLATES, L)
            R_rn, urn = collect_residuals(model, REFERENCE, NEUTRAL_TEMPLATES, L)
            if R_tn is None or R_rn is None:
                continue
            Rtn, Rrn, _ = aligned_pair(R_tn, utn, R_rn, urn)
            e = Rtn.mean(0) - Rrn.mean(0)
            _, d_par, d_perp = decompose(d, e)
            d_n = float(d.norm()); e_n = float(e.norm())
            cos = float((d @ e).item()) / max(d_n * e_n, 1e-9)
            d_perp_resc = d_perp / max(float(d_perp.norm()), 1e-9) * d_n
            e_resc      = e      / max(e_n, 1e-9) * d_n
            tf = aggregate_sweep(model, tgt, d, L, HELDOUT_TEMPLATES)[1.0]
            tp = aggregate_sweep(model, tgt, d_perp_resc, L, HELDOUT_TEMPLATES)[1.0]
            te = aggregate_sweep(model, tgt, e_resc, L, HELDOUT_TEMPLATES)[1.0]
            ret = (tp / max(abs(tf), 1e-9)) if tf > 0 else 0.0
            print(f"  cos(d,e)={cos:+.3f}  frac_par={(d_par.norm()/d_n)**2:.3f}  "
                  f"tf={tf:+.3f}  tp={tp:+.3f}  te={te:+.3f}  ret={ret:+.3f}")
            all_results[tgt][L] = dict(
                cos_d_e=cos, frac_par=float((d_par.norm()/d_n)**2),
                transfer_full=tf, transfer_perp=tp, transfer_emb=te,
                retention=ret, d_norm=d_n, e_norm=e_n)
    rets = [v["retention"] for t in all_results.values() for L, v in t.items()
            if L >= LAYER_THRESHOLD]
    mr = float(np.mean(rets)) if rets else 0.0
    verdict = "PASS" if mr >= 0.5 else "PARTIAL" if mr >= 0.25 else "FAIL"
    print(f"[33] verdict: {verdict}  mean_retention(L>={LAYER_THRESHOLD})={mr:+.3f}")
    (out_dir / "summary.json").write_text(json.dumps(
        {"model": MODEL_NAME, "results": {str(t): {str(L): v for L, v in d.items()}
                                            for t, d in all_results.items()},
         "verdict": verdict, "mean_retention": mr}, indent=2, default=float))
    lines = [f"Exp 33 ({MODEL_NAME})", "=" * 70, f"VERDICT: {verdict}",
             f"mean retention at L>={LAYER_THRESHOLD}: {mr:+.3f}", ""]
    for t in TARGETS:
        lines.append(f"\n### target={t}")
        for L in sorted(all_results.get(t, {}).keys()):
            v = all_results[t][L]
            lines.append(f"  L={L:2d}  cos(d,e)={v['cos_d_e']:+.3f}  "
                         f"frac_par={v['frac_par']:.3f}  "
                         f"tf={v['transfer_full']:+.3f}  "
                         f"tp={v['transfer_perp']:+.3f}  "
                         f"te={v['transfer_emb']:+.3f}  ret={v['retention']:+.3f}")
    (out_dir / "report.txt").write_text("\n".join(lines))
    return verdict, all_results


# ---------------------------------------------------------------------------
# Exp 35: bounded-capacity boundary fitting
# ---------------------------------------------------------------------------

CAPACITY_LADDER = [("linear", 0), ("mlp_h16", 16), ("mlp_h64", 64),
                    ("mlp_h256", 256), ("mlp_h1024", 1024)]


class MLPProbe(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        if h == 0:
            self.net = nn.Linear(d, 1)
        else:
            self.net = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Linear(h, 1))
    def forward(self, x):
        return self.net(x).squeeze(-1)


def fit_probe(X_tr, y_tr, h, n_iters=400, lr=1e-2, wd=1e-3):
    p = MLPProbe(X_tr.shape[1], h)
    opt = torch.optim.Adam(p.parameters(), lr=lr, weight_decay=wd)
    bce = nn.BCEWithLogitsLoss()
    for _ in range(n_iters):
        opt.zero_grad()
        bce(p(X_tr), y_tr).backward()
        opt.step()
    return p


def evaluate_probe(p, X, y):
    p.eval()
    with torch.no_grad():
        logits = p(X)
        probs = torch.sigmoid(logits)
        pred = (probs >= 0.5).float()
    return float((pred == y).float().mean()), float(((probs - y) ** 2).mean())


def run_exp35(model, out_dir):
    print("\n\n========== EXP 35: bounded-capacity boundary (Llama-3 8B) ==========")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {"stripped": {}, "raw": {}}
    for strip in (True, False):
        for tgt in TARGETS:
            print(f"\n[35] target={tgt}  strip_emb={strip}")
            Xt, ut = collect_joint_states(model, tgt, DIVERSE_TEMPLATES, PROBE_LAYERS)
            Xr, ur = collect_joint_states(model, REFERENCE, DIVERSE_TEMPLATES, PROBE_LAYERS)
            if Xt is None or Xr is None:
                continue
            if strip:
                Xtn, utn = collect_joint_states(model, tgt, NEUTRAL_TEMPLATES, PROBE_LAYERS)
                Xrn, urn = collect_joint_states(model, REFERENCE, NEUTRAL_TEMPLATES, PROBE_LAYERS)
                shared = [t for t in utn if t in urn]
                ti = [utn.index(t) for t in shared]; ri = [urn.index(t) for t in shared]
                e_joint = Xtn[ti].float().mean(0) - Xrn[ri].float().mean(0)
                Xt = strip_along(Xt.float(), e_joint)
                Xr = strip_along(Xr.float(), e_joint)
            else:
                Xt = Xt.float(); Xr = Xr.float()
            X = torch.cat([Xt, Xr], dim=0)
            y = torch.cat([torch.ones(len(Xt)), torch.zeros(len(Xr))])
            groups = ut + ur
            mu = X.mean(0); sd = X.std(0)
            sd = torch.where(sd > 1e-6, sd, torch.ones_like(sd))
            X = (X - mu) / sd
            n_splits = min(5, len(set(groups)))
            gkf = GroupKFold(n_splits=n_splits)
            folds = list(gkf.split(X.numpy(), y.numpy(), groups=groups))
            results_per_h = {}
            for label, h in CAPACITY_LADDER:
                accs, briers = [], []
                for tr_idx, te_idx in folds:
                    p = fit_probe(X[tr_idx], y[tr_idx], h)
                    a, b = evaluate_probe(p, X[te_idx], y[te_idx])
                    accs.append(a); briers.append(b)
                results_per_h[label] = dict(h=h, mean_acc=float(np.mean(accs)),
                                             std_acc=float(np.std(accs)),
                                             mean_brier=float(np.mean(briers)))
                print(f"  {label:<11s}  acc={np.mean(accs):.3f}+/-{np.std(accs):.3f}  "
                      f"brier={np.mean(briers):.3f}")
            cap90 = next((lbl for lbl, _ in CAPACITY_LADDER
                          if results_per_h[lbl]["mean_acc"] >= 0.9), None)
            (out["stripped"] if strip else out["raw"])[tgt] = dict(
                results=results_per_h, cap_to_90=cap90,
                joint_dim=int(Xt.shape[1]))
    def vd(d):
        if any(e["cap_to_90"] in {"linear", "mlp_h16", "mlp_h64"}
               for e in d.values() if e):
            covered = all(e["cap_to_90"] in {"linear", "mlp_h16", "mlp_h64"}
                           for e in d.values() if e)
            if covered:
                return "PASS"
        if all(e["cap_to_90"] is not None for e in d.values() if e):
            return "PARTIAL"
        return "FAIL"
    sv, rv = vd(out["stripped"]), vd(out["raw"])
    print(f"[35] stripped verdict: {sv}   raw verdict: {rv}")
    (out_dir / "summary.json").write_text(json.dumps(
        {"model": MODEL_NAME, "stripped": {str(t): v for t, v in out["stripped"].items()},
         "raw": {str(t): v for t, v in out["raw"].items()},
         "verdict_stripped": sv, "verdict_raw": rv}, indent=2, default=float))
    lines = [f"Exp 35 ({MODEL_NAME})", "=" * 70,
             f"VERDICT stripped: {sv}", f"VERDICT raw:      {rv}", ""]
    for kind, results in (("STRIPPED", out["stripped"]), ("RAW", out["raw"])):
        lines.append(f"\n--- {kind} ---")
        for t in TARGETS:
            e = results.get(t)
            if not e:
                continue
            lines.append(f"\ntarget={t}  cap_to_90={e['cap_to_90']}")
            for lbl, _ in CAPACITY_LADDER:
                r = e["results"][lbl]
                lines.append(f"  {lbl:<11s}  acc={r['mean_acc']:.3f}+/-{r['std_acc']:.3f}  "
                             f"brier={r['mean_brier']:.3f}")
    (out_dir / "report.txt").write_text("\n".join(lines))
    return sv, rv, out


# ---------------------------------------------------------------------------
# Exp 36: local-tangent atlas
# ---------------------------------------------------------------------------

K_NBR = 20

def k_nearest(X, anchors, k):
    Xn = X / (X.norm(dim=1, keepdim=True) + 1e-9)
    out = []
    for i in anchors:
        sims = Xn @ Xn[i]
        sims[i] = -2.0
        top = torch.topk(sims, k=min(k, X.shape[0] - 1)).indices
        out.append(top.tolist())
    return out


def local_normals(X, y, anchors, k):
    nn_lists = k_nearest(X, anchors, k)
    normals = []; accs = []
    for ai, nbrs in zip(anchors, nn_lists):
        idxs = [ai] + nbrs
        Xn = X[idxs]; yn = y[idxs]
        if (yn == 1).sum() == 0 or (yn == 0).sum() == 0:
            continue
        c_t = Xn[yn == 1].mean(0); c_r = Xn[yn == 0].mean(0)
        n = c_t - c_r
        n = n / (n.norm() + 1e-9)
        normals.append(n)
        scores = (Xn - c_r) @ n - 0.5 * ((c_t - c_r) @ n)
        pred = (scores > 0).float()
        if pred.eq(yn).float().mean() < 0.5:
            pred = 1.0 - pred
        accs.append(float(pred.eq(yn).float().mean()))
    if not normals:
        return None, []
    return torch.stack(normals), accs


def normal_field_stats(N):
    M = N.shape[0]
    Nc = N - N.mean(0, keepdim=True)
    U, S, V = torch.linalg.svd(Nc, full_matrices=False)
    var_total = float((S * S).sum())
    ev_pc1 = float((S[0] * S[0]).item()) / max(var_total, 1e-12)
    mean_dir = N.mean(0)
    mean_dir = mean_dir / (mean_dir.norm() + 1e-9)
    sign = torch.sign(N @ mean_dir); sign[sign == 0] = 1.0
    No = N * sign.unsqueeze(1)
    C = No @ No.T
    C = torch.clamp(C, -1.0, 1.0)
    mask = ~torch.eye(M, dtype=torch.bool)
    angles = torch.rad2deg(torch.arccos(C[mask])).numpy()
    cosines = (N @ N.T)[mask].numpy()
    return dict(mean_cos=float(cosines.mean()),
                pc1_ev=ev_pc1,
                mean_angle_deg=float(angles.mean()),
                n_normals=M)


def run_exp36(model, out_dir):
    print("\n\n========== EXP 36: local-tangent atlas (Llama-3 8B) ==========")
    out_dir.mkdir(parents=True, exist_ok=True)
    per_target = {}
    for tgt in TARGETS:
        print(f"\n[36] target={tgt}")
        Xt, ut = collect_joint_states(model, tgt, DIVERSE_TEMPLATES, PROBE_LAYERS)
        if Xt is None:
            continue
        Xs = [Xt.float()]; ys = [torch.ones(len(Xt))]; tags = [(tgt, t) for t in ut]
        for ref in REFERENCE_BATTERY:
            Xr, ur = collect_joint_states(model, ref, DIVERSE_TEMPLATES, PROBE_LAYERS)
            if Xr is None:
                continue
            Xs.append(Xr.float()); ys.append(torch.zeros(len(Xr)))
            tags += [(ref, t) for t in ur]
        Xtn, utn = collect_joint_states(model, tgt, NEUTRAL_TEMPLATES, PROBE_LAYERS)
        Xrn, urn = collect_joint_states(model, REFERENCE, NEUTRAL_TEMPLATES, PROBE_LAYERS)
        if Xtn is not None and Xrn is not None:
            shared = [t for t in utn if t in urn]
            ti = [utn.index(t) for t in shared]; ri = [urn.index(t) for t in shared]
            e = Xtn[ti].float().mean(0) - Xrn[ri].float().mean(0)
            Xs = [strip_along(x, e) for x in Xs]
        X = torch.cat(Xs, dim=0); y = torch.cat(ys, dim=0)
        anchors = (y == 1).nonzero(as_tuple=True)[0].tolist()
        Nr, accs = local_normals(X, y, anchors, K_NBR)
        if Nr is None:
            continue
        rs = normal_field_stats(Nr); rs["mean_local_acc"] = float(np.mean(accs))
        gen = torch.Generator().manual_seed(42)
        ys = y[torch.randperm(len(y), generator=gen)]
        Nn, accs2 = local_normals(X, ys,
                                    (ys == 1).nonzero(as_tuple=True)[0].tolist(),
                                    K_NBR)
        ns = normal_field_stats(Nn) if Nn is not None else None
        if ns:
            ns["mean_local_acc"] = float(np.mean(accs2))
        print(f"  real:  mean_cos={rs['mean_cos']:+.3f}  PC1_EV={rs['pc1_ev']:.3f}  "
              f"angle={rs['mean_angle_deg']:.1f}deg  acc={rs['mean_local_acc']:.3f}")
        if ns:
            print(f"  null:  mean_cos={ns['mean_cos']:+.3f}  PC1_EV={ns['pc1_ev']:.3f}  "
                  f"angle={ns['mean_angle_deg']:.1f}deg  acc={ns['mean_local_acc']:.3f}")
        per_target[tgt] = {"real": rs, "null": ns}
    pc1s = [v["real"]["pc1_ev"] for v in per_target.values()]
    mev = float(np.mean(pc1s)) if pc1s else 0.0
    angles_real = [v["real"]["mean_angle_deg"] for v in per_target.values()]
    angles_null = [v["null"]["mean_angle_deg"] for v in per_target.values() if v.get("null")]
    mar = float(np.mean(angles_real)) if angles_real else 90.0
    man = float(np.mean(angles_null)) if angles_null else 90.0
    if mar < 30 and man > 60 and mev >= 0.6:
        v = "PASS"
    elif mev >= 0.3:
        v = "PARTIAL"
    else:
        v = "FAIL"
    print(f"[36] verdict: {v}  PC1_EV={mev:.3f}  angle_real={mar:.1f}  angle_null={man:.1f}")
    (out_dir / "summary.json").write_text(json.dumps(
        {"model": MODEL_NAME, "per_target": {str(t): e for t, e in per_target.items()},
         "verdict": v, "mean_pc1_ev": mev, "mean_angle_real": mar,
         "mean_angle_null": man}, indent=2, default=float))
    lines = [f"Exp 36 ({MODEL_NAME})", "=" * 70, f"VERDICT: {v}",
             f"mean PC1 EV: {mev:.3f}  angle_real: {mar:.1f}  angle_null: {man:.1f}", ""]
    for t in TARGETS:
        e = per_target.get(t)
        if not e:
            continue
        lines.append(f"\n### target={t}")
        lines.append(f"  REAL: {e['real']}")
        if e.get('null'):
            lines.append(f"  NULL: {e['null']}")
    (out_dir / "report.txt").write_text("\n".join(lines))
    return v, per_target


# ---------------------------------------------------------------------------
# Exp 37: causal faithfulness
# ---------------------------------------------------------------------------

class LinProbe(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.w = nn.Parameter(torch.zeros(d))
        self.b = nn.Parameter(torch.zeros(1))
    def forward(self, x):
        return x @ self.w + self.b


def fit_lin_probe(X, y, n_iters=600, lr=5e-2, wd=1e-2):
    p = LinProbe(X.shape[1])
    opt = torch.optim.Adam(p.parameters(), lr=lr, weight_decay=wd)
    bce = nn.BCEWithLogitsLoss()
    for _ in range(n_iters):
        opt.zero_grad()
        bce(p(X), y).backward()
        opt.step()
    return p


def fit_target_layer_probe(model, target, layer):
    Rt, ut = collect_residuals(model, target, TRAIN_TEMPLATES, layer)
    Rr, ur = collect_residuals(model, REFERENCE, TRAIN_TEMPLATES, layer)
    Rtt, Rrr, _ = aligned_pair(Rt, ut, Rr, ur)
    Rtn, utn = collect_residuals(model, target, NEUTRAL_TEMPLATES, layer)
    Rrn, urn = collect_residuals(model, REFERENCE, NEUTRAL_TEMPLATES, layer)
    Rttn, Rrrn, _ = aligned_pair(Rtn, utn, Rrn, urn)
    e = Rttn.mean(0) - Rrrn.mean(0)
    e_n2 = (e * e).sum()
    def strip(X):
        return X if e_n2.item() < 1e-12 else X - ((X @ e) / e_n2).unsqueeze(1) * e.unsqueeze(0)
    Xt = strip(Rtt); Xr = strip(Rrr)
    X = torch.cat([Xt, Xr], dim=0); y = torch.cat([torch.ones(len(Xt)), torch.zeros(len(Xr))])
    mu = X.mean(0); sd = X.std(0)
    sd = torch.where(sd > 1e-6, sd, torch.ones_like(sd))
    Xn = (X - mu) / sd
    p = fit_lin_probe(Xn, y)
    raw = p.w.detach() / sd
    if e_n2.item() > 1e-12:
        raw = raw - ((raw @ e) / e_n2) * e
    return raw / (raw.norm() + 1e-9), e


def first_token_id(model, s):
    """Return the first token id of `s` as the model would tokenize it
    (without BOS). Works regardless of whether `s` is a single token."""
    ids = model.to_tokens(s, prepend_bos=False)
    return int(ids[0, 0].item())


def evaluate_intervention(model, target, ref, template, n_dir, e, alpha, mode,
                           layer, gen):
    text = template.format(n=target)
    pos = last_token_of_span(model, text, str(target))
    if pos is None:
        return None
    target_tok = first_token_id(model, f" {target}")
    ref_tok    = first_token_id(model, f" {ref}")
    r0 = capture_resid(model, text, pos, layer)
    step = float(r0.norm()) * 0.1
    if mode == "baseline":
        delta = torch.zeros_like(n_dir)
    elif mode == "across":
        delta = -alpha * step * n_dir
    elif mode == "along":
        v = torch.randn(n_dir.numel(), generator=gen)
        e_n2 = (e * e).sum()
        if e_n2.item() > 1e-12:
            v = v - ((v @ e) / e_n2) * e
        v = v - (v @ n_dir) * n_dir
        v = v / (v.norm() + 1e-9)
        delta = alpha * step * v
    elif mode == "random":
        v = torch.randn(n_dir.numel(), generator=gen)
        v = v / (v.norm() + 1e-9)
        delta = alpha * step * v
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    delta_dev = delta.to(DEVICE).to(DTYPE)
    def patch(value, hook):
        value[0, pos, :] = value[0, pos, :] + delta_dev
        return value
    with torch.no_grad():
        logits = model.run_with_hooks(
            tokens, fwd_hooks=[(f"blocks.{layer}.hook_resid_pre", patch)])
    last = logits[0, -1, :].to("cpu").float()
    return float(last[target_tok] - last[ref_tok])


def run_exp37(model, out_dir):
    print("\n\n========== EXP 37: causal faithfulness (Llama-3 8B) ==========")
    out_dir.mkdir(parents=True, exist_ok=True)
    gen = torch.Generator().manual_seed(123)
    all_results = {}
    for tgt in TARGETS:
        print(f"\n[37] target={tgt}")
        n_dir, e = fit_target_layer_probe(model, tgt, INTERVENTION_LAYER)
        per_t = []
        for t in HELDOUT_TEMPLATES:
            row = {"template": t}
            for mode, a in (("baseline", 0.0), ("across", 1.0),
                             ("along", 1.0), ("random", 1.0)):
                row[mode] = evaluate_intervention(model, tgt, REFERENCE, t, n_dir,
                                                   e, a, mode, INTERVENTION_LAYER,
                                                   gen)
            per_t.append(row)
            print(f"  [{t[:30]:<30s}] base={row['baseline']:+.2f} "
                  f"across={row['across']:+.2f} along={row['along']:+.2f} "
                  f"random={row['random']:+.2f}")
        valid = [r for r in per_t if all(r.get(k) is not None
                 for k in ("baseline", "across", "along", "random"))]
        agg = {}
        for k in ("across", "along", "random"):
            shifts = [r[k] - r["baseline"] for r in valid]
            agg[k] = float(np.mean(shifts))
        all_results[tgt] = dict(per_template=per_t, agg=agg)
        print(f"  shifts: across={agg['across']:+.3f}  along={agg['along']:+.3f}  "
              f"random={agg['random']:+.3f}")
    avg_a = float(np.mean([abs(all_results[t]["agg"]["across"]) -
                            abs(all_results[t]["agg"]["random"]) for t in TARGETS]))
    avg_l = float(np.mean([abs(all_results[t]["agg"]["along"]) -
                            abs(all_results[t]["agg"]["random"]) for t in TARGETS]))
    if avg_a >= 0.5 and avg_l <= 0.15:
        v = "PASS"
    elif avg_a >= 0.3:
        v = "PARTIAL"
    else:
        v = "FAIL"
    print(f"[37] verdict: {v}  across+={avg_a:+.3f}  along+={avg_l:+.3f}")
    (out_dir / "summary.json").write_text(json.dumps(
        {"model": MODEL_NAME, "results": {str(t): all_results[t] for t in TARGETS},
         "verdict": v, "avg_across_extra": avg_a, "avg_along_extra": avg_l},
        indent=2, default=float))
    lines = [f"Exp 37 ({MODEL_NAME})", "=" * 70, f"VERDICT: {v}",
             f"avg |across|-|random|: {avg_a:+.3f}",
             f"avg |along|-|random|:  {avg_l:+.3f}", ""]
    for t in TARGETS:
        e = all_results[t]
        lines.append(f"\n### target={t}  agg={e['agg']}")
    (out_dir / "report.txt").write_text("\n".join(lines))
    return v, all_results


# ---------------------------------------------------------------------------
# Exp 38: graph-cut signature (reduced — every 4th layer + all heads + MLPs)
# ---------------------------------------------------------------------------

CUT_LAYERS = [0, 4, 8, 12, 16, 20, 24, 28, 31]


def make_attn_zero(L, H, pos_holder):
    def fn(value, hook):
        value[0, pos_holder[0], H, :] = 0.0
        return value
    return (f"blocks.{L}.attn.hook_z", fn)


def make_mlp_zero(L, pos_holder):
    def fn(value, hook):
        value[0, pos_holder[0], :] = 0.0
        return value
    return (f"blocks.{L}.hook_mlp_out", fn)


def margin(model, text, target_tok, ref_tok):
    L = baseline_logits(model, text)
    return float(L[target_tok] - L[ref_tok])


def margin_with(model, text, target_tok, ref_tok, hooks):
    tokens = model.to_tokens(text, prepend_bos=True).to(DEVICE)
    with torch.no_grad():
        logits = model.run_with_hooks(tokens, fwd_hooks=hooks)
    last = logits[0, -1, :].to("cpu").float()
    return float(last[target_tok] - last[ref_tok])


def rank_nodes(model, target, n_eval=3):
    target_tok = first_token_id(model, f" {target}")
    ref_tok    = first_token_id(model, f" {REFERENCE}")
    bms = {}
    for t in HELDOUT_TEMPLATES[:n_eval]:
        text = t.format(n=target)
        if last_token_of_span(model, text, str(target)) is None:
            continue
        bms[t] = margin(model, text, target_tok, ref_tok)
    pos = [0]
    nodes = []
    n_heads = model.cfg.n_heads
    for L in CUT_LAYERS:
        for H in range(n_heads):
            ds = []
            for t, b in bms.items():
                text = t.format(n=target)
                pos[0] = last_token_of_span(model, text, str(target))
                m = margin_with(model, text, target_tok, ref_tok,
                                 [make_attn_zero(L, H, pos)])
                ds.append(b - m)
            nodes.append((float(np.mean(ds)), "attn", L, H))
        ds = []
        for t, b in bms.items():
            text = t.format(n=target)
            pos[0] = last_token_of_span(model, text, str(target))
            m = margin_with(model, text, target_tok, ref_tok,
                             [make_mlp_zero(L, pos)])
            ds.append(b - m)
        nodes.append((float(np.mean(ds)), "mlp", L, -1))
    nodes.sort(key=lambda x: -x[0])
    return nodes, bms


def cut_deltas(model, cut_nodes, intervention_layer):
    deltas = []
    pos = [0]
    for dmg, kind, L, H in cut_nodes:
        per = []
        for t in HELDOUT_TEMPLATES[:5]:
            for tgt in TARGETS:
                text = t.format(n=tgt)
                p_t = last_token_of_span(model, text, str(tgt))
                if p_t is None:
                    continue
                pos[0] = p_t
                cap_n = {}
                def cn(value, hook):
                    cap_n["r"] = value[0, p_t, :].detach().clone().to("cpu").float()
                    return value
                with torch.no_grad():
                    model.run_with_hooks(model.to_tokens(text, prepend_bos=True).to(DEVICE),
                                          fwd_hooks=[(f"blocks.{intervention_layer}.hook_resid_pre", cn)])
                rn = cap_n["r"]
                ablate = make_attn_zero(L, H, pos) if kind == "attn" else make_mlp_zero(L, pos)
                cap_a = {}
                def ca(value, hook):
                    cap_a["r"] = value[0, p_t, :].detach().clone().to("cpu").float()
                    return value
                with torch.no_grad():
                    model.run_with_hooks(model.to_tokens(text, prepend_bos=True).to(DEVICE),
                                          fwd_hooks=[ablate,
                                                     (f"blocks.{intervention_layer}.hook_resid_pre", ca)])
                ra = cap_a["r"]
                per.append(rn - ra)
        if per:
            deltas.append(torch.stack(per).mean(0))
    if not deltas:
        return None
    return torch.stack(deltas)


def alignment(n_dir, K_basis):
    if K_basis is None or K_basis.shape[0] == 0:
        return None
    Kc = K_basis - K_basis.mean(0, keepdim=True)
    U, S, V = torch.linalg.svd(Kc, full_matrices=False)
    nd = n_dir / (n_dir.norm() + 1e-9)
    top = V[0] / (V[0].norm() + 1e-9)
    return abs(float((nd @ top).item()))


def run_exp38(model, out_dir):
    print("\n\n========== EXP 38: graph-cut signature (Llama-3 8B) ==========")
    out_dir.mkdir(parents=True, exist_ok=True)
    all_results = {}
    for tgt in TARGETS:
        print(f"\n[38] target={tgt}")
        nodes, _ = rank_nodes(model, tgt, n_eval=3)
        top10 = nodes[:10]
        print("  top-10:", [(d, k, L, H) for d, k, L, H in top10])
        Kb = cut_deltas(model, top10, INTERVENTION_LAYER)
        n_dir, _ = fit_target_layer_probe(model, tgt, INTERVENTION_LAYER)
        ali = alignment(n_dir, Kb)
        rng = np.random.default_rng(seed=hash((tgt, "null")) & 0xFFFFFFFF)
        idxs = rng.choice(np.arange(20, len(nodes)), size=10, replace=False)
        nullc = [nodes[i] for i in idxs]
        Knul = cut_deltas(model, nullc, INTERVENTION_LAYER)
        ali_n = alignment(n_dir, Knul)
        print(f"  cos(n_dir, top PC of K_C): {ali}")
        print(f"  null cos:                  {ali_n}")
        all_results[tgt] = dict(top10=[(d, k, L, H) for d, k, L, H in top10],
                                  cos_real=ali, cos_null=ali_n)
    cr = [all_results[t]["cos_real"] for t in TARGETS if all_results[t]["cos_real"] is not None]
    cn = [all_results[t]["cos_null"] for t in TARGETS if all_results[t]["cos_null"] is not None]
    avg_r = float(np.mean(cr)) if cr else 0.0
    avg_n = float(np.mean(cn)) if cn else 0.0
    if avg_r >= 0.7 and avg_n < 0.3:
        v = "PASS"
    elif avg_r >= 0.3:
        v = "PARTIAL"
    else:
        v = "FAIL"
    print(f"[38] verdict: {v}  avg_cos_real={avg_r:.3f}  avg_cos_null={avg_n:.3f}")
    (out_dir / "summary.json").write_text(json.dumps(
        {"model": MODEL_NAME, "results": {str(t): all_results[t] for t in TARGETS},
         "verdict": v, "avg_cos_real": avg_r, "avg_cos_null": avg_n},
        indent=2, default=float))
    lines = [f"Exp 38 ({MODEL_NAME})", "=" * 70, f"VERDICT: {v}",
             f"avg cos real: {avg_r:.3f}  avg cos null: {avg_n:.3f}", ""]
    for t in TARGETS:
        e = all_results[t]
        lines.append(f"\n### target={t}")
        lines.append(f"  cos_real={e['cos_real']}  cos_null={e['cos_null']}")
        for d, k, L, H in e["top10"]:
            tag = f"L{L}H{H}" if k == "attn" else f"L{L}MLP"
            lines.append(f"    {tag:<8s} damage={d:+.3f}")
    (out_dir / "report.txt").write_text("\n".join(lines))
    return v, all_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    model = load_model()
    verdicts = {}

    try:
        v, _ = run_exp33(model, RESULTS / "33_embedding_decomposition_llama3")
        verdicts["33"] = v
    except Exception as e:
        print(f"[33] FAILED: {e}"); traceback.print_exc(); verdicts["33"] = "ERROR"

    try:
        sv, rv, _ = run_exp35(model, RESULTS / "35_bounded_capacity_boundary_llama3")
        verdicts["35"] = f"stripped={sv} raw={rv}"
    except Exception as e:
        print(f"[35] FAILED: {e}"); traceback.print_exc(); verdicts["35"] = "ERROR"

    try:
        v, _ = run_exp36(model, RESULTS / "36_local_tangent_atlas_llama3")
        verdicts["36"] = v
    except Exception as e:
        print(f"[36] FAILED: {e}"); traceback.print_exc(); verdicts["36"] = "ERROR"

    try:
        v, _ = run_exp37(model, RESULTS / "37_causal_faithfulness_llama3")
        verdicts["37"] = v
    except Exception as e:
        print(f"[37] FAILED: {e}"); traceback.print_exc(); verdicts["37"] = "ERROR"

    try:
        v, _ = run_exp38(model, RESULTS / "38_graph_cut_signature_llama3")
        verdicts["38"] = v
    except Exception as e:
        print(f"[38] FAILED: {e}"); traceback.print_exc(); verdicts["38"] = "ERROR"

    elapsed = time.time() - t0
    print(f"\n\n========== SWEEP DONE in {elapsed/60:.1f} min ==========")
    print(json.dumps(verdicts, indent=2))
    summary = RESULTS / "llama3_full_sweep_summary.json"
    summary.write_text(json.dumps(
        {"model": MODEL_NAME, "elapsed_min": elapsed / 60.0,
         "verdicts": verdicts}, indent=2))
    print(f"Summary: {summary}")


if __name__ == "__main__":
    main()
