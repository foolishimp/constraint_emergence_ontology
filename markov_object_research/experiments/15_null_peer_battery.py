"""
Experiment 15: Null-Peer Battery — Do Boring Numbers Show the Same Structure?

Critique the Markov-object story must answer: if we run exp 09's 8-context
decomposition on *structurally uninteresting* numbers (137, 813, 250, 3, 11,
400, 500, 800, 512), do we see the same core+coat structure, or does the
decomposition collapse to generic "number" features?

Predictions (theory-side):
  - Both cultural AND boring numbers should show core+coat decomposition,
    because decomposition is a property of objecthood in LLMs (exp 12).
  - Cultural numbers' cores should contain semantically loaded features
    (911, demon, 9/11-date, ...).
  - Boring numbers' cores should contain only structural/numerical features.
  - Cross-target core overlap for boring numbers should be high (they share
    a generic "number" skeleton); cultural numbers' cores should contain
    target-unique features not present in the boring-number core pool.

Falsifier: if boring-number cores contain the same distribution of
semantically loaded features as cultural-number cores, the coat/core signal
is a pipeline artifact.
"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import urllib.request

RESULTS_DIR = Path(__file__).parent.parent / "results" / "15_null_peer_battery"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

EXP09_CACHE = Path(__file__).parent.parent / "results" / "09_context_conditional" / "neuronpedia_cache.json"
EXP08_CACHE = Path(__file__).parent.parent / "results" / "08_feature_identity" / "neuronpedia_cache.json"
CACHE_FILE = RESULTS_DIR / "neuronpedia_cache.json"

PROBE_LAYER = 8
ACTIVATION_THRESHOLD = 0.5

CULTURAL = [666, 999, 7, 42, 100]
BORING   = [137, 813, 250, 3, 11, 400, 500, 800]

CONTEXTS = {
    "referential":  "The number {n} is",
    "page":         "Page {n} of the book",
    "currency":     "The price was {n} dollars",
    "quantity":     "There were {n} people",
    "address":      "They live at {n} Main Street",
    "temporal":     "In the year {n}",
    "arithmetic":   "When you calculate {n} plus one",
    "symbolic":     "The sacred number {n} means",
}


# ---------------------------------------------------------------------------
# Cache + labels
# ---------------------------------------------------------------------------

def load_cache():
    cache = {}
    for p in (EXP08_CACHE, EXP09_CACHE, CACHE_FILE):
        if p.exists():
            cache.update(json.loads(p.read_text()))
    return cache


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def fetch_feature_label(feature_id, cache, delay=0.2):
    key = f"gpt2-small/{PROBE_LAYER}-res-jb/{feature_id}"
    if key in cache:
        return cache[key]
    url = f"https://www.neuronpedia.org/api/feature/gpt2-small/{PROBE_LAYER}-res-jb/{feature_id}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        exps = data.get("explanations") or []
        label = exps[0].get("description") if exps else None
        cache[key] = label
        time.sleep(delay)
        return label
    except Exception:
        cache[key] = None
        return None


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


def get_features(model, sae, text, n):
    import torch
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    target = str(n)
    pos = None
    for i, tok in enumerate(str_tokens):
        if tok.strip() == target:
            pos = i
            break
    if pos is None:
        for i, tok in enumerate(str_tokens):
            if target in tok.strip():
                pos = i
                break
    if pos is None:
        return None, None
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{PROBE_LAYER}.hook_resid_pre"
    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=hook_name)
    resid = cache[hook_name][0, pos, :]
    with torch.no_grad():
        acts = sae.encode(resid.unsqueeze(0))[0]
    return acts.numpy(), pos


# ---------------------------------------------------------------------------
# Decomposition (same as exp 09)
# ---------------------------------------------------------------------------

def decompose(feats_by_context, threshold=ACTIVATION_THRESHOLD):
    active = {c: set(np.where(v > threshold)[0].tolist())
              for c, v in feats_by_context.items()}
    all_active = set().union(*active.values())
    core = set.intersection(*active.values()) if active else set()
    specific = {}
    for c in active:
        others = set().union(*[s for cc, s in active.items() if cc != c])
        specific[c] = active[c] - others
    shared = all_active - core - set().union(*specific.values())
    return {"active": active, "all_active": all_active, "core": core,
            "shared": shared, "specific": specific}


def scan_target(model, sae, n):
    feats = {}
    for ctx, template in CONTEXTS.items():
        text = template.format(n=n)
        vec, pos = get_features(model, sae, text, n)
        if vec is None:
            continue
        feats[ctx] = vec
    if len(feats) < len(CONTEXTS):
        return None
    return {"feats": feats, "decomp": decompose(feats)}


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def core_overlap(data):
    """Pairwise: |core_a ∩ core_b| / |core_a ∪ core_b| across targets."""
    targets = list(data.keys())
    n = len(targets)
    mat = np.full((n, n), np.nan)
    for i, a in enumerate(targets):
        for j, b in enumerate(targets):
            ca, cb = data[a]["decomp"]["core"], data[b]["decomp"]["core"]
            union = ca | cb
            mat[i, j] = len(ca & cb) / len(union) if union else 0.0
    return mat, targets


def generic_number_core(boring_data):
    """Features that are in the invariant core of EVERY boring number.
    This is the 'generic number' skeleton — the pipeline's null."""
    cores = [d["decomp"]["core"] for d in boring_data.values()]
    return set.intersection(*cores) if cores else set()


def target_unique_core(target_core, generic_core):
    return target_core - generic_core


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_core_size_comparison(cult_data, boring_data):
    fig, ax = plt.subplots(figsize=(12, 5))

    targets = list(cult_data.keys()) + list(boring_data.keys())
    core_sizes = ([len(cult_data[t]["decomp"]["core"]) for t in cult_data] +
                  [len(boring_data[t]["decomp"]["core"]) for t in boring_data])
    colors = ["tomato"] * len(cult_data) + ["steelblue"] * len(boring_data)

    x = np.arange(len(targets))
    bars = ax.bar(x, core_sizes, color=colors, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in targets])
    ax.set_ylabel("|invariant core| (features on in all 8 contexts)")
    ax.set_title("Invariant-core size: cultural (red) vs boring (blue)")

    cult_mean = np.mean(core_sizes[:len(cult_data)])
    boring_mean = np.mean(core_sizes[len(cult_data):])
    ax.axhline(cult_mean, color="tomato", linestyle="--", alpha=0.6,
               label=f"cultural mean = {cult_mean:.1f}")
    ax.axhline(boring_mean, color="steelblue", linestyle="--", alpha=0.6,
               label=f"boring mean = {boring_mean:.1f}")
    ax.legend()

    for b, v in zip(bars, core_sizes):
        ax.text(b.get_x() + b.get_width()/2, v, str(v),
                ha="center", va="bottom", fontsize=8)

    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "core_size_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_coat_core_ratio(cult_data, boring_data):
    fig, ax = plt.subplots(figsize=(12, 5))
    targets = list(cult_data.keys()) + list(boring_data.keys())
    ratios = []
    for t in list(cult_data.keys()) + list(boring_data.keys()):
        d = (cult_data.get(t) or boring_data.get(t))["decomp"]
        coat = sum(len(s) for s in d["specific"].values())
        core = max(len(d["core"]), 1)
        ratios.append(coat / core)
    colors = ["tomato"] * len(cult_data) + ["steelblue"] * len(boring_data)
    x = np.arange(len(targets))
    bars = ax.bar(x, ratios, color=colors, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in targets])
    ax.set_ylabel("coat / core ratio")
    ax.set_title("Coat/core ratio — cultural (red) vs boring (blue)")
    for b, v in zip(bars, ratios):
        ax.text(b.get_x() + b.get_width()/2, v, f"{v:.1f}",
                ha="center", va="bottom", fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "coat_core_ratio.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_core_overlap(all_data):
    mat, targets = core_overlap(all_data)
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(mat, cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(range(len(targets)))
    ax.set_xticklabels([str(t) for t in targets], rotation=45, ha="right")
    ax.set_yticks(range(len(targets)))
    ax.set_yticklabels([str(t) for t in targets])
    ax.set_title("Jaccard overlap between invariant cores\n"
                 "(cultural targets in top-left, boring in bottom-right)")
    for i in range(len(targets)):
        for j in range(len(targets)):
            v = mat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=7, color="black" if v < 0.6 else "white")
    plt.colorbar(im, ax=ax, fraction=0.045)
    fig.tight_layout()
    out = RESULTS_DIR / "core_jaccard_overlap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_generic_vs_unique(cult_data, boring_data, generic_core):
    fig, ax = plt.subplots(figsize=(12, 5))
    targets = list(cult_data.keys()) + list(boring_data.keys())
    generic_sizes = []
    unique_sizes = []
    for t in targets:
        core = (cult_data.get(t) or boring_data.get(t))["decomp"]["core"]
        generic_sizes.append(len(core & generic_core))
        unique_sizes.append(len(core - generic_core))

    x = np.arange(len(targets))
    w = 0.4
    ax.bar(x - w/2, generic_sizes, w, label=f"in generic-boring core ({len(generic_core)} feats)",
           color="steelblue", alpha=0.8)
    ax.bar(x + w/2, unique_sizes, w, label="unique to this target",
           color="tomato", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([str(t) for t in targets])
    ax.set_ylabel("feature count in this target's core")
    ax.set_title("How much of each target's core is generic-number "
                 "vs target-specific?")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out = RESULTS_DIR / "generic_vs_unique.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(cult_data, boring_data, generic_core, cache):
    out = RESULTS_DIR / "null_peer_report.txt"
    lines = [f"Null-Peer Battery Report — layer {PROBE_LAYER}",
             "=" * 70, ""]

    lines.append("GENERIC-NUMBER CORE (intersection across ALL boring-number cores):")
    lines.append(f"  size = {len(generic_core)} features")
    for fid in sorted(generic_core,
                      key=lambda f: -np.mean([
                          boring_data[t]["feats"]["referential"][f]
                          for t in boring_data])):
        label = fetch_feature_label(int(fid), cache) or "—"
        mean_strength = np.mean([boring_data[t]["feats"]["referential"][fid]
                                 for t in boring_data])
        lines.append(f"    F{int(fid):5d}  μ_ref={mean_strength:5.2f}  {label}")

    lines.append("\n" + "=" * 70)
    lines.append("CULTURAL TARGETS — core decomposition + what's unique")
    lines.append("=" * 70)
    for t, data in cult_data.items():
        decomp = data["decomp"]
        core = decomp["core"]
        unique = core - generic_core
        generic_hit = core & generic_core
        coat = sum(len(s) for s in decomp["specific"].values())
        lines.append(f"\n### n = {t}")
        lines.append(f"  core={len(core)}  unique_to_target={len(unique)}  "
                     f"shared_with_generic={len(generic_hit)}  coat={coat}  "
                     f"coat/core={coat/max(len(core),1):.1f}")
        lines.append("  TARGET-UNIQUE CORE FEATURES:")
        for fid in sorted(unique,
                          key=lambda f: -np.mean([data["feats"][c][f]
                                                  for c in data["feats"]])):
            label = fetch_feature_label(int(fid), cache) or "—"
            mu = np.mean([data["feats"][c][fid] for c in data["feats"]])
            lines.append(f"    F{int(fid):5d}  μ={mu:5.2f}  {label}")

    lines.append("\n" + "=" * 70)
    lines.append("BORING TARGETS — core decomposition + what's unique")
    lines.append("=" * 70)
    for t, data in boring_data.items():
        decomp = data["decomp"]
        core = decomp["core"]
        unique = core - generic_core
        generic_hit = core & generic_core
        coat = sum(len(s) for s in decomp["specific"].values())
        lines.append(f"\n### n = {t}")
        lines.append(f"  core={len(core)}  unique_to_target={len(unique)}  "
                     f"shared_with_generic={len(generic_hit)}  coat={coat}  "
                     f"coat/core={coat/max(len(core),1):.1f}")
        if unique:
            lines.append("  TARGET-UNIQUE CORE FEATURES:")
            for fid in sorted(unique,
                              key=lambda f: -np.mean([data["feats"][c][f]
                                                      for c in data["feats"]])):
                label = fetch_feature_label(int(fid), cache) or "—"
                mu = np.mean([data["feats"][c][fid] for c in data["feats"]])
                lines.append(f"    F{int(fid):5d}  μ={mu:5.2f}  {label}")

    out.write_text("\n".join(lines))
    save_cache(cache)
    print(f"\nReport: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()
    cache = load_cache()

    cult_data = {}
    for n in CULTURAL:
        print(f"\n=== cultural {n} ===")
        d = scan_target(model, sae, n)
        if d is None:
            print(f"   [{n}] skipped (token issue)")
            continue
        cult_data[n] = d
        print(f"   core={len(d['decomp']['core'])}  "
              f"coat={sum(len(s) for s in d['decomp']['specific'].values())}")

    boring_data = {}
    for n in BORING:
        print(f"\n=== boring {n} ===")
        d = scan_target(model, sae, n)
        if d is None:
            print(f"   [{n}] skipped (token issue)")
            continue
        boring_data[n] = d
        print(f"   core={len(d['decomp']['core'])}  "
              f"coat={sum(len(s) for s in d['decomp']['specific'].values())}")

    # Generic-number core: features present in EVERY boring core
    generic_core = generic_number_core(boring_data)
    print(f"\nGeneric-number core (∩ of boring cores): {len(generic_core)} features")

    all_data = {**cult_data, **boring_data}

    print("\nGenerating plots...")
    plot_core_size_comparison(cult_data, boring_data)
    plot_coat_core_ratio(cult_data, boring_data)
    plot_core_overlap(all_data)
    plot_generic_vs_unique(cult_data, boring_data, generic_core)

    print("\nWriting report...")
    write_report(cult_data, boring_data, generic_core, cache)

    # Summary
    print("\n--- Summary ---")
    print("target    group      core   unique_to_target   coat/core")
    for t, d in list(cult_data.items()) + list(boring_data.items()):
        group = "cultural" if t in cult_data else "boring  "
        core = d["decomp"]["core"]
        unique = len(core - generic_core)
        coat = sum(len(s) for s in d["decomp"]["specific"].values())
        ratio = coat / max(len(core), 1)
        print(f"  {t:>4}  {group}   {len(core):>4}   {unique:>4}            "
              f"{ratio:>6.1f}")

    cult_unique = np.mean([len(cult_data[t]["decomp"]["core"] - generic_core)
                           for t in cult_data])
    boring_unique = np.mean([len(boring_data[t]["decomp"]["core"] - generic_core)
                             for t in boring_data])
    print(f"\n  MEAN unique-core per target: cultural={cult_unique:.2f}, "
          f"boring={boring_unique:.2f}")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
