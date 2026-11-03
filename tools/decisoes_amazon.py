"""Decisões editoriais vinculadas ao livro e à ficha Amazon específica."""
import csv
import re


def asin_from_url(url):
    match = re.search(r"amazon\.com\.br/dp/([A-Z0-9]{10})", url or "", re.I)
    return match.group(1).upper() if match else ""


def load_decisions(path):
    decisions = {}
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                asin = asin_from_url(row.get("URL", ""))
                if asin:
                    decisions[(int(row["ID Calibre"]), asin)] = row["Decisão"]
    return decisions


def decision_for(decisions, book_id, item):
    asin = (item.get("asin") or asin_from_url(item.get("product_url", ""))).upper()
    return decisions.get((book_id, asin), "")
