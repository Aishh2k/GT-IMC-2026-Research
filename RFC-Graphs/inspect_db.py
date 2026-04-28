from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict
import os

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["rfcs_database"]

collections = [
    "all_rfc_details_4_2026",
    "all_rfc_details_5_2025"
]

for collection_name in collections:
    collection = db[collection_name]
    count = collection.count_documents({})
    print(f"{collection_name}: {count} records") #counts in teo collections