from pymongo import MongoClient
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_4_2026"]

COUNTRY_ORDER = [
    "United States",
    "Germany",
    "United Kingdom",
    "Finland",
    "China",
    "France",
    "Canada",
    "Japan",
    "Sweden",
    "India",
    "Other",
]

COUNTRY_COLORS = {
    "United States": "tab:blue",
    "Germany": "tab:orange",
    "United Kingdom": "tab:green",
    "Finland": "tab:red",
    "China": "tab:purple",
    "France": "tab:brown",
    "Canada": "tab:pink",
    "Japan": "tab:gray",
    "Sweden": "tab:olive",
    "India": "tab:cyan",
    "Other": "tab:red",
}

COUNTRY_MAP = {
    "united states": "United States",
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "united states of america": "United States",

    "germany": "Germany",

    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",

    "finland": "Finland",
    "china": "China",
    "france": "France",
    "canada": "Canada",
    "japan": "Japan",
    "sweden": "Sweden",
    "india": "India",
}

def normalize_country(country):
    if country is None:
        return None

    country = str(country).strip()
    if country == "":
        return None

    key = country.lower().strip()
    return COUNTRY_MAP.get(key, country)

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "author_details": 1,
    }
)

counts = defaultdict(lambda: defaultdict(int))
years = set()

for doc in docs:
    year = doc.get("publication_year")
    author_details = doc.get("author_details", [])

    if year is None:
        continue

    # Use April 2026 snapshot, but include only RFCs published through Dec 2025
    if year < 2001 or year > 2025:
        continue

    if not isinstance(author_details, list):
        continue

    for author in author_details:
        if not isinstance(author, dict):
            continue

        country = normalize_country(author.get("Country"))

        if country is None:
            continue

        if country not in COUNTRY_ORDER:
            country = "Other"

        counts[year][country] += 1
        years.add(year)

years = sorted(years)

percent_series = []

for country in COUNTRY_ORDER:
    values = []

    for year in years:
        total = sum(counts[year].values())

        if total == 0:
            values.append(0)
        else:
            values.append((counts[year].get(country, 0) / total) * 100)

    percent_series.append(values)

colors = [COUNTRY_COLORS[country] for country in COUNTRY_ORDER]

fig, ax = plt.subplots(figsize=(8.2, 5.2))

ax.stackplot(
    years,
    *percent_series,
    labels=COUNTRY_ORDER,
    colors=colors
)

ax.axvline(
    x=2020,
    color="black",
    linestyle=":",
    linewidth=1.8,
    zorder=10
)

ax.set_xlabel("Year")
ax.set_ylabel("Percentage of authors")

ax.set_xlim(2000, 2026)
ax.set_xticks(list(range(2001, 2026)))
ax.tick_params(axis="x", rotation=90)

ax.set_ylim(0, 100)
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)

ax.legend(
    title="Country",
    ncol=3,
    loc="lower left",
    frameon=True,
    fontsize=8,
    title_fontsize=9
)

plt.tight_layout()
plt.savefig("authorship_countries_normalized_until_2025.png", dpi=300, bbox_inches="tight")
plt.close()