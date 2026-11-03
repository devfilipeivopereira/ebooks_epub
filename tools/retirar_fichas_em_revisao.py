"""Retira do Calibre descrições Amazon que falharam na revisão posterior.

Execute com: calibre-debug -e tools/retirar_fichas_em_revisao.py
"""
import csv
import json
import re
from pathlib import Path

from calibre.db.legacy import LibraryDatabase

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = Path(r"D:\CalibreLibrary")
rejected = set()
decisions = ROOT / "DECISOES_AMAZON.csv"
if decisions.exists():
    with decisions.open(encoding="utf-8-sig", newline="") as stream:
        rejected = {int(row["ID Calibre"]) for row in csv.DictReader(stream)
                    if row["Decisão"] == "rejeitar"}
records = {}
for line in (ROOT / "dados_amazon.jsonl").read_text(encoding="utf-8").splitlines():
    try:
        item = json.loads(line)
        state = records.setdefault(item["id"], {"latest": None, "verified": None})
        state["latest"] = item
        if item.get("status") == "verificado":
            state["verified"] = item
    except (ValueError, KeyError):
        pass

db = LibraryDatabase(str(LIBRARY))
api = db.new_api
cleared = 0
unlinked = 0
for book_id, state in records.items():
    if state["latest"].get("status") not in ("revisao_pendente", "idioma_incompativel") and book_id not in rejected:
        continue
    prior = state["verified"]
    if not prior or not api.has_id(book_id):
        continue
    current = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", api.field_for("comments", book_id) or "")).strip()
    if current == re.sub(r"\s+", " ", prior.get("description", "")).strip():
        api.set_field("comments", {book_id: ""})
        cleared += 1
    identifiers = dict(api.field_for("identifiers", book_id) or {})
    filtered = {key: value for key, value in identifiers.items()
                if not (key.startswith("amazon_br") and value == prior.get("asin"))}
    if filtered != identifiers:
        api.set_field("identifiers", {book_id: filtered})
        unlinked += 1
print(f"Descrições retiradas: {cleared}; identificadores Amazon retirados: {unlinked}")
