from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["rfcs_database"]

collection = db["all_rfc_details_4_2026"]

# RFCs published after 2021 till Dec 2025 = years 2022, 2023, 2024, 2025
start_year = 2022
end_year = 2025

count = collection.count_documents({
    "publication_year": {
        "$gte": start_year,
        "$lte": end_year
    }
})

print(f"Total RFCs published from {start_year} to Dec {end_year}: {count}")

pipeline = [
    {
        "$match": {
            "publication_year": {
                "$gte": start_year,
                "$lte": end_year
            }
        }
    },
    {
        "$group": {
            "_id": "$publication_year",
            "count": {"$sum": 1}
        }
    },
    {
        "$sort": {
            "_id": 1
        }
    }
]

print("\nYear-wise counts:")

for row in collection.aggregate(pipeline):
    print(f"{row['_id']}: {row['count']}")

client.close()