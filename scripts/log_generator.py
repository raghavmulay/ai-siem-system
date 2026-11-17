import os
import time
import random
import requests
import pandas as pd
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

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

def create_session():
    """Create requests session with retry logic"""
    session = requests.Session()
    retry = Retry(
        total=10,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    return session

def generate_realistic_log(session):
    """
    Generate a single log with realistic attack ratio (20% attacks, 80% normal)
    """

    # 80% chance of normal traffic, 20% attack
    if random.random() < 0.80:
        # Normal traffic - use "normal" class only
        attack_type = "normal"
        row = grouped.get_group(attack_type).sample(n=1).iloc[0]
    else:
        # Attack traffic - random attack type (exclude "normal")
        attack_types = [t for t in grouped.groups.keys() if t != "normal"]
        attack_type = random.choice(attack_types)
        row = grouped.get_group(attack_type).sample(n=1).iloc[0]

    features = []

    for i, val in enumerate(row[:-1]):  # exclude label
        try:
            val = float(val)

            # 🔥 INCREASED NOISE for better attack differentiation
            if attack_type == "normal":
                # Normal traffic: small noise (90% minimal, 10% moderate)
                if random.random() < 0.90:
                    noise = random.uniform(-0.1, 0.1)
                else:
                    noise = random.uniform(-0.3, 0.3)
            else:
                # Attack traffic: moderate noise (80% mild, 20% strong)
                if random.random() < 0.80:
                    noise = random.uniform(-0.3, 0.3)
                else:
                    noise = random.uniform(-0.8, 0.8)

            features.append(val + noise)

        except:
            # Keep categorical values as strings (they get encoded later)
            features.append(val)

    try:
        response = session.post(API_URL, json={"features": features}, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[!] Generator Error: {e}")
        return False

def generate_attack_burst(session, size=10):
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
                # 🔥 INCREASED NOISE for burst attacks
                noise = random.uniform(-1.0, 1.0)
                features.append(val + noise)
            except:
                features.append(val)

        burst.append(features)

    return burst

def start_log_generator(interval=3):
    print(f"[*] Starting log generator (interval={interval}s)")
    print(f"[*] Sending logs to: {API_URL}")
    
    # Wait for backend to be ready
    print("[*] Waiting for backend to be ready...")
    session = create_session()
    
    for i in range(30):  # Wait up to 15 seconds
        try:
            response = session.get(f"{BASE_URL}/", timeout=2)
            if response.status_code == 200:
                print("[OK] Backend is ready!")
                break
        except:
            pass
        time.sleep(0.5)
    else:
        print("[!] Warning: Backend might not be ready")

    count = 0

    while True:
        count += 1

        try:
            # 🔥 Occasionally trigger burst attack
            if random.random() < 0.15:
                print("[!] Attack burst triggered")

                burst_logs = generate_attack_burst(session, size=8)

                for features in burst_logs:
                    session.post(API_URL, json={"features": features}, timeout=5)

                print("[!] Burst completed")

            else:
                # Normal log
                generate_realistic_log(session)

            if count % 10 == 0:
                print(f"[*] Sent {count} logs")

        except Exception as e:
            print(f"[!] Generator Error: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    start_log_generator(interval=3)
