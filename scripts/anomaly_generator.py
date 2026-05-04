"""
anomaly_generator.py
Sends deliberate attack sequences to trigger multi-step chain detection.
Filters rows by attack type from test.csv and sends them in order.
"""
import os
import time
import random
import requests
import pandas as pd

API_URL = "http://127.0.0.1:5000/predict"

# Find project root relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "ml", "data", "test.csv")

df = pd.read_csv(CSV_PATH)
labels = df.iloc[:, -1]
features_df = df.iloc[:, :-1]

# ── Attack chains to simulate ─────────────────────────────────────────────────
SCENARIOS = [
    {
        "name": "Recon → DoS  (portsweep → neptune)",
        "sequence": ["portsweep", "portsweep", "neptune", "neptune", "neptune"],
    },
    {
        "name": "Probe → Flood  (satan → smurf)",
        "sequence": ["satan", "satan", "smurf", "smurf"],
    },
    {
        "name": "Full Recon → DoS  (ipsweep → portsweep → neptune)",
        "sequence": ["ipsweep", "ipsweep", "portsweep", "neptune", "neptune"],
    },
    {
        "name": "Scan → Exploit  (nmap → back)",
        "sequence": ["nmap", "back", "back"],
    },
]


def get_sample(attack_type: str) -> list:
    """Return a random feature row matching the given attack label."""
    mask = labels.str.lower() == attack_type.lower()
    pool = features_df[mask]
    if pool.empty:
        print(f"  [!] No rows found for '{attack_type}' — skipping")
        return None
    row = pool.sample(n=1).iloc[0]
    features = []
    for val in row:
        try:
            features.append(float(val) + random.uniform(-0.02, 0.02))
        except (ValueError, TypeError):
            features.append(val)
    return features


def run_scenario(scenario: dict, delay: float = 1.5):
    print(f"\n{'='*60}")
    print(f"  Scenario: {scenario['name']}")
    print(f"{'='*60}")

    for step, attack_type in enumerate(scenario["sequence"], 1):
        features = get_sample(attack_type)
        if features is None:
            continue

        try:
            resp = requests.post(API_URL, json={
                "features": features,
                "force_anomaly": {
                    "attack_type": attack_type,
                    "confidence": round(random.uniform(0.82, 0.97), 3)
                }
            }, timeout=5)
            data = resp.json()
            detected = data.get("attack_type", "?")
            anomaly  = data.get("anomaly", False)
            severity = data.get("severity", "?")
            print(
                f"  Step {step:2d} | target={attack_type:<12} "
                f"detected={detected:<12} anomaly={str(anomaly):<5} severity={severity}"
            )
        except Exception as e:
            print(f"  Step {step} | ERROR: {e}")

        time.sleep(delay)


if __name__ == "__main__":
    print("AI-SIEM Anomaly Generator")
    print("Simulating coordinated multi-step attack chains...\n")

    for scenario in SCENARIOS:
        run_scenario(scenario, delay=1.2)
        time.sleep(3)   # pause between scenarios

    print("\n✅ Done. Check /attack-chains or the dashboard for detected patterns.")
