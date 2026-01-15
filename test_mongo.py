"""Quick test to verify MongoDB Atlas connection"""
import os
import certifi
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://kabu_db_user:pass101pass101@cluster0.kxhmgjt.mongodb.net/"

print("Testing MongoDB connection...")
print(f"URI: {uri[:50]}...")

try:
    client = MongoClient(
        uri,
        server_api=ServerApi("1"),
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,  # 5 second timeout for faster test
    )
    
    # Test connection
    client.admin.command('ping')
    print("✓ SUCCESS: Connected to MongoDB Atlas!")
    
    # Test database access
    db = client["kabu_db_user"]
    collections = db.list_collection_names()
    print(f"✓ Collections found: {collections}")
    
except Exception as e:
    print(f"✗ FAILED: {type(e).__name__}")
    print(f"Error: {e}")
    print("\n--- Troubleshooting ---")
    print("1. Check Network Access in MongoDB Atlas")
    print("2. Verify 0.0.0.0/0 is whitelisted with green checkmark")
    print("3. Wait 2-3 minutes after adding IP whitelist")
    print("4. Check if your network/firewall blocks port 27017")
