from pymongo import MongoClient
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_4_2026"]

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
    }
)

counts = defaultdict(lambda: defaultdict(int))
years = set()

for doc in docs:
    year = doc.get("publication_year")
    if year is None:
        continue

    raw_area = doc.get("rfc_area")

    # Missing/empty area should go to "other"
    if raw_area is None or str(raw_area).strip() == "":
        area = "other"
    else:
        area = normalize_area(raw_area)

    counts[year][area] += 1
    years.add(year)

years = sorted(years)

series = []
for area in AREA_ORDER:
    series.append([counts[year].get(area, 0) for year in years])

colors = [AREA_COLORS[area] for area in AREA_ORDER]
total_per_year = [sum(counts[year].values()) for year in years]
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
ax.set_ylabel("RFCs published")

ax.legend(
    ncol=5,
    loc="upper left",
    bbox_to_anchor=(0.0, 1.22),
    frameon=True
)

# Left gap + same right-side spacing
ax.set_xlim(1966, 2030)
ax.set_xticks([1970, 1980, 1990, 2000, 2010, 2020, 2030])
ax.set_ylim(0, ymax * 1.08)

# Draw vertical dotted lines LAST so they stay in front
ax.vlines(1986, 0, ax.get_ylim()[1], colors="black", linestyles=":", linewidth=2, zorder=100)
ax.vlines(2020, 0, ax.get_ylim()[1], colors="black", linestyles=":", linewidth=2, zorder=100)

# Draw text after the lines
ax.text(
    1986,
    ymax * 0.96,
    "Creation of the IETF",
    color="darkred",
    ha="center",
    va="center",
    bbox=dict(facecolor="lightgray", edgecolor="none", alpha=0.85, pad=3),
    zorder=101
)

plt.tight_layout()
plt.savefig("rfc_by_area_untill_2026.png", dpi=300, bbox_inches="tight")
plt.close()