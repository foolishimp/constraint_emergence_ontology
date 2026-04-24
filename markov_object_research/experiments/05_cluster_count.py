"""
Experiment 05: How Many Clusters of 7 Are There?

Don't define registers in advance — let the model reveal them.

Run "7" across hundreds of diverse contexts. Extract the activation at the
position of the token "7" in each sentence. Cluster. Count.

The number of stable clusters is the number of distinct Markov objects
the model has learned for the surface token "7".

Method:
  - 200+ sentences containing "7" across every semantic context we can think of
  - Tokenize each, find the "7" token position
  - Extract hidden state at that position, per layer
  - UMAP → 2D, then HDBSCAN (no k required — discovers k from density)
  - Count clusters, label by inspecting members
  - Compare cluster count across layers: where does "7" fragment most?
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path(__file__).parent.parent / "results" / "05_cluster_count"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PROBE_LAYERS = [0, 2, 4, 6, 8, 10, 11]  # embedding + transformer layers


CONTEXTS = [
    # --- arithmetic / pure math ---
    ("math", "1 + 6 = 7"),
    ("math", "3 + 4 = 7"),
    ("math", "14 - 7 = 7"),
    ("math", "7 squared is 49"),
    ("math", "7 is a prime number"),
    ("math", "The seventh prime is 17"),
    ("math", "Divide 21 by 3 to get 7"),
    ("math", "7 times 8 is 56"),
    ("math", "The factorial of 7 is 5040"),
    ("math", "log base 10 of 7 is approximately 0.845"),
    ("math", "7 is odd"),
    ("math", "7 is less than 8"),
    ("math", "The square root of 49 is 7"),
    ("math", "2 to the power of 7 is 128"),
    ("math", "7 mod 3 equals 1"),

    # --- money / financial ---
    ("money", "The coffee cost 7 dollars"),
    ("money", "She saved 7 pounds"),
    ("money", "It was on sale for 7 euros"),
    ("money", "He earned 7 dollars an hour"),
    ("money", "The ticket costs 7 dollars"),
    ("money", "She paid 7 cents in change"),
    ("money", "The stock rose by 7 percent"),
    ("money", "His salary was 7 figures"),
    ("money", "The bill came to 7 hundred dollars"),
    ("money", "She invested 7 thousand in the fund"),

    # --- time ---
    ("time", "The meeting is at 7 o'clock"),
    ("time", "She woke up at 7 in the morning"),
    ("time", "The train leaves at 7"),
    ("time", "He stayed until 7 pm"),
    ("time", "It was exactly 7 minutes past the hour"),
    ("time", "The alarm rang at 7 am"),
    ("time", "Dinner is served at 7"),
    ("time", "The store opens at 7"),
    ("time", "The flight departs at 7 in the evening"),
    ("time", "It takes 7 seconds to complete"),

    # --- ordinal / ranking ---
    ("ordinal", "She finished in 7th place"),
    ("ordinal", "The 7th chapter was the best"),
    ("ordinal", "He was the 7th person in line"),
    ("ordinal", "This is the 7th time it happened"),
    ("ordinal", "The 7th floor had the best view"),
    ("ordinal", "She was ranked 7th in the competition"),
    ("ordinal", "The 7th of July is a holiday"),
    ("ordinal", "It was the 7th attempt"),
    ("ordinal", "He came 7th out of ten"),
    ("ordinal", "The 7th element is nitrogen"),

    # --- date / calendar ---
    ("date", "July 7th was a Monday"),
    ("date", "She was born on the 7th of March"),
    ("date", "The deadline is November 7"),
    ("date", "They met on December 7"),
    ("date", "The event is scheduled for February 7th"),
    ("date", "It happened on August 7"),
    ("date", "The 7th of January was cold"),
    ("date", "She graduated on May 7th"),
    ("date", "The meeting is on the 7th"),
    ("date", "It was January 7, 2020"),

    # --- measurement / quantity ---
    ("measurement", "The room was 7 meters wide"),
    ("measurement", "She ran 7 kilometers"),
    ("measurement", "The temperature was 7 degrees"),
    ("measurement", "It weighed 7 kilograms"),
    ("measurement", "The cable is 7 feet long"),
    ("measurement", "He drank 7 glasses of water"),
    ("measurement", "The building has 7 floors"),
    ("measurement", "The box holds 7 liters"),
    ("measurement", "She waited 7 hours"),
    ("measurement", "The speed limit is 7 miles per hour"),

    # --- label / identifier ---
    ("label", "She stayed in room 7"),
    ("label", "Take bus number 7"),
    ("label", "Channel 7 had the best coverage"),
    ("label", "Player number 7 scored the goal"),
    ("label", "Gate 7 was at the end of the terminal"),
    ("label", "Highway 7 runs through the valley"),
    ("label", "Table 7 was by the window"),
    ("label", "Section 7 of the contract"),
    ("label", "Platform 7 at the station"),
    ("label", "Figure 7 shows the results"),

    # --- age ---
    ("age", "She was 7 years old"),
    ("age", "At age 7 he learned to read"),
    ("age", "The child is 7"),
    ("age", "The dog was 7 years old"),
    ("age", "He retired at 7 decades"),
    ("age", "The company was 7 years in business"),
    ("age", "She looked 7 years younger"),
    ("age", "The building is 7 years old"),
    ("age", "He has been here for 7 years"),
    ("age", "The tradition is 7 centuries old"),

    # --- score / rating ---
    ("score", "She gave it a 7 out of 10"),
    ("score", "He scored 7 in the exam"),
    ("score", "The movie got a 7 on the review site"),
    ("score", "The team won 7 to 3"),
    ("score", "She rated the restaurant 7 stars"),
    ("score", "His pain level was 7 out of 10"),
    ("score", "The judge gave her a 7"),
    ("score", "The essay was graded 7"),
    ("score", "He bowled a 7 on that frame"),
    ("score", "The match ended 7 all"),

    # --- cultural / symbolic ---
    ("cultural", "Seven is considered a lucky number"),
    ("cultural", "The seven deadly sins"),
    ("cultural", "Snow White and the 7 dwarfs"),
    ("cultural", "Seven wonders of the world"),
    ("cultural", "The seven seas"),
    ("cultural", "Seven days in a week"),
    ("cultural", "Lucky number 7 brought him fortune"),
    ("cultural", "The seventh son of a seventh son"),
    ("cultural", "Seven colors in the rainbow"),
    ("cultural", "The magnificent seven"),

    # --- science ---
    ("science", "The pH of pure water is 7"),
    ("science", "Nitrogen has atomic number 7"),
    ("science", "The group 7 elements are halogens"),
    ("science", "The seventh planet is Uranus"),
    ("science", "7 is the OSI model layer count"),
    ("science", "The half-life is 7 days"),
    ("science", "A week has 7 days due to astronomical observation"),
    ("science", "The scale goes from 0 to 7"),
    ("science", "There are 7 base SI units"),
    ("science", "The sample had a concentration of 7 molar"),

    # --- negative / signed ---
    ("negative", "The temperature dropped to minus 7"),
    ("negative", "He lost 7 points"),
    ("negative", "The balance was negative 7"),
    ("negative", "She was 7 under par"),
    ("negative", "The altitude is minus 7 meters"),
    ("negative", "The deficit was 7 billion"),
    ("negative", "He subtracted 7 from the total"),
    ("negative", "The feedback score was down 7"),
    ("negative", "Negative 7 degrees Celsius"),
    ("negative", "The index fell 7 points"),

    # --- fraction / ratio ---
    ("fraction", "7 out of 10 people agreed"),
    ("fraction", "She completed 7 of the 10 tasks"),
    ("fraction", "The ratio was 7 to 3"),
    ("fraction", "7 percent of the population"),
    ("fraction", "One seventh of the total"),
    ("fraction", "He answered 7 questions correctly out of 10"),
    ("fraction", "7 in every 100 cases"),
    ("fraction", "The probability was 7 in 10"),
    ("fraction", "She solved 7 out of the 12 problems"),
    ("fraction", "7 parts per million"),

    # --- address / location ---
    ("address", "She lived at number 7 on the street"),
    ("address", "The office is at 7 Main Street"),
    ("address", "Apartment 7 was on the second floor"),
    ("address", "He moved to 7 Oak Avenue"),
    ("address", "Seat 7 was in the middle row"),
    ("address", "The locker is number 7"),
    ("address", "Exit 7 on the motorway"),
    ("address", "Ward 7 in the hospital"),
    ("address", "Kilometre marker 7 on the trail"),
    ("address", "Bay 7 in the warehouse"),
]


def load_model():
    import torch
    from transformers import GPT2Model, GPT2Tokenizer
    print("Loading GPT-2...")
    tok = GPT2Tokenizer.from_pretrained("gpt2")
    model = GPT2Model.from_pretrained("gpt2", output_hidden_states=True)
    model.eval()
    return model, tok, torch


def find_seven_position(tokenizer, text):
    """
    Find the token index of '7' in the tokenized text.
    Returns the index of the first token that decodes to a string containing '7',
    or None if not found.
    """
    tokens = tokenizer.encode(text)
    for i, tok_id in enumerate(tokens):
        decoded = tokenizer.decode([tok_id])
        if "7" in decoded:
            return i
    return None


def extract_at_position(model, tokenizer, torch, text, layer, position):
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        out = model(**inputs, output_hidden_states=True)
    return out.hidden_states[layer][0, position, :].numpy()


def collect_activations(model, tokenizer, torch, layer):
    print(f"  Extracting activations at layer {layer}...")
    vecs, labels, sentences = [], [], []

    for label, text in CONTEXTS:
        pos = find_seven_position(tokenizer, text)
        if pos is None:
            continue
        vec = extract_at_position(model, tokenizer, torch, text, layer, pos)
        vecs.append(vec)
        labels.append(label)
        sentences.append(text)

    return np.array(vecs), labels, sentences


def cluster_hdbscan(vecs, min_cluster_size=4):
    try:
        import hdbscan
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                     min_samples=2, metric="euclidean")
        return clusterer.fit_predict(vecs)
    except ImportError:
        pass
    # Fallback: DBSCAN
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    scaled = StandardScaler().fit_transform(vecs)
    db = DBSCAN(eps=3.0, min_samples=3)
    return db.fit_predict(scaled)


def reduce_umap(vecs):
    try:
        from umap import UMAP
        return UMAP(n_components=2, random_state=42,
                    n_neighbors=10, min_dist=0.05).fit_transform(vecs)
    except ImportError:
        from sklearn.decomposition import PCA
        print("    (umap not available, using PCA)")
        return PCA(n_components=2, random_state=42).fit_transform(vecs)


def plot_layer(coords, cluster_ids, labels, sentences, layer, n_clusters):
    unique_clusters = sorted(set(cluster_ids))
    cmap = cm.get_cmap("tab20", max(len(unique_clusters), 1))

    fig, (ax_main, ax_legend) = plt.subplots(
        1, 2, figsize=(14, 7),
        gridspec_kw={"width_ratios": [3, 1]}
    )

    register_colors = {
        "math": "#e41a1c", "money": "#377eb8", "time": "#4daf4a",
        "ordinal": "#984ea3", "date": "#ff7f00", "measurement": "#a65628",
        "label": "#f781bf", "age": "#999999", "score": "#66c2a5",
        "cultural": "#fc8d62", "science": "#8da0cb", "negative": "#e78ac3",
        "fraction": "#a6d854", "address": "#ffd92f",
    }

    for cid in unique_clusters:
        mask = cluster_ids == cid
        color = "lightgray" if cid == -1 else cmap(cid)
        label_str = "noise" if cid == -1 else f"cluster {cid}"
        ax_main.scatter(coords[mask, 0], coords[mask, 1],
                        c=[color], s=60, alpha=0.8, label=label_str, zorder=3)

    # Overlay register as marker edge colour
    for i, (reg, sent) in enumerate(zip(labels, sentences)):
        ec = register_colors.get(reg, "black")
        ax_main.scatter(coords[i, 0], coords[i, 1],
                        s=60, facecolors="none", edgecolors=ec,
                        linewidths=1.2, zorder=4)

    ax_main.set_title(f"Layer {layer} — {n_clusters} cluster(s) found\n"
                      "Fill = cluster  |  Ring = semantic register")
    ax_main.set_xlabel("UMAP dim 1")
    ax_main.set_ylabel("UMAP dim 2")
    ax_main.grid(True, alpha=0.2)

    # Legend panel: cluster composition
    ax_legend.axis("off")
    lines = [f"Clusters: {n_clusters}  (noise={sum(cluster_ids==-1)})\n"]
    for cid in unique_clusters:
        if cid == -1:
            continue
        mask = cluster_ids == cid
        members = [labels[i] for i in range(len(labels)) if mask[i]]
        counter = defaultdict(int)
        for m in members:
            counter[m] += 1
        top = sorted(counter.items(), key=lambda x: -x[1])[:4]
        top_str = ", ".join(f"{k}({v})" for k, v in top)
        lines.append(f"C{cid} [{sum(mask)}]: {top_str}")

    ax_legend.text(0.02, 0.98, "\n".join(lines),
                   transform=ax_legend.transAxes,
                   va="top", ha="left", fontsize=7.5,
                   fontfamily="monospace",
                   bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))

    # Register colour key
    reg_text = "\nRegister colours:\n" + "\n".join(
        f"  {r}" for r in register_colors
    )
    ax_legend.text(0.02, 0.55, reg_text,
                   transform=ax_legend.transAxes,
                   va="top", ha="left", fontsize=6.5,
                   fontfamily="monospace")

    fig.tight_layout()
    out = RESULTS_DIR / f"layer_{layer:02d}_clusters.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_cluster_count_by_layer(layer_results):
    layers = [r["layer"] for r in layer_results]
    counts = [r["n_clusters"] for r in layer_results]
    noise = [r["n_noise"] for r in layer_results]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(layers, counts, marker="o", color="steelblue",
            linewidth=2, label="clusters found")
    ax.fill_between(layers, counts, alpha=0.15, color="steelblue")
    ax2 = ax.twinx()
    ax2.bar(layers, noise, alpha=0.25, color="tomato",
            width=0.6, label="noise points")
    ax2.set_ylabel("Noise points", color="tomato")
    ax.set_xlabel("Layer")
    ax.set_ylabel("Number of clusters")
    ax.set_title("How many distinct Markov objects does '7' have?\n"
                 "Cluster count by layer")
    ax.legend(loc="upper left", fontsize=8)
    ax2.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "cluster_count_by_layer.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Cluster count summary: {out}")


def main():
    model, tokenizer, torch = load_model()
    print(f"\n{len(CONTEXTS)} context sentences loaded")

    layer_results = []

    for layer in PROBE_LAYERS:
        print(f"\n=== Layer {layer} ===")
        vecs, labels, sentences = collect_activations(model, tokenizer, torch, layer)
        print(f"  {len(vecs)} activations extracted")

        coords = reduce_umap(vecs)
        cluster_ids = cluster_hdbscan(vecs)

        n_clusters = len(set(cluster_ids)) - (1 if -1 in cluster_ids else 0)
        n_noise = sum(cluster_ids == -1)
        print(f"  Clusters found: {n_clusters}  (noise: {n_noise})")

        # Cluster composition
        for cid in sorted(set(cluster_ids)):
            if cid == -1:
                continue
            mask = cluster_ids == cid
            members = [labels[i] for i in range(len(labels)) if mask[i]]
            counter = defaultdict(int)
            for m in members:
                counter[m] += 1
            top = sorted(counter.items(), key=lambda x: -x[1])[:5]
            print(f"    C{cid} [{sum(mask)}]: {', '.join(f'{k}({v})' for k, v in top)}")

        out = plot_layer(coords, cluster_ids, labels, sentences, layer, n_clusters)
        print(f"  Plot: {out.name}")

        layer_results.append({
            "layer": layer,
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "cluster_ids": cluster_ids,
            "labels": labels,
        })

    plot_cluster_count_by_layer(layer_results)

    print("\n--- Summary ---")
    print(f"{'Layer':>6}  {'Clusters':>8}  {'Noise':>6}")
    for r in layer_results:
        print(f"{r['layer']:>6}  {r['n_clusters']:>8}  {r['n_noise']:>6}")

    peak = max(layer_results, key=lambda r: r["n_clusters"])
    print(f"\nPeak fragmentation at layer {peak['layer']}: "
          f"{peak['n_clusters']} distinct objects for '7'")
    print(f"\nAll results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
