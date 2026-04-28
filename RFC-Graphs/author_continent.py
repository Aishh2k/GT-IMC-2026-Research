from pymongo import MongoClient
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_4_2026"]

MIN_YEAR = 2001
MAX_YEAR = 2025   # includes Dec 2025, excludes 2026

CONTINENT_ORDER = [
    "North America",
    "Europe",
    "Asia",
    "Oceania",
    "Africa",
    "South America",
]

CONTINENT_COLORS = {
    "North America": "tab:blue",
    "Europe": "tab:orange",
    "Asia": "tab:green",
    "Oceania": "tab:red",
    "Africa": "tab:purple",
    "South America": "tab:brown",
}

def normalize_continent(continent):
    if continent is None:
        return None

    continent = str(continent).strip()

    mapping = {
        "North America": "North America",
        "Europe": "Europe",
        "Asia": "Asia",
        "Oceania": "Oceania",
        "Africa": "Africa",
        "South America": "South America",
    }

    return mapping.get(continent, None)

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "author_details": 1,
    }
)

author_counts = defaultdict(lambda: defaultdict(int))

for doc in docs:
    year = doc.get("publication_year")
    if year is None or year < MIN_YEAR or year > MAX_YEAR:
        continue

    author_details = doc.get("author_details")
    if not isinstance(author_details, list):
        continue

    for author in author_details:
        if not isinstance(author, dict):
            continue

        continent = normalize_continent(author.get("Continent"))
        if continent is None:
            continue

        author_counts[year][continent] += 1

years = list(range(MIN_YEAR, MAX_YEAR + 1))

series = []
for continent in CONTINENT_ORDER:
    values = []
    for year in years:
        total_authors = sum(author_counts[year][c] for c in CONTINENT_ORDER)

        if total_authors == 0:
            values.append(0)
        else:
            pct = (author_counts[year][continent] / total_authors) * 100
            values.append(pct)

    series.append(values)

colors = [CONTINENT_COLORS[c] for c in CONTINENT_ORDER]

fig, ax = plt.subplots(figsize=(8.2, 5.7))

ax.set_axisbelow(True)

ax.stackplot(
    years,
    *series,
    labels=CONTINENT_ORDER,
    colors=colors,
    zorder=2
)

ax.grid(True, linestyle="--", alpha=0.5, zorder=0)

ax.axvline(
    x=2020,
    color="black",
    linestyle=":",
    linewidth=2,
    zorder=10
)

ax.set_xlabel("Year")
ax.set_ylabel("Percentage of authors")

ax.set_xlim(2000, 2026)
ax.set_xticks(list(range(2001, 2026)))
ax.tick_params(axis="x", rotation=90)

ax.set_ylim(0, 102)

ax.legend(
    loc="lower left",
    ncol=3,
    frameon=True
)

plt.tight_layout()
plt.savefig("authorship_continents_normalized_until_2025.png", dpi=300, bbox_inches="tight")
plt.close()