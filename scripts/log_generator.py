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
            # if it's string, keep as is
            features.append(val)

    return features


def start_log_generator(interval=2):
    """
    Background worker that continuously generates logs.
    """
    print(f"[*] Signal: Starting background log generator (interval={interval}s)")
    count = 0
    while True:
        count += 1
        features = generate_realistic_log()
        try:
            # Use relative URL or hardcoded if internal networking is simple.
            # Localhost is fine since they run on the same machine/server.
            requests.post(API_URL, json={"features": features}, timeout=5)
            if count % 10 == 0:
                print(f"[*] Background Generator: Sent {count} logs total")
        except Exception as e:
            print(f"[!] Background Generator Error: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    # If run standalone, execute with default interval
    start_log_generator()