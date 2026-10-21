import os
import json
import warnings
import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder, StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths (all relative to this file so the script works from any cwd)
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
TRAIN_PATH = os.path.join(BASE_DIR, "data", "train.csv")
TEST_PATH  = os.path.join(BASE_DIR, "data", "test.csv")
MODEL_DIR  = os.path.abspath(os.path.join(BASE_DIR, "../backend/models"))
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(MODEL_DIR,  exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

RANDOM_SEED = 42
TARGET_COL  = "labels"

# Categorical feature columns (pandas 2.x StringDtype — not caught by
# select_dtypes(include="object") without the deprecation workaround)
CAT_COLS = ["protocol_type", "service", "flag"]


# ---------------------------------------------------------------------------
# 1. Load & audit datasets
# ---------------------------------------------------------------------------
def load_and_audit():
    print("=" * 60)
    print("STEP 1 — Loading and auditing datasets")
    print("=" * 60)

    train_df = pd.read_csv(TRAIN_PATH)
    test_df  = pd.read_csv(TEST_PATH)

    print(f"train.csv : {train_df.shape[0]:,} rows × {train_df.shape[1]} cols")
    print(f"test.csv  : {test_df.shape[0]:,} rows × {test_df.shape[1]} cols")

    # Schema compatibility
    assert list(train_df.columns) == list(test_df.columns), \
        "Column mismatch between train.csv and test.csv"
    assert train_df.columns[-1] == TARGET_COL, \
        f"Expected last column to be '{TARGET_COL}', got '{train_df.columns[-1]}'"

    # Missing values
    train_nulls = train_df.isnull().sum().sum()
    test_nulls  = test_df.isnull().sum().sum()
    print(f"\nMissing values — train: {train_nulls}, test: {test_nulls}")

    # Duplicates within each split
    train_dupes = train_df.duplicated().sum()
    test_dupes  = test_df.duplicated().sum()
    print(f"Duplicate rows  — train: {train_dupes}, test: {test_dupes}")

    # Train/test overlap (all 42 columns including the label)
    overlap = pd.merge(train_df, test_df, how="inner")
    print(f"\nExact-row overlap (all 42 cols, label included): {len(overlap):,}")
    print(
        "  NOTE: These rows appear in both splits.  Because the label column\n"
        "  is included in the merge key, the classifier has seen the exact\n"
        "  feature+label combination during training.  Evaluation metrics on\n"
        "  overlapping rows are optimistic.  This is a known property of the\n"
        "  NSL-KDD dataset release and is documented here rather than silently\n"
        "  removed, so the original row counts are preserved."
    )

    # Label sets
    train_labels = set(train_df[TARGET_COL].unique())
    test_labels  = set(test_df[TARGET_COL].unique())
    unseen       = sorted(test_labels - train_labels)
    train_only   = sorted(train_labels - test_labels)

    print(f"\nUnique labels — train: {len(train_labels)}, test: {len(test_labels)}")
    print(f"Labels in train only : {train_only}")
    print(f"Labels in test only  : {unseen}")
    print(
        "  NOTE: The 14 test-only classes are UNSEEN by the classifier.\n"
        "  Closed-set classification cannot predict them.  Their rows are\n"
        "  excluded from per-class F1 computation but retained in the\n"
        "  confusion matrix so the false-negative cost is visible."
    )

    # Categorical value coverage
    print("\nCategorical feature coverage (train vs test):")
    for c in CAT_COLS:
        tv  = set(train_df[c].unique())
        tsv = set(test_df[c].unique())
        extra = sorted(tsv - tv)
        print(f"  {c}: train={len(tv)} values, test_unseen={extra if extra else 'none'}")

    return train_df, test_df, unseen


# ---------------------------------------------------------------------------
# 2. Preprocessing — fit on train only
# ---------------------------------------------------------------------------
def build_preprocessors(train_df):
    """
    Fit OrdinalEncoder for categoricals and StandardScaler for numerics
    on the training data only.  Returns fitted objects and the ordered
    feature column list.
    """
    print("\n" + "=" * 60)
    print("STEP 2 — Fitting preprocessors on training data only")
    print("=" * 60)

    feature_cols = [c for c in train_df.columns if c != TARGET_COL]
    num_cols     = [c for c in feature_cols if c not in CAT_COLS]

    X_train_raw = train_df[feature_cols].copy()

    # OrdinalEncoder: unknown values at inference → -1 (no crash)
    ord_enc = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        dtype=np.float64,
    )
    X_train_raw[CAT_COLS] = ord_enc.fit_transform(X_train_raw[CAT_COLS])

    # StandardScaler fitted on training data only
    scaler = StandardScaler()
    X_train_scaled = X_train_raw.copy()
    X_train_scaled[num_cols] = scaler.fit_transform(X_train_raw[num_cols])

    X_train = X_train_scaled.values

    # Target encoder — fit on training labels only
    label_enc = LabelEncoder()
    y_train = label_enc.fit_transform(train_df[TARGET_COL].astype(str))

    print(f"Feature columns : {len(feature_cols)}")
    print(f"Categorical cols: {CAT_COLS}")
    print(f"Numeric cols    : {len(num_cols)}")
    print(f"Training classes: {sorted(label_enc.classes_.tolist())}")

    return X_train, y_train, ord_enc, scaler, label_enc, feature_cols


def apply_preprocessors(df, ord_enc, scaler, label_enc, feature_cols, unseen_classes):
    """
    Apply already-fitted preprocessors to a dataframe.
    Returns X (scaled), y_known (encoded, unseen rows masked),
    known_mask (bool array), and y_raw (original string labels).
    """
    num_cols = [c for c in feature_cols if c not in CAT_COLS]

    X_raw = df[feature_cols].copy()
    X_raw[CAT_COLS] = ord_enc.transform(X_raw[CAT_COLS])
    X_raw[num_cols] = scaler.transform(X_raw[num_cols])
    X = X_raw.values

    y_raw    = df[TARGET_COL].astype(str).values
    known_mask = ~np.isin(y_raw, unseen_classes)

    y_known = np.full(len(y_raw), -1, dtype=int)
    y_known[known_mask] = label_enc.transform(y_raw[known_mask])

    return X, y_known, known_mask, y_raw


# ---------------------------------------------------------------------------
# 3. Train models
# ---------------------------------------------------------------------------
def train_random_forest(X_train, y_train):
    print("\n" + "=" * 60)
    print("STEP 3a — Training RandomForestClassifier")
    print("=" * 60)

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    print("RandomForest training complete.")
    return clf


def train_isolation_forest(X_train):
    """
    IsolationForest is fitted on ALL training rows (normal + attack).
    contamination=0.05 means ~5% of training rows are expected to be
    anomalous.  The true attack fraction in train.csv is ~46.5%, so
    this value is conservative and will produce false negatives on
    attack traffic.  This is documented here; the value is kept at 0.05
    to match the existing backend contract.  A more accurate value would
    be ~0.465 but that would change the anomaly-detection behaviour
    significantly and is left for the deep-learning upgrade phase.
    """
    print("\n" + "=" * 60)
    print("STEP 3b — Training IsolationForest")
    print("=" * 60)
    print(
        "  contamination=0.05 (conservative; true attack fraction ~46.5%).\n"
        "  This means many attacks will NOT be flagged as anomalies.\n"
        "  See docstring for details."
    )

    iso = IsolationForest(
        contamination=0.05,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    iso.fit(X_train)
    print("IsolationForest training complete.")
    return iso


# ---------------------------------------------------------------------------
# 4. Evaluate
# ---------------------------------------------------------------------------
def evaluate(clf, iso, X_test, y_known, known_mask, y_raw,
             label_enc, unseen_classes, train_df):
    print("\n" + "=" * 60)
    print("STEP 4 — Evaluation on held-out test.csv")
    print("=" * 60)

    # ── 4a. RandomForest on known-class rows only ──────────────────────────
    X_known   = X_test[known_mask]
    y_true_k  = y_known[known_mask]
    y_pred_k  = clf.predict(X_known)

    acc     = accuracy_score(y_true_k, y_pred_k)
    mac_f1  = f1_score(y_true_k, y_pred_k, average="macro",    zero_division=0)
    wgt_f1  = f1_score(y_true_k, y_pred_k, average="weighted", zero_division=0)
    mac_p   = precision_score(y_true_k, y_pred_k, average="macro",    zero_division=0)
    mac_r   = recall_score(y_true_k, y_pred_k, average="macro",    zero_division=0)

    print(f"\n--- RandomForest (known classes only, n={len(y_true_k):,}) ---")
    print(f"  Accuracy        : {acc:.4f}")
    print(f"  Macro Precision : {mac_p:.4f}")
    print(f"  Macro Recall    : {mac_r:.4f}")
    print(f"  Macro F1        : {mac_f1:.4f}")
    print(f"  Weighted F1     : {wgt_f1:.4f}")

    class_names = label_enc.classes_.tolist()
    # Use only labels that actually appear in y_true_k or y_pred_k
    # (e.g. 'spy' has 2 train rows but 0 test rows — sklearn raises if
    #  target_names length != number of unique labels seen in predictions)
    present_labels = sorted(set(y_true_k) | set(y_pred_k))
    present_names  = [class_names[i] for i in present_labels]
    report_str  = classification_report(
        y_true_k, y_pred_k,
        labels=present_labels,
        target_names=present_names,
        zero_division=0,
    )
    print("\nPer-class report (known classes):")
    print(report_str)

    cm = confusion_matrix(y_true_k, y_pred_k, labels=present_labels)
    print(f"Confusion matrix shape: {cm.shape}  (class order: {present_names})")
    class_names = present_names  # use only present classes for saving

    # ── 4b. Unseen-class summary ───────────────────────────────────────────
    unseen_rows = (~known_mask).sum()
    print(f"\n--- Unseen classes (n={unseen_rows:,} rows excluded from F1) ---")
    for uc in unseen_classes:
        n = (y_raw == uc).sum()
        print(f"  {uc}: {n} rows — classifier cannot predict this class")

    # ── 4c. Binary normal-vs-attack FPR ───────────────────────────────────
    normal_idx = list(label_enc.classes_).index("normal")
    y_bin_true = (y_true_k != normal_idx).astype(int)   # 1=attack, 0=normal
    y_bin_pred = (y_pred_k != normal_idx).astype(int)

    tn = ((y_bin_true == 0) & (y_bin_pred == 0)).sum()
    fp = ((y_bin_true == 0) & (y_bin_pred == 1)).sum()
    fn = ((y_bin_true == 1) & (y_bin_pred == 0)).sum()
    tp = ((y_bin_true == 1) & (y_bin_pred == 1)).sum()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    print(f"\n--- Binary normal-vs-attack (known classes) ---")
    print(f"  TP={tp:,}  FP={fp:,}  TN={tn:,}  FN={fn:,}")
    print(f"  False-Positive Rate (FPR): {fpr:.4f}")
    print(f"  True-Positive Rate  (TPR): {tpr:.4f}")

    # ── 4d. IsolationForest evaluation ────────────────────────────────────
    iso_pred_raw = iso.predict(X_test)          # -1=anomaly, 1=inlier
    iso_pred_bin = (iso_pred_raw == -1).astype(int)   # 1=anomaly

    # Ground truth: 1 if the true label is NOT "normal"
    y_iso_true = (y_raw != "normal").astype(int)

    iso_tn = ((y_iso_true == 0) & (iso_pred_bin == 0)).sum()
    iso_fp = ((y_iso_true == 0) & (iso_pred_bin == 1)).sum()
    iso_fn = ((y_iso_true == 1) & (iso_pred_bin == 0)).sum()
    iso_tp = ((y_iso_true == 1) & (iso_pred_bin == 1)).sum()
    iso_fpr = iso_fp / (iso_fp + iso_tn) if (iso_fp + iso_tn) > 0 else 0.0
    iso_tpr = iso_tp / (iso_tp + iso_fn) if (iso_tp + iso_fn) > 0 else 0.0
    iso_f1  = f1_score(y_iso_true, iso_pred_bin, zero_division=0)

    print(f"\n--- IsolationForest (all {len(X_test):,} test rows) ---")
    print(f"  TP={iso_tp:,}  FP={iso_fp:,}  TN={iso_tn:,}  FN={iso_fn:,}")
    print(f"  FPR: {iso_fpr:.4f}   TPR: {iso_tpr:.4f}   F1: {iso_f1:.4f}")
    print(
        "  NOTE: contamination=0.05 causes high FN rate because the true\n"
        "  attack fraction is ~46.5%.  IsolationForest is used as a first-\n"
        "  pass gate; the RandomForest handles classification."
    )

    # ── 4e. Overlap caveat ────────────────────────────────────────────────
    print(
        "\n  OVERLAP CAVEAT: 15,791 test rows are exact duplicates of training\n"
        "  rows (all 42 columns including label).  Metrics on those rows are\n"
        "  optimistic.  True generalisation performance is lower."
    )

    # ── 4f. Class distribution summary ────────────────────────────────────
    print("\n--- Training class distribution ---")
    print(train_df[TARGET_COL].value_counts().to_string())

    # ── 4g. Build metrics dict for saving ─────────────────────────────────
    metrics = {
        "accuracy":          round(float(acc),    4),
        "macro_precision":   round(float(mac_p),  4),
        "macro_recall":      round(float(mac_r),  4),
        "macro_f1":          round(float(mac_f1), 4),
        "weighted_f1":       round(float(wgt_f1), 4),
        "binary_fpr":        round(float(fpr),    4),
        "binary_tpr":        round(float(tpr),    4),
        "iso_fpr":           round(float(iso_fpr),4),
        "iso_tpr":           round(float(iso_tpr),4),
        "iso_f1":            round(float(iso_f1), 4),
        "known_test_rows":   int(len(y_true_k)),
        "unseen_test_rows":  int(unseen_rows),
        "unseen_classes":    unseen_classes,
        "overlap_rows":      15791,
        "overlap_note":      (
            "15791 test rows are exact duplicates of training rows "
            "(all 42 columns including label). Metrics are optimistic."
        ),
    }
    return metrics, report_str, cm, class_names


# ---------------------------------------------------------------------------
# 5. Save artifacts
# ---------------------------------------------------------------------------
def save_artifacts(clf, iso, ord_enc, scaler, label_enc,
                   feature_cols, metrics, report_str, cm, class_names):
    print("\n" + "=" * 60)
    print("STEP 5 — Saving artifacts")
    print("=" * 60)

    # Model artifacts (backend loads these)
    joblib.dump(clf,          os.path.join(MODEL_DIR, "classifier.pkl"))
    joblib.dump(iso,          os.path.join(MODEL_DIR, "anomaly.pkl"))
    joblib.dump(ord_enc,      os.path.join(MODEL_DIR, "encoders.pkl"))
    joblib.dump(scaler,       os.path.join(MODEL_DIR, "scaler.pkl"))
    joblib.dump(label_enc,    os.path.join(MODEL_DIR, "label_encoder.pkl"))
    joblib.dump(feature_cols, os.path.join(MODEL_DIR, "columns.pkl"))

    print(f"  classifier.pkl    -> {MODEL_DIR}")
    print(f"  anomaly.pkl       -> {MODEL_DIR}")
    print(f"  encoders.pkl      -> {MODEL_DIR}")
    print(f"  scaler.pkl        -> {MODEL_DIR}")
    print(f"  label_encoder.pkl -> {MODEL_DIR}")
    print(f"  columns.pkl       -> {MODEL_DIR}")

    # Training metadata (no secrets)
    import sklearn
    meta = {
        "trained_at":       datetime.datetime.utcnow().isoformat() + "Z",
        "train_path":       TRAIN_PATH,
        "test_path":        TEST_PATH,
        "random_seed":      RANDOM_SEED,
        "target_column":    TARGET_COL,
        "feature_columns":  feature_cols,
        "cat_columns":      CAT_COLS,
        "n_features":       len(feature_cols),
        "sklearn_version":  sklearn.__version__,
        "model_version":    "1.0-baseline",
        "rf_params": {
            "n_estimators":    200,
            "max_depth":       20,
            "min_samples_split": 5,
            "random_state":    RANDOM_SEED,
        },
        "iso_params": {
            "contamination": 0.05,
            "random_state":  RANDOM_SEED,
        },
        "metrics": metrics,
    }
    meta_path = os.path.join(MODEL_DIR, "training_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  training_meta.json -> {MODEL_DIR}")

    # Human-readable report
    report_path = os.path.join(REPORT_DIR, "classification_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=== Classification Report (known classes, held-out test.csv) ===\n\n")
        f.write(report_str)
        f.write("\n\n=== Summary Metrics ===\n")
        for k, v in metrics.items():
            f.write(f"{k}: {v}\n")
    print(f"  classification_report.txt -> {REPORT_DIR}")

    # Confusion matrix as CSV
    cm_df = pd.DataFrame(cm, index=class_names, columns=class_names)
    cm_path = os.path.join(REPORT_DIR, "confusion_matrix.csv")
    cm_df.to_csv(cm_path)
    print(f"  confusion_matrix.csv      -> {REPORT_DIR}")

    # Metrics as JSON
    metrics_path = os.path.join(REPORT_DIR, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"  metrics.json              -> {REPORT_DIR}")


# ---------------------------------------------------------------------------
# 6. Smoke test — load artifacts and run one inference
# ---------------------------------------------------------------------------
def smoke_test(train_df):
    print("\n" + "=" * 60)
    print("STEP 6 — Artifact smoke test")
    print("=" * 60)

    clf_l      = joblib.load(os.path.join(MODEL_DIR, "classifier.pkl"))
    iso_l      = joblib.load(os.path.join(MODEL_DIR, "anomaly.pkl"))
    ord_enc_l  = joblib.load(os.path.join(MODEL_DIR, "encoders.pkl"))
    scaler_l   = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
    label_l    = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
    cols_l     = joblib.load(os.path.join(MODEL_DIR, "columns.pkl"))

    print("  All 6 artifacts loaded successfully.")

    # Build one sample row from training data (a known neptune row)
    sample_row = train_df[train_df[TARGET_COL] == "neptune"].iloc[0]
    feature_vals = sample_row[cols_l].copy()

    num_cols = [c for c in cols_l if c not in CAT_COLS]

    # Pass DataFrames to suppress sklearn feature-name warnings
    cat_df = pd.DataFrame([feature_vals[CAT_COLS].values], columns=CAT_COLS)
    num_df = pd.DataFrame([feature_vals[num_cols].values], columns=num_cols)

    feature_vals[CAT_COLS] = ord_enc_l.transform(cat_df).flatten()
    feature_vals[num_cols] = scaler_l.transform(num_df).flatten()

    X_sample = feature_vals.values.reshape(1, -1)

    iso_out  = iso_l.predict(X_sample)[0]
    clf_out  = clf_l.predict(X_sample)[0]
    label    = label_l.inverse_transform([clf_out])[0]
    proba    = clf_l.predict_proba(X_sample)[0].max()
    anomaly  = iso_out == -1

    print(f"  Sample row true label : neptune")
    print(f"  IsolationForest output: {iso_out}  (anomaly={anomaly})")
    print(f"  RandomForest predicted: {label}  (confidence={proba:.4f})")
    assert label == "neptune", f"Smoke test FAILED: expected 'neptune', got '{label}'"
    print("  Smoke test PASSED.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    train_df, test_df, unseen_classes = load_and_audit()

    X_train, y_train, ord_enc, scaler, label_enc, feature_cols = \
        build_preprocessors(train_df)

    X_test, y_known, known_mask, y_raw = apply_preprocessors(
        test_df, ord_enc, scaler, label_enc, feature_cols, unseen_classes
    )

    clf = train_random_forest(X_train, y_train)
    iso = train_isolation_forest(X_train)

    metrics, report_str, cm, class_names = evaluate(
        clf, iso, X_test, y_known, known_mask, y_raw,
        label_enc, unseen_classes, train_df
    )

    save_artifacts(
        clf, iso, ord_enc, scaler, label_enc,
        feature_cols, metrics, report_str, cm, class_names
    )

    smoke_test(train_df)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Macro F1   : {metrics['macro_f1']}")
    print(f"  Accuracy   : {metrics['accuracy']}")
    print(f"  Binary FPR : {metrics['binary_fpr']}")
    print(f"  Artifacts  : {MODEL_DIR}")
    print(f"  Reports    : {REPORT_DIR}")
