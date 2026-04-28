from pymongo import MongoClient
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_4_2026"]

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "rfc_updated": 1,
        "rfc_obsoleted": 1,
    }
)

total_by_year = defaultdict(int)
update_or_obsolete_by_year = defaultdict(int)

def non_empty_array(value):
    return isinstance(value, list) and len(value) > 0

for doc in docs:
    year = doc.get("publication_year")
    if year is None:
        continue

    if year < 2000 or year > 2025:
        continue

    total_by_year[year] += 1

    has_updated = non_empty_array(doc.get("rfc_updated"))
    has_obsoleted = non_empty_array(doc.get("rfc_obsoleted"))

    if has_updated or has_obsoleted:
        update_or_obsolete_by_year[year] += 1

years = sorted(total_by_year.keys())

percentages = []
for year in years:
    total = total_by_year[year]
    count = update_or_obsolete_by_year[year]
    percentages.append((count / total) * 100 if total > 0 else 0)

fig, ax = plt.subplots(figsize=(8.2, 5.2))

ax.plot(
    years,
    percentages,
    color="blue",
    marker="o",
    markersize=4,
    linewidth=1.5
)

ax.axvline(
    x=2020,
    color="black",
    linestyle="--",
    linewidth=1.5,
    zorder=10
)

ax.set_xlabel("Year")
ax.set_ylabel("Percentage (%)")

ax.set_xlim(1999, 2026)
ax.set_xticks(list(range(2000, 2026)))
ax.tick_params(axis="x", rotation=90)

ax.set_ylim(0, 100)
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)

plt.tight_layout()
plt.savefig("rfcs_update_or_obsolete_previous_rfcs_untill_2026.png", dpi=300, bbox_inches="tight")
plt.close()