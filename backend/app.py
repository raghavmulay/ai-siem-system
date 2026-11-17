from flask import Flask
from flask_cors import CORS
from backend.routes.predict import predict_bp
from backend.routes.logs import logs_bp
from backend.routes.alerts import alerts_bp
from backend.routes.attack_chains import attack_chains_bp
from backend.config.db_config import get_db

import os
import threading
from scripts.log_generator import start_log_generator

app = Flask(__name__)
CORS(app)

# Try MongoDB connection, but don't fail if it's unavailable
try:
    db = get_db()
    db.command("ping")
    db["logs"].create_index([("timestamp", -1), ("attack_type", 1)], background=True)
    print("✅ MongoDB connected & indexes ensured")
except Exception as e:
    print(f"⚠️ MongoDB not available (using in-memory mode): {e}")
    db = None

# Routes
app.register_blueprint(predict_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(attack_chains_bp)

@app.route("/")
def home():
    return "AI SIEM Backend Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))