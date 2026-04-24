"""
Experiment 32: Value Topology in GPT-2

This is a topology-mapping experiment, not a Markov-blanket promotion
gate. The question is whether GPT-2 small represents "value" mostly as
a lexical basin, or whether the same surface word carries separable
regime fibers: market, accounting, policy, legal, insurance, moral,
personal, social, information, and medical.

Two assays are run:

1. Value-regime assay:
   All prompts contain the token "value". The context changes by regime.
   If the residual at "value" is regime-separable, GPT-2 has at least a
   contextual topology around value rather than a flat lexical basin.

2. Carrier assay:
   Matched templates vary the carrier word among value/price/cost/worth.
   If carrier identity is much easier to classify than regime, lexical
   form dominates this region of the topology.

Outputs are descriptive: probe scores, centroid geometry, PCA plots,
and a report classifying the observed shape.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


RESULTS_DIR = Path(__file__).parent.parent / "results" / "32_value_topology"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LAYERS = [2, 4, 6, 8, 10, 11]
PLOT_LAYER = 8
RNG_SEED = 42

VALUE_REGIME_PROMPTS = [
    # market / exchange value
    {"regime": "market", "text": "The market value of the asset changed overnight."},
    {"regime": "market", "text": "Traders debated the value of the stock after earnings."},
    {"regime": "market", "text": "The value of the currency fell against the dollar."},
    {"regime": "market", "text": "The auction revealed the value buyers would accept."},
    {"regime": "market", "text": "Liquidity changed the value quoted on the exchange."},
    {"regime": "market", "text": "The value of the commodity rose with demand."},

    # accounting value
    {"regime": "accounting", "text": "The book value of the asset was impaired."},
    {"regime": "accounting", "text": "Auditors reviewed the fair value in the report."},
    {"regime": "accounting", "text": "The carrying value was adjusted after depreciation."},
    {"regime": "accounting", "text": "The value on the balance sheet was restated."},
    {"regime": "accounting", "text": "Management estimated the recoverable value of goodwill."},
    {"regime": "accounting", "text": "The residual value affected the lease calculation."},

    # policy / statistical value
    {"regime": "policy", "text": "The statistical value of a life guides safety rules."},
    {"regime": "policy", "text": "Regulators used the value of a life in cost benefit analysis."},
    {"regime": "policy", "text": "The value assigned to risk reduction shaped the policy."},
    {"regime": "policy", "text": "The agency estimated the value of avoided fatalities."},
    {"regime": "policy", "text": "Public policy compared the value of safety with cost."},
    {"regime": "policy", "text": "The value of prevention was measured across the population."},

    # legal / damages value
    {"regime": "legal", "text": "The court considered the value of the lost claim."},
    {"regime": "legal", "text": "Damages reflected the value of the contract right."},
    {"regime": "legal", "text": "The legal value of the evidence depended on relevance."},
    {"regime": "legal", "text": "The value of the estate was disputed in court."},
    {"regime": "legal", "text": "The judge assessed the value of compensation."},
    {"regime": "legal", "text": "The settlement turned on the value of the injury."},

    # insurance / actuarial value
    {"regime": "insurance", "text": "The insured value of the property set the premium."},
    {"regime": "insurance", "text": "The policy stated the value payable after death."},
    {"regime": "insurance", "text": "Actuaries estimated the value of the future claim."},
    {"regime": "insurance", "text": "The replacement value was higher than the cash payout."},
    {"regime": "insurance", "text": "The value of the annuity depended on life expectancy."},
    {"regime": "insurance", "text": "The insurer calculated the value of the loss."},

    # moral / dignity value
    {"regime": "moral", "text": "The value of a human life cannot be reduced to money."},
    {"regime": "moral", "text": "Moral value is not the same as market price."},
    {"regime": "moral", "text": "The value of dignity survived every calculation."},
    {"regime": "moral", "text": "The value of compassion mattered more than profit."},
    {"regime": "moral", "text": "A person's value is not measured by productivity."},
    {"regime": "moral", "text": "The value of justice constrained the decision."},

    # personal / family value
    {"regime": "personal", "text": "To her family the value of his life was immeasurable."},
    {"regime": "personal", "text": "The ring had value because it belonged to her mother."},
    {"regime": "personal", "text": "The value of the letter came from memory."},
    {"regime": "personal", "text": "Sentimental value made the old watch priceless."},
    {"regime": "personal", "text": "The value of the photograph was personal."},
    {"regime": "personal", "text": "Its value came from grief, love, and history."},

    # social value
    {"regime": "social", "text": "The social value of trust held the community together."},
    {"regime": "social", "text": "The value of reputation changed how people cooperated."},
    {"regime": "social", "text": "The public value of the park exceeded its revenue."},
    {"regime": "social", "text": "The value of care work was ignored by the market."},
    {"regime": "social", "text": "The value of the institution depended on legitimacy."},
    {"regime": "social", "text": "The value of cooperation appeared during the crisis."},

    # information value
    {"regime": "information", "text": "The value of the signal was its reduction of uncertainty."},
    {"regime": "information", "text": "Information value rose before the decision deadline."},
    {"regime": "information", "text": "The value of the data depended on its accuracy."},
    {"regime": "information", "text": "The report had value because it changed the forecast."},
    {"regime": "information", "text": "The value of the clue was revealed later."},
    {"regime": "information", "text": "The option had value because it preserved information."},

    # medical / triage value
    {"regime": "medical", "text": "The medical team protected the value of each life."},
    {"regime": "medical", "text": "Triage exposed the value of time under scarcity."},
    {"regime": "medical", "text": "The value of treatment depended on expected benefit."},
    {"regime": "medical", "text": "The value of a transplant slot was ethically fraught."},
    {"regime": "medical", "text": "The value of care was measured in survival and dignity."},
    {"regime": "medical", "text": "The value of intervention changed with prognosis."},
]

CARRIER_TERMS = ["value", "price", "cost", "worth"]
CARRIER_TEMPLATES = [
    "In the market report, the asset's {term} was uncertain.",
    "During the court case, the claim's {term} was debated.",
    "Under the policy model, the expected {term} was calculated.",
    "At the family meeting, the object's {term} was personal.",
    "In the accounting note, the recorded {term} changed.",
    "For the insurer, the replacement {term} was disputed.",
    "Before the trade, the quoted {term} moved quickly.",
    "In the ethics review, the human {term} could not be priced.",
    "After the forecast changed, the information's {term} rose.",
    "In the contract, the promised {term} became unclear.",
    "For the community, the institution's {term} depended on trust.",
    "During triage, the intervention's {term} depended on prognosis.",
]


# ---------------------------------------------------------------------------
# Model and residual capture
# ---------------------------------------------------------------------------

def load_model():
    from transformer_lens import HookedTransformer
    print("Loading GPT-2 small...")
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


def capture_resids_at_layers(model, text, pos, layers=LAYERS):
    import torch

    tokens = model.to_tokens(text, prepend_bos=True)
    captured = {}

    def make_capture(layer):
        def capture(value, hook):
            captured[layer] = value[0, pos, :].detach().clone().float()
            return value
        return capture

    hooks = [
        (f"blocks.{layer}.hook_resid_pre", make_capture(layer))
        for layer in layers
    ]
    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=hooks)
    return captured


def collect_value_regime_residuals(model):
    import torch

    rows = []
    labels = []
    texts = []
    for item in VALUE_REGIME_PROMPTS:
        text = item["text"]
        pos = last_token_of_span(model, text, "value")
        if pos is None:
            raise RuntimeError(f"Could not find value token in: {text}")
        captured = capture_resids_at_layers(model, text, pos)
        rows.append(torch.stack([captured[layer] for layer in LAYERS], dim=0))
        labels.append(item["regime"])
        texts.append(text)
    return torch.stack(rows, dim=0), labels, texts


def collect_carrier_residuals(model):
    import torch

    rows = []
    terms = []
    templates = []
    texts = []
    for term in CARRIER_TERMS:
        for template in CARRIER_TEMPLATES:
            text = template.format(term=term)
            pos = last_token_of_span(model, text, term)
            if pos is None:
                raise RuntimeError(f"Could not find {term} token in: {text}")
            captured = capture_resids_at_layers(model, text, pos)
            rows.append(torch.stack([captured[layer] for layer in LAYERS], dim=0))
            terms.append(term)
            templates.append(template)
            texts.append(text)
    return torch.stack(rows, dim=0), terms, templates, texts


# ---------------------------------------------------------------------------
# Geometry and probes
# ---------------------------------------------------------------------------

def encode_labels(labels):
    names = sorted(set(labels))
    idx = {name: i for i, name in enumerate(names)}
    return names, np.array([idx[x] for x in labels], dtype=int)


def layer_array(R, layer):
    i = LAYERS.index(layer)
    return R[:, i, :].cpu().numpy()


def l2_normalize(X):
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


def probe_cv_by_layer(R, labels, n_splits=3):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import StandardScaler

    names, y = encode_labels(labels)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RNG_SEED)
    results = {}
    for layer in LAYERS:
        X = layer_array(R, layer)
        accs = []
        f1s = []
        for train_idx, test_idx in cv.split(X, y):
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X[train_idx])
            X_test = scaler.transform(X[test_idx])
            clf = LogisticRegression(
                C=0.1,
                penalty="l2",
                solver="lbfgs",
                max_iter=3000,
                random_state=RNG_SEED,
            )
            clf.fit(X_train, y[train_idx])
            pred = clf.predict(X_test)
            accs.append(accuracy_score(y[test_idx], pred))
            f1s.append(f1_score(y[test_idx], pred, average="macro"))
        results[layer] = {
            "accuracy": float(np.mean(accs)),
            "macro_f1": float(np.mean(f1s)),
            "fold_accuracy": [float(x) for x in accs],
            "fold_macro_f1": [float(x) for x in f1s],
        }
    return names, results


def centroid_geometry(X, labels):
    names = sorted(set(labels))
    Xn = l2_normalize(X)
    centroids = []
    for name in names:
        c = Xn[np.array(labels) == name].mean(axis=0)
        c = c / (np.linalg.norm(c) + 1e-9)
        centroids.append(c)
    C = np.stack(centroids, axis=0)
    cosine = C @ C.T

    within = []
    between = []
    for i in range(len(Xn)):
        for j in range(i + 1, len(Xn)):
            d = 1.0 - float(Xn[i] @ Xn[j])
            if labels[i] == labels[j]:
                within.append(d)
            else:
                between.append(d)

    return {
        "names": names,
        "centroid_cosine": cosine,
        "within_cosine_distance": float(np.mean(within)),
        "between_cosine_distance": float(np.mean(between)),
        "between_minus_within": float(np.mean(between) - np.mean(within)),
    }


def silhouette_by_layer(R, labels):
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    _, y = encode_labels(labels)
    results = {}
    for layer in LAYERS:
        X = StandardScaler().fit_transform(layer_array(R, layer))
        try:
            score = silhouette_score(X, y, metric="euclidean")
        except ValueError:
            score = float("nan")
        results[layer] = float(score)
    return results


def pca_projection(X):
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    Xs = StandardScaler().fit_transform(X)
    pca = PCA(n_components=2, random_state=RNG_SEED)
    Z = pca.fit_transform(Xs)
    return Z, [float(x) for x in pca.explained_variance_ratio_]


def nearest_carriers_to_value(carrier_geom):
    names = carrier_geom["names"]
    cos = carrier_geom["centroid_cosine"]
    i_value = names.index("value")
    pairs = []
    for i, name in enumerate(names):
        if name == "value":
            continue
        pairs.append({"term": name, "cosine_to_value": float(cos[i_value, i])})
    return sorted(pairs, key=lambda x: x["cosine_to_value"], reverse=True)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_probe_scores(regime_probe, carrier_probe):
    fig, ax = plt.subplots(figsize=(8, 5))
    xs = np.array(LAYERS)
    ax.plot(
        xs,
        [regime_probe[layer]["accuracy"] for layer in LAYERS],
        marker="o",
        linewidth=2,
        label="value regime accuracy",
    )
    ax.plot(
        xs,
        [carrier_probe[layer]["accuracy"] for layer in LAYERS],
        marker="o",
        linewidth=2,
        label="carrier accuracy",
    )
    ax.axhline(1 / 10, color="steelblue", linestyle=":", linewidth=1,
               label="regime chance")
    ax.axhline(1 / len(CARRIER_TERMS), color="orange", linestyle=":",
               linewidth=1, label="carrier chance")
    ax.set_xlabel("layer")
    ax.set_ylabel("CV accuracy")
    ax.set_title("Probe separability by layer")
    ax.set_ylim(0.0, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = RESULTS_DIR / "probe_accuracy_by_layer.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_pca(Z, labels, title, filename):
    names = sorted(set(labels))
    cmap = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, name in enumerate(names):
        idx = np.array(labels) == name
        ax.scatter(
            Z[idx, 0],
            Z[idx, 1],
            s=42,
            alpha=0.85,
            color=cmap(i % 10),
            label=name,
        )
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    out = RESULTS_DIR / filename
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_centroid_heatmap(geom, title, filename):
    names = geom["names"]
    cos = geom["centroid_cosine"]
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cos, vmin=0.0, vmax=1.0, cmap="viridis")
    ax.set_xticks(np.arange(len(names)))
    ax.set_yticks(np.arange(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticklabels(names)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="centroid cosine")
    fig.tight_layout()
    out = RESULTS_DIR / filename
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_silhouette(regime_sil, carrier_sil):
    fig, ax = plt.subplots(figsize=(8, 5))
    xs = np.array(LAYERS)
    ax.plot(
        xs,
        [regime_sil[layer] for layer in LAYERS],
        marker="o",
        linewidth=2,
        label="value regimes",
    )
    ax.plot(
        xs,
        [carrier_sil[layer] for layer in LAYERS],
        marker="o",
        linewidth=2,
        label="carriers",
    )
    ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("layer")
    ax.set_ylabel("silhouette score")
    ax.set_title("Cluster compactness by layer")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = RESULTS_DIR / "silhouette_by_layer.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def classify_shape(regime_probe, carrier_probe, regime_sil, carrier_sil):
    best_regime_layer = max(
        LAYERS, key=lambda layer: regime_probe[layer]["accuracy"],
    )
    best_carrier_layer = max(
        LAYERS, key=lambda layer: carrier_probe[layer]["accuracy"],
    )
    regime_acc = regime_probe[best_regime_layer]["accuracy"]
    carrier_acc = carrier_probe[best_carrier_layer]["accuracy"]
    regime_gain = regime_acc - (1 / 10)
    carrier_gain = carrier_acc - (1 / len(CARRIER_TERMS))

    if carrier_gain > 0.60 and regime_gain < 0.25:
        reading = "lexical_basin_dominant"
    elif carrier_gain > 0.60 and regime_gain >= 0.25:
        reading = "lexical_basin_with_regime_fibers"
    elif regime_gain >= 0.35:
        reading = "regime_topology_visible"
    else:
        reading = "weak_or_diffuse_topology"

    return {
        "reading": reading,
        "best_regime_layer": int(best_regime_layer),
        "best_regime_accuracy": float(regime_acc),
        "best_regime_macro_f1": float(
            regime_probe[best_regime_layer]["macro_f1"],
        ),
        "best_regime_silhouette": float(regime_sil[best_regime_layer]),
        "best_carrier_layer": int(best_carrier_layer),
        "best_carrier_accuracy": float(carrier_acc),
        "best_carrier_macro_f1": float(
            carrier_probe[best_carrier_layer]["macro_f1"],
        ),
        "best_carrier_silhouette": float(carrier_sil[best_carrier_layer]),
        "regime_gain_over_chance": float(regime_gain),
        "carrier_gain_over_chance": float(carrier_gain),
    }


def write_report(summary):
    lines = [
        "Exp 32 - Value Topology in GPT-2",
        "=" * 72,
        "",
        "This is a topology-mapping experiment, not a promotion gate.",
        "",
        f"Layers: {LAYERS}",
        f"Value-regime prompts: {len(VALUE_REGIME_PROMPTS)}",
        f"Carrier prompts: {len(CARRIER_TERMS) * len(CARRIER_TEMPLATES)}",
        "",
        f"TOPOLOGY READING: {summary['classification']['reading']}",
        "",
        "Best value-regime separability:",
        f"  layer:      {summary['classification']['best_regime_layer']}",
        f"  accuracy:   {summary['classification']['best_regime_accuracy']:.3f}",
        f"  macro F1:   {summary['classification']['best_regime_macro_f1']:.3f}",
        f"  silhouette: {summary['classification']['best_regime_silhouette']:.3f}",
        "",
        "Best carrier separability:",
        f"  layer:      {summary['classification']['best_carrier_layer']}",
        f"  accuracy:   {summary['classification']['best_carrier_accuracy']:.3f}",
        f"  macro F1:   {summary['classification']['best_carrier_macro_f1']:.3f}",
        f"  silhouette: {summary['classification']['best_carrier_silhouette']:.3f}",
        "",
        "Probe accuracy by layer:",
    ]
    for layer in LAYERS:
        r = summary["regime_probe"][str(layer)]
        c = summary["carrier_probe"][str(layer)]
        lines.append(
            f"  layer {layer}: value-regime acc={r['accuracy']:.3f}, "
            f"carrier acc={c['accuracy']:.3f}"
        )

    lines.extend([
        "",
        f"Centroid geometry at layer {PLOT_LAYER}:",
        "  value regimes:",
        f"    within cosine distance:  "
        f"{summary['regime_geometry']['within_cosine_distance']:.4f}",
        f"    between cosine distance: "
        f"{summary['regime_geometry']['between_cosine_distance']:.4f}",
        f"    between - within:        "
        f"{summary['regime_geometry']['between_minus_within']:.4f}",
        "  carriers:",
        f"    within cosine distance:  "
        f"{summary['carrier_geometry']['within_cosine_distance']:.4f}",
        f"    between cosine distance: "
        f"{summary['carrier_geometry']['between_cosine_distance']:.4f}",
        f"    between - within:        "
        f"{summary['carrier_geometry']['between_minus_within']:.4f}",
        "",
        "Carrier centroid cosine to value at layer 8:",
    ])
    for item in summary["carrier_neighbors_to_value"]:
        lines.append(f"  {item['term']}: {item['cosine_to_value']:.4f}")

    lines.extend([
        "",
        "Interpretation:",
        "  The carrier probe is expected to be easier because the target",
        "  token changes. Its purpose is to measure how strongly local",
        "  lexical carrier identity survives after varied left contexts.",
        "  A high value-regime score would mean the same token 'value'",
        "  carries separable contextual fibers. GPT-2 should be read as",
        "  topologically richer when regime separability rises above chance",
        "  without merely collapsing into carrier form.",
    ])

    report = RESULTS_DIR / "value_topology_report.txt"
    report.write_text("\n".join(lines))
    print(f"Report: {report.name}")

    summary_path = RESULTS_DIR / "value_topology_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Summary JSON: {summary_path.name}")


def stringify_probe(probe):
    return {
        str(layer): {
            "accuracy": float(values["accuracy"]),
            "macro_f1": float(values["macro_f1"]),
            "fold_accuracy": values["fold_accuracy"],
            "fold_macro_f1": values["fold_macro_f1"],
        }
        for layer, values in probe.items()
    }


def stringify_silhouette(values):
    return {str(layer): float(score) for layer, score in values.items()}


def main():
    model = load_model()

    print("\nCollecting value-regime residuals...")
    R_regime, regime_labels, regime_texts = collect_value_regime_residuals(model)
    print(f"  samples: {len(regime_labels)}")

    print("Collecting carrier residuals...")
    R_carrier, carrier_labels, carrier_templates, carrier_texts = (
        collect_carrier_residuals(model)
    )
    print(f"  samples: {len(carrier_labels)}")

    print("\nRunning regime probe...")
    regime_names, regime_probe = probe_cv_by_layer(R_regime, regime_labels)

    print("Running carrier probe...")
    carrier_names, carrier_probe = probe_cv_by_layer(R_carrier, carrier_labels)

    print("Computing geometry...")
    regime_sil = silhouette_by_layer(R_regime, regime_labels)
    carrier_sil = silhouette_by_layer(R_carrier, carrier_labels)
    regime_geom = centroid_geometry(layer_array(R_regime, PLOT_LAYER), regime_labels)
    carrier_geom = centroid_geometry(layer_array(R_carrier, PLOT_LAYER), carrier_labels)
    carrier_neighbors = nearest_carriers_to_value(carrier_geom)

    print("Plotting...")
    plot_probe_scores(regime_probe, carrier_probe)
    plot_silhouette(regime_sil, carrier_sil)
    Z_regime, regime_pca_var = pca_projection(layer_array(R_regime, PLOT_LAYER))
    Z_carrier, carrier_pca_var = pca_projection(layer_array(R_carrier, PLOT_LAYER))
    plot_pca(
        Z_regime,
        regime_labels,
        f"Value-regime PCA at layer {PLOT_LAYER}",
        "value_regime_pca_layer8.png",
    )
    plot_pca(
        Z_carrier,
        carrier_labels,
        f"Carrier PCA at layer {PLOT_LAYER}",
        "carrier_pca_layer8.png",
    )
    plot_centroid_heatmap(
        regime_geom,
        f"Value-regime centroid cosine at layer {PLOT_LAYER}",
        "value_regime_centroid_cosine_layer8.png",
    )
    plot_centroid_heatmap(
        carrier_geom,
        f"Carrier centroid cosine at layer {PLOT_LAYER}",
        "carrier_centroid_cosine_layer8.png",
    )

    classification = classify_shape(
        regime_probe,
        carrier_probe,
        regime_sil,
        carrier_sil,
    )
    summary = {
        "classification": classification,
        "layers": LAYERS,
        "plot_layer": PLOT_LAYER,
        "regime_names": regime_names,
        "carrier_names": carrier_names,
        "regime_probe": stringify_probe(regime_probe),
        "carrier_probe": stringify_probe(carrier_probe),
        "regime_silhouette": stringify_silhouette(regime_sil),
        "carrier_silhouette": stringify_silhouette(carrier_sil),
        "regime_geometry": {
            "names": regime_geom["names"],
            "centroid_cosine": regime_geom["centroid_cosine"].tolist(),
            "within_cosine_distance": regime_geom["within_cosine_distance"],
            "between_cosine_distance": regime_geom["between_cosine_distance"],
            "between_minus_within": regime_geom["between_minus_within"],
        },
        "carrier_geometry": {
            "names": carrier_geom["names"],
            "centroid_cosine": carrier_geom["centroid_cosine"].tolist(),
            "within_cosine_distance": carrier_geom["within_cosine_distance"],
            "between_cosine_distance": carrier_geom["between_cosine_distance"],
            "between_minus_within": carrier_geom["between_minus_within"],
        },
        "carrier_neighbors_to_value": carrier_neighbors,
        "pca_variance": {
            "value_regime_layer8": regime_pca_var,
            "carrier_layer8": carrier_pca_var,
        },
        "value_regime_prompts": VALUE_REGIME_PROMPTS,
        "carrier_terms": CARRIER_TERMS,
        "carrier_templates": CARRIER_TEMPLATES,
    }

    write_report(summary)
    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
