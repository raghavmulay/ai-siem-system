import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def get_db():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    return client["siem"]
