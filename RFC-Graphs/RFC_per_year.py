from pymongo import MongoClient
import pandas as pd
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import os 

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_4_2026"]

pipeline = [
    {
        "$match": {
            "publication_year": {"$exists": True, "$ne": None},
            "publication_year": {"$lte": 2025}
        }
    },
    {
        "$group": {
            "_id": "$publication_year",
            "count": {"$sum": 1}
        }
    },
    {
        "$sort": {"_id": 1}
    }
]

rows = list(collection.aggregate(pipeline))

df = pd.DataFrame(rows).rename(columns={"_id": "year"})
df["year"] = df["year"].astype(int)
df = df.sort_values("year")

plt.figure(figsize=(10, 5))

plt.plot(
    df["year"],
    df["count"],
    color="blue",
    marker="o",
    markersize=3,
    linewidth=1.2,
    label="RFC Count"
)

plt.axvline(
    x=2020,
    color="red",
    linestyle="--",
    linewidth=1.5,
    label="Data Analysed In Original Work"
)

plt.xlabel("Year")
plt.ylabel("Number of RFCs published")
plt.legend(loc="upper left")
plt.tight_layout()

plt.savefig("rfc_count_per_year_until_2026.png", dpi=300)
plt.close()