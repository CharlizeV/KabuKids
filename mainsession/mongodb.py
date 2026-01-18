import os
import certifi
import uuid
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ReturnDocument

uri = os.getenv("MONGODB_URI", "mongodb+srv://kabu_db_user:pass101pass101@cluster0.kxhmgjt.mongodb.net/?appName=Cluster0")

client = MongoClient(
    uri,
    server_api=ServerApi("1"),
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=20000,
)

db = client["kabu_db_user"]
children_col = db["Children"]
meals_col = db["Meals"]
counters_col = db["counters"]

def _get_next_sequence(name: str) -> int:
    doc = counters_col.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])

def _format_numeric_id(seq: int, width: int = 4) -> str:
    return f"{seq:0{width}d}"

def insert_meal(meal_doc: dict, width: int = 4) -> str:
    if meal_doc.get("_id"):
        meal_doc["_id"] = str(meal_doc["_id"])
    else:
        meal_doc["_id"] = str(uuid.uuid4())

    meals_col.insert_one(meal_doc)
    return str(meal_doc["_id"])

def insert_child(child_doc: dict, width: int = 4) -> str:
    seq = _get_next_sequence("child")
    user_id = _format_numeric_id(seq, width=width)
    child_doc.setdefault("user_id", user_id)
    children_col.insert_one(child_doc)
    return user_id

def find_meal(meal_id: str) -> dict | None:
    try:
        meal_document = meals_col.find_one({"_id": meal_id})
        return meal_document
    except ValueError:
        return None

def init_counter(name: str, start: int = 0) -> None:
    counters_col.update_one({"_id": name}, {"$setOnInsert": {"seq": int(start)}}, upsert=True)

def get_child_by_id(user_id: str) -> dict | None:
    try:
        user_information = children_col.find_one({"_id": user_id})
        return user_information
    except ValueError:
        return None
