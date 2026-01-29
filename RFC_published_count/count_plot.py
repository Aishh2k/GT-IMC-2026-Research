#!/usr/bin/env python3
"""
count_plot.py

- Uses RFC Editor rfc-index.xml to get TRUE RFC publication years.
- Plots RFCs published per year from the earliest year in the index through 2026.
- X-axis ticks every 10 years (while plotting every year).
- Dashed vertical line at 2020 in RED labeled "Data Analysed In Original Work".
- Saves ONLY PNG.

Output:
  - rfc_publications_to_2026.png
"""

from __future__ import annotations

import ssl
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

import matplotlib.pyplot as plt


# --------- CONFIG ---------
END_YEAR = 2025
X_TICK_STEP = 10
VERTICAL_LINE_YEAR = 2020
OUT_PNG = f"rfc_publications_to_{END_YEAR}.png"

RFC_INDEX_URLS = [
    "https://www.rfc-editor.org/rfc/rfc-index.xml",
    "https://www.rfc-editor.org/rfc-index.xml",
]


def fetch_url_text(url: str, timeout: int = 60) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "rfc-publication-plot/1.0 (academic replication)",
            "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace")


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_rfc_index_year_counts(xml_text: str) -> dict[int, int]:
    head = xml_text.lstrip()[:200].lower()
    if "<html" in head or "<!doctype html" in head:
        raise RuntimeError("Fetched HTML, not XML. URL likely redirected or blocked.")

    root = ET.fromstring(xml_text)

    year_counts: dict[int, int] = defaultdict(int)

    entries = [elem for elem in root.iter() if strip_ns(elem.tag) == "rfc-entry"]
    if not entries:
        raise RuntimeError("No <rfc-entry> elements found in rfc-index.xml (unexpected format).")

    for entry in entries:
        year_val = None
        date_elem = None

        for child in entry:
            if strip_ns(child.tag) == "date":
                date_elem = child
                break

        if date_elem is not None:
            for sub in date_elem:
                if strip_ns(sub.tag) == "year" and sub.text:
                    try:
                        year_val = int(sub.text.strip())
                    except ValueError:
                        year_val = None
                    break

        if year_val is None:
            continue

        year_counts[year_val] += 1

    return dict(year_counts)


def get_year_counts_from_rfc_editor() -> dict[int, int]:
    last_err = None
    for url in RFC_INDEX_URLS:
        try:
            xml_text = fetch_url_text(url)
            return parse_rfc_index_year_counts(xml_text)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Failed to fetch/parse RFC Editor index from all URLs: {last_err}")


def main() -> int:
    plt.rcParams.update({"font.size": 14}) 
    year_counts = get_year_counts_from_rfc_editor()
    
    min_year_in_index = min(year_counts.keys())
    max_year_in_index = max(year_counts.keys())

    # ---- Extra count: RFCs published after 2021 ----
    # (interpreting "after 2021" as years >= 2022)
    after_year = 2021
    rfcs_after_2021 = sum(c for y, c in year_counts.items() if y > after_year)
    print(f"RFCs published after {after_year} (i.e., {after_year+1}+): {rfcs_after_2021}")

    plot_start_year = min_year_in_index
    plot_end_year = END_YEAR  # show through 2026 (future years will be 0 if not in index yet)

    years = list(range(plot_start_year, plot_end_year + 1))
    counts = [year_counts.get(y, 0) for y in years]

    plt.figure(figsize=(12, 4.8))
    plt.plot(
        years,
        counts,
        marker="o",
        linestyle="-",
        linewidth=2,
        markersize=5,
        color="blue", 
        label="RFC Count",
    )

    if plot_start_year <= VERTICAL_LINE_YEAR <= plot_end_year:
        plt.axvline(
            x=VERTICAL_LINE_YEAR,
            color="red",
            linestyle="--",
            linewidth=2,
            label="Data Analysed In Original Work",
        )

    plt.xlabel("Year")
    plt.ylabel("Number of RFCs published")

    # X ticks every 10 years (but all years are plotted)
    first_tick = ((max(1970, plot_start_year) + (X_TICK_STEP - 1)) // X_TICK_STEP) * X_TICK_STEP
    xticks = list(range(first_tick, plot_end_year + 1, X_TICK_STEP))
    if 1970 >= plot_start_year and 1970 <= plot_end_year and 1970 not in xticks:
        xticks.insert(0, 1970)
    plt.xticks(xticks)

    plt.legend(loc="upper left")
    plt.tight_layout()

    plt.savefig(OUT_PNG, dpi=200)
    print(f"Saved: {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
