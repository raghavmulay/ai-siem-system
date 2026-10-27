import json
import os
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))
DEVICE = torch.device("cpu")


class Autoencoder(nn.Module):
    def __init__(self, input_dim=41, hidden_dims=(32, 16, 8)):
        super().__init__()
        h1, h2, h3 = hidden_dims
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, h1), nn.ReLU(),
            nn.Linear(h1, h2), nn.ReLU(),
            nn.Linear(h2, h3)
        )
        self.decoder = nn.Sequential(
            nn.Linear(h3, h2), nn.ReLU(),
            nn.Linear(h2, h1), nn.ReLU(),
            nn.Linear(h1, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

class AutoencoderService:
    def __init__(self):
        with open(os.path.join(BASE_DIR, "ae_config.json")) as f:
            self.config = json.load(f)

        self.feature_cols = self.config["feature_columns"]
        self.cat_cols = self.config["categorical_columns"]
        self.num_cols = self.config["numerical_columns"]

        self.encoder = joblib.load(os.path.join(BASE_DIR, "ae_encoder.pkl"))
        self.scaler = joblib.load(os.path.join(BASE_DIR, "ae_scaler.pkl"))

        checkpoint = torch.load(
            os.path.join(BASE_DIR, "autoencoder.pt"),
            map_location=DEVICE,
            weights_only=True
        )

        self.model = Autoencoder(
            input_dim=checkpoint["input_dim"],
            hidden_dims=tuple(checkpoint["hidden_dims"])
        ).to(DEVICE)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        self.threshold = float(checkpoint["threshold"])

    def preprocess(self, features):
        if len(features) != len(self.feature_cols):
            raise ValueError(
                f"Expected {len(self.feature_cols)} features, got {len(features)}"
            )

        df = pd.DataFrame([features], columns=self.feature_cols)
        df[self.cat_cols] = df[self.cat_cols].astype(str)

        categorical = self.encoder.transform(df[self.cat_cols])
        numerical = self.scaler.transform(
            df[self.num_cols].astype(float)
        )

        transformed = pd.DataFrame(
            index=[0], columns=self.feature_cols, dtype=float
        )
        transformed[self.cat_cols] = categorical
        transformed[self.num_cols] = numerical

        values = transformed[self.feature_cols].to_numpy(dtype=np.float32)

        if not np.isfinite(values).all():
            raise ValueError("Input contains non-finite values after preprocessing")

        return values

    def predict(self, features):
        values = self.preprocess(features)
        tensor = torch.from_numpy(values).to(DEVICE)

        with torch.no_grad():
            reconstructed = self.model(tensor)
            error = torch.mean((reconstructed - tensor) ** 2).item()

        return {
            "anomaly": bool(error > self.threshold),
            "reconstruction_error": float(error),
            "threshold": self.threshold
        }


_service = None


def predict_autoencoder(features):
    global _service

    if _service is None:
        _service = AutoencoderService()

    return _service.predict(features)
