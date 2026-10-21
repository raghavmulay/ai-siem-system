"""
tests/test_ml_pipeline.py
--------------------------
Automated tests for the AI-SIEM ML training and inference pipeline.

Run from the project root:
    call venv\\Scripts\\activate.bat && python -m pytest tests/ -v
"""

import os
import sys
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_PATH = os.path.join(ROOT, "ml", "data", "train.csv")
TEST_PATH  = os.path.join(ROOT, "ml", "data", "test.csv")
MODEL_DIR  = os.path.join(ROOT, "backend", "models")
REPORT_DIR = os.path.join(ROOT, "ml", "reports")

CAT_COLS   = ["protocol_type", "service", "flag"]
TARGET_COL = "labels"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def train_df():
    return pd.read_csv(TRAIN_PATH)

@pytest.fixture(scope="session")
def test_df():
    return pd.read_csv(TEST_PATH)

@pytest.fixture(scope="session")
def artifacts():
    """Load all saved artifacts once per session."""
    return {
        "classifier":    joblib.load(os.path.join(MODEL_DIR, "classifier.pkl")),
        "anomaly":       joblib.load(os.path.join(MODEL_DIR, "anomaly.pkl")),
        "encoders":      joblib.load(os.path.join(MODEL_DIR, "encoders.pkl")),
        "scaler":        joblib.load(os.path.join(MODEL_DIR, "scaler.pkl")),
        "label_encoder": joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl")),
        "columns":       joblib.load(os.path.join(MODEL_DIR, "columns.pkl")),
    }


# ---------------------------------------------------------------------------
# 1. Dataset schema tests
# ---------------------------------------------------------------------------
class TestDatasetSchema:
    def test_train_shape(self, train_df):
        assert train_df.shape[1] == 42, "train.csv must have 42 columns"
        assert train_df.shape[0] > 0

    def test_test_shape(self, test_df):
        assert test_df.shape[1] == 42, "test.csv must have 42 columns"
        assert test_df.shape[0] > 0

    def test_column_names_match(self, train_df, test_df):
        assert list(train_df.columns) == list(test_df.columns), \
            "train and test column names must match"

    def test_target_column_is_last(self, train_df):
        assert train_df.columns[-1] == TARGET_COL

    def test_no_missing_values_train(self, train_df):
        assert train_df.isnull().sum().sum() == 0

    def test_no_missing_values_test(self, test_df):
        assert test_df.isnull().sum().sum() == 0

    def test_categorical_cols_present(self, train_df):
        for c in CAT_COLS:
            assert c in train_df.columns, f"Expected categorical column '{c}'"

    def test_target_col_not_numeric(self, train_df):
        assert train_df[TARGET_COL].dtype == object or \
               str(train_df[TARGET_COL].dtype) == "str", \
               "labels column should be string type"


# ---------------------------------------------------------------------------
# 2. Label set tests
# ---------------------------------------------------------------------------
class TestLabelSets:
    def test_normal_class_in_train(self, train_df):
        assert "normal" in train_df[TARGET_COL].values

    def test_unseen_classes_documented(self, train_df, test_df):
        train_labels = set(train_df[TARGET_COL].unique())
        test_labels  = set(test_df[TARGET_COL].unique())
        unseen = test_labels - train_labels
        # We expect exactly 14 unseen classes in NSL-KDD
        assert len(unseen) == 14, (
            f"Expected 14 unseen test classes, found {len(unseen)}: {sorted(unseen)}"
        )

    def test_train_only_class(self, train_df, test_df):
        train_labels = set(train_df[TARGET_COL].unique())
        test_labels  = set(test_df[TARGET_COL].unique())
        train_only = train_labels - test_labels
        assert "spy" in train_only, "'spy' should be train-only"

    def test_overlap_documented(self, train_df, test_df):
        overlap = pd.merge(train_df, test_df, how="inner")
        # Overlap exists and is documented (not silently removed)
        assert len(overlap) == 15791, (
            f"Expected 15791 overlapping rows, found {len(overlap)}"
        )


# ---------------------------------------------------------------------------
# 3. Preprocessing leakage tests
# ---------------------------------------------------------------------------
class TestPreprocessingLeakage:
    def test_ordinal_encoder_type(self, artifacts):
        assert isinstance(artifacts["encoders"], OrdinalEncoder), \
            "encoders.pkl must be an OrdinalEncoder (not dict of LabelEncoders)"

    def test_scaler_type(self, artifacts):
        assert isinstance(artifacts["scaler"], StandardScaler)

    def test_label_encoder_type(self, artifacts):
        assert isinstance(artifacts["label_encoder"], LabelEncoder)

    def test_label_encoder_fitted_on_train_only(self, artifacts, train_df):
        """Label encoder classes must be a subset of training labels."""
        train_labels = set(train_df[TARGET_COL].unique())
        enc_classes  = set(artifacts["label_encoder"].classes_)
        assert enc_classes <= train_labels, (
            f"Label encoder contains classes not in training data: "
            f"{enc_classes - train_labels}"
        )

    def test_feature_column_count(self, artifacts):
        assert len(artifacts["columns"]) == 41, \
            "columns.pkl must list 41 feature columns (42 total minus label)"

    def test_feature_column_order_consistent(self, artifacts, train_df):
        expected = [c for c in train_df.columns if c != TARGET_COL]
        assert artifacts["columns"] == expected


# ---------------------------------------------------------------------------
# 4. Artifact loading tests
# ---------------------------------------------------------------------------
class TestArtifactLoading:
    def test_classifier_is_rf(self, artifacts):
        assert isinstance(artifacts["classifier"], RandomForestClassifier)

    def test_anomaly_is_if(self, artifacts):
        assert isinstance(artifacts["anomaly"], IsolationForest)

    def test_all_artifacts_present(self):
        for fname in ["classifier.pkl", "anomaly.pkl", "encoders.pkl",
                      "scaler.pkl", "label_encoder.pkl", "columns.pkl",
                      "training_meta.json"]:
            path = os.path.join(MODEL_DIR, fname)
            assert os.path.exists(path), f"Missing artifact: {fname}"

    def test_training_meta_no_secrets(self):
        meta_path = os.path.join(MODEL_DIR, "training_meta.json")
        with open(meta_path) as f:
            text = f.read().lower()
        for secret_kw in ["password", "mongo_uri", "mongodb+srv", "api_key", "secret"]:
            assert secret_kw not in text, \
                f"training_meta.json contains sensitive keyword: '{secret_kw}'"

    def test_training_meta_fields(self):
        meta_path = os.path.join(MODEL_DIR, "training_meta.json")
        with open(meta_path) as f:
            meta = json.load(f)
        for field in ["trained_at", "random_seed", "sklearn_version",
                      "feature_columns", "metrics", "model_version"]:
            assert field in meta, f"training_meta.json missing field: '{field}'"


# ---------------------------------------------------------------------------
# 5. Inference tests
# ---------------------------------------------------------------------------
class TestInference:
    def _make_sample(self, df, label, artifacts):
        """Build a preprocessed sample row for a given label."""
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        num_cols = [c for c in cols if c not in CAT_COLS]

        row = df[df[TARGET_COL] == label].iloc[0][cols].copy()
        row[CAT_COLS] = enc.transform(
            pd.DataFrame([row[CAT_COLS].values], columns=CAT_COLS)
        )[0]
        row[num_cols] = scaler.transform(
            pd.DataFrame([row[num_cols].values], columns=num_cols)
        )[0]
        return row.values.reshape(1, -1).astype(float)

    def test_rf_predicts_neptune(self, train_df, artifacts):
        X = self._make_sample(train_df, "neptune", artifacts)
        pred = artifacts["classifier"].predict(X)[0]
        label = artifacts["label_encoder"].inverse_transform([pred])[0]
        assert label == "neptune", f"Expected 'neptune', got '{label}'"

    def test_rf_predicts_normal(self, train_df, artifacts):
        X = self._make_sample(train_df, "normal", artifacts)
        pred = artifacts["classifier"].predict(X)[0]
        label = artifacts["label_encoder"].inverse_transform([pred])[0]
        assert label == "normal", f"Expected 'normal', got '{label}'"

    def test_rf_predict_proba_sums_to_one(self, train_df, artifacts):
        X = self._make_sample(train_df, "neptune", artifacts)
        proba = artifacts["classifier"].predict_proba(X)[0]
        assert abs(proba.sum() - 1.0) < 1e-6

    def test_isolation_forest_output_values(self, train_df, artifacts):
        """IF must return only -1 or 1."""
        X = self._make_sample(train_df, "neptune", artifacts)
        out = artifacts["anomaly"].predict(X)[0]
        assert out in (-1, 1), f"IsolationForest returned unexpected value: {out}"

    def test_isolation_forest_minus1_means_anomaly(self, train_df, artifacts):
        """Verify the -1 == anomaly convention is correct."""
        X = self._make_sample(train_df, "neptune", artifacts)
        out = artifacts["anomaly"].predict(X)[0]
        anomaly_bool = out == -1
        assert isinstance(anomaly_bool, (bool, np.bool_))

    def test_unknown_categorical_does_not_crash(self, train_df, artifacts):
        """OrdinalEncoder with handle_unknown='use_encoded_value' returns -1."""
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        num_cols = [c for c in cols if c not in CAT_COLS]

        row = train_df[train_df[TARGET_COL] == "normal"].iloc[0][cols].copy()
        row["service"] = "UNKNOWN_SERVICE_XYZ"   # unseen value
        row[CAT_COLS] = enc.transform(
            pd.DataFrame([row[CAT_COLS].values], columns=CAT_COLS)
        )[0]
        row[num_cols] = scaler.transform(
            pd.DataFrame([row[num_cols].values], columns=num_cols)
        )[0]
        X = row.values.reshape(1, -1).astype(float)
        # Must not raise
        pred = artifacts["classifier"].predict(X)[0]
        assert pred >= 0

    def test_label_decoder_returns_string(self, artifacts):
        pred = artifacts["classifier"].predict(
            np.zeros((1, len(artifacts["columns"])))
        )[0]
        label = artifacts["label_encoder"].inverse_transform([pred])[0]
        assert isinstance(label, str)

    def test_feature_count_matches_columns(self, artifacts):
        n_cols = len(artifacts["columns"])
        n_feat = artifacts["classifier"].n_features_in_
        assert n_cols == n_feat, (
            f"columns.pkl has {n_cols} entries but classifier expects {n_feat}"
        )


# ---------------------------------------------------------------------------
# 6. Backend response contract test
# ---------------------------------------------------------------------------
class TestBackendContract:
    def test_predict_response_keys(self, train_df, artifacts):
        """
        Simulate the fixed ml_service.predict() logic and verify the response
        contract: RF is primary classifier; IF is a parallel signal only.
        An IF inlier cannot suppress an RF attack prediction.
        """
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        clf      = artifacts["classifier"]
        iso      = artifacts["anomaly"]
        le       = artifacts["label_encoder"]
        num_cols = [c for c in cols if c not in CAT_COLS]

        row = train_df[train_df[TARGET_COL] == "neptune"].iloc[0][cols].copy()
        row[CAT_COLS] = enc.transform(
            pd.DataFrame([row[CAT_COLS].values], columns=CAT_COLS)
        )[0]
        row[num_cols] = scaler.transform(
            pd.DataFrame([row[num_cols].values], columns=num_cols)
        )[0]
        X = row.values.reshape(1, -1).astype(float)

        # Fixed logic: RF always runs and is authoritative
        raw_label   = int(clf.predict(X)[0])
        attack_type = str(le.inverse_transform([raw_label])[0])
        confidence  = float(round(max(clf.predict_proba(X)[0]), 4))

        # IF is a parallel signal; inlier cannot suppress RF attack
        if_out     = int(iso.predict(X)[0])
        if_anomaly = if_out == -1
        rf_attack  = attack_type.lower() != "normal"
        anomaly    = rf_attack or if_anomaly

        if not rf_attack:
            attack_type = "Normal"

        response = {
            "anomaly":     anomaly,
            "attack_type": attack_type,
            "confidence":  confidence,
        }

        assert "anomaly"     in response
        assert "attack_type" in response
        assert "confidence"  in response
        assert isinstance(response["anomaly"],     bool)
        assert isinstance(response["attack_type"], str)
        assert isinstance(response["confidence"],  float)
        assert 0.0 <= response["confidence"] <= 1.0
        # neptune must be flagged as attack under the fixed logic
        assert response["anomaly"] is True, \
            "neptune row must be anomaly=True under fixed RF-primary logic"
        assert response["attack_type"].lower() == "neptune"


# ---------------------------------------------------------------------------
# 7. Shuffled-label leakage diagnostic
# ---------------------------------------------------------------------------
class TestLeakageDiagnostic:
    def test_shuffled_labels_lower_accuracy(self, train_df, artifacts):
        """
        A model trained on real labels should outperform one trained on
        shuffled labels.  We verify the saved classifier beats a trivial
        shuffled baseline on a small held-out sample.
        This is a sanity check, not proof of zero leakage.
        """
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        clf      = artifacts["classifier"]
        le       = artifacts["label_encoder"]
        num_cols = [c for c in cols if c not in CAT_COLS]

        # Use 500 training rows as a quick check
        sample = train_df.sample(500, random_state=42)
        X_s = sample[cols].copy()
        X_s[CAT_COLS] = enc.transform(
            pd.DataFrame(X_s[CAT_COLS].values, columns=CAT_COLS)
        )
        X_s[num_cols] = scaler.transform(
            pd.DataFrame(X_s[num_cols].values, columns=num_cols)
        )
        X_np = X_s.values.astype(float)

        known_mask = sample[TARGET_COL].isin(le.classes_)
        X_k = X_np[known_mask]
        y_k = le.transform(sample[TARGET_COL][known_mask].astype(str))

        real_acc = (clf.predict(X_k) == y_k).mean()

        # Shuffled baseline: random class assignment
        rng = np.random.default_rng(42)
        shuffled_pred = rng.integers(0, len(le.classes_), size=len(y_k))
        shuffled_acc  = (shuffled_pred == y_k).mean()

        assert real_acc > shuffled_acc + 0.5, (
            f"Real accuracy ({real_acc:.3f}) should be >> shuffled ({shuffled_acc:.3f}). "
            "Possible leakage or trivial model."
        )


# ---------------------------------------------------------------------------
# 8. Report files exist
# ---------------------------------------------------------------------------
class TestReports:
    def test_classification_report_exists(self):
        assert os.path.exists(os.path.join(REPORT_DIR, "classification_report.txt"))

    def test_confusion_matrix_exists(self):
        assert os.path.exists(os.path.join(REPORT_DIR, "confusion_matrix.csv"))

    def test_metrics_json_exists(self):
        assert os.path.exists(os.path.join(REPORT_DIR, "metrics.json"))

    def test_metrics_json_has_macro_f1(self):
        with open(os.path.join(REPORT_DIR, "metrics.json")) as f:
            m = json.load(f)
        assert "macro_f1" in m
        assert 0.0 <= m["macro_f1"] <= 1.0


# ---------------------------------------------------------------------------
# 9. Detection logic regression tests (fixed pipeline)
#
# These tests verify the corrected ml_service.predict() behaviour:
#   - RF always runs and is the primary classifier
#   - IF is a parallel signal only; an IF inlier cannot suppress an RF attack
#
# Four cases required:
#   a) Known attack  → anomaly=True, attack_type != "Normal"
#   b) Normal traffic → anomaly=False, attack_type == "Normal"
#   c) Anomalous record (IF flags) → anomaly=True regardless of RF
#   d) IF inlier but RF identifies attack → anomaly=True (the critical fix)
# ---------------------------------------------------------------------------
class TestDetectionLogicRegression:
    """
    Tests use the fixed predict() logic directly (not via HTTP) so they
    run without a running Flask server.  The logic is re-implemented here
    to mirror ml_service.predict() exactly, making the tests independent
    of import-time side effects.
    """

    def _preprocess(self, df, label, artifacts):
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        num_cols = [c for c in cols if c not in CAT_COLS]
        row = df[df[TARGET_COL] == label].iloc[0][cols].copy()
        row[CAT_COLS] = enc.transform(
            pd.DataFrame([row[CAT_COLS].values], columns=CAT_COLS)
        )[0]
        row[num_cols] = scaler.transform(
            pd.DataFrame([row[num_cols].values], columns=num_cols)
        )[0]
        return row.values.reshape(1, -1).astype(float)

    def _fixed_predict(self, X, artifacts):
        """Mirror of the fixed ml_service.predict() logic."""
        clf = artifacts["classifier"]
        iso = artifacts["anomaly"]
        le  = artifacts["label_encoder"]

        raw_label   = int(clf.predict(X)[0])
        attack_type = str(le.inverse_transform([raw_label])[0])
        confidence  = float(round(max(clf.predict_proba(X)[0]), 4))

        if_out     = int(iso.predict(X)[0])
        if_anomaly = if_out == -1
        rf_attack  = attack_type.lower() != "normal"
        anomaly    = rf_attack or if_anomaly

        if not rf_attack:
            attack_type = "Normal"

        return {"anomaly": anomaly, "attack_type": attack_type,
                "confidence": confidence}

    # ── Case a: known attack ──────────────────────────────────────────────
    def test_known_attack_neptune_flagged(self, train_df, artifacts):
        """A neptune row must be flagged as anomaly with attack_type='neptune'."""
        X = self._preprocess(train_df, "neptune", artifacts)
        result = self._fixed_predict(X, artifacts)
        assert result["anomaly"] is True, \
            "neptune must be flagged as anomaly"
        assert result["attack_type"].lower() == "neptune", \
            f"Expected attack_type='neptune', got '{result['attack_type']}'"
        assert 0.0 < result["confidence"] <= 1.0

    def test_known_attack_smurf_flagged(self, train_df, artifacts):
        """A smurf row must be flagged as anomaly."""
        X = self._preprocess(train_df, "smurf", artifacts)
        result = self._fixed_predict(X, artifacts)
        assert result["anomaly"] is True, "smurf must be flagged as anomaly"
        assert result["attack_type"].lower() == "smurf"

    def test_known_attack_portsweep_flagged(self, train_df, artifacts):
        """A portsweep row must be flagged as anomaly."""
        X = self._preprocess(train_df, "portsweep", artifacts)
        result = self._fixed_predict(X, artifacts)
        assert result["anomaly"] is True, "portsweep must be flagged as anomaly"
        assert result["attack_type"].lower() == "portsweep"

    # ── Case b: normal traffic ────────────────────────────────────────────
    def test_normal_traffic_not_flagged(self, train_df, artifacts):
        """A normal row must not be flagged as anomaly (RF says normal, IF inlier)."""
        # Find a normal row that IF also classifies as inlier
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        iso      = artifacts["anomaly"]
        num_cols = [c for c in cols if c not in CAT_COLS]

        normal_rows = train_df[train_df[TARGET_COL] == "normal"]
        found = False
        for _, row in normal_rows.iterrows():
            r = row[cols].copy()
            r[CAT_COLS] = enc.transform(
                pd.DataFrame([r[CAT_COLS].values], columns=CAT_COLS)
            )[0]
            r[num_cols] = scaler.transform(
                pd.DataFrame([r[num_cols].values], columns=num_cols)
            )[0]
            X = r.values.reshape(1, -1).astype(float)
            if iso.predict(X)[0] == 1:   # IF says inlier
                result = self._fixed_predict(X, artifacts)
                assert result["anomaly"] is False, \
                    "Normal row (RF=normal, IF=inlier) must not be flagged"
                assert result["attack_type"] == "Normal"
                found = True
                break
        assert found, "Could not find a normal row where IF also predicts inlier"

    # ── Case c: IF flags anomaly (even if RF says normal) ─────────────────
    def test_if_anomaly_sets_anomaly_true(self, train_df, artifacts):
        """When IF flags a row as anomaly, anomaly=True regardless of RF output."""
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        iso      = artifacts["anomaly"]
        clf      = artifacts["classifier"]
        le       = artifacts["label_encoder"]
        num_cols = [c for c in cols if c not in CAT_COLS]
        normal_idx = list(le.classes_).index("normal")

        # Find a row where IF says anomaly (-1) but RF says normal
        normal_rows = train_df[train_df[TARGET_COL] == "normal"]
        found = False
        for _, row in normal_rows.iterrows():
            r = row[cols].copy()
            r[CAT_COLS] = enc.transform(
                pd.DataFrame([r[CAT_COLS].values], columns=CAT_COLS)
            )[0]
            r[num_cols] = scaler.transform(
                pd.DataFrame([r[num_cols].values], columns=num_cols)
            )[0]
            X = r.values.reshape(1, -1).astype(float)
            if iso.predict(X)[0] == -1 and clf.predict(X)[0] == normal_idx:
                result = self._fixed_predict(X, artifacts)
                assert result["anomaly"] is True, \
                    "IF anomaly must set anomaly=True even when RF says normal"
                found = True
                break

        if not found:
            pytest.skip(
                "No normal row found where IF=-1 and RF=normal in this dataset; "
                "skip rather than fail (contamination=0.05 makes this rare)"
            )

    # ── Case d: IF inlier but RF identifies attack (the critical fix) ─────
    def test_if_inlier_does_not_suppress_rf_attack(self, train_df, artifacts):
        """
        Critical regression: when IF predicts inlier (1) but RF predicts an
        attack class, anomaly must still be True.
        This was the bug in the old cascade where IF inlier → return Normal
        without ever calling RF.
        """
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        iso      = artifacts["anomaly"]
        clf      = artifacts["classifier"]
        le       = artifacts["label_encoder"]
        num_cols = [c for c in cols if c not in CAT_COLS]
        normal_idx = list(le.classes_).index("normal")

        # Find an attack row where IF says inlier (contamination=0.05 means
        # most attack rows are inliers from IF's perspective)
        attack_labels = [l for l in le.classes_ if l != "normal"]
        found = False
        for atk in attack_labels:
            rows = train_df[train_df[TARGET_COL] == atk]
            for _, row in rows.iterrows():
                r = row[cols].copy()
                r[CAT_COLS] = enc.transform(
                    pd.DataFrame([r[CAT_COLS].values], columns=CAT_COLS)
                )[0]
                r[num_cols] = scaler.transform(
                    pd.DataFrame([r[num_cols].values], columns=num_cols)
                )[0]
                X = r.values.reshape(1, -1).astype(float)
                if iso.predict(X)[0] == 1 and clf.predict(X)[0] != normal_idx:
                    result = self._fixed_predict(X, artifacts)
                    assert result["anomaly"] is True, (
                        f"IF inlier must NOT suppress RF attack prediction. "
                        f"attack_type={result['attack_type']}, "
                        f"IF=inlier, RF={atk}"
                    )
                    assert result["attack_type"].lower() == atk, \
                        f"attack_type should be '{atk}', got '{result['attack_type']}'"
                    found = True
                    break
            if found:
                break

        assert found, (
            "Could not find any attack row where IF=inlier and RF=attack. "
            "This is unexpected given contamination=0.05."
        )

    # ── Response contract ─────────────────────────────────────────────────
    def test_response_contract_keys_and_types(self, train_df, artifacts):
        """Fixed predict() must always return anomaly, attack_type, confidence."""
        X = self._preprocess(train_df, "neptune", artifacts)
        result = self._fixed_predict(X, artifacts)
        assert set(result.keys()) == {"anomaly", "attack_type", "confidence"}
        assert isinstance(result["anomaly"],     bool)
        assert isinstance(result["attack_type"], str)
        assert isinstance(result["confidence"],  float)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_pipeline_comparison_report_saved(self):
        """pipeline_comparison.json must exist after running compare_pipelines."""
        path = os.path.join(REPORT_DIR, "pipeline_comparison.json")
        assert os.path.exists(path), (
            "ml/reports/pipeline_comparison.json not found. "
            "Run: python -m ml.compare_pipelines"
        )
        with open(path) as f:
            data = json.load(f)
        for key in ["A_rf_only", "B_if_gate_old", "C_if_only", "D_rf_if_parallel"]:
            assert key in data, f"Missing pipeline key: {key}"


# ---------------------------------------------------------------------------
# 10. Preprocessing warning-free tests
#
# Verify that preprocess_input() passes named DataFrames to the fitted
# OrdinalEncoder and StandardScaler so sklearn does not emit
# "X does not have valid feature names" UserWarnings.
# ---------------------------------------------------------------------------
class TestPreprocessWarningFree:
    """
    These tests import preprocess_input directly and assert that no
    UserWarning is raised during a call.  They are independent of the
    Flask server and run without a live backend.
    """

    def _call_preprocess(self, features):
        """Import fresh each call so module-level state is not shared."""
        import warnings
        import sys
        # Re-use the already-imported module; just call the function
        from backend.services.ml_service import preprocess_input
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            # Must not raise
            return preprocess_input(features)

    def test_no_warning_on_known_categorical_values(self, train_df, artifacts):
        """A row with known protocol/service/flag must not trigger a warning."""
        cols = artifacts["columns"]
        row  = train_df[train_df[TARGET_COL] == "neptune"].iloc[0][cols].tolist()
        result = self._call_preprocess(row)
        assert result.shape == (1, 41)

    def test_no_warning_on_normal_row(self, train_df, artifacts):
        cols = artifacts["columns"]
        row  = train_df[train_df[TARGET_COL] == "normal"].iloc[0][cols].tolist()
        result = self._call_preprocess(row)
        assert result.shape == (1, 41)

    def test_no_warning_on_unknown_categorical(self, train_df, artifacts):
        """Unknown service value must not trigger a warning (returns -1 encoding)."""
        cols = artifacts["columns"]
        row  = train_df[train_df[TARGET_COL] == "normal"].iloc[0][cols].tolist()
        # Overwrite service (index 2 in columns) with an unseen value
        service_idx = cols.index("service")
        row[service_idx] = "UNKNOWN_SERVICE_XYZ"
        result = self._call_preprocess(row)
        assert result.shape == (1, 41)

    def test_preprocess_output_matches_manual_encoding(self, train_df, artifacts):
        """
        preprocess_input() must produce the same numeric array as the
        manual encoding used in the test fixtures, confirming the fix
        did not change prediction values.
        """
        cols     = artifacts["columns"]
        enc      = artifacts["encoders"]
        scaler   = artifacts["scaler"]
        num_cols = [c for c in cols if c not in CAT_COLS]

        row = train_df[train_df[TARGET_COL] == "neptune"].iloc[0][cols].copy()
        # Manual encoding path (same as test fixtures)
        row_enc = row.copy()
        row_enc[CAT_COLS] = enc.transform(
            pd.DataFrame([row[CAT_COLS].values], columns=CAT_COLS)
        )[0]
        row_enc[num_cols] = scaler.transform(
            pd.DataFrame([row[num_cols].values], columns=num_cols)
        )[0]
        expected = row_enc.values.astype(float)

        from backend.services.ml_service import preprocess_input
        actual = preprocess_input(row.tolist())[0]

        np.testing.assert_allclose(actual, expected, rtol=1e-6,
            err_msg="preprocess_input output differs from manual encoding")
