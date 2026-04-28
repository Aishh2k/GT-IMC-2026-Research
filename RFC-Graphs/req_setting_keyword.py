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
        "total_keyword_matches": 1,
        "page_count": 1,
    }
)

values_by_year = defaultdict(list)

for doc in docs:
    year = doc.get("publication_year")
    keyword_count = doc.get("total_keyword_matches")
    page_count = doc.get("page_count")

    if year is None or keyword_count is None or page_count is None:
        continue

    if year < 2001 or year > 2025:
        continue

    try:
        keyword_count = float(keyword_count)
        page_count = float(page_count)
    except (TypeError, ValueError):
        continue

    if page_count <= 0:
        continue

    keywords_per_page = keyword_count / page_count
    values_by_year[year].append(keywords_per_page)

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
ax.set_ylabel("Standard Keywords")

ax.set_xlim(2000, 2026)
ax.set_xticks(list(range(2001, 2026)))
ax.tick_params(axis="x", rotation=90)

ax.set_axisbelow(False)
ax.grid(True, which="both", axis="both", color="#9e9e9e", linewidth=1, alpha=0.8, zorder=10)

ax.legend(
    handles=[line, fill],
    labels=["Median", "25th-75th percentile"],
    loc="upper left",
    frameon=True
)

plt.tight_layout()
plt.savefig("requirement_setting_2026", dpi=300, bbox_inches="tight")
plt.close()