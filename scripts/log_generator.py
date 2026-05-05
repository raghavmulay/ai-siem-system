import os
import time
import random
import requests
import pandas as pd

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
API_URL = f"{BASE_URL}/predict"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "ml", "data", "test.csv")

df = pd.read_csv(CSV_PATH)

# Separate features and label
label_col = df.columns[-1]
features_df = df.iloc[:, :-1]
labels = df[label_col]

# Group by attack type for balanced sampling
grouped = df.groupby(label_col)

print(f"[+] Loaded dataset with {len(df)} rows and {len(grouped)} attack types")

def generate_realistic_log():
    """
    Generate a single log with balanced attack distribution
    """

    # 🔥 Balanced sampling across attack types
    attack_type = random.choice(list(grouped.groups.keys()))
    row = grouped.get_group(attack_type).sample(n=1).iloc[0]

    features = []

    for val in row[:-1]:  # exclude label
        try:
            val = float(val)

            # 🔥 MIX: normal vs strong anomaly
            if random.random() < 0.3:
                noise = random.uniform(-2, 2)   # strong anomaly
            else:
                noise = random.uniform(-0.1, 0.1)  # normal traffic

            features.append(val + noise)

        except:
            features.append(val)

    return features

def generate_attack_burst(size=10):
    """
    Simulate attack bursts (real-world scenario)
    """
    attack_type = random.choice(list(grouped.groups.keys()))
    burst = []

    for _ in range(size):
        row = grouped.get_group(attack_type).sample(n=1).iloc[0]

        features = []
        for val in row[:-1]:
            try:
                val = float(val)
                noise = random.uniform(-1.5, 1.5)
                features.append(val + noise)
            except:
                features.append(val)

        burst.append(features)

    return burst

def start_log_generator(interval=1):
    print(f"[*] Starting log generator (interval={interval}s)")
    print(f"[*] Sending logs to: {API_URL}")

    count = 0

    while True:
        count += 1

        try:
            # 🔥 Occasionally trigger burst attack
            if random.random() < 0.15:
                print("[!] Attack burst triggered")

                burst_logs = generate_attack_burst(size=8)

                for features in burst_logs:
                    requests.post(API_URL, json={"features": features}, timeout=5)

                print("[!] Burst completed")

            else:
                # Normal log
                features = generate_realistic_log()
                requests.post(API_URL, json={"features": features}, timeout=5)

            if count % 10 == 0:
                print(f"[*] Sent {count} logs")

        except Exception as e:
            print(f"[!] Generator Error: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    start_log_generator(interval=1)