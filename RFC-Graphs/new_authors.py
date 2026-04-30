from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict
import matplotlib.pyplot as plt
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["rfcs_database"]
collection = db["all_rfc_details_4_2026"]

START_YEAR = 2001
END_YEAR = 2025

authors_by_year = defaultdict(set)

docs = collection.find(
    {},
    {
        "_id": 0,
        "publication_year": 1,
        "author_details.Author": 1,
    }
)

def clean_author_name(name):
    return " ".join(name.strip().lower().split())

for doc in docs:
    year = doc.get("publication_year")

    if year is None:
        continue

    year = int(year)

    if year < START_YEAR or year > END_YEAR:
        continue

    for author in doc.get("author_details", []):
        name = author.get("Author")

        if isinstance(name, str) and name.strip():
            authors_by_year[year].add(clean_author_name(name))


seen_authors = set()
years = []
percent_new_authors = []

for year in range(START_YEAR, END_YEAR + 1):
    authors_this_year = authors_by_year[year]
    new_authors = authors_this_year - seen_authors

    if authors_this_year:
        percent_new = (len(new_authors) / len(authors_this_year)) * 100
    else:
        percent_new = 0

    years.append(year)
    percent_new_authors.append(percent_new)

    print(
        f"{year}: total authors = {len(authors_this_year)}, "
        f"new authors = {len(new_authors)}, "
        f"percent new = {percent_new:.2f}"
    )

    seen_authors.update(authors_this_year)


plt.figure(figsize=(10, 6))

plt.plot(
    years,
    percent_new_authors,
    color="blue",
    linewidth=1.2
)

plt.axvline(
    x=2020,
    color="black",
    linestyle="--",
    linewidth=1.2
)

plt.xlabel("Year")
plt.ylabel("Percentage of New Authors")

plt.xlim(2000, 2026)
plt.ylim(0, 100)

plt.xticks(range(2001, 2026), rotation=45)
plt.yticks(range(0, 101, 20))

plt.grid(True, which="major", color="gray", alpha=0.5)

plt.tight_layout()

plt.savefig("percentage_new_authors_2025.png", dpi=300)
plt.close()