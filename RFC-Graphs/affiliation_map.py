from pymongo import MongoClient
from collections import defaultdict, Counter
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import os
import sys

# --------------------------------------------------
# Import affiliation mapping dictionary
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AFFILIATION_DIR = os.path.join(BASE_DIR, "Validation_LLM", "Affiliation")

sys.path.append(AFFILIATION_DIR)

from affiliation_mapping_dictionary import affiliation_list_map

# --------------------------------------------------
# MongoDB setup
# --------------------------------------------------
load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_4_2026"]

MIN_YEAR = 2001
MAX_YEAR = 2025   # includes Dec 2025, excludes 2026

LABELS = [
    "Cisco Systems",
    "Huawei Technologies",
    "Ericsson",
    "Juniper Networks",
    "Microsoft Corporation",
    "Google",
    "Nokia Corporation",
    "Oracle",
    "AT&T",
    "Alcatel-Lucent",
    "Academia",
    "Other",
]

COLORS = [
    "#1f77b4",  # Cisco Systems
    "#ff7f0e",  # Huawei Technologies
    "#2ca02c",  # Ericsson
    "#d62728",  # Juniper Networks
    "#9467bd",  # Microsoft Corporation
    "#8c564b",  # Google
    "#e377c2",  # Nokia Corporation
    "#7f7f7f",  # Oracle
    "#bcbd22",  # AT&T
    "#17becf",  # Alcatel-Lucent
    "#a11515",  # Academia
    "#6c757d",  # Other
]

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def normalize_raw_affiliation(raw_affiliation):
    if raw_affiliation is None:
        return []

    raw_affiliation = str(raw_affiliation).strip()
    if raw_affiliation == "":
        return []

    # Exact dictionary lookup
    if raw_affiliation in affiliation_list_map:
        return affiliation_list_map[raw_affiliation]

    # Case-insensitive dictionary lookup
    raw_lower = raw_affiliation.lower()
    for key, values in affiliation_list_map.items():
        if key.lower() == raw_lower:
            return values

    # Fallback
    return [raw_affiliation]


def is_academia(affiliation):
    a = str(affiliation).lower().strip()

    academia_keywords = [
        "university",
        "unviersity",
        "universitaet",
        "universität",
        "universite",
        "université",
        "universidad",
        "college",
        "school of",
        "institute of technology",
        "technical university",
        "polytechnic",
        "academy of science",
        "academy of sciences",
        "chinese academy of science",
        "chinese academy of sciences",
        "academia sinica",
        "carnegie mellon",
        "california institute of technology",
        "massachusetts institute of technology",
        "mit university",
        "kaist",
        "eth",
        "epfl",
        "cnrs",
        "inria",
        "aist",
        "cwi",
        "nist",
        "tzi",
    ]

    return any(keyword in a for keyword in academia_keywords)


def clean_company_string(value):
    a = str(value).lower().strip()

    replacements = [
        (",", ""),
        (".", ""),
        (" corporation", ""),
        (" corp", ""),
        (" incorporated", ""),
        (" inc", ""),
        (" ltd", ""),
        (" limited", ""),
        (" co ", " "),
        (" co", ""),
        (" company", ""),
    ]

    for old, new in replacements:
        a = a.replace(old, new)

    return " ".join(a.split())


def bucket_affiliation(normalized_affiliation):
    raw = str(normalized_affiliation).strip()
    a = raw.lower()
    a_clean = clean_company_string(raw)

    if "cisco" in a_clean or a_clean == "cis":
        return "Cisco Systems"

    if "huawei" in a_clean or "futurewei" in a_clean:
        return "Huawei Technologies"

    if "ericsson" in a_clean:
        return "Ericsson"

    if "juniper" in a_clean:
        return "Juniper Networks"

    if "microsoft" in a_clean:
        return "Microsoft Corporation"

    if "google" in a_clean:
        return "Google"

    if "nokia" in a_clean:
        return "Nokia Corporation"

    if "oracle" in a_clean or "sun microsystems" in a_clean:
        return "Oracle"

    if a_clean in {"att", "at&t"} or "at&t" in a or "at and t" in a_clean:
        return "AT&T"

    if "alcatel" in a_clean or "lucent" in a_clean:
        return "Alcatel-Lucent"

    if is_academia(raw):
        return "Academia"

    return "Other"


# --------------------------------------------------
# Count affiliations
# --------------------------------------------------
counts_by_year = defaultdict(Counter)
total_by_year = defaultdict(int)

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "author_details": 1,
    }
)

for doc in docs:
    year = doc.get("publication_year")
    if year is None or year < MIN_YEAR or year > MAX_YEAR:
        continue

    author_details = doc.get("author_details", [])
    if not isinstance(author_details, list):
        continue

    for author in author_details:
        if not isinstance(author, dict):
            continue

        raw_affiliation = author.get("Affiliation")
        normalized_affiliations = normalize_raw_affiliation(raw_affiliation)

        if not normalized_affiliations:
            continue

        for normalized_affiliation in normalized_affiliations:
            label = bucket_affiliation(normalized_affiliation)

            counts_by_year[year][label] += 1
            total_by_year[year] += 1


# --------------------------------------------------
# Convert to percentages
# --------------------------------------------------
years = list(range(MIN_YEAR, MAX_YEAR + 1))

series = []
for label in LABELS:
    values = []

    for year in years:
        total = total_by_year[year]
        count = counts_by_year[year][label]

        pct = (count / total) * 100 if total > 0 else 0
        values.append(pct)

    series.append(values)


# --------------------------------------------------
# Plot
# --------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 7))

ax.stackplot(
    years,
    series,
    labels=LABELS,
    colors=COLORS,
    zorder=2
)

ax.axvline(
    x=2020,
    color="black",
    linestyle="--",
    linewidth=1.5,
    zorder=10
)

ax.set_xlabel("Year")
ax.set_ylabel("Percentage of authors")

ax.set_xlim(2000, 2026)
ax.set_xticks(years)
ax.tick_params(axis="x", rotation=45)

ax.set_ylim(0, 100)
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.6, zorder=0)

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, 1.13),
    ncol=4,
    frameon=True
)

plt.tight_layout()
plt.savefig("authorship_affiliations_normalized_until_2025.png", dpi=300, bbox_inches="tight")
plt.close()

print("Saved: authorship_affiliations_normalized_until_2025.png")