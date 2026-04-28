from pymongo import MongoClient
from collections import defaultdict
import numpy as np
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
        "number_of_drafts": 1,
    }
)

values_by_year = defaultdict(list)

for doc in docs:
    year = doc.get("publication_year")
    drafts = doc.get("number_of_drafts")

    if year is None or drafts is None:
        continue

    if year < 2001 or year > 2025:
        continue

    try:
        drafts = float(drafts)
    except (TypeError, ValueError):
        continue

    if drafts < 0:
        continue

    values_by_year[year].append(drafts)

years = sorted(values_by_year.keys())

medians = []
p25 = []
p75 = []

for year in years:
    vals = values_by_year[year]
    medians.append(np.percentile(vals, 50))
    p25.append(np.percentile(vals, 25))
    p75.append(np.percentile(vals, 75))

fig, ax = plt.subplots(figsize=(8.2, 5.7))

fill = ax.fill_between(
    years,
    p25,
    p75,
    color="skyblue",
    alpha=1.0,
    label="25th-75th percentile",
    zorder=1
)

line, = ax.plot(
    years,
    medians,
    color="navy",
    linewidth=2,
    label="Median",
    zorder=2
)

ax.axvline(
    x=2020,
    color="black",
    linestyle="--",
    linewidth=2,
    zorder=10
)

ax.set_xlabel("Year")
ax.set_ylabel("Number of Drafts")

ax.set_xlim(2000, 2026)
ax.set_xticks(list(range(2001, 2026)))
ax.tick_params(axis="x", rotation=90)


ax.legend(
    handles=[line, fill],
    labels=["Median", "25th-75th percentile"],
    loc="upper left",
    frameon=True
)

plt.tight_layout()
plt.savefig("number_of_drafts_per_rfc_untill_2026.png", dpi=300, bbox_inches="tight")
plt.close()