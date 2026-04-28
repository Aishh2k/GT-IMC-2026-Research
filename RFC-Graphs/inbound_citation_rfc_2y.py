from pymongo import MongoClient
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
import os
import re
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db["all_rfc_details_4_2026"]


def normalize_rfc_number(value):
    if value is None:
        return None

    s = str(value).strip().upper()

    # handles things like:
    # "RFC2310", "RFC 2310", "rfc2310"
    match = re.search(r"RFC\s*0*([0-9]+)", s)
    if match:
        return f"RFC{match.group(1)}"

    return None


# ------------------------------------------------------------
# PASS 1: Build RFC number -> publication year map
# ------------------------------------------------------------
rfc_year_map = {}

docs = collection.find(
    {},
    {
        "_id": 0,
        "rfc_number": 1,
        "publication_year": 1,
    }
)

for doc in docs:
    rfc_num = normalize_rfc_number(doc.get("rfc_number"))
    year = doc.get("publication_year")

    if rfc_num is None or year is None:
        continue

    try:
        year = int(year)
    except (TypeError, ValueError):
        continue

    rfc_year_map[rfc_num] = year


# ------------------------------------------------------------
# PASS 2: For each RFC, count inbound RFC citations within 2 years
# ------------------------------------------------------------
values_by_year = defaultdict(list)

docs = collection.find(
    {},
    {
        "_id": 0,
        "rfc_number": 1,
        "publication_year": 1,
        "inbound_rfc_citations": 1,
    }
)

for doc in docs:
    cited_rfc = normalize_rfc_number(doc.get("rfc_number"))
    pub_year = doc.get("publication_year")
    inbound = doc.get("inbound_rfc_citations", [])

    if cited_rfc is None or pub_year is None:
        continue

    try:
        pub_year = int(pub_year)
    except (TypeError, ValueError):
        continue

    # Full 2-year window available only through publication year 2023
    # because the corpus goes through Dec 2025.
    if pub_year < 2001 or pub_year > 2023:
        continue

    if not isinstance(inbound, list):
        inbound = []

    count_within_2_years = 0
    seen_citing_rfcs = set()

    for ref in inbound:
        citing_rfc = normalize_rfc_number(ref)

        # skip drafts / non-RFC refs
        if citing_rfc is None:
            continue

        # avoid duplicate citing RFCs
        if citing_rfc in seen_citing_rfcs:
            continue
        seen_citing_rfcs.add(citing_rfc)

        citing_year = rfc_year_map.get(citing_rfc)
        if citing_year is None:
            continue

        # count RFCs published in same year, or within next 2 years
        if pub_year <= citing_year <= pub_year + 2:
            count_within_2_years += 1

    values_by_year[pub_year].append(count_within_2_years)


# ------------------------------------------------------------
# Build stats
# ------------------------------------------------------------
years = sorted(values_by_year.keys())

medians = []
p25 = []
p75 = []

for year in years:
    vals = values_by_year[year]

    med = np.percentile(vals, 50)
    q1 = np.percentile(vals, 25)
    q3 = np.percentile(vals, 75)

    medians.append(med)
    p25.append(q1)
    p75.append(q3)

    print(
        f"{year} median: {med:.1f} "
        f"p25: {q1:.1f} "
        f"p75: {q3:.1f} "
        f"n: {len(vals)}"
    )


# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------
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

ax.set_xlabel("Year")
ax.set_ylabel("Count of RFCs Referencing within 2 Years")

ax.set_xlim(2000, 2024)
ax.set_xticks(list(range(2001, 2024)))
ax.tick_params(axis="x", rotation=90)

ax.set_ylim(bottom=-0.2)

ax.grid(True, which="both", axis="both", color="#9e9e9e", linewidth=1, alpha=0.8)

ax.legend(
    handles=[line, fill],
    labels=["Median", "25th-75th percentile"],
    loc="upper right",
    frameon=True
)

plt.tight_layout()
plt.savefig("inbound_rfc_citations_within_2_years.png", dpi=300, bbox_inches="tight")
plt.close()