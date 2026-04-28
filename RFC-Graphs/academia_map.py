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
    "UC System",
    "INRIA",
    "Columbia U.",
    "Tsinghua U.",
    "NIST",
    "U. of Bremen/TZI",
    "USC/ISI",
    "U. of Aberdeen",
    "MIT",
    "JHU",
    "Other",
]

COLORS = [
    "#1f77b4",  # UC System
    "#ff7f0e",  # INRIA
    "#2ca02c",  # Columbia U.
    "#d62728",  # Tsinghua U.
    "#9467bd",  # NIST
    "#8c564b",  # U. of Bremen/TZI
    "#e377c2",  # USC/ISI
    "#7f7f7f",  # U. of Aberdeen
    "#bcbd22",  # MIT
    "#17becf",  # JHU
    "#a32645",  # Other
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

    if raw_affiliation in affiliation_list_map:
        return affiliation_list_map[raw_affiliation]

    raw_lower = raw_affiliation.lower()
    for key, values in affiliation_list_map.items():
        if key.lower() == raw_lower:
            return values

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
        "isi",
    ]

    return any(keyword in a for keyword in academia_keywords)


def bucket_academic_affiliation(affiliation):
    a = str(affiliation).lower().strip()

    # UC system
    if (
        "university of california" in a
        or "uc berkeley" in a
        or "ucb" in a
        or "ucla" in a
        or "uc san diego" in a
        or "ucsd" in a
        or "uc irvine" in a
        or "uci" in a
        or "uc davis" in a
        or "uc santa cruz" in a
        or "ucsc" in a
        or "uc santa barbara" in a
        or "ucsb" in a
    ):
        return "UC System"

    if "inria" in a:
        return "INRIA"

    if "columbia university" in a or a == "columbia":
        return "Columbia U."

    if "tsinghua" in a:
        return "Tsinghua U."

    if "nist" in a or "national institute of standards" in a:
        return "NIST"

    if "bremen" in a or "tzi" in a:
        return "U. of Bremen/TZI"

    if (
        "usc" in a
        or "university of southern california" in a
        or "information sciences institute" in a
        or a == "isi"
    ):
        return "USC/ISI"

    if "aberdeen" in a:
        return "U. of Aberdeen"

    if (
        "mit" in a
        or "massachusetts institute of technology" in a
        or "mit university" in a
    ):
        return "MIT"

    if (
        "johns hopkins" in a
        or "jhu" in a
        or "john hopkins" in a
    ):
        return "JHU"

    return "Other"


# --------------------------------------------------
# Count academic affiliations
# --------------------------------------------------
counts_by_year = defaultdict(Counter)
total_academic_by_year = defaultdict(int)
other_counter = Counter()

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
            if not is_academia(normalized_affiliation):
                continue

            label = bucket_academic_affiliation(normalized_affiliation)

            counts_by_year[year][label] += 1
            total_academic_by_year[year] += 1

            if label == "Other":
                other_counter[normalized_affiliation] += 1


# --------------------------------------------------
# Convert to percentages
# --------------------------------------------------
years = list(range(MIN_YEAR, MAX_YEAR + 1))

series = []
for label in LABELS:
    values = []

    for year in years:
        total = total_academic_by_year[year]
        count = counts_by_year[year][label]

        pct = (count / total) * 100 if total > 0 else 0
        values.append(pct)

    series.append(values)


# --------------------------------------------------
# Print debug summary
# --------------------------------------------------
print("\nACADEMIC AFFILIATION YEARLY SUMMARY")
print("=" * 80)

for year in years:
    total = total_academic_by_year[year]
    if total == 0:
        continue

    print(f"\n{year} total_academic_entries={total}")
    for label in LABELS:
        pct = counts_by_year[year][label] / total * 100
        print(f"{label}: {pct:.2f}")

print("\nTOP ACADEMIC AFFILIATIONS STILL GOING TO OTHER")
print("=" * 80)

for aff, count in other_counter.most_common(50):
    print(count, aff)


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

ax.set_xlabel("Year")
ax.set_ylabel("Percentage of academic authors")

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
plt.savefig("authorship_academic_affiliations_normalized_until_2025.png", dpi=300, bbox_inches="tight")
plt.close()

print("\nSaved: authorship_academic_affiliations_normalized_until_2025.png")