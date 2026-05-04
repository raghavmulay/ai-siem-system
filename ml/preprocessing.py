import os
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder, StandardScaler


def preprocess(train_df, test_df):
    print("Starting preprocessing...")

    combined = pd.concat([train_df, test_df])

    encoders = {}

    # Encode categorical feature columns
    for col in combined.select_dtypes(include=["object"]).columns:
        if col != "labels":
            le = LabelEncoder()
            combined[col] = le.fit_transform(combined[col])
            encoders[col] = le

    # Encode target column & save its encoder for decoding at inference
    target_encoder = LabelEncoder()
    combined["labels"] = target_encoder.fit_transform(combined["labels"])

    # Split back
    train = combined[: len(train_df)]
    test  = combined[len(train_df):]

    X_train = train.drop("labels", axis=1)
    y_train = train["labels"]
    X_test  = test.drop("labels", axis=1)
    y_test  = test["labels"]

    final_columns = X_train.columns.tolist()

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    # Save preprocessing artefacts
    model_dir = "backend/models"
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(encoders,        os.path.join(model_dir, "encoders.pkl"))
    joblib.dump(scaler,          os.path.join(model_dir, "scaler.pkl"))
    joblib.dump(final_columns,   os.path.join(model_dir, "columns.pkl"))
    joblib.dump(target_encoder,  os.path.join(model_dir, "label_encoder.pkl"))  # ← NEW

    print("Preprocessing done. label_encoder.pkl saved.")

    return X_train, X_test, y_train, y_test