"""
ml/compare_pipelines.py
-----------------------
Baseline comparison of three detection strategies on the held-out test set:

  A. RandomForest only (RF-only)
  B. Old cascade: IsolationForest gate → RandomForest (IF-gate)
  C. IsolationForest anomaly detection alone (IF-only)
  D. Fixed pipeline: RF always runs, IF is a parallel signal (RF+IF-parallel)

Metrics reported (multiclass and binary kept separate):
  Multiclass (known-class rows only):
    - macro F1, per-class recall
  Binary normal-vs-attack (known-class rows):
    - attack recall (TPR), false-positive rate (FPR), confusion matrix
  Inference latency (ms per sample, median over 1000 samples)

Definitions
-----------
  macro F1        : unweighted mean of per-class F1; treats all classes equally
                    regardless of support. Sensitive to low-recall minority classes.
  per-class recall: TP_c / (TP_c + FN_c) — fraction of true instances of class c
                    that were correctly identified.
  attack recall   : binary TPR — fraction of attack rows correctly flagged as attack.
  FPR             : FP / (FP + TN) — fraction of normal rows incorrectly flagged.
  confusion matrix: rows=true, cols=predicted; binary (normal vs attack).

Validation note
---------------
No threshold or model selection is performed here. The test set is used
read-only for reporting. All model artifacts were produced by train_model.py
using only training data.

Usage:
    python -m ml.compare_pipelines
"""

import os
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    f1_score,
    recall_score,
    classification_report,
    confusion_matrix,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
TEST_PATH  = os.path.join(BASE_DIR, "data", "test.csv")
MODEL_DIR  = os.path.abspath(os.path.join(BASE_DIR, "../backend/models"))
REPORT_DIR = os.path.join(BASE_DIR, "reports")

CAT_COLS   = ["protocol_type", "service", "flag"]
TARGET_COL = "labels"

os.makedirs(REPORT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Load artifacts and test data
# ---------------------------------------------------------------------------
def load_all():
    clf       = joblib.load(os.path.join(MODEL_DIR, "classifier.pkl"))
    iso       = joblib.load(os.path.join(MODEL_DIR, "anomaly.pkl"))
    ord_enc   = joblib.load(os.path.join(MODEL_DIR, "encoders.pkl"))
    scaler    = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
    label_enc = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
    columns   = joblib.load(os.path.join(MODEL_DIR, "columns.pkl"))

    test_df = pd.read_csv(TEST_PATH)
    num_cols = [c for c in columns if c not in CAT_COLS]

    X_raw = test_df[columns].copy()
    X_raw[CAT_COLS] = ord_enc.transform(X_raw[CAT_COLS])
    X_raw[num_cols] = scaler.transform(X_raw[num_cols])
    X = X_raw.values.astype(float)

    y_raw      = test_df[TARGET_COL].astype(str).values
    known_mask = np.isin(y_raw, label_enc.classes_)

    return clf, iso, label_enc, X, y_raw, known_mask


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def binary_metrics(y_true_bin, y_pred_bin):
    """y_true_bin / y_pred_bin: 1=attack, 0=normal"""
    tn = int(((y_true_bin == 0) & (y_pred_bin == 0)).sum())
    fp = int(((y_true_bin == 0) & (y_pred_bin == 1)).sum())
    fn = int(((y_true_bin == 1) & (y_pred_bin == 0)).sum())
    tp = int(((y_true_bin == 1) & (y_pred_bin == 1)).sum())
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "attack_recall_TPR": round(tpr, 4),
            "false_positive_rate_FPR": round(fpr, 4)}


def multiclass_metrics(y_true, y_pred, label_enc):
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    per_class_recall = {}
    for i, cls in enumerate(label_enc.classes_):
        mask = y_true == i
        if mask.sum() == 0:
            continue
        per_class_recall[cls] = round(float((y_pred[mask] == i).mean()), 4)
    return {"macro_f1": round(float(macro_f1), 4),
            "per_class_recall": per_class_recall}


LATENCY_SAMPLE = 150  # number of single-row calls for latency measurement
LATENCY_WARMUP = 10   # warm-up calls (discarded) before timing


def latency_ms(fn, X, n=LATENCY_SAMPLE, warmup=LATENCY_WARMUP):
    """Sampled single-record latency (ms): median and p95 over n rows.

    Warms up the model first to avoid cold-start JIT/thread-pool overhead,
    then measures n randomly sampled individual rows.  Uses a small fixed
    sample so that n_jobs=-1 parallel-pool spin-up cost is not multiplied
    across thousands of calls.
    """
    rng = np.random.default_rng(42)
    warm_idx = rng.integers(0, len(X), warmup)
    for i in warm_idx:
        fn(X[i:i+1])

    idx = rng.integers(0, len(X), n)
    times = []
    for i in idx:
        t0 = time.perf_counter()
        fn(X[i:i+1])
        times.append(time.perf_counter() - t0)
    arr = np.array(times) * 1000  # convert to ms
    return {
        "median_ms": round(float(np.median(arr)), 4),
        "p95_ms":    round(float(np.percentile(arr, 95)), 4),
        "sample_n":  n,
    }


# ---------------------------------------------------------------------------
# Pipeline implementations (mirror ml_service.py logic exactly)
# ---------------------------------------------------------------------------
def pipeline_rf_only(clf, label_enc, X, y_raw, known_mask):
    """RF classification only; anomaly = RF predicts non-normal."""
    normal_idx = list(label_enc.classes_).index("normal")
    X_k = X[known_mask]
    y_true_k = label_enc.transform(y_raw[known_mask])

    print("  [A] Running batch predictions...")
    y_pred_k = clf.predict(X_k)
    print("  [A] Calculating metrics...")
    mc = multiclass_metrics(y_true_k, y_pred_k, label_enc)
    y_bin_true = (y_true_k != normal_idx).astype(int)
    y_bin_pred = (y_pred_k != normal_idx).astype(int)
    bm = binary_metrics(y_bin_true, y_bin_pred)
    print(f"  [A] Measuring sampled single-record latency ({LATENCY_SAMPLE} rows)...")
    lat = latency_ms(lambda x: clf.predict(x), X_k)
    print("  [A] Done.")
    return {"multiclass": mc, "binary": bm, "sampled_latency": lat}


def pipeline_if_gate(clf, iso, label_enc, X, y_raw, known_mask):
    """Old cascade: IF gate → RF only when IF flags anomaly."""
    normal_idx = list(label_enc.classes_).index("normal")
    X_k = X[known_mask]
    y_true_k = label_enc.transform(y_raw[known_mask])

    print("  [B] Running batch IF prediction...")
    iso_pred = iso.predict(X_k)          # -1=anomaly, 1=inlier
    y_pred_k = np.full(len(X_k), normal_idx, dtype=int)
    anomaly_mask = iso_pred == -1
    if anomaly_mask.any():
        print(f"  [B] Running batch RF on {anomaly_mask.sum():,} IF-flagged rows...")
        rf_pred = clf.predict(X_k[anomaly_mask])
        y_pred_k[anomaly_mask] = rf_pred

    print("  [B] Calculating metrics...")
    mc = multiclass_metrics(y_true_k, y_pred_k, label_enc)
    y_bin_true = (y_true_k != normal_idx).astype(int)
    y_bin_pred = (y_pred_k != normal_idx).astype(int)
    bm = binary_metrics(y_bin_true, y_bin_pred)

    def _cascade(x):
        if iso.predict(x)[0] == -1:
            clf.predict(x)
    print(f"  [B] Measuring sampled single-record latency ({LATENCY_SAMPLE} rows)...")
    lat = latency_ms(_cascade, X_k)
    print("  [B] Done.")
    return {"multiclass": mc, "binary": bm, "sampled_latency": lat}


def pipeline_if_only(iso, label_enc, X, y_raw, known_mask):
    """IF anomaly detection alone; no RF classification."""
    normal_idx = list(label_enc.classes_).index("normal")
    X_k = X[known_mask]
    y_true_k = label_enc.transform(y_raw[known_mask])

    print("  [C] Running batch IF prediction...")
    iso_pred = iso.predict(X_k)          # -1=anomaly, 1=inlier
    y_bin_pred = (iso_pred == -1).astype(int)
    y_bin_true = (y_true_k != normal_idx).astype(int)
    print("  [C] Calculating metrics...")
    bm = binary_metrics(y_bin_true, y_bin_pred)
    print(f"  [C] Measuring sampled single-record latency ({LATENCY_SAMPLE} rows)...")
    lat = latency_ms(lambda x: iso.predict(x), X_k)
    print("  [C] Done.")
    return {"multiclass": {"macro_f1": "N/A (IF cannot classify)",
                           "per_class_recall": "N/A"},
            "binary": bm, "sampled_latency": lat}


def pipeline_rf_if_parallel(clf, iso, label_enc, X, y_raw, known_mask):
    """Fixed pipeline: RF always runs; IF is a parallel signal.
    anomaly = RF predicts attack OR IF flags anomaly."""
    normal_idx = list(label_enc.classes_).index("normal")
    X_k = X[known_mask]
    y_true_k = label_enc.transform(y_raw[known_mask])

    print("  [D] Running batch RF prediction...")
    y_pred_k = clf.predict(X_k)
    print("  [D] Running batch IF prediction...")
    iso_pred = iso.predict(X_k)
    print("  [D] Calculating metrics...")
    mc = multiclass_metrics(y_true_k, y_pred_k, label_enc)
    rf_attack = (y_pred_k != normal_idx).astype(int)
    if_anomaly = (iso_pred == -1).astype(int)
    y_bin_pred = np.clip(rf_attack + if_anomaly, 0, 1)
    y_bin_true = (y_true_k != normal_idx).astype(int)
    bm = binary_metrics(y_bin_true, y_bin_pred)

    def _parallel(x):
        clf.predict(x)
        iso.predict(x)
    print(f"  [D] Measuring sampled single-record latency ({LATENCY_SAMPLE} rows)...")
    lat = latency_ms(_parallel, X_k)
    print("  [D] Done.")
    return {"multiclass": mc, "binary": bm, "sampled_latency": lat}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t_start = time.perf_counter()

    print("Loading artifacts...")
    clf, iso, label_enc, X, y_raw, known_mask = load_all()
    print(f"  Artifacts and test data loaded. "
          f"Test rows: {len(X):,}  |  Known-class rows: {known_mask.sum():,}")

    pipeline_fns = [
        ("A_rf_only",        "A. RF-only",               lambda: pipeline_rf_only(clf, label_enc, X, y_raw, known_mask)),
        ("B_if_gate_old",    "B. IF-gate (old/buggy)",   lambda: pipeline_if_gate(clf, iso, label_enc, X, y_raw, known_mask)),
        ("C_if_only",        "C. IF-only",               lambda: pipeline_if_only(iso, label_enc, X, y_raw, known_mask)),
        ("D_rf_if_parallel", "D. RF+IF-parallel (fixed)",lambda: pipeline_rf_if_parallel(clf, iso, label_enc, X, y_raw, known_mask)),
    ]

    results = {}
    for key, name, fn in pipeline_fns:
        print(f"\nRunning pipeline: {name}")
        results[key] = fn()

    total_s = time.perf_counter() - t_start

    # Pretty-print summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPARISON — held-out test.csv (known-class rows)")
    print(f"(Latency = sampled single-record, n={LATENCY_SAMPLE}, after {LATENCY_WARMUP}-call warm-up)")
    print("=" * 70)
    labels = {
        "A_rf_only":        "A. RF-only",
        "B_if_gate_old":    "B. IF-gate (old/buggy)",
        "C_if_only":        "C. IF-only",
        "D_rf_if_parallel": "D. RF+IF-parallel (fixed)",
    }
    for key, name in labels.items():
        r = results[key]
        mc = r["multiclass"]
        bm = r["binary"]
        lat = r["sampled_latency"]
        print(f"\n{name}")
        print(f"  Multiclass macro F1 : {mc['macro_f1']}")
        print(f"  Binary attack recall: {bm['attack_recall_TPR']}")
        print(f"  Binary FPR          : {bm['false_positive_rate_FPR']}")
        print(f"  Binary confusion    : TP={bm['TP']} FP={bm['FP']} "
              f"TN={bm['TN']} FN={bm['FN']}")
        print(f"  Sampled latency     : median={lat['median_ms']} ms  "
              f"p95={lat['p95_ms']} ms  (n={lat['sample_n']})")

    print(f"\nTotal runtime: {total_s:.1f}s")

    # Save to ml/reports/
    out_path = os.path.join(REPORT_DIR, "pipeline_comparison.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved: {out_path}")

    # Save human-readable text report
    txt_path = os.path.join(REPORT_DIR, "pipeline_comparison.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("PIPELINE COMPARISON REPORT\n")
        f.write("=" * 70 + "\n\n")
        f.write("Metric definitions\n")
        f.write("  macro F1        : unweighted mean per-class F1 (multiclass)\n")
        f.write("  attack recall   : TP / (TP + FN) — fraction of attacks caught\n")
        f.write("  FPR             : FP / (FP + TN) — fraction of normals mislabelled\n")
        f.write(f"  latency         : sampled single-record inference time (ms),\n")
        f.write(f"                    n={LATENCY_SAMPLE} rows after {LATENCY_WARMUP}-call warm-up\n\n")
        f.write("Validation note: test set used read-only; no tuning performed.\n\n")
        for key, name in labels.items():
            r = results[key]
            mc = r["multiclass"]
            bm = r["binary"]
            lat = r["sampled_latency"]
            f.write(f"{name}\n")
            f.write(f"  macro_f1            : {mc['macro_f1']}\n")
            f.write(f"  attack_recall (TPR) : {bm['attack_recall_TPR']}\n")
            f.write(f"  FPR                 : {bm['false_positive_rate_FPR']}\n")
            f.write(f"  TP / FP / TN / FN   : {bm['TP']} / {bm['FP']} / "
                    f"{bm['TN']} / {bm['FN']}\n")
            f.write(f"  latency_median_ms   : {lat['median_ms']}\n")
            f.write(f"  latency_p95_ms      : {lat['p95_ms']}\n")
            f.write(f"  latency_sample_n    : {lat['sample_n']}\n")
            if isinstance(mc.get("per_class_recall"), dict):
                f.write("  per_class_recall:\n")
                for cls, rec in mc["per_class_recall"].items():
                    f.write(f"    {cls:<20}: {rec}\n")
            f.write("\n")
        f.write(f"Total runtime: {total_s:.1f}s\n")
    print(f"Saved: {txt_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Script was cancelled. No results saved.")
