from pymongo import MongoClient
from collections import defaultdict, Counter
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import os
import sys
import re
import unicodedata


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
db = client[os.getenv("MONGO_DB", "rfcs_database")]
collection = db["all_rfc_details_4_2026"]

MIN_YEAR = 2001
MAX_YEAR = 2025
TOP_N = 10

OUTPUT_FILE = "top_10_academic_affiliations_2001_2025.png"


# --------------------------------------------------
# Plot colors, same style as original figure
# --------------------------------------------------
COLORS = [
    "#1f77b4",  # 1st
    "#ff7f0e",  # 2nd
    "#2ca02c",  # 3rd
    "#d62728",  # 4th
    "#9467bd",  # 5th
    "#8c564b",  # 6th
    "#e377c2",  # 7th
    "#7f7f7f",  # 8th
    "#bcbd22",  # 9th
    "#17becf",  # 10th
    "#9c1138",  # Other
]


# --------------------------------------------------
# Explicit exclusions
# --------------------------------------------------
NON_ACADEMIC_AFFILIATIONS = {
    "verisign",
    "verisign inc",
    "isode limited",
    "arm limited",
    "the mitre corporation",
    "mitre corporation",
    "mitre",
}


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def clean_name(value):
    return " ".join(str(value).strip().split())


def clean_author_name(name):
    return " ".join(str(name).strip().lower().split())


def strip_accents(text):
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", str(text))
        if not unicodedata.combining(ch)
    )


def normalize_text(text):
    text = strip_accents(str(text)).lower().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[/,_\-]+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = " ".join(text.split())
    return text


def mapping_value_to_list(value):
    """
    affiliation_list_map values can be:
      "MIT"
      ["MIT"]
      ["MIT", "IBM"]

    Return a clean list of strings.
    """
    if isinstance(value, str):
        value = clean_name(value)
        return [value] if value else []

    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(clean_name(item))
        return result

    return []


# --------------------------------------------------
# Build exact normalized dictionary lookup
# --------------------------------------------------
normalized_mapping = {}

for raw_key, mapped_value in affiliation_list_map.items():
    raw_key_clean = clean_name(raw_key)
    raw_key_norm = normalize_text(raw_key_clean)

    mapped_values = mapping_value_to_list(mapped_value)

    if raw_key_norm and mapped_values:
        normalized_mapping[raw_key_norm] = mapped_values


# One requested manual fix only
normalized_mapping[normalize_text("VeriSign, Inc.")] = ["VeriSign"]
normalized_mapping[normalize_text("VeriSign")] = ["VeriSign"]


def map_affiliation_through_dictionary(raw_affiliation):
    """
    For every affiliation:
      1. Check expert mapping dictionary.
      2. If mapped, return mapped value(s).
      3. Otherwise return the original affiliation as a one-item list.
    """
    if raw_affiliation is None:
        return []

    raw_affiliation = clean_name(raw_affiliation)

    if not raw_affiliation:
        return []

    key = normalize_text(raw_affiliation)

    if not key:
        return []

    if key in {"unknown", "none", "nan", "n/a", "null", "na", "-"}:
        return []

    if key in normalized_mapping:
        return normalized_mapping[key]

    return [raw_affiliation]


def is_academic_affiliation(affiliation):
    """
    Decide if an affiliation is academic/research.
    This is applied after dictionary normalization.
    """
    a = normalize_text(affiliation)

    # Explicit exclusions: these are not academic institutions.
    if a in NON_ACADEMIC_AFFILIATIONS:
        return False

    academic_keywords = [
        "university",
        "college",
        "school of",
        "institute of technology",
        "technical university",
        "polytechnic",
        "academy of science",
        "academy of sciences",
        "academia sinica",

        # Research institutes that are academic/research-like
        "inria",
        "cnrs",
        "nist",
        "aist",
        "cwi",
        "isi",
        "tzi",
        "kaist",
        "epfl",
        "eth",
        "mit",
        "uc3m",
    ]

    return any(keyword in a for keyword in academic_keywords)


def academic_display_name(affiliation):
    """
    Convert mapped academic affiliation to figure-style label.
    This does NOT group all UC campuses into one UC System.
    """
    a = normalize_text(affiliation)

    # Original figure-style labels
    if "columbia university" in a or a == "columbia":
        return "Columbia U."

    if "tsinghua" in a:
        return "Tsinghua U."

    if (
        a == "mit"
        or "massachusetts institute of technology" in a
        or "mit university" in a
    ):
        return "MIT"

    if "inria" in a:
        return "INRIA"

    if (
        a == "ucl"
        or "university college london" in a
        or "uclouvain" in a
    ):
        return "UCL"

    if "nist" in a or "national institute of standards" in a:
        return "NIST"

    if "bremen" in a or "tzi" in a:
        return "U. of Bremen/TZI"

    if (
        a == "isi"
        or "usc isi" in a
        or "information sciences institute" in a
        or "university of southern california" in a
    ):
        return "ISI"

    if (
        "uc3m" in a
        or "carlos iii" in a
        or "universidad carlos iii" in a
        or "university carlos iii" in a
        or "university carlos iii of madrid" in a
    ):
        return "UC3M"

    if (
        "university of auckland" in a
        or "auckland university" in a
        or "u auckland" in a
    ):
        return "U. of Auckland"

    # Keep UC campuses separate
    if (
        "university of california berkeley" in a
        or "uc berkeley" in a
        or a == "ucb"
    ):
        return "UC Berkeley"

    if (
        "university of california los angeles" in a
        or a == "ucla"
    ):
        return "UCLA"

    if (
        "university of california san diego" in a
        or "uc san diego" in a
        or a == "ucsd"
    ):
        return "UC San Diego"

    if (
        "university of california irvine" in a
        or "uc irvine" in a
        or a == "uci"
    ):
        return "UC Irvine"

    if (
        "university of california davis" in a
        or "uc davis" in a
    ):
        return "UC Davis"

    if (
        "university of california santa cruz" in a
        or "uc santa cruz" in a
        or a == "ucsc"
    ):
        return "UC Santa Cruz"

    if (
        "university of california santa barbara" in a
        or "uc santa barbara" in a
        or a == "ucsb"
    ):
        return "UC Santa Barbara"

    # Other common academic display names
    if "carnegie mellon" in a:
        return "Carnegie Mellon U."

    if "stanford" in a:
        return "Stanford U."

    if "harvard" in a:
        return "Harvard U."

    if "princeton" in a:
        return "Princeton U."

    if "cornell" in a:
        return "Cornell U."

    if "university of cambridge" in a or a == "cambridge":
        return "Cambridge U."

    if "university of oxford" in a or a == "oxford":
        return "Oxford U."

    if "aalto" in a:
        return "Aalto U."

    if "eth zurich" in a or a == "eth":
        return "ETH Zurich"

    if "epfl" in a:
        return "EPFL"

    if "kaist" in a:
        return "KAIST"

    if "aist" in a:
        return "AIST"

    if "cwi" in a:
        return "CWI"

    if "cnrs" in a:
        return "CNRS"

    if (
        "chinese academy of science" in a
        or "chinese academy of sciences" in a
    ):
        return "Chinese Academy of Sciences"

    if (
        "beijing university of posts and telecommunications" in a
        or a == "bupt"
    ):
        return "BUPT"

    if (
        "beijing jiao tong university" in a
        or "beijing jiaotong university" in a
    ):
        return "Beijing Jiaotong U."

    if "university of waterloo" in a:
        return "U. of Waterloo"

    if "boston university" in a:
        return "Boston U."

    if "arizona state university" in a:
        return "Arizona State U."

    if "north carolina state university" in a:
        return "NC State U."

    if (
        "johns hopkins" in a
        or "john hopkins" in a
        or a == "jhu"
    ):
        return "JHU"

    if (
        "university of aberdeen" in a
        or "unviersity of aberdeen" in a
        or "aberdeen" in a
    ):
        return "U. of Aberdeen"

    # Fallback: lightly shorten University to U.
    name = clean_name(affiliation)

    replacements = {
        "University": "U.",
        "Universität": "U.",
        "Universite": "U.",
        "Université": "U.",
        "Universidad": "U.",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    return name


# --------------------------------------------------
# Count academic affiliations
# --------------------------------------------------
counts_by_year = defaultdict(Counter)
total_academic_by_year = defaultdict(int)
overall_academic_counts = Counter()

# Deduplicate same author, same year, same final academic label
processed_author_year_label = defaultdict(set)

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "author_details.Author": 1,
        "author_details.Affiliation": 1,
    },
)

for doc in docs:
    year = doc.get("publication_year")

    if year is None:
        continue

    try:
        year = int(year)
    except (TypeError, ValueError):
        continue

    if year < MIN_YEAR or year > MAX_YEAR:
        continue

    author_details = doc.get("author_details", [])

    if not isinstance(author_details, list):
        continue

    for author in author_details:
        if not isinstance(author, dict):
            continue

        author_name = author.get("Author")
        if not isinstance(author_name, str) or not author_name.strip():
            continue

        author_key = clean_author_name(author_name)

        raw_affiliation = author.get("Affiliation")
        mapped_affiliations = map_affiliation_through_dictionary(raw_affiliation)

        for mapped_affiliation in mapped_affiliations:
            if not is_academic_affiliation(mapped_affiliation):
                continue

            label = academic_display_name(mapped_affiliation)

            dedupe_key = (author_key, label)

            if dedupe_key in processed_author_year_label[year]:
                continue

            processed_author_year_label[year].add(dedupe_key)

            counts_by_year[year][label] += 1
            total_academic_by_year[year] += 1
            overall_academic_counts[label] += 1


# --------------------------------------------------
# Find top 10 academic affiliations
# --------------------------------------------------
top_academic_affiliations = [
    affiliation
    for affiliation, _ in overall_academic_counts.most_common(TOP_N)
]

labels = top_academic_affiliations + ["Other"]

print("\nTOP 10 ACADEMIC AFFILIATIONS")
print("=" * 80)
for affiliation, count in overall_academic_counts.most_common(TOP_N):
    print(f"{affiliation}: {count}")

print("\nTOP 50 ACADEMIC AFFILIATIONS")
print("=" * 80)
for affiliation, count in overall_academic_counts.most_common(50):
    print(f"{affiliation}: {count}")


# --------------------------------------------------
# Convert counts to yearly percentages
# --------------------------------------------------
years = list(range(MIN_YEAR, MAX_YEAR + 1))

series = []

for label in labels:
    values = []

    for year in years:
        total = total_academic_by_year[year]

        if label == "Other":
            top_count = sum(
                counts_by_year[year][affiliation]
                for affiliation in top_academic_affiliations
            )
            count = total - top_count
        else:
            count = counts_by_year[year][label]

        pct = (count / total) * 100 if total > 0 else 0
        values.append(pct)

    series.append(values)


# --------------------------------------------------
# Print exact yearly values
# --------------------------------------------------
print("\nYEARLY ACADEMIC AFFILIATION PERCENTAGES")
print("=" * 80)

for year in years:
    total = total_academic_by_year[year]

    if total == 0:
        continue

    print(f"\n{year} total_academic_authors = {total}")

    top_sum = 0

    for label in top_academic_affiliations:
        count = counts_by_year[year][label]
        pct = (count / total) * 100
        top_sum += count
        print(f"{label}: {count} authors, {pct:.2f}%")

    other_count = total - top_sum
    other_pct = (other_count / total) * 100
    top_pct = (top_sum / total) * 100

    print(f"Other: {other_count} authors, {other_pct:.2f}%")
    print(f"Top {TOP_N} combined: {top_sum} authors, {top_pct:.2f}%")


# --------------------------------------------------
# Print exact values for paper paragraph
# --------------------------------------------------
REPORT_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

print("\n" + "=" * 100)
print("EXACT VALUES FOR PAPER PARAGRAPH")
print("=" * 100)

print("\nTop 10 academic affiliations over full 2001-2025 period:")
for rank, affiliation in enumerate(top_academic_affiliations, start=1):
    count = overall_academic_counts[affiliation]
    print(f"{rank}. {affiliation}: {count} author-year counts")

for year in REPORT_YEARS:
    total = total_academic_by_year[year]

    if total == 0:
        print(f"\n{year}: no academic authors found")
        continue

    print("\n" + "-" * 100)
    print(f"{year}: total academic authors = {total}")
    print("-" * 100)

    top_sum = 0

    for affiliation in top_academic_affiliations:
        count = counts_by_year[year][affiliation]
        pct = (count / total) * 100
        top_sum += count

        print(f"{affiliation}: {count} authors, {pct:.2f}%")

    other_count = total - top_sum
    other_pct = (other_count / total) * 100
    top_pct = (top_sum / total) * 100

    print(f"Top {TOP_N} combined: {top_sum} authors, {top_pct:.2f}%")
    print(f"Other: {other_count} authors, {other_pct:.2f}%")


print("\n" + "=" * 100)
print("SPECIFIC CLAIM CHECKS")
print("=" * 100)

CLAIM_AFFILIATIONS = [
    "MIT",
    "Columbia U.",
    "ISI",
    "UCL",
    "Tsinghua U.",
    "JHU",
]

for affiliation in CLAIM_AFFILIATIONS:
    print(f"\n{affiliation}")
    print("-" * 60)

    for year in REPORT_YEARS:
        total = total_academic_by_year[year]

        if total == 0:
            continue

        count = counts_by_year[year][affiliation]
        pct = (count / total) * 100

        print(f"{year}: {count} authors, {pct:.2f}%")


print("\n" + "=" * 100)
print("TOP 10 ACADEMIC AFFILIATIONS USING DATA ONLY UNTIL 2020")
print("=" * 100)

counts_until_2020 = Counter()

for year in range(MIN_YEAR, 2020 + 1):
    for affiliation, count in counts_by_year[year].items():
        counts_until_2020[affiliation] += count

top_10_until_2020 = [aff for aff, _ in counts_until_2020.most_common(TOP_N)]

for rank, affiliation in enumerate(top_10_until_2020, start=1):
    print(f"{rank}. {affiliation}: {counts_until_2020[affiliation]} author-year counts")

print("\nTop 10 until 2020 but NOT in full 2001-2025 top 10:")
for affiliation in top_10_until_2020:
    if affiliation not in top_academic_affiliations:
        print(f"- {affiliation}")

print("\nFull 2001-2025 top 10 but NOT in top 10 until 2020:")
for affiliation in top_academic_affiliations:
    if affiliation not in top_10_until_2020:
        print(f"- {affiliation}")


# --------------------------------------------------
# Plot
# --------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 7))

ax.stackplot(
    years,
    series,
    labels=labels,
    colors=COLORS[:len(labels)],
    zorder=2,
)

ax.set_xlabel("Year")
ax.set_ylabel("Percentage of academic authors")

ax.set_xlim(MIN_YEAR - 1, MAX_YEAR + 1)
ax.set_xticks(years)
ax.tick_params(axis="x", rotation=45)

ax.set_ylim(0, 100)
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.6, zorder=0)

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, 1.13),
    ncol=4,
    frameon=True,
)

plt.tight_layout()
plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
plt.close()

print(f"\nSaved: {OUTPUT_FILE}")