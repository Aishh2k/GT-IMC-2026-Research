from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict
import matplotlib.pyplot as plt
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["ietfdata_mailarchive_v2"]
collection = db["messages"]

START_YEAR = 1995
END_YEAR = 2024

messages_by_year = defaultdict(int)
person_ids_by_year = defaultdict(set)

docs = collection.find(
    {},
    {
        "_id": 0,
        "timestamp": 1,
        "uid": 1,
    }
)

for doc in docs:
    ts = doc.get("timestamp")
    uid = doc.get("uid")

    if ts is None or uid is None:
        continue

    year = ts.year if hasattr(ts, "year") else int(str(ts)[:4])

    if START_YEAR <= year <= END_YEAR:
        messages_by_year[year] += 1
        person_ids_by_year[year].add(uid)

years = list(range(START_YEAR, END_YEAR + 1))
message_counts = [messages_by_year[y] for y in years]
person_id_counts = [len(person_ids_by_year[y]) for y in years]

print("\nDEBUG COUNTS")
print("-" * 60)
print(f"{'Year':<8}{'Person IDs':<15}{'Messages':<15}")
print("-" * 60)

for y, p, m in zip(years, person_id_counts, message_counts):
    print(f"{y:<8}{p:<15}{m:<15}")

print("-" * 60)
print(f"Max person IDs: {max(person_id_counts)}")
print(f"Max messages: {max(message_counts)}")
print(f"Total messages plotted: {sum(message_counts)}")

fig, ax1 = plt.subplots(figsize=(7.2, 4.2))

ax1.plot(
    years,
    person_id_counts,
    color="blue",
    linewidth=1.2,
    label="Number of Person IDs"
)

ax2 = ax1.twinx()

ax2.plot(
    years,
    message_counts,
    color="red",
    linestyle="--",
    linewidth=1.2,
    label="Number of Messages"
)

ax1.set_xlabel("Year", fontsize=10)
ax1.set_ylabel("Number of Person IDs", fontsize=10)
ax2.set_ylabel("Number of Messages", fontsize=10, color="red")

ax1.tick_params(axis="x", labelsize=8)
ax1.tick_params(axis="y", labelsize=8)
ax2.tick_params(axis="y", labelsize=8, labelcolor="red")

ax1.set_xlim(1994, 2026)

ax1.set_ylim(0, max(person_id_counts) * 1.10)
ax2.set_ylim(0, max(message_counts) * 1.10)

ax1.set_xticks(years)
ax1.set_xticklabels(years, rotation=90)

ax1.grid(True, which="major", color="gray", alpha=0.35)

lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()

ax1.legend(
    lines_1 + lines_2,
    labels_1 + labels_2,
    loc="upper left",
    fontsize=9,
    frameon=True
)

plt.tight_layout()
plt.savefig("email_volume_person_ids_messages_1995_2025.png", dpi=300)
plt.close()