# insert_reports.py
import os
import json
from db import meals_col

# --- Load your JSON data ---
def load_reports_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "reports_data.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Prepare documents ---
reports = load_reports_data()
documents = []
for report_id, data in reports.items():
    # Use report_id as the primary _id to avoid duplicates
    data["_id"] = report_id
    documents.append(data)

# --- Insert (ignore duplicates) ---
try:
    result = meals_col.insert_many(documents, ordered=False)
    print(f"✅ Successfully inserted {len(result.inserted_ids)} reports.")
except Exception as e:
    # Bulk insert may partially succeed; check for duplicate key errors
    if "duplicate key error" in str(e):
        print("⚠️ Some reports already exist (skipped duplicates).")
    else:
        print("❌ Insert failed:", e)