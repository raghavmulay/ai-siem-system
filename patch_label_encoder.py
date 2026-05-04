"""
patch_label_encoder.py
----------------------
Run this ONCE from the project root if you have existing .pkl models
but are missing label_encoder.pkl.

It reads the classes learned by your RandomForestClassifier and rebuilds
a LabelEncoder that maps  0..N-1 → class names.

Usage:
    python patch_label_encoder.py

If the classifier was trained on numeric labels (ints like 0,1,2,...),
the encoder will map them back to those same integers as strings, which
is still valid.  Re-run ml/main.py to get true string class names.
"""
import os
import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder

BASE = os.path.join("backend", "models")

clf_path = os.path.join(BASE, "classifier.pkl")
out_path = os.path.join(BASE, "label_encoder.pkl")

if not os.path.exists(clf_path):
    print("classifier.pkl not found — run ml/main.py first.")
    raise SystemExit(1)

clf = joblib.load(clf_path)
classes = clf.classes_          # numpy array of class labels the RF knows

le = LabelEncoder()
le.fit(classes)                 # re-creates the encoder with the same classes

joblib.dump(le, out_path)
print(f"Saved label_encoder.pkl  →  classes: {list(classes)}")
print("Done ✅")
