import os
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder, StandardScaler

def preprocess(train_df, test_df):

    print("Starting preprocessing...")

    # Combine both datasets
    combined = pd.concat([train_df, test_df])

    encoders = {}
    feature_cols = [col for col in combined.columns if col != 'labels']

    # Encode categorical columns
    for col in combined.select_dtypes(include=['object']).columns:
        if col != 'labels':  # target column
            le = LabelEncoder()
            combined[col] = le.fit_transform(combined[col])
            encoders[col] = le

    # Encode target
    target_encoder = LabelEncoder()
    combined['labels'] = target_encoder.fit_transform(combined['labels'])

    # Split back
    train = combined[:len(train_df)]
    test = combined[len(train_df):]

    # Features & labels
    X_train = train.drop('labels', axis=1)
    y_train = train['labels']

    X_test = test.drop('labels', axis=1)
    y_test = test['labels']

    # Keep track of the columns before scaling returns numpy arrays
    final_columns = X_train.columns.tolist()

    # Scaling
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # Save preprocessing objects
    model_dir = "backend/models"
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(encoders, os.path.join(model_dir, "encoders.pkl"))
    joblib.dump(scaler, os.path.join(model_dir, "scaler.pkl"))
    joblib.dump(final_columns, os.path.join(model_dir, "columns.pkl"))

    print("Preprocessing Done ✅")

    return X_train, X_test, y_train, y_test