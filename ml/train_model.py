import os
import pandas as pd
import joblib

from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# 📁 Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "test.csv")
MODEL_DIR = os.path.abspath(os.path.join(BASE_DIR, "../backend/models"))
os.makedirs(MODEL_DIR, exist_ok=True)


def load_data():
    df = pd.read_csv(DATA_PATH)

    # Split features/label
    X = df.iloc[:, :-1].copy()
    y = df.iloc[:, -1]

    # ---- 1) Encode ALL categorical columns ----
    encoders = {}
    for col in X.columns:
        if X[col].dtype == "object":
            le_col = LabelEncoder()
            X[col] = le_col.fit_transform(X[col].astype(str))
            encoders[col] = le_col

    # ---- 2) Coerce any leftovers to numeric (safety net) ----
    # If any column still has non-numeric junk, this turns it into NaN then fills with 0
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)

    # ---- 3) Encode target BEFORE split ----
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y.astype(str))

    # ---- 4) Split ----
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42
    )

    # Debug sanity (optional)
    print("Any non-numeric left in X_train? ->", not all(pd.api.types.is_numeric_dtype(X_train[c]) for c in X_train.columns))

    return X_train, X_test, y_train, y_test, encoders, label_encoder, X.columns


def train_models(X_train, X_test, y_train, y_test, encoders, label_encoder, columns):
    print("🚀 Training models...")

    # 🔹 Random Forest
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)

    print("\n📊 Classification Results:")
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # 🔹 Isolation Forest
    anomaly_model = IsolationForest(
        contamination=0.05,
        random_state=42,
        n_jobs=-1
    )
    anomaly_model.fit(X_train)
    print("\n🚨 Anomaly Detection Ready")

    # ---- Save artifacts ----
    joblib.dump(anomaly_model, os.path.join(MODEL_DIR, "anomaly.pkl"))
    joblib.dump(clf, os.path.join(MODEL_DIR, "classifier.pkl"))
    joblib.dump(label_encoder, os.path.join(MODEL_DIR, "label_encoder.pkl"))
    joblib.dump(encoders, os.path.join(MODEL_DIR, "encoders.pkl"))
    joblib.dump(list(columns), os.path.join(MODEL_DIR, "columns.pkl"))

    print("\n✅ Models + Encoders saved successfully")


if __name__ == "__main__":
    X_train, X_test, y_train, y_test, encoders, label_encoder, columns = load_data()
    train_models(X_train, X_test, y_train, y_test, encoders, label_encoder, columns)