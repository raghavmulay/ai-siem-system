import os
import sys
import threading
import time
import subprocess
import signal
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

def start_backend():
    """Start the Flask backend server"""
    print_section("[START] AI SIEM SYSTEM")
    print("Starting backend server...")
    
    from backend.app import app
    
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=False)


def start_log_generator(interval=1):
    """Simulate network traffic and send to backend"""
    import random
    import requests
    import pandas as pd
    
    BASE_DIR = Path(__file__).parent.resolve()
    CSV_PATH = BASE_DIR / "ml" / "data" / "test.csv"
    
    df = pd.read_csv(CSV_PATH)
    label_col = df.columns[-1]
    features_df = df.iloc[:, :-1]
    
    grouped = df.groupby(label_col)
    API_URL = "http://127.0.0.1:5000/predict"
    
    count = 0
    
    while True:
        try:
            # Occasionally trigger burst attack
            if random.random() < 0.15:
                attack_type = random.choice(list(grouped.groups.keys()))
                for _ in range(8):
                    row = grouped.get_group(attack_type).sample(n=1).iloc[0]
                    features = []
                    for val in row[:-1]:
                        try:
                            val = float(val)
                            noise = random.uniform(-1.5, 1.5)
                            features.append(val + noise)
                        except:
                            features.append(val)
                    requests.post(API_URL, json={"features": features}, timeout=3)
            
            else:
                attack_type = random.choice(list(grouped.groups.keys()))
                row = grouped.get_group(attack_type).sample(n=1).iloc[0]
                features = []
                for val in row[:-1]:
                    try:
                        val = float(val)
                        noise = random.uniform(-0.1, 0.1) if random.random() < 0.3 else random.uniform(-0.1, 0.1)
                        features.append(val + noise)
                    except:
                        features.append(val)
                requests.post(API_URL, json={"features": features}, timeout=3)
            
            count += 1
            if count % 10 == 0:
                print(f"  [LOG] Sent {count} logs")
                
        except Exception as e:
            pass  # Silent fail if backend not ready
        
        time.sleep(interval)


def start_frontend():
    """Start the Vite development server"""
    print_section("[START] Frontend (React + Vite)")
    
    frontend_dir = BASE_DIR / "frontend"
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("[!] node_modules not found. Installing dependencies...")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
            print("[OK] Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install dependencies: {e}")
            return
    
    # Start Vite dev server
    try:
        print("  Starting Vite dev server...")
        subprocess.run(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Frontend failed to start: {e}")


def main():
    """Main entry point - starts backend only (frontend requires separate terminal)"""
    print_section("[AI SIEM SYSTEM]")
    print("Starting backend server...")
    
    # Check if in virtual environment
    if "venv" not in sys.prefix:
        print("\n[WARNING] Not running in virtual environment!")
        print("Please activate venv first:")
        print("  .\\venv\\Scripts\\Activate.ps1")
        print("  python run.py\n")
        return
    
    start_backend()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Complete. Goodbye!")
        sys.exit(0)
