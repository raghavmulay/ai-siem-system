from flask import Flask
from flask_cors import CORS
from backend.routes.predict import predict_bp
from backend.config.db_config import get_db
from backend.routes.logs import logs_bp
from backend.routes.alerts import alerts_bp

app = Flask(__name__)
CORS(app)

# Verify DB connection
try:
    get_db().command("ping")
    print("✅ MongoDB connected")
except Exception as e:
    print(f"⚠️ MongoDB connection failed: {e}")

# ✅ Register ALL blueprints BEFORE running app
app.register_blueprint(predict_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(alerts_bp)

@app.route("/")
def home():
    return "AI SIEM Backend Running 🚀"

if __name__ == "__main__":
    app.run(debug=True)