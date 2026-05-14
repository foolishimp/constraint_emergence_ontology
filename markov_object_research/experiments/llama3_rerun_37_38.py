"""Rerun only exps 37 and 38 on Llama-3 8B (after tokenization fix)."""

import json, time, traceback
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

# Import the master sweep module
spec = importlib.util.spec_from_file_location(
    "lsweep",
    Path(__file__).parent / "llama3_full_sweep.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    t0 = time.time()
    model = m.load_model()
    print(f"\n========== rerun: exp 37 + 38 only ==========")

    try:
        v37, _ = m.run_exp37(model,
                              m.RESULTS / "37_causal_faithfulness_llama3")
        print(f"[37] verdict: {v37}")
    except Exception as e:
        print(f"[37] FAILED: {e}")
        traceback.print_exc()

    try:
        v38, _ = m.run_exp38(model,
                              m.RESULTS / "38_graph_cut_signature_llama3")
        print(f"[38] verdict: {v38}")
    except Exception as e:
        print(f"[38] FAILED: {e}")
        traceback.print_exc()

    print(f"\nelapsed: {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
