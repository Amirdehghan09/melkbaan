"""Simple real estate price scraper.

This script fetches real estate listings from Divar and Sheypoor for a given
محله (neighborhood). The HTML responses are parsed using BeautifulSoup and the
results are filtered so that only listings with ``year`` equal to ``1403`` or
``1404`` are considered. Up to the first 20 listings matching the filter are
used to compute an average price.

Usage::

    python scraper.py <neighborhood>

The script prints the calculated average price and stores the raw listing data
in ``listings.json``. Scraping third-party websites may be subject to legal and
ethical restrictions; always consult the site’s Terms of Service and
``robots.txt`` before running this script.
"""

import sys
import json
from dataclasses import dataclass
from typing import List, Optional
import re

import requests
from bs4 import BeautifulSoup


@dataclass
class Listing:
    title: str
    price: int
    year: int


def _parse_price(text: str) -> Optional[int]:
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else None


def _parse_year(text: str) -> Optional[int]:
    m = re.search(r"14\d{2}", text)
    return int(m.group()) if m else None


def _parse_listings(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings: List[Listing] = []

    for card in soup.select("div"):
        text = card.get_text(" ", strip=True)
        year = _parse_year(text)
        price_tag = card.find(lambda tag: tag.name in {"div", "span"} and "price" in tag.get("class", []))
        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price = _parse_price(price_text)
        title_tag = card.find("a")
        title = title_tag.get_text(strip=True) if title_tag else ""

        if year in {1403, 1404} and price is not None and title:
            listings.append(Listing(title=title, price=price, year=year))
            if len(listings) == 20:
                break
    return listings


def fetch_divar(neighborhood: str) -> List[Listing]:
    url = f"https://divar.ir/s/tehran/{neighborhood}?category=real-estate"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return _parse_listings(resp.text)


def fetch_sheypoor(neighborhood: str) -> List[Listing]:
    url = f"https://www.sheypoor.com/tehran/{neighborhood}/real-estate"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return _parse_listings(resp.text)


def compute_average_price(listings: List[Listing]) -> float:
    if not listings:
        return 0.0
    total = sum(l.price for l in listings)
    return total / len(listings)


def main(neighborhood: str) -> None:
    all_listings: List[Listing] = []

    try:
        all_listings.extend(fetch_divar(neighborhood))
    except Exception as exc:
        print(f"Failed to fetch Divar listings: {exc}")

    try:
        all_listings.extend(fetch_sheypoor(neighborhood))
    except Exception as exc:
        print(f"Failed to fetch Sheypoor listings: {exc}")

    unique = {(l.title, l.price, l.year): l for l in all_listings}
    filtered = list(unique.values())[:20]
    avg = compute_average_price(filtered)
    print(f"Average price based on {len(filtered)} listings: {avg:.2f}")

    with open("listings.json", "w", encoding="utf-8") as fh:
        json.dump([l.__dict__ for l in filtered], fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scraper.py <neighborhood>")
    main(sys.argv[1])
