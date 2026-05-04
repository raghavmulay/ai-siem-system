# AI SIEM System: Complete Deployment Guide

This document provides a step-by-step guide to deploying and running the AI SIEM System.

## Architecture & Project Structure
The project is organized for clean separation of concerns:
- **`backend/`**: Flask API and ML inference logic.
- **`frontend/`**: React/Vite dashboard.
- **`ml/`**: Model training and data preprocessing.
- **`scripts/`**: Standalone utility and simulation scripts (e.g., `log_generator.py`).
- **`docs/`**: Documentation (including this guide).

---

## 1. Local Development Setup

### Backend
1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Set environment variables in a `.env` file (see `.env.example`).
4. Run: `python run.py`.

### Frontend
1. Navigate to `frontend/`.
2. Install: `npm install`.
3. Run: `npm run dev`.

---

## 2. Production Deployment (Cloud)

### Database (MongoDB Atlas)
1. Create a free-tier cluster.
2. Obtain your `MONGO_URI` (ensure your IP or `0.0.0.0/0` is allowed).

### Backend (Render)
1. Connect your GitHub repository to a new **Web Service**.
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `gunicorn "backend.app:app"`
4. **Env Vars**: Add `MONGO_URI` and `PORT` (usually 10000).

### Frontend (Vercel)
1. Import your repository.
2. Set **Root Directory** to `frontend`.
3. **Env Vars**: Add `VITE_API_URL` (pointing to your Render backend).

---

## 3. Traffic Simulation
The system is equipped with an **Integrated Log Generator** that starts automatically with the backend.
- **Manual Simulation (Optional)**: If you need to generate specific logs or run coordinated attacks:
  - `python scripts/log_generator.py` (Standard Logs)
  - `python scripts/anomaly_generator.py` (Attack Chains)

---

## 4. Verification
1. Open the Vercel dashboard URL.
2. Check that the "System Status" is active.
3. Observe real-time log updates in the logs table. **Logs will begin populating automatically as soon as the backend is running.**
