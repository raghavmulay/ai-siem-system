import joblib
import os

BASE = os.path.dirname(__file__)

anomaly_model = joblib.load(os.path.join(BASE, "anomaly.pkl"))
classifier = joblib.load(os.path.join(BASE, "classifier.pkl"))
