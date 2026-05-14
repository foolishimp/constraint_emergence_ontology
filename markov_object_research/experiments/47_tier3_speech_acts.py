"""
Experiment 47 (Tier 3): Speech-act / functional-role continuation cluster

Tier 1-2 verified that named entities and named categories cluster as the
dominant variable. Tier 3 escalates: do *speech acts / functional roles*
cluster? The targets are no longer surface tokens but **functional positions**
in discourse — apology, request, accusation, concession, justification,
greeting. Each is realized in many surface forms; the question is whether the
function survives that surface variation.

For each speech act, multiple surface realizations (different phrasings) and
multiple content fillers (different topics/situations). The continuation
should respond to the FUNCTION, not the surface or content.

Pre-registered:
  PASS    silhouette(act) >= 0.15  AND  act > realization + 0.05  AND  act > template + 0.05
  PARTIAL silhouette(act) >= 0.07  AND  act > realization AND act > template
  FAIL    otherwise

Note thresholds drop from Tier 2 (0.20 / 0.10) to (0.15 / 0.07) reflecting the
expected loosening at higher abstraction.

Outputs:
  results/47_tier3_speech_acts/
    report.txt, summary.json, embedding_pca.png, silhouette_comparison.png
"""

import json, time, random
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import torch
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results" / "47_tier3_speech_acts"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LLM_NAME = "meta-llama/Meta-Llama-3-8B"
DEVICE   = "mps"
DTYPE    = torch.float16
EMBED_MODEL = "all-mpnet-base-v2"

# Each speech act has multiple realizations (surface forms) and a content filler.
# The continuation prompt asks the model to respond AS IF it had received this
# speech act. The function should drive the cluster geometry; surface form and
# content should be secondary.

SPEECH_ACTS = {
    "apology": [
        "I'm really sorry about {c}.",
        "I owe you an apology for {c}.",
        "Please forgive me for {c}.",
    ],
    "request": [
        "Could you please help me with {c}?",
        "Would you mind {c}?",
        "I'd appreciate it if you could {c}.",
    ],
    "accusation": [
        "You're the one responsible for {c}.",
        "It was you who did {c}, wasn't it?",
        "You knew about {c} and said nothing.",
    ],
    "concession": [
        "Fine, you're right about {c}.",
        "I'll grant you that {c}.",
        "OK, I can see why you'd say that about {c}.",
    ],
    "justification": [
        "The reason is that {c}.",
        "I had to do it because {c}.",
        "It only makes sense given {c}.",
    ],
}

# Content fillers — varied topics so cluster cannot be lexical-content-driven.
CONTENTS = [
    "the meeting yesterday",
    "the broken vase",
    "the missing report",
    "the noise last night",
]

# Continuation prompt: ask the model what comes next as a *response* to the
# speech act. So the response-continuation reflects the function role.
RESPONSE_FRAME = "{utterance} The other person responds:"

N_GEN_PER_PROMPT = 5
MAX_NEW_TOKENS  = 24
TEMPERATURE     = 0.8
SEED            = 42


def load_llm():
    from transformer_lens import HookedTransformer
    print(f"Loading {LLM_NAME} on {DEVICE} ({DTYPE})...")
    t0 = time.time()
    model = HookedTransformer.from_pretrained(LLM_NAME, device=DEVICE,
                                                dtype=DTYPE)
    model.eval()
    print(f"  loaded in {time.time()-t0:.1f}s.")
    return model


def load_embedder():
    from sentence_transformers import SentenceTransformer
    print(f"Loading embedder {EMBED_MODEL} ...")
    return SentenceTransformer(EMBED_MODEL)


def generate_continuations(model, prompt, n=N_GEN_PER_PROMPT,
                            max_new_tokens=MAX_NEW_TOKENS,
                            temperature=TEMPERATURE):
    outputs = []
    tokens = model.to_tokens(prompt, prepend_bos=True).to(DEVICE)
    for i in range(n):
        torch.manual_seed(SEED + i * 17 + abs(hash(prompt)) % 100)
        with torch.no_grad():
            gen = model.generate(
                tokens, max_new_tokens=max_new_tokens,
                temperature=temperature, top_k=40, top_p=0.95,
                stop_at_eos=True, verbose=False,
            )
        text = model.tokenizer.decode(gen[0].cpu().tolist(),
                                       skip_special_tokens=True)
        completion = text[len(prompt):].strip() if text.startswith(prompt) else text.strip()
        outputs.append(completion)
    return outputs


def main():
    random.seed(SEED); torch.manual_seed(SEED); np.random.seed(SEED)
    llm = load_llm()
    embedder = load_embedder()

    print("\n=== generation phase ===")
    samples = []
    total_cells = sum(len(reals) for reals in SPEECH_ACTS.values()) * len(CONTENTS)
    cell = 0
    t_total_start = time.time()
    for act, realizations in SPEECH_ACTS.items():
        for real_idx, realization in enumerate(realizations):
            for content in CONTENTS:
                cell += 1
                utterance = realization.format(c=content)
                prompt = RESPONSE_FRAME.format(utterance=utterance)
                t0 = time.time()
                comps = generate_continuations(llm, prompt)
                elapsed = time.time() - t0
                for c in comps:
                    samples.append({
                        "act": act,
                        "realization": realization,
                        "realization_idx": real_idx,
                        "content": content,
                        "utterance": utterance,
                        "prompt": prompt,
                        "completion": c,
                    })
                print(f"  [{cell:3d}/{total_cells} act={act:<13s} real#{real_idx} "
                      f"content={content[:25]:<25s}] {N_GEN_PER_PROMPT} in {elapsed:.1f}s")
    print(f"\nTotal generation time: {(time.time()-t_total_start)/60:.1f} min")
    print(f"Total samples: {len(samples)}")

    print("\n=== embedding phase ===")
    completions = [s["completion"] for s in samples]
    embeddings = embedder.encode(completions, show_progress_bar=False,
                                   convert_to_numpy=True)
    print(f"  shape: {embeddings.shape}")

    act_labels   = [s["act"] for s in samples]
    real_labels  = [f"{s['act']}/{s['realization_idx']}" for s in samples]
    content_labels = [s["content"] for s in samples]

    sil_act     = float(silhouette_score(embeddings, act_labels,     metric="cosine"))
    sil_real    = float(silhouette_score(embeddings, real_labels,    metric="cosine"))
    sil_content = float(silhouette_score(embeddings, content_labels, metric="cosine"))
    print(f"\n  silhouette by ACT:         {sil_act:+.3f}")
    print(f"  silhouette by REALIZATION: {sil_real:+.3f}")
    print(f"  silhouette by CONTENT:     {sil_content:+.3f}")

    # Per-act centroid + tightness
    act_within = {}
    centroids = {}
    for act in SPEECH_ACTS.keys():
        mask = np.array([s["act"] == act for s in samples])
        em = embeddings[mask]
        c = em.mean(0); centroids[act] = c
        cn = c / (np.linalg.norm(c) + 1e-9)
        en = em / (np.linalg.norm(em, axis=1, keepdims=True) + 1e-9)
        act_within[act] = float(np.mean(en @ cn))
    print("\n  per-act within-cluster tightness:")
    for a, v in act_within.items():
        print(f"    {a:<14s}  {v:+.3f}")

    # Pairwise act centroid cosines
    acts = list(SPEECH_ACTS.keys())
    pair = {}
    for i, a1 in enumerate(acts):
        for a2 in acts[i+1:]:
            v1 = centroids[a1] / (np.linalg.norm(centroids[a1]) + 1e-9)
            v2 = centroids[a2] / (np.linalg.norm(centroids[a2]) + 1e-9)
            pair[f"{a1}--{a2}"] = float(np.dot(v1, v2))

    # Verdict
    if (sil_act >= 0.15 and sil_act > sil_real + 0.05
            and sil_act > sil_content + 0.05):
        verdict = "PASS"
    elif sil_act >= 0.07 and sil_act > sil_real and sil_act > sil_content:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    print(f"\nVERDICT: {verdict}")

    # Plots
    pca = PCA(n_components=2)
    proj = pca.fit_transform(embeddings)
    fig, ax = plt.subplots(figsize=(11, 8))
    cmap = plt.cm.tab10(np.linspace(0, 1, len(SPEECH_ACTS)))
    for color, act in zip(cmap, SPEECH_ACTS.keys()):
        mask = np.array([s["act"] == act for s in samples])
        ax.scatter(proj[mask, 0], proj[mask, 1], color=color, label=act,
                   alpha=0.6, s=30)
        cm = proj[mask].mean(0)
        ax.scatter(cm[0], cm[1], color=color, marker="X", s=300,
                   edgecolors="black", linewidths=1.5)
    ax.legend(fontsize=10)
    ax.set_title(f"Tier 3 — PCA of response-continuations colored by SPEECH ACT\n"
                 f"sil: act {sil_act:+.3f}  realization {sil_real:+.3f}  "
                 f"content {sil_content:+.3f}")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "embedding_pca.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(["act", "realization", "content"],
            [sil_act, sil_real, sil_content],
            color=["steelblue", "lightcoral", "lightgray"])
    ax.axhline(0.15, color="green",  linestyle="--", alpha=0.5, label="PASS thr 0.15")
    ax.axhline(0.07, color="orange", linestyle="--", alpha=0.5, label="PARTIAL thr 0.07")
    ax.set_ylabel("silhouette score (cosine)")
    ax.set_title("Tier 3: silhouette by speech act vs realization vs content")
    ax.legend(); ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "silhouette_comparison.png", dpi=150)
    plt.close(fig)

    lines = [f"Exp 47 - Tier 3 Speech-Act Continuation Cluster",
             f"Substrate: {LLM_NAME}   Embedder: {EMBED_MODEL}", "=" * 70, ""]
    lines.append(f"Speech acts ({len(SPEECH_ACTS)}): {list(SPEECH_ACTS.keys())}")
    lines.append(f"Realizations per act: {len(next(iter(SPEECH_ACTS.values())))}")
    lines.append(f"Content fillers: {len(CONTENTS)}")
    lines.append(f"Generations per (real × content): {N_GEN_PER_PROMPT}")
    lines.append(f"Total samples: {len(samples)}")
    lines.append("")
    lines.append("Pre-registered outcome rules (Tier 3 — looser than Tier 1/2):")
    lines.append("  PASS    sil(act) >= 0.15 AND act > real + 0.05 AND act > content + 0.05")
    lines.append("  PARTIAL sil(act) >= 0.07 AND act > real AND act > content")
    lines.append("  FAIL    otherwise")
    lines.append("")
    lines.append(f"AGGREGATE OUTCOME: {verdict}")
    lines.append(f"  silhouette by ACT:         {sil_act:+.3f}")
    lines.append(f"  silhouette by REALIZATION: {sil_real:+.3f}")
    lines.append(f"  silhouette by CONTENT:     {sil_content:+.3f}")
    lines.append(f"  act - realization gap: {sil_act - sil_real:+.3f}")
    lines.append(f"  act - content gap:     {sil_act - sil_content:+.3f}")
    lines.append("")
    lines.append("Per-act within-cluster tightness:")
    for a, v in act_within.items():
        lines.append(f"  {a:<14s}  {v:+.3f}")
    lines.append("")
    lines.append("Pairwise act centroid cosine (lower = more separated):")
    for k, v in sorted(pair.items(), key=lambda x: -x[1]):
        lines.append(f"  {k:<32s}  {v:+.3f}")
    (RESULTS_DIR / "report.txt").write_text("\n".join(lines))
    print(f"\nReport: {RESULTS_DIR / 'report.txt'}")

    summary = {
        "design": "exp 47: Tier 3 speech acts",
        "llm": LLM_NAME,
        "embedder": EMBED_MODEL,
        "speech_acts": SPEECH_ACTS,
        "contents": CONTENTS,
        "n_samples": len(samples),
        "silhouette_by_act":         sil_act,
        "silhouette_by_realization": sil_real,
        "silhouette_by_content":     sil_content,
        "act_minus_real_gap":    sil_act - sil_real,
        "act_minus_content_gap": sil_act - sil_content,
        "per_act_within": act_within,
        "pairwise_act_centroid_cosines": pair,
        "verdict": verdict,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2,
                                                          default=float))
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
