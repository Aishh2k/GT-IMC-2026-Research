from pymongo import MongoClient
from dotenv import load_dotenv
import os
from pprint import pprint

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]

print("Connected databases:")
print(client.list_database_names())

print("\nCollections in rfcs_database:")
collections = db.list_collection_names()
print(collections)

print("\nDocument counts:")
for name in collections:
    print(f"{name}: {db[name].count_documents({})}")



db = client["rfcs_database"]
collection = db["all_rfc_details_5_2025"]

count_after_2021 = collection.count_documents({
    "publication_year": {"$gt": 2021}
})

print("RFCs after 2021:", count_after_2021)

