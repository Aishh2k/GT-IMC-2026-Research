from pymongo import MongoClient
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_5_2025"]

AREA_ORDER = ["other", "rtg", "int", "app", "ops", "sec", "tsv", "rai", "art", "wit"]

AREA_COLORS = {
    "other": "tab:blue",
    "rtg": "tab:orange",
    "int": "tab:green",
    "app": "tab:red",
    "ops": "tab:purple",
    "sec": "tab:brown",
    "tsv": "tab:pink",
    "rai": "tab:gray",
    "art": "tab:olive",
    "wit": "tab:cyan",
}

AREA_MAP = {
    "other": "other",
    "rtg": "rtg",
    "routing": "rtg",
    "int": "int",
    "internet": "int",
    "app": "app",
    "applications": "app",
    "ops": "ops",
    "operations": "ops",
    "operations and management": "ops",
    "sec": "sec",
    "security": "sec",
    "tsv": "tsv",
    "transport": "tsv",
    "rai": "rai",
    "real-time applications and infrastructure": "rai",
    "art": "art",
    "applications and real-time": "art",
    "wit": "wit",
    "web and internet transport": "wit",
}

def normalize_area(area):
    if area is None:
        return "other"
    area = str(area).lower().strip()
    return AREA_MAP.get(area, area if area in AREA_ORDER else "other")

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "rfc_area": 1,
        "working_group": 1,
        "stream": 1,
    }
)

# year -> area -> unique WGs/streams
counts = defaultdict(lambda: defaultdict(set))
years = set()

for doc in docs:
    year = doc.get("publication_year")
    if year is None:
        continue

    raw_area = doc.get("rfc_area")
    area = normalize_area(raw_area)

    wg = doc.get("working_group")
    stream = doc.get("stream")

    if wg is not None and str(wg).strip() != "":
        entity = str(wg).lower().strip()
    elif stream is not None and str(stream).strip() != "":
        area = "other"
        entity = str(stream).lower().strip()
    else:
        continue

    counts[year][area].add(entity)
    years.add(year)

years = sorted(years)

series = []
for area in AREA_ORDER:
    series.append([len(counts[year].get(area, set())) for year in years])

colors = [AREA_COLORS[area] for area in AREA_ORDER]
total_per_year = [sum(len(counts[year].get(area, set())) for area in AREA_ORDER) for year in years]
ymax = max(total_per_year)

fig, ax = plt.subplots(figsize=(10, 5.2))
ax.set_axisbelow(True)

ax.stackplot(
    years,
    *series,
    labels=["Other", "rtg", "int", "app", "ops", "sec", "tsv", "rai", "art", "wit"],
    colors=colors,
    zorder=2
)

ax.grid(True, color="0.7", linewidth=0.8, zorder=0)

ax.set_xlabel("Year")
ax.set_ylabel("RFC-publishing WGs or streams")

ax.legend(
    ncol=5,
    loc="upper left",
    bbox_to_anchor=(0.0, 1.22),
    frameon=True
)

ax.set_xlim(1966, 2030)
ax.set_xticks([1970, 1980, 1990, 2000, 2010, 2020, 2030])
ax.set_ylim(0, ymax * 1.08)

ax.vlines(2020, 0, ax.get_ylim()[1], colors="black", linestyles=":", linewidth=2, zorder=100)

plt.tight_layout()
plt.savefig("publishing_working_groups_by_area_may_2025.png", dpi=300, bbox_inches="tight")
plt.close()