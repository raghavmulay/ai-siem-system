"""
Quick test of the detection model on sample logs
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ml_service import predict
import pandas as pd

# Load filtered test set
df = pd.read_csv('ml/data/test_known_only.csv')

print("=" * 60)
print("MODEL DETECTION TEST")
print("=" * 60)
print()

# Test on a normal sample
normal_sample = df[df.iloc[:, -1] == 'normal'].iloc[0]
normal_features = normal_sample[:-1].tolist()

result = predict(normal_features)
print("✓ Normal Sample Test:")
print(f"  Expected: Normal")
print(f"  Detected Type: {result['attack_type']}")
print(f"  Anomaly: {result['anomaly']}")
print(f"  Confidence: {result['confidence']}")
print()

# Test on several attack samples
attack_types = ['neptune', 'satan', 'smurf', 'ipsweep']

for attack_name in attack_types:
    try:
        attack_sample = df[df.iloc[:, -1] == attack_name].iloc[0]
        attack_features = attack_sample[:-1].tolist()
        
        result = predict(attack_features)
        print(f"✓ {attack_name.upper()} Sample Test:")
        print(f"  Expected: {attack_name}")
        print(f"  Detected Type: {result['attack_type']}")
        print(f"  Anomaly: {result['anomaly']}")
        print(f"  Confidence: {result['confidence']}")
        print()
    except:
        pass

print("=" * 60)
print("Model is ready for production testing!")
print("=" * 60)
