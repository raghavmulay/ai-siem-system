"""
Filter test.csv to only include attack classes that the model was trained on.
This ensures the log generator only produces samples the model has seen during training.
"""

import pandas as pd
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CSV = os.path.join(BASE_DIR, "ml", "data", "test.csv")
METRICS_JSON = os.path.join(BASE_DIR, "ml", "reports", "metrics.json")
OUTPUT_CSV = os.path.join(BASE_DIR, "ml", "data", "test_known_only.csv")

# Load full test set
df = pd.read_csv(TEST_CSV)
print(f"[+] Original test set: {len(df)} rows")
print(f"[+] Unique attack types: {df.iloc[:, -1].nunique()}")

# Load trained class labels to know which attack types the model knows
with open(METRICS_JSON) as f:
    metrics = json.load(f)
    unseen = set(metrics["unseen_classes"])

print(f"[+] Unseen classes (excluded from training): {unseen}")

# Filter to only known classes
df_filtered = df[~df.iloc[:, -1].isin(unseen)]
print(f"[+] Filtered test set (only known classes): {len(df_filtered)} rows")

# Show class distribution
print("\n[+] Class distribution in filtered test set:")
print(df_filtered.iloc[:, -1].value_counts().to_string())

# Save as new file for log generator
df_filtered.to_csv(OUTPUT_CSV, index=False)
print(f"\n[+] Saved to {OUTPUT_CSV}")
print(f"[+] Now update log_generator.py to use test_known_only.csv")
