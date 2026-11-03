"""Reavalia todas as fichas coletadas após mudanças nas regras de matching."""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from coletar_amazon import clean_title, description_is_synopsis, description_language_ok, title_score

ROOT = Path(__file__).resolve().parents[1]
books = {book["id"]: book for book in json.loads((ROOT / "catalogo.json").read_text(encoding="utf-8"))}
rejected = set()
decisions = ROOT / "DECISOES_AMAZON.csv"
if decisions.exists():
    with decisions.open(encoding="utf-8-sig", newline="") as stream:
        rejected = {int(row["ID Calibre"]) for row in csv.DictReader(stream)
                    if row["Decisão"] == "rejeitar"}
latest = {}
for line in (ROOT / "dados_amazon.jsonl").read_text(encoding="utf-8").splitlines():
    try:
        item = json.loads(line)
        latest[item["id"]] = item
    except (ValueError, KeyError):
        pass

suspects = []
for book_id, item in latest.items():
    if item.get("status") != "verificado" or book_id not in books or book_id in rejected:
        continue
    book = books[book_id]
    score = title_score(clean_title(book["title"], book.get("authors", "")), item["amazon_title"], item.get("amazon_authors", ""))
    language = description_language_ok(book, item["description"])
    threshold = 92 if item.get("author_match") is None else 83
    if score < threshold or not language or not description_is_synopsis(item["description"]):
        suspects.append((book, item, score, language))

with (ROOT / "REVISAO_AMAZON.csv").open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(["ID Calibre", "Título Calibre", "Autores", "Título Amazon", "ASIN", "URL", "Pontuação nova", "Idioma compatível", "Status"])
    for book, item, score, language in suspects:
        writer.writerow([book["id"], book["title"], book["authors"], item["amazon_title"], item["asin"], item["product_url"], score, language, "revisão pendente"])

if "--apply" in sys.argv:
    with (ROOT / "dados_amazon.jsonl").open("a", encoding="utf-8") as stream:
        for book, item, score, language in suspects:
            record = {"id": book["id"], "status": "revisao_pendente", "asin": item["asin"],
                      "product_url": item["product_url"], "amazon_title": item["amazon_title"],
                      "reason": "título" if score < (92 if item.get("author_match") is None else 83) else "idioma",
                      "checked_at": datetime.now(timezone.utc).isoformat()}
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
print("Fichas para revisão:", len(suspects), "aplicadas:" if "--apply" in sys.argv else "prévia:", "--apply" in sys.argv)
