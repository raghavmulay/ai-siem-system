# AI-SIEM System 🛡️

AI-SIEM (Security Information and Event Management) is a modern, machine learning-powered security monitoring system. It analyzes network logs in real-time to detect, classify, and alert on various types of cyber attacks, such as Neptune, Smurf, Portsweep, and more.

## 🚀 Features
- **Real-time Threat Detection**: Classifies network traffic using advanced ML models.
- **Interactive Dashboard**: Visualizes alerts, attack distribution, and system logs.
- **Automated Log Generation**: Tooling to simulate network traffic for testing.
- **Extensible Architecture**: Easy to integrate new models and data sources.

---

## 🛠️ Prerequisites
- **Python**: 3.9+ 
- **Node.js**: 18+ (with npm)

---

## 🏗️ Installation Guide

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/ai-siem-system.git
cd ai-siem-system
```

### 2. Backend Setup (Flask + ML)
The backend handles log processing and ML inference.

1. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate the Virtual Environment**:
   - **Windows**:
     ```bash
     .\venv\Scripts\activate
     ```
   - **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Environment**: (Optional, check `.env` in `backend/`)
   ```bash
   # Make sure any necessary environment variables are set in backend/.env
   ```

### 3. Frontend Setup (React + Vite)
The frontend provides the security dashboard.

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

---

## 🚦 Usage

### 1. Start the Backend
From the **root directory** (with venv activated):
```bash
python -m backend.app
```
The server will start at `http://localhost:5000`.

### 2. Start the Frontend
From the `frontend` directory:
```bash
npm run dev
```
The dashboard will be available at `http://localhost:5173`.

### 3. Generate Sample Logs
To test the system's detection capabilities, run the log generator from the root:
```bash
python log_generator.py
```

---

## 🧠 Machine Learning
- **Preprocessing**: Data cleaning and feature engineering are handled in `ml/preprocessing.py`.
- **Training**: Re-train models using `ml/train_model.py`.
- **Classification**: Real-time inference services are located in `backend/services/`.

---

## 📁 Project Structure
- `backend/`: Flask server, routes, and services.
- `frontend/`: React application (Vite-based).
- `ml/`: Model training and data preprocessing scripts.
- `log_generator.py`: Utility for simulating network events.
- `requirements.txt`: Python package dependencies.

---

## 🔧 Technologies Used
- **Frontend**: React, Vite, Recharts, CSS3.
- **Backend**: Python, Flask.
- **ML**: Scikit-learn, Pandas, NumPy, Matplotlib.
- **Testing**: Python-driven log simulation.

---

Developed with ❤️ for Advanced Security Monitoring.