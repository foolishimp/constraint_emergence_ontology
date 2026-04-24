"""
Experiment 22: Free-form Generation under α-Intervention

Exp 18's transfer is measured as next-token KL shift toward the
reference distribution. A transfer of 0.27 is meaningful as a metric
value, but whether it corresponds to behavioural redirection in
generated text is a separate empirical question.

Protocol:
  1. 20 generation prompts per target where the target token appears
     mid-sentence.
  2. For each (prompt, α ∈ {0, 0.5, 1.0, 1.5, 2.0}) greedy-generate
     N_NEW tokens with the exp 18 mean-diff direction subtracted at
     the target position.
  3. Score each continuation:
     a. Lexical: target-word count vs reference-word count; classify
        as target-loaded / reference-loaded / neutral.
     b. Perplexity: log-prob of the continuation under the reference
        prompt (with n=5 substituted). Higher → reference-loaded.
  4. Aggregate per α: rate of reference-loaded continuations and mean
     delta-log-prob.

Pre-registered expectation:
  At α = 1: reference-loaded rate ≥ 40% (≤ 10% at α = 0).
  Perplexity under reference-prefix drops ≥ 0.5 nats from α=0 to α=1.
  Monotonic trend across α ∈ {0, 0.5, 1, 1.5, 2}.

Outcome interpretation:
  PASS     behavioural transfer tracks KL transfer.
  PARTIAL  behavioural transfer appears only at α ≥ 1.5.
  FAIL     no behavioural signal despite KL shift — metric artifact.
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DEFAULT_PROBE_LAYER = 8


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run free-form generation under alpha intervention at a chosen layer.",
    )
    parser.add_argument(
        "--layer",
        type=int,
        default=DEFAULT_PROBE_LAYER,
        help=f"Residual stream layer to probe (default: {DEFAULT_PROBE_LAYER})",
    )
    return parser.parse_args()


ARGS = parse_args()
PROBE_LAYER = ARGS.layer

RESULTS_ROOT = Path(__file__).parent.parent / "results" / "22_freeform_generation"
RESULTS_DIR = (RESULTS_ROOT if PROBE_LAYER == DEFAULT_PROBE_LAYER
               else RESULTS_ROOT / f"layer_{PROBE_LAYER}")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE = 5
TARGETS = [999, 666, 137]

ALPHAS = [0.0, 0.5, 1.0, 1.5, 2.0]

N_NEW_TOKENS = 30

# Generation prompts: the model continues after "{n}" token and we
# score the continuation. Use stems that admit diverse continuations.
GEN_PROMPTS = [
    "Call {n} immediately,",
    "{n} is the number that",
    "She dialed {n} and",
    "Everyone fears {n} because",
    "The story of {n} starts",
    "Legend says {n} was",
    "Imagine {n} in a",
    "History records {n} as",
    "People avoid {n} when",
    "The code {n} unlocks",
    "Warnings about {n} suggest",
    "Stories about {n} tell of",
    "The feeling of {n} reminds",
    "Encountering {n} means",
    "They rang {n} during the",
    "Some say {n} brings",
    "The symbol {n} represents",
    "Children learn {n} as the",
    "Whispers of {n} spread when",
    "News of {n} came through",
]

# Lexical scoring dictionaries.
TARGET_WORDS = {
    999: [" 911", "emergency", "fire", "police", "ambulance",
          "disaster", "help", "urgent", "crisis", "danger",
          "rescue", "panic", "accident", "hospital"],
    666: ["devil", "satan", "demon", "evil", "hell", "beast",
          "occult", "sin", "apocalypse", "cursed", "darkness",
          "wicked", "unholy", "dark", "antichrist"],
    137: ["alpha", "physics", "constant", "fine", "structure",
          "mystery", "pauli", "electromagnet", "quantum",
          "dimensionless", "atom", "coupling", "element"],
}

# Reference words: generic numeric / mundane context associated with n=5.
REF_WORDS = [
    " five", " fifth", "hundred", "dollar", "dollars", "cent",
    "page", "pages", "chapter", "line", "row", "person", "people",
    "minute", "year", "hour", "day", "week", "month",
    "house", "room", "number", "amount", "count", "total",
    "friend", "copy", "card", "book", "meter",
]

# Pre-reg thresholds
REF_RATE_ALPHA0_MAX   = 0.10
REF_RATE_ALPHA1_MIN   = 0.40
LOGPROB_DROP_ALPHA1   = 0.50  # nats, per-token mean


# ---------------------------------------------------------------------------
# Model
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


def capture_resid(model, text, pos, layer=PROBE_LAYER):
    import torch
    tokens = model.to_tokens(text, prepend_bos=True)
    hook_name = f"blocks.{layer}.hook_resid_pre"
    captured = {}

    def capture(value, hook):
        captured["resid"] = value[0, pos, :].detach().clone()
        return value

    with torch.no_grad():
        model.run_with_hooks(tokens, fwd_hooks=[(hook_name, capture)])
    return captured["resid"]


# ---------------------------------------------------------------------------
# Direction extraction (same protocol as exp 18)
# ---------------------------------------------------------------------------

DIRECTION_TEMPLATES = [
    "The number {n} is",
    "Call {n} immediately",
    "In {n} AD the Vikings",
    "Price was ${n} only",
    "There were {n} people",
    "Page {n} of the book",
    "Line {n}: error",
    "She whispered {n}",
    "Yesterday we saw {n}",
    "We had {n} choices",
    "The sacred number {n} means",
    "Room {n} is empty",
    "{n} is the answer",
    "My code is {n}",
    "They sang song {n}",
    "Box {n} contains",
    "Channel {n} is broadcasting",
    "The tribe numbered {n}",
    "Mission {n} begins now",
    "Only {n} remain standing",
]


def extract_mean_diff_direction(model, target):
    import torch
    R_tgt, used_tgt = [], []
    R_ref, used_ref = [], []
    for t in DIRECTION_TEMPLATES:
        text_tgt = t.format(n=target)
        text_ref = t.format(n=REFERENCE)
        pos_tgt = last_token_of_span(model, text_tgt, str(target))
        pos_ref = last_token_of_span(model, text_ref, str(REFERENCE))
        if pos_tgt is None or pos_ref is None:
            continue
        R_tgt.append(capture_resid(model, text_tgt, pos_tgt))
        R_ref.append(capture_resid(model, text_ref, pos_ref))
        used_tgt.append(t); used_ref.append(t)
    R_tgt_t = torch.stack(R_tgt).float()
    R_ref_t = torch.stack(R_ref).float()
    d = R_tgt_t.mean(0) - R_ref_t.mean(0)
    return d


# ---------------------------------------------------------------------------
# Greedy generation with persistent target-position intervention
# ---------------------------------------------------------------------------

def generate_with_intervention(model, prompt_text, target_pos, direction,
                               alpha, n_new=N_NEW_TOKENS):
    """
    Greedy decode n_new tokens. At every forward pass the residual at
    `target_pos` is patched by subtracting α * direction at layer
    PROBE_LAYER. Positions after the prompt are not patched; they see
    the patched prompt state through attention.
    """
    import torch
    hook_name = f"blocks.{PROBE_LAYER}.hook_resid_pre"

    def patch(value, hook):
        if value.shape[1] > target_pos:
            value[0, target_pos, :] = value[0, target_pos, :] - alpha * direction
        return value

    tokens = model.to_tokens(prompt_text, prepend_bos=True)
    generated_ids = []
    for _ in range(n_new):
        with torch.no_grad():
            logits = model.run_with_hooks(
                tokens, fwd_hooks=[(hook_name, patch)],
            )
        next_id = int(logits[0, -1].argmax().item())
        generated_ids.append(next_id)
        next_tok = torch.tensor([[next_id]], device=tokens.device,
                                dtype=tokens.dtype)
        tokens = torch.cat([tokens, next_tok], dim=1)
    return model.to_string(torch.tensor(generated_ids))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def lexical_classify(continuation, target):
    text_low = continuation.lower()
    tgt_count = 0
    for w in TARGET_WORDS[target]:
        tgt_count += text_low.count(w.lower().strip())
    ref_count = 0
    for w in REF_WORDS:
        ref_count += text_low.count(w.lower().strip())

    if tgt_count > ref_count and tgt_count > 0:
        cls = "target"
    elif ref_count > tgt_count and ref_count > 0:
        cls = "reference"
    else:
        cls = "neutral"
    return cls, tgt_count, ref_count


def continuation_logprob(model, prompt_text, continuation):
    """
    Mean per-token log-probability of `continuation` conditional on
    `prompt_text`.
    """
    import torch

    full = prompt_text + continuation
    full_toks = model.to_tokens(full, prepend_bos=True)[0]
    prompt_toks = model.to_tokens(prompt_text, prepend_bos=True)[0]
    n_prompt = len(prompt_toks)
    n_total = len(full_toks)
    if n_total <= n_prompt:
        return 0.0

    with torch.no_grad():
        logits = model(full_toks.unsqueeze(0))[0]

    logprobs_per_tok = []
    for i in range(n_prompt, n_total):
        tok_id = full_toks[i].item()
        logprobs = torch.log_softmax(logits[i-1], dim=-1)
        logprobs_per_tok.append(float(logprobs[tok_id].item()))
    return float(np.mean(logprobs_per_tok))


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_per_alpha(records):
    """records: list of dicts with keys alpha, cls, logprob_ref."""
    by_alpha = {a: {"n": 0, "target": 0, "reference": 0, "neutral": 0,
                    "logprob_ref": []} for a in ALPHAS}
    for r in records:
        a = r["alpha"]
        by_alpha[a]["n"] += 1
        by_alpha[a][r["cls"]] += 1
        by_alpha[a]["logprob_ref"].append(r["logprob_ref"])
    summary = {}
    for a in ALPHAS:
        n = max(by_alpha[a]["n"], 1)
        summary[a] = {
            "n":        by_alpha[a]["n"],
            "ref_rate": by_alpha[a]["reference"] / n,
            "tgt_rate": by_alpha[a]["target"]    / n,
            "neu_rate": by_alpha[a]["neutral"]   / n,
            "mean_logprob_ref": float(np.mean(by_alpha[a]["logprob_ref"]))
                                if by_alpha[a]["logprob_ref"] else 0.0,
        }
    return summary


def score_outcome(per_target_summary):
    passes = 0
    partials = 0
    fails = 0
    for target, summary in per_target_summary.items():
        ref0 = summary[0.0]["ref_rate"]
        ref1 = summary[1.0]["ref_rate"]
        lp0  = summary[0.0]["mean_logprob_ref"]
        lp1  = summary[1.0]["mean_logprob_ref"]
        monotonic = all(summary[ALPHAS[i]]["ref_rate"]
                        >= summary[ALPHAS[i-1]]["ref_rate"] - 0.05
                        for i in range(1, len(ALPHAS)))
        if (ref0 <= REF_RATE_ALPHA0_MAX
                and ref1 >= REF_RATE_ALPHA1_MIN
                and (lp1 - lp0) >= LOGPROB_DROP_ALPHA1
                and monotonic):
            passes += 1
        elif summary[1.5]["ref_rate"] >= REF_RATE_ALPHA1_MIN:
            partials += 1
        else:
            fails += 1
    if passes >= 2:
        return "PASS"
    if fails == len(per_target_summary):
        return "FAIL"
    return "PARTIAL"


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_ref_rate_curves(per_target_summary):
    fig, ax = plt.subplots(figsize=(9, 5))
    for target, summary in per_target_summary.items():
        xs = ALPHAS
        ys = [summary[a]["ref_rate"] for a in xs]
        ax.plot(xs, ys, marker="o", linewidth=2, label=f"n={target}")
    ax.axhline(REF_RATE_ALPHA1_MIN, color="green", linestyle="--", alpha=0.4,
               label=f"pass threshold ({REF_RATE_ALPHA1_MIN})")
    ax.axhline(REF_RATE_ALPHA0_MAX, color="red", linestyle="--", alpha=0.4,
               label=f"α=0 ceiling ({REF_RATE_ALPHA0_MAX})")
    ax.set_xlabel("α (intervention magnitude)")
    ax.set_ylabel("reference-loaded continuation rate")
    ax.set_title("Behavioural transfer — lexical scoring")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "ref_rate_curves.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_logprob_curves(per_target_summary):
    fig, ax = plt.subplots(figsize=(9, 5))
    for target, summary in per_target_summary.items():
        xs = ALPHAS
        ys = [summary[a]["mean_logprob_ref"] for a in xs]
        ax.plot(xs, ys, marker="o", linewidth=2, label=f"n={target}")
    ax.set_xlabel("α (intervention magnitude)")
    ax.set_ylabel("mean per-token log-prob under reference prompt")
    ax.set_title("Continuation log-prob under reference prefix")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = RESULTS_DIR / "logprob_curves.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


def plot_class_stack(per_target_summary):
    fig, axes = plt.subplots(1, len(per_target_summary), figsize=(14, 5),
                             sharey=True)
    if len(per_target_summary) == 1:
        axes = [axes]
    for ax, (target, summary) in zip(axes, per_target_summary.items()):
        xs = ALPHAS
        tgt = [summary[a]["tgt_rate"] for a in xs]
        neu = [summary[a]["neu_rate"] for a in xs]
        ref = [summary[a]["ref_rate"] for a in xs]
        ax.bar(xs, tgt, width=0.3, color="tomato", label="target-loaded")
        ax.bar(xs, neu, width=0.3, bottom=tgt, color="lightgray",
               label="neutral")
        bottom2 = [t + n for t, n in zip(tgt, neu)]
        ax.bar(xs, ref, width=0.3, bottom=bottom2, color="steelblue",
               label="reference-loaded")
        ax.set_xlabel("α")
        ax.set_title(f"n = {target}")
        if target == list(per_target_summary.keys())[0]:
            ax.set_ylabel("continuation class rate")
            ax.legend(fontsize=8)
    fig.suptitle("Continuation classification by α")
    fig.tight_layout()
    out = RESULTS_DIR / "class_stack.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out.name}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(per_target_summary, aggregate, all_records):
    lines = [
        "Exp 22 — Free-form Generation under α-Intervention",
        f"                   layer {PROBE_LAYER}",
        "=" * 72,
        "",
        f"Reference: n = {REFERENCE}",
        f"Targets:   {TARGETS}",
        f"Generation prompts per target: {len(GEN_PROMPTS)}",
        f"New tokens per completion: {N_NEW_TOKENS}",
        f"α values: {ALPHAS}",
        "",
        "Pre-registered rules (per target):",
        f"  PASS     ref-rate at α=0 ≤ {REF_RATE_ALPHA0_MAX}  "
            f"AND ref-rate at α=1 ≥ {REF_RATE_ALPHA1_MIN}  "
            f"AND logprob Δ ≥ {LOGPROB_DROP_ALPHA1} nats  AND monotonic",
        f"  PARTIAL  ref-rate at α=1.5 ≥ {REF_RATE_ALPHA1_MIN}",
        f"  FAIL     otherwise",
        "",
        f"AGGREGATE OUTCOME: {aggregate}",
        "",
    ]

    for target in TARGETS:
        lines.append(f"\n### target = {target}")
        summary = per_target_summary[target]
        lines.append("")
        lines.append(f"  {'α':>4s} | {'n':>3s} | "
                     f"{'ref_rate':>8s} | {'tgt_rate':>8s} | "
                     f"{'neu_rate':>8s} | {'logprob_ref':>11s}")
        for a in ALPHAS:
            s = summary[a]
            lines.append(
                f"  {a:>4.1f} | {s['n']:>3d} | "
                f"{s['ref_rate']:>8.3f} | {s['tgt_rate']:>8.3f} | "
                f"{s['neu_rate']:>8.3f} | {s['mean_logprob_ref']:>+11.3f}"
            )

        lines.append("")
        lines.append(f"  Example continuations at α ∈ {{0, 1, 2}}:")
        for a in [0.0, 1.0, 2.0]:
            recs = [r for r in all_records
                    if r["target"] == target and r["alpha"] == a][:2]
            for r in recs:
                prompt = GEN_PROMPTS[r["prompt_idx"]].format(n=target)
                cont = r["continuation"]
                lines.append(f"    α={a} [{r['cls'][:3]}] "
                             f"prompt: {prompt!r}")
                cont_trunc = cont.replace("\n", " ")[:120]
                lines.append(f"           cont: {cont_trunc!r}")

    out = RESULTS_DIR / "generation_report.txt"
    out.write_text("\n".join(lines))
    print(f"Report: {out.name}")

    json_summary = {
        "aggregate":   aggregate,
        "per_target":  {str(t): {str(a): per_target_summary[t][a]
                                 for a in ALPHAS}
                        for t in TARGETS},
        "thresholds": {
            "ref_rate_alpha0_max": REF_RATE_ALPHA0_MAX,
            "ref_rate_alpha1_min": REF_RATE_ALPHA1_MIN,
            "logprob_drop_alpha1": LOGPROB_DROP_ALPHA1,
        },
    }
    (RESULTS_DIR / "generation_summary.json").write_text(
        json.dumps(json_summary, indent=2))
    print("Summary JSON: generation_summary.json")

    # Full records for inspection.
    (RESULTS_DIR / "all_completions.jsonl").write_text(
        "\n".join(json.dumps(r) for r in all_records))
    print("All completions: all_completions.jsonl")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import torch

    model = load_model()

    per_target_summary = {}
    all_records = []

    for target in TARGETS:
        print(f"\n=== target = {target} ===")

        print("  extracting mean-diff direction...")
        d = extract_mean_diff_direction(model, target)
        print(f"    ||d|| = {d.norm().item():.3f}")

        records_target = []
        for prompt_idx, stem in enumerate(GEN_PROMPTS):
            prompt_tgt = stem.format(n=target)
            prompt_ref = stem.format(n=REFERENCE)
            pos = last_token_of_span(model, prompt_tgt, str(target))
            if pos is None:
                print(f"    skip prompt_idx={prompt_idx} (no target span)")
                continue

            for a in ALPHAS:
                cont = generate_with_intervention(
                    model, prompt_tgt, pos, d, a, n_new=N_NEW_TOKENS,
                )
                cls, tgt_cnt, ref_cnt = lexical_classify(cont, target)
                lp_ref = continuation_logprob(model, prompt_ref, cont)
                rec = {
                    "target":       target,
                    "prompt_idx":   prompt_idx,
                    "alpha":        a,
                    "continuation": cont,
                    "cls":          cls,
                    "tgt_count":    tgt_cnt,
                    "ref_count":    ref_cnt,
                    "logprob_ref":  lp_ref,
                }
                records_target.append(rec)
                all_records.append(rec)

            if prompt_idx < 3:
                print(f"    prompt {prompt_idx}: {stem!r}")
                for a in ALPHAS:
                    last = [r for r in records_target
                            if r["prompt_idx"] == prompt_idx
                            and r["alpha"] == a][-1]
                    cont_trunc = last["continuation"].replace("\n", " ")[:60]
                    print(f"      α={a}  [{last['cls'][:3]}]  "
                          f"{cont_trunc!r}")

        summary = aggregate_per_alpha(records_target)
        per_target_summary[target] = summary
        print(f"  summary (ref-rate by α):")
        for a in ALPHAS:
            print(f"    α={a}  ref-rate={summary[a]['ref_rate']:.3f}  "
                  f"logprob_ref={summary[a]['mean_logprob_ref']:+.3f}")

    plot_ref_rate_curves(per_target_summary)
    plot_logprob_curves(per_target_summary)
    plot_class_stack(per_target_summary)

    aggregate = score_outcome(per_target_summary)
    print(f"\n=== AGGREGATE OUTCOME: {aggregate} ===")

    write_report(per_target_summary, aggregate, all_records)

    print(f"\nResults: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
