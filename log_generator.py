import time
import random
import requests
import pandas as pd

API_URL = "http://127.0.0.1:5000/predict"

df = pd.read_csv("ml/data/test.csv")
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


count = 0

while True:
    count += 1

    features = generate_realistic_log()

    try:
        response = requests.post(API_URL, json={
            "features": features
        })

        print(f"\nLog #{count}")
        print(response.json())

    except Exception as e:
        print("Error:", e)

    time.sleep(2)