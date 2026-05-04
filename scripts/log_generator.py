import os
import time
import random
import requests
import pandas as pd

# Use environment variable for base URL
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
API_URL = f"{BASE_URL}/predict"

# Find project root relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "ml", "data", "test.csv")

df = pd.read_csv(CSV_PATH)
df = df.iloc[:, :-1]

FEATURE_COUNT = len(df.columns)


def generate_realistic_log():
    row = df.sample(n=1).iloc[0]
    features = []

    for val in row:
        try:
            val = float(val)
            noise = random.uniform(-0.05, 0.05)
            features.append(val + noise)
        except:
            features.append(val)

    return features


def start_log_generator(interval=2):
    print(f"[*] Signal: Starting background log generator (interval={interval}s)")
    print(f"[*] Sending logs to: {API_URL}")

    count = 0
    while True:
        count += 1
        features = generate_realistic_log()

        try:
            requests.post(API_URL, json={"features": features}, timeout=5)

            if count % 10 == 0:
                print(f"[*] Background Generator: Sent {count} logs total")

        except Exception as e:
            print(f"[!] Background Generator Error: {e}")

        time.sleep(interval)


if __name__ == "__main__":
    start_log_generator()