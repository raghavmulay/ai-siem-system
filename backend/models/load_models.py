import os
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_models():
    anomaly_path = os.path.join(BASE_DIR, "anomaly.pkl")
    classifier_path = os.path.join(BASE_DIR, "classifier.pkl")

    print("Loading models from:", anomaly_path)

    anomaly_model = joblib.load(anomaly_path)
    classifier = joblib.load(classifier_path)

    return anomaly_model, classifier