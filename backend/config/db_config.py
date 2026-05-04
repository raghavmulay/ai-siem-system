import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def get_db():
    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        raise ValueError("MONGO_URI is not set in environment variables")

    client = MongoClient(mongo_uri)
    return client["siem"]