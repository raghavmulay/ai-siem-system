from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from backend.config.db_config import get_db
import bcrypt 

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def seed_admin():
    db = get_db()
    if not db["users"].find_one({"username": "admin"}):
        hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt())
        db["users"].insert_one({
            "username": "admin",
            "password": hashed,
            "role": "admin"
        })
        print("Admin user seeded")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").encode()

    db = get_db()
    user = db["users"].find_one({"username": username})

    if not user or not bcrypt.checkpw(password, user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(
        identity=username,
        additional_claims={"role": user["role"]}
    )
    return jsonify({"token": token, "role": user["role"]})
