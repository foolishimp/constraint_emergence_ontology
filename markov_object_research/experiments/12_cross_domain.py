"""
Experiment 12: Cross-Domain Generalization

Does the Markov-object structure discovered for numbers (fat feature count for
culturally-loaded items, thin for generic; context-selected coat over thin core)
hold for other semantic domains?

Domains tested:
  - colors     (common → rare: red, blue, green, burgundy, vermilion, taupe, puce)
  - emotions   (common → rare: happy, sad, angry, melancholy, schadenfreude, saudade)
  - names      (common → rare: John, Mary, Muhammad, Siddhartha, Aoife, Guadalupe)
  - objects    (common → rare: car, dog, book, astrolabe, samovar, armoire)

Method:
  - Template: "The {domain} {word}"
    e.g. "The color red", "The emotion happy"
  - Extract SAE features at layer 8 for the target word's last token
  - Measure active feature count

Prediction:
  Common/heavy terms have more SAE features than rare/narrow terms —
  analogous to 999 > 500 in numbers. If the pattern holds, Markov-object
  density tracks cultural/semantic weight across domains, not just numbers.

Bonus: run a context-conditional probe on one heavy term per domain
(red, happy, Muhammad, car) to check if coat/core decomposition generalizes.
"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import urllib.request

RESULTS_DIR = Path(__file__).parent.parent / "results" / "12_cross_domain"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILES_READ = [
    Path(__file__).parent.parent / "results" / "08_feature_identity" / "neuronpedia_cache.json",
    Path(__file__).parent.parent / "results" / "09_context_conditional" / "neuronpedia_cache.json",
    Path(__file__).parent.parent / "results" / "10_layer_assembly" / "neuronpedia_cache.json",
    Path(__file__).parent.parent / "results" / "11_cross_representation" / "neuronpedia_cache.json",
]
CACHE_FILE = RESULTS_DIR / "neuronpedia_cache.json"

PROBE_LAYER = 8
ACTIVATION_THRESHOLD = 0.5

DOMAINS = {
    "color":   [
        ("red", "common"), ("blue", "common"), ("green", "common"),
        ("burgundy", "uncommon"), ("vermilion", "rare"),
        ("taupe", "rare"), ("puce", "rare"), ("cerise", "rare"),
    ],
    "emotion": [
        ("happy", "common"), ("sad", "common"), ("angry", "common"),
        ("melancholy", "uncommon"), ("jealous", "common"),
        ("schadenfreude", "rare"), ("saudade", "rare"),
        ("ennui", "uncommon"),
    ],
    "name":    [
        ("John", "common"), ("Mary", "common"), ("David", "common"),
        ("Muhammad", "common"), ("Siddhartha", "uncommon"),
        ("Aoife", "rare"), ("Guadalupe", "uncommon"),
    ],
    "object":  [
        ("car", "common"), ("dog", "common"), ("book", "common"),
        ("astrolabe", "rare"), ("samovar", "rare"),
        ("armoire", "uncommon"),
    ],
}

TEMPLATES = {
    "color":   "The color {word}",
    "emotion": "The emotion {word}",
    "name":    "The person {word}",
    "object":  "The object {word}",
}

CONTEXT_TEST_WORDS = {
    "color":   "red",
    "emotion": "happy",
    "name":    "Muhammad",
    "object":  "car",
}

CONTEXTS = {
    "referential":  "The {domain} {word} is",
    "descriptive":  "A {word} thing appeared",
    "narrative":    "She loved the {word}",
    "negation":     "It was not {word}",
    "comparative":  "More {word} than before",
}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def load_cache():
    cache = {}
    for p in CACHE_FILES_READ:
        if p.exists():
            cache.update(json.loads(p.read_text()))
    if CACHE_FILE.exists():
        cache.update(json.loads(CACHE_FILE.read_text()))
    return cache


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def fetch_feature_label(fid, cache, delay=0.2):
    key = f"gpt2-small/{PROBE_LAYER}-res-jb/{fid}"
    if key in cache:
        return cache[key]
    url = f"https://www.neuronpedia.org/api/feature/gpt2-small/{PROBE_LAYER}-res-jb/{fid}"
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
# Model
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


def get_features(model, sae, text, span):
    import torch
    pos = last_token_of_span(model, text, span)
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


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def collect_domain_features(model, sae):
    """For each (domain, word), get feature vector and active count."""
    data = {}
    for domain, words in DOMAINS.items():
        data[domain] = []
        print(f"\n  domain: {domain}")
        for word, rarity in words:
            text = TEMPLATES[domain].format(word=word)
            vec, pos = get_features(model, sae, text, word)
            if vec is None:
                print(f"    [{word:15s}] '{text}' — span not found")
                continue
            n_active = int((vec > ACTIVATION_THRESHOLD).sum())
            print(f"    [{word:15s}] ({rarity:8s}) pos={pos}  active={n_active}")
            data[domain].append({
                "word": word,
                "rarity": rarity,
                "vec": vec,
                "n_active": n_active,
            })
    return data


def context_conditional_probe(model, sae, domain, word):
    """
    Like exp 09 but for a non-numeric word. Returns feature decomposition
    across contexts.
    """
    vectors = {}
    for ctx_name, template in CONTEXTS.items():
        text = template.format(domain=domain, word=word)
        vec, pos = get_features(model, sae, text, word)
        if vec is None:
            continue
        vectors[ctx_name] = vec

    if len(vectors) < 3:
        return None

    # Decompose
    active_sets = {c: set(np.where(v > ACTIVATION_THRESHOLD)[0].tolist())
                   for c, v in vectors.items()}
    all_active = set().union(*active_sets.values())
    core = set.intersection(*active_sets.values())
    context_specific = {}
    for c in active_sets:
        others = set().union(*[s for cc, s in active_sets.items() if cc != c])
        context_specific[c] = active_sets[c] - others
    total_specific = sum(len(s) for s in context_specific.values())

    return {
        "vectors": vectors,
        "all_active": all_active,
        "core": core,
        "context_specific": context_specific,
        "total_specific": total_specific,
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_feature_count_by_domain(data):
    fig, axes = plt.subplots(1, len(data), figsize=(4.5 * len(data), 5), sharey=True)
    if len(data) == 1:
        axes = [axes]
    rarity_color = {"common": "steelblue", "uncommon": "gold", "rare": "tomato"}

    for ax, (domain, entries) in zip(axes, data.items()):
        words = [e["word"] for e in entries]
        counts = [e["n_active"] for e in entries]
        colors = [rarity_color[e["rarity"]] for e in entries]
        ax.bar(range(len(words)), counts, color=colors, alpha=0.85)
        ax.set_xticks(range(len(words)))
        ax.set_xticklabels(words, rotation=40, ha="right", fontsize=8)
        ax.set_title(domain)
        ax.grid(True, alpha=0.3, axis="y")
        for i, c in enumerate(counts):
            ax.text(i, c + 0.5, str(c), ha="center", fontsize=8)

    axes[0].set_ylabel("Active SAE features")
    # Add legend as patches
    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(color=c, label=r) for r, c in rarity_color.items()]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9)
    fig.suptitle(f"Feature count by domain — layer {PROBE_LAYER}\n"
                 "Does the 'cultural weight → fatter object' pattern hold outside numbers?",
                 fontweight="bold")
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    out = RESULTS_DIR / "feature_count_by_domain.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Feature count plot: {out.name}")


def plot_rarity_aggregation(data):
    """
    Aggregated bar: for each domain, mean feature count per rarity class.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    domains = list(data.keys())
    rarities = ["common", "uncommon", "rare"]
    x = np.arange(len(domains))
    width = 0.27
    colors = ["steelblue", "gold", "tomato"]

    for i, rarity in enumerate(rarities):
        means = []
        for d in domains:
            vals = [e["n_active"] for e in data[d] if e["rarity"] == rarity]
            means.append(np.mean(vals) if vals else 0)
        ax.bar(x + i * width, means, width, color=colors[i], alpha=0.9,
               label=rarity)
        for xi, v in zip(x + i * width, means):
            if v > 0:
                ax.text(xi, v + 0.5, f"{v:.0f}", ha="center", fontsize=8)

    ax.set_xticks(x + width)
    ax.set_xticklabels(domains)
    ax.set_ylabel("Mean active SAE features")
    ax.set_title(f"Mean feature count by rarity — layer {PROBE_LAYER}\n"
                 "Prediction: common > uncommon > rare if pattern is universal")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(fontsize=9)
    fig.tight_layout()
    out = RESULTS_DIR / "rarity_aggregation.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Rarity aggregation: {out.name}")


def plot_context_decomposition(context_data):
    """
    For each cross-domain probed word, show core / shared / specific.
    Stacked bars.
    """
    words = list(context_data.keys())
    core = [len(context_data[w]["core"]) for w in words]
    specific = [context_data[w]["total_specific"] for w in words]
    total = [len(context_data[w]["all_active"]) for w in words]
    shared = [total[i] - core[i] - specific[i] for i in range(len(words))]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(words))
    ax.bar(x, core,   label="Invariant core",    color="steelblue")
    ax.bar(x, shared, bottom=core, label="Shared pool", color="gold")
    ax.bar(x, specific, bottom=[c+s for c,s in zip(core, shared)],
           label="Context-specific", color="tomato")

    ax.set_xticks(x)
    ax.set_xticklabels(words, fontsize=10)
    ax.set_xlabel("Word (one from each domain)")
    ax.set_ylabel("SAE features")
    ax.set_title(f"Context decomposition for non-numeric words — layer {PROBE_LAYER}\n"
                 "Does 'tiny core, fat coat' generalize beyond numbers?")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    for xi, (c, s, sp) in enumerate(zip(core, shared, specific)):
        tot = c + s + sp
        ax.text(xi, tot + 2, f"core={c}\ncoat={sp}\ntotal={tot}",
                ha="center", fontsize=7)
    fig.tight_layout()
    out = RESULTS_DIR / "cross_domain_context_decomposition.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Context decomposition: {out.name}")


def write_report(data, context_data, cache):
    out = RESULTS_DIR / "domain_report.txt"
    lines = [f"Cross-Domain Report — layer {PROBE_LAYER}", "=" * 70, ""]
    for domain, entries in data.items():
        lines.append(f"\n### {domain}")
        lines.append("-" * 50)
        for e in entries:
            lines.append(f"  {e['word']:20s} ({e['rarity']:8s})  {e['n_active']:>3} features")

    lines.append("\n\n### Context decomposition (one word per domain)")
    lines.append("=" * 50)
    for word, dec in context_data.items():
        if dec is None:
            continue
        lines.append(f"\n{word}")
        lines.append(f"  total  = {len(dec['all_active'])}")
        lines.append(f"  core   = {len(dec['core'])}")
        lines.append(f"  coat   = {dec['total_specific']}")
        lines.append("  core features:")
        sorted_core = sorted(dec["core"],
                             key=lambda f: -np.mean([dec["vectors"][c][f] for c in dec["vectors"]]))
        for fid in sorted_core[:6]:
            label = fetch_feature_label(int(fid), cache) or "—"
            ms = np.mean([dec["vectors"][c][fid] for c in dec["vectors"]])
            lines.append(f"    F{int(fid):5d}  μ={ms:5.2f}  {label}")
        save_cache(cache)

    out.write_text("\n".join(lines))
    print(f"Domain report: {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model, sae = load_model_and_sae()
    cache = load_cache()

    print("Collecting domain features...")
    data = collect_domain_features(model, sae)

    print("\nContext-conditional probe on one word per domain...")
    context_data = {}
    for domain, word in CONTEXT_TEST_WORDS.items():
        print(f"  {domain} / {word}")
        context_data[word] = context_conditional_probe(model, sae, domain, word)

    print("\nGenerating plots...")
    plot_feature_count_by_domain(data)
    plot_rarity_aggregation(data)
    plot_context_decomposition({w: d for w, d in context_data.items() if d is not None})

    print("\nWriting report (querying Neuronpedia for core labels)...")
    write_report(data, context_data, cache)

    # Summary
    print("\n--- Summary: feature count by rarity per domain ---")
    for domain, entries in data.items():
        by_rarity = {}
        for e in entries:
            by_rarity.setdefault(e["rarity"], []).append(e["n_active"])
        line = f"  {domain:10s}: "
        for r in ("common", "uncommon", "rare"):
            if r in by_rarity:
                line += f"{r}={np.mean(by_rarity[r]):5.1f}  "
        print(line)

    print("\n--- Context decomposition summary ---")
    for word, dec in context_data.items():
        if dec is None:
            print(f"  {word:15s}: too few contexts")
            continue
        print(f"  {word:15s}: total={len(dec['all_active']):>3}  "
              f"core={len(dec['core']):>3}  coat={dec['total_specific']:>3}  "
              f"coat/core ratio={dec['total_specific']/max(len(dec['core']),1):.1f}")

    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
