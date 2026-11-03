"""Aplica descrições Amazon verificadas aos registros sem sinopse no Calibre.

Execute com: calibre-debug -e tools/aplicar_descricoes_calibre.py
"""
import csv
import json
import re
from pathlib import Path

from calibre.db.legacy import LibraryDatabase

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = Path(r"D:\CalibreLibrary")
DATA = ROOT / "dados_amazon.jsonl"
DECISIONS = ROOT / "DECISOES_AMAZON.csv"
rejected = set()
if DECISIONS.exists():
    with DECISIONS.open(encoding="utf-8-sig", newline="") as stream:
        rejected = {int(row["ID Calibre"]) for row in csv.DictReader(stream)
                    if row["Decisão"] == "rejeitar"}
results = {}
for line in DATA.read_text(encoding="utf-8").splitlines():
    try:
        item = json.loads(line)
        results[item["id"]] = item
    except (KeyError, ValueError):
        continue

db = LibraryDatabase(str(LIBRARY))
api = db.new_api
applied = 0
linked = 0
comments_to_apply = {}
identifiers_to_apply = {}
for book_id, item in results.items():
    if item.get("status") != "verificado" or book_id in rejected or not api.has_id(book_id):
        continue
    description = item.get("description", "").strip()
    if len(description) < 90 or not item.get("product_url", "").startswith("https://www.amazon.com.br/dp/"):
        continue
    old_comment = re.sub(r"<[^>]+>", " ", api.field_for("comments", book_id) or "").strip()
    if len(old_comment) < 35 or old_comment.lower().startswith(("downloaded from", "isbn", "não há", "null")):
        comments_to_apply[book_id] = description
        applied += 1
    asin = item.get("asin", "")
    if re.fullmatch(r"[A-Z0-9]{10,13}", asin):
        identifiers = dict(api.field_for("identifiers", book_id) or {})
        if asin not in identifiers.values():
            key = "amazon_br"
            suffix = 2
            while key in identifiers:
                key = f"amazon_br_{suffix}"
                suffix += 1
            identifiers[key] = asin
            identifiers_to_apply[book_id] = identifiers
            linked += 1
if comments_to_apply:
    api.set_field("comments", comments_to_apply)
if identifiers_to_apply:
    api.set_field("identifiers", identifiers_to_apply)
print(f"Descrições aplicadas: {applied}; fichas vinculadas por identificador: {linked}")
