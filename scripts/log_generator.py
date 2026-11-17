import os
import time
import random
import requests
import pandas as pd

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
API_URL = f"{BASE_URL}/predict"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Use only the dataset with known attack classes (those the model was trained on)
CSV_PATH = os.path.join(BASE_DIR, "ml", "data", "test_known_only.csv")

# Fall back to full test.csv if filtered version doesn't exist
if not os.path.exists(CSV_PATH):
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
    Generate a single log with realistic attack ratio (~25% attacks, 75% normal)
    and minimal noise to simulate real-world traffic patterns.
    
    Noise strategy:
    - Normal logs: mostly tiny noise (95%) with occasional small perturbations (5%)
    - Attack logs: small noise (85%) with occasional moderate noise (15%)
      This creates realistic variance while preserving attack signatures
    """

    # 75% chance of normal traffic, 25% attack (realistic security scenario)
    if random.random() < 0.75:
        # Normal traffic - use "normal" class only
        attack_type = "normal"
        row = grouped.get_group(attack_type).sample(n=1).iloc[0]
    else:
        # Attack traffic - random attack type (exclude "normal")
        attack_types = [t for t in grouped.groups.keys() if t != "normal"]
        attack_type = random.choice(attack_types)
        row = grouped.get_group(attack_type).sample(n=1).iloc[0]

    features = []

    for val in row[:-1]:  # exclude label
        try:
            val = float(val)

            # 🔥 MINIMAL NOISE for realistic traffic
            if attack_type == "normal":
                # Normal traffic: very minimal noise (95% tiny, 5% small)
                # This simulates legitimate traffic with minor measurement variance
                if random.random() < 0.95:
                    noise = random.uniform(-0.04, 0.04)
                else:
                    noise = random.uniform(-0.12, 0.12)
            else:
                # Attack traffic: small noise (85% mild, 15% moderate)
                # Attacks have more variance due to different attack intensities
                if random.random() < 0.85:
                    noise = random.uniform(-0.08, 0.08)
                else:
                    noise = random.uniform(-0.25, 0.25)

            features.append(val + noise)

        except:
            features.append(val)

    return features

def generate_attack_burst(size=8):
    """
    Simulate attack bursts (real-world scenario where attackers repeat similar actions).
    
    Strategy:
    - Pick a random attack type
    - Generate 'size' logs of that attack type with consistent small noise
    - This simulates coordinated attack attempts (e.g., port scanning, DoS flood)
    """
    attack_types = [t for t in grouped.groups.keys() if t != "normal"]
    attack_type = random.choice(attack_types)
    burst = []

    for _ in range(size):
        row = grouped.get_group(attack_type).sample(n=1).iloc[0]

        features = []
        for val in row[:-1]:
            try:
                val = float(val)
                # Small consistent noise for burst (simulates repeated similar actions)
                noise = random.uniform(-0.15, 0.15)
                features.append(val + noise)
            except:
                features.append(val)

        burst.append(features)

    return burst

def start_log_generator(interval=1):
    """
    Main log generator loop. Runs continuously, generating logs and sending them to the backend.
    
    Behavior:
    - Generates logs at configurable interval (default: 1 second per log)
    - 75% normal traffic, 25% attacks
    - Occasional attack bursts (10% chance every 5-10 logs)
    - Prints statistics every 50 logs
    """
    print(f"[*] Starting log generator (interval={interval}s)")
    print(f"[*] Target API: {API_URL}")
    print(f"[*] Dataset: test_known_only.csv (22 known attack types)")
    print(f"[*] Traffic ratio: 75% normal, 25% attacks")
    print(f"[*] Burst probability: 10% (8 consecutive attacks)")
    print()

    count = 0
    normal_count = 0
    attack_count = 0
    burst_count = 0

    while True:
        count += 1

        try:
            # 🔥 Occasionally trigger burst attack (10% chance)
            if random.random() < 0.10:
                burst_logs = generate_attack_burst(size=8)
                burst_count += 1

                for features in burst_logs:
                    requests.post(API_URL, json={"features": features}, timeout=5)
                    attack_count += 1

                print(f"[!] Burst #{burst_count} triggered (8 attacks)")

            else:
                # Normal log (75% normal traffic in long run)
                features = generate_realistic_log()
                response = requests.post(API_URL, json={"features": features}, timeout=5)
                
                # Count based on response if possible
                try:
                    result = response.json()
                    if result.get("anomaly"):
                        attack_count += 1
                    else:
                        normal_count += 1
                except:
                    normal_count += 1

            # Print statistics every 50 logs
            if count % 50 == 0:
                anomaly_rate = (attack_count / count * 100) if count > 0 else 0
                print(f"[*] Total: {count} logs | Normal: {normal_count} | Attacks: {attack_count} | Bursts: {burst_count} | Anomaly Rate: {anomaly_rate:.1f}%")

        except requests.exceptions.Timeout:
            print(f"[!] API timeout - backend may be down")
        except Exception as e:
            print(f"[!] Generator Error: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    start_log_generator(interval=1)
