from pymongo import MongoClient
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_5_2025"]

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "citation_count_literature": 1,
    }
)

nonzero_by_year = defaultdict(int)

for doc in docs:
    year = doc.get("publication_year")
    citation_count = doc.get("citation_count_literature")

    if year is None or citation_count is None:
        continue

    if year < 2001 or year > 2025:
        continue

    try:
        citation_count = float(citation_count)
    except (TypeError, ValueError):
        continue

    if citation_count > 0:
        nonzero_by_year[year] += 1

# force full range 2001 to 2025
years = list(range(2001, 2026))
counts = [nonzero_by_year.get(year, 0) for year in years]

fig, ax = plt.subplots(figsize=(8.2, 5.7))

ax.plot(
    years,
    counts,
    color="tab:blue",
    marker="o",
    linewidth=1.5,
    markersize=4
)

ax.set_xlabel("Year")
ax.set_ylabel("Number of RFCs")

ax.set_xlim(2000.5, 2025.5)
ax.set_xticks(years)
ax.tick_params(axis="x", rotation=90)

ax.grid(True, linestyle="-", linewidth=0.8, color="0.7")

plt.tight_layout()
plt.savefig("rfcs_with_nonzero_citation_count_2001_2025.png", dpi=300, bbox_inches="tight")
plt.close()