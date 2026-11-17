# AI-SIEM — Intelligent Security Information & Event Management System

A full-stack, production-ready SIEM platform that uses machine learning to detect network intrusions in real time. Built with a Python/Flask backend, React/Vite frontend, MongoDB Atlas for persistence, and dual ML models (RandomForest + IsolationForest) trained on the KDD Cup 1999 dataset.

---

## Live Demo

| Service | URL |
|---|---|
| Dashboard (Vercel) | https://ai-siem-system.vercel.app |
| API (Render) | https://ai-siem-backend.onrender.com |

> The Render free tier sleeps after 15 minutes of inactivity. The first request after sleep takes ~30 seconds to wake up — this is expected.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [ML Models](#ml-models)
5. [Project Structure](#project-structure)
6. [Local Setup](#local-setup)
7. [Environment Variables](#environment-variables)
8. [API Reference](#api-reference)
9. [Deployment](#deployment)
10. [Tech Stack](#tech-stack)

---

## Overview

Traditional SIEM systems rely on static rule sets. This system uses machine learning to classify network traffic into 22 known attack types and flag anomalies — including novel patterns that rules would miss.

The log generator simulates a realistic network environment:
- **75%** normal traffic
- **25%** attacks across 22 types
- **10%** chance of coordinated attack bursts (8 consecutive events)

The backend starts the log generator automatically on launch. No separate process needed.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           Browser (React + Vite)            │
│  Dashboard  ·  Charts  ·  Alerts  ·  Logs  │
└──────────────────┬──────────────────────────┘
                   │ HTTP (every 3s)
                   ▼
┌─────────────────────────────────────────────┐
│          Flask Backend (Gunicorn)           │
│  /predict  /logs  /alerts  /attack-chains  │
└───────┬────────────────────┬────────────────┘
        │                    │
        ▼                    ▼
┌───────────────┐   ┌────────────────────────┐
│  ML Models    │   │   MongoDB Atlas        │
│  RandomForest │   │   logs · alerts        │
│  IsolationFor │   │   attack chains        │
└───────────────┘   └────────────────────────┘
        ▲
        │
┌───────────────────────────────────────────┐
│   Log Generator (background thread)      │
│   Samples from test_known_only.csv        │
│   75% normal · 25% attacks · 10% bursts  │
└───────────────────────────────────────────┘
```

---

## Features

- **Real-time detection** — logs processed and classified every 2 seconds
- **Dual ML pipeline** — RandomForest for classification, IsolationForest as supplementary anomaly signal
- **22 attack types** — neptune, satan, smurf, ipsweep, portsweep, back, teardrop, and 15 more
- **Attack chain analysis** — detects coordinated multi-step attack patterns in a 10-minute window
- **Severity scoring** — CRITICAL / HIGH / MEDIUM / LOW per alert
- **Dark / Light theme** — toggle in the header, persists for the session
- **Responsive dashboard** — works on desktop and tablet
- **Auto log generation** — realistic traffic simulation starts with the backend

---

## ML Models

### Dataset
KDD Cup 1999 network intrusion dataset, filtered and balanced:
- **Training set**: 50% normal, 50% attacks (balanced to reduce false positives)
- **Attack classes**: 22 known types (14 rare/unseen classes excluded)
- **Features**: 41 network connection attributes

### Pipeline

```
Raw features (41)
      │
      ▼
OrdinalEncoder   ← protocol_type, service, flag
StandardScaler   ← all numeric features
      │
      ├──▶ RandomForestClassifier  → attack_type (22 classes)
      │                            → confidence score
      │
      └──▶ IsolationForest         → supplementary anomaly flag
```

**Detection rule:**
```
anomaly = True  if  RF predicts attack  OR  IsolationForest flags outlier
anomaly = False only when both agree the traffic is normal
```

### Performance

| Metric | Value |
|---|---|
| Accuracy | 96.27% |
| Macro F1 | 69.88% |
| Weighted F1 | 94.75% |
| Binary False Positive Rate | 0.71% |
| Binary True Positive Rate | 93.0% |
| Training samples | 21,398 |
| Known attack classes | 22 |

Confidence scores on clean test samples:

| Sample | Expected | Detected | Confidence |
|---|---|---|---|
| Normal | normal | Normal | 99.3% |
| Neptune | neptune | neptune | 100% |
| Satan | satan | satan | 97.8% |
| Smurf | smurf | smurf | 100% |
| Ipsweep | ipsweep | ipsweep | 99.9% |

---

## Project Structure

```
ai-siem-system/
│
├── backend/
│   ├── app.py                  # Flask app, starts log generator thread
│   ├── config/
│   │   └── db_config.py        # MongoDB connection
│   ├── models/
│   │   ├── load_models.py      # Model loader
│   │   ├── classifier.pkl      # RandomForest (47 MB)
│   │   ├── anomaly.pkl         # IsolationForest
│   │   ├── encoders.pkl        # OrdinalEncoder
│   │   ├── scaler.pkl          # StandardScaler
│   │   ├── label_encoder.pkl   # Class label decoder
│   │   └── columns.pkl         # Feature column order
│   ├── routes/
│   │   ├── predict.py          # POST /predict
│   │   ├── logs.py             # GET /logs, DELETE /clear
│   │   ├── alerts.py           # GET /alerts
│   │   └── attack_chains.py    # GET /attack-chains
│   └── services/
│       └── ml_service.py       # Inference logic
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main dashboard component
│   │   ├── index.css           # Dark/light theme, all styles
│   │   └── main.jsx            # React entry point
│   ├── vercel.json             # SPA rewrite rule for Vercel
│   ├── vite.config.js
│   └── package.json
│
├── ml/
│   ├── train_model.py          # Training script
│   ├── data/
│   │   └── test_known_only.csv # 21,398 rows, 22 known attack types
│   └── reports/
│       ├── metrics.json        # Accuracy, F1, FPR, TPR
│       └── classification_report.txt
│
├── scripts/
│   ├── log_generator.py        # Traffic simulator (auto-started by backend)
│   ├── filter_test_data.py     # Utility: filter test.csv to known classes
│   └── test_detection.py       # Quick model sanity check
│
├── .env                        # Backend secrets (not committed)
├── .env.example                # Template for .env
├── requirements.txt            # Python dependencies
├── runtime.txt                 # python-3.12.7
├── Procfile                    # Gunicorn start command
├── render.yaml                 # Render deployment config
└── run.py                      # Local dev entry point
```

---

## Local Setup

### Prerequisites

- Python 3.12.x
- Node.js 18+
- A MongoDB Atlas cluster (free tier works)

### 1. Clone the repo

```bash
git clone https://github.com/raghavmulay/ai-siem-system.git
cd ai-siem-system
```

### 2. Create Python virtual environment

```powershell
python -m venv venv_clean
.\venv_clean\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net
```

Create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:5000
```

### 4. Start the backend

```powershell
# From project root with venv active
python run.py
```

Expected output:
```
MongoDB connected & indexes ensured
[+] Loaded dataset with 21398 rows and 22 attack types
[*] Starting log generator (interval=2s)
[*] Target API: http://127.0.0.1:5000/predict
[*] Traffic ratio: 75% normal, 25% attacks
```

### 5. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open: **http://localhost:5173** (or the port Vite prints)

### 6. Verify model detection (optional)

```powershell
# From project root with venv active
python scripts/test_detection.py
```

---

## Environment Variables

### Backend (`.env` in project root)

| Variable | Description | Required |
|---|---|---|
| `MONGO_URI` | MongoDB Atlas connection string | Yes |

### Frontend (`frontend/.env`)

| Variable | Description | Required |
|---|---|---|
| `VITE_API_URL` | Backend base URL | Yes |

For local dev: `http://127.0.0.1:5000`  
For production: `https://ai-siem-backend.onrender.com`

---

## API Reference

All endpoints return JSON.

### `POST /predict`

Classify a single network connection.

**Request body:**
```json
{ "features": [0, "tcp", "http", "SF", 215, 45076, 0, 0, ...] }
```
41 feature values in KDD Cup column order. Categorical columns (`protocol_type`, `service`, `flag`) may be strings or encoded integers.

**Response:**
```json
{
  "anomaly": true,
  "attack_type": "neptune",
  "confidence": 0.9978
}
```

---

### `GET /logs`

Returns the latest 500 log entries, newest first.

```json
[
  {
    "_id": "...",
    "timestamp": "2025-01-15T10:30:00Z",
    "anomaly": true,
    "attack_type": "neptune",
    "confidence": 0.9978,
    "severity": "HIGH"
  }
]
```

---

### `GET /alerts`

Returns the latest 100 alerts (anomalous events only).

```json
[
  {
    "_id": "...",
    "timestamp": "2025-01-15T10:30:00Z",
    "severity": "HIGH",
    "attack_type": "neptune",
    "confidence": 0.9978,
    "message": "neptune attack detected"
  }
]
```

---

### `GET /attack-chains`

Returns coordinated attack patterns detected in the last 10 minutes.

```json
{
  "chains": [
    {
      "pattern": "Probe → DoS",
      "severity": "CRITICAL",
      "steps": ["ipsweep", "neptune"],
      "log_count": 12,
      "first_seen": "2025-01-15T10:25:00Z",
      "last_seen": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

### `DELETE /clear`

Clears all logs, alerts, and attack chains from the database.

```json
{ "message": "cleared" }
```

---

## Deployment

### Backend → Render

1. Go to [render.com](https://render.com) and create a new **Web Service**
2. Connect the GitHub repo `raghavmulay/ai-siem-system`
3. Use these settings:

| Field | Value |
|---|---|
| Root Directory | *(blank)* |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn backend.app:app --workers 1 --threads 2 --timeout 120` |
| Instance Type | Free |

4. Add environment variable:
   - `MONGO_URI` → your Atlas connection string

5. Deploy. Note the URL — you will need it for the frontend.

---

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) and import the same GitHub repo
2. Set **Root Directory** to `frontend`
3. Framework preset: **Vite**
4. Add environment variable:
   - `VITE_API_URL` → `https://your-service.onrender.com`

5. Deploy.

---

### MongoDB Atlas — allow Render's IP

In Atlas → **Network Access** → **Add IP Address** → **Allow Access from Anywhere** (`0.0.0.0/0`).

---

### Auto-deploy on push

Both Render and Vercel watch the `main` branch. Every `git push origin main` triggers a redeploy of both services automatically.

---

## Tech Stack

### Backend
| Library | Version | Purpose |
|---|---|---|
| Flask | 3.0.3 | Web framework |
| flask-cors | 4.0.1 | Cross-origin requests |
| scikit-learn | 1.4.2 | RandomForest + IsolationForest |
| pandas | 2.2.2 | Data processing |
| numpy | latest | Numerical ops |
| pymongo | 4.7.2 | MongoDB driver |
| gunicorn | 22.0.0 | Production WSGI server |
| joblib | 1.4.2 | Model serialisation |

### Frontend
| Library | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI framework |
| Vite | 5.4.1 | Build tool / dev server |
| Recharts | 3.8.1 | Charts and visualisations |

### Infrastructure
| Service | Purpose |
|---|---|
| MongoDB Atlas | Persistent storage (logs, alerts, chains) |
| Render | Backend hosting (free tier) |
| Vercel | Frontend hosting (free tier) |
| GitHub | Source control + CI/CD trigger |

---

## Retraining the Model

If you want to retrain from scratch with new data:

```powershell
# Place your dataset at ml/data/train.csv and ml/data/test.csv
# Then with venv active:
python ml/train_model.py
```

After training, regenerate the filtered test set:

```powershell
python scripts/filter_test_data.py
```

Models are saved to `backend/models/`. Commit them before deploying.

---

## Authors

Raghav Mulay — VIT Pune, SY · Semester II · Machine Learning Course Project
