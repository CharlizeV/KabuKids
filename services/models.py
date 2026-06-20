import uuid
import traceback
from datetime import datetime
from typing import Dict, Any, Callable

# import the Mongo collections
from db import meals_col

SAMPLE_REPORTS: Dict[str, Any] = {}
CURRENT_MEAL: Dict[str, Any] = {}

def init_current_meal(user_id=None):
    global CURRENT_MEAL
    CURRENT_MEAL = {
        "_id": str(uuid.uuid4()),
        "user_id": str(user_id) if user_id else "",
        "date": "",
        "start_time": "",
        "end_time": "",
        "transcript": [],
        "summary": "",
        "conversation_suggestions": [],
        "ingredient_suggestions": [],
        "food_before_meal": [],
        "food_not_finished": [],
        "portion_before_image": "",
        "portion_after_image": "",
        "created_at": datetime.utcnow(),
    }

def clear_current_meal():
    global CURRENT_MEAL
    CURRENT_MEAL = {}


def get_logged_in_user_id(current_user) -> str:
    """Return the MongoDB Children _id for the logged-in user (consistent everywhere)."""
    if not current_user:
        return ""
    try:
        if isinstance(current_user, dict):
            uid = current_user.get("_id")
        else:
            uid = getattr(current_user, "_id", None)
        return str(uid) if uid is not None else ""
    except Exception:
        return ""

def fetch_reports_for_user(user_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
    try:
        if not user_id:
            print("[services.models] fetch_reports_for_user: no user_id passed")
            callback({})
            return

        print(f"[services.models] querying meals for user_id={user_id}")
        cursor = meals_col.find({"user_id": str(user_id)})
        reports = {str(doc.get("_id")): doc for doc in cursor}
        print(f"[services.models] fetched {len(reports)} reports")
        callback(reports)
    except Exception as e:
        print("[services.models] fetch_reports_for_user ERROR:", e)
        traceback.print_exc()
        try:
            callback({})
        except Exception:
            pass