"""Mescla registros Calibre com a mesma ficha Amazon verificada.

Prévia: calibre-debug -e tools/mesclar_duplicados_amazon.py
Aplicação: calibre-debug -e tools/mesclar_duplicados_amazon.py -- --apply
Só mescla formatos complementares; remoções vão para a lixeira do Calibre.
"""
import argparse
import csv
import json
import sys
import sqlite3
import subprocess
from collections import defaultdict
from pathlib import Path

from calibre.db.legacy import LibraryDatabase
from decisoes_amazon import decision_for, load_decisions

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = Path(r"D:\CalibreLibrary")
CLI = Path(r"C:\Program Files\Calibre2\calibredb.exe")
LOG = ROOT / "mesclagens_amazon.jsonl"
parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
arguments = parser.parse_args([arg for arg in sys.argv[1:] if arg != "--"])
decisions = ROOT / "DECISOES_AMAZON.csv"
decisions = load_decisions(decisions)

latest = {}
for line in (ROOT / "dados_amazon.jsonl").read_text(encoding="utf-8").splitlines():
    try:
        item = json.loads(line)
        latest[item["id"]] = item
    except (KeyError, ValueError):
        continue

groups = defaultdict(list)
for book_id, item in latest.items():
    if item.get("status") == "verificado" and item.get("asin") and decision_for(decisions, book_id, item) != "rejeitar":
        groups[item["asin"]].append(book_id)

with sqlite3.connect(LIBRARY / "metadata.db") as conn:
    paths = dict(conn.execute("SELECT id,path FROM books"))
    formats = defaultdict(dict)
    for book_id, name, fmt in conn.execute("SELECT book,name,format FROM data"):
        formats[book_id][fmt] = LIBRARY / paths[book_id] / f"{name}.{fmt.lower()}"

tasks = []
for asin, ids in groups.items():
    ids = sorted(book_id for book_id in ids if book_id in paths)
    if len(ids) < 2:
        continue
    keeper = ids[0]
    for duplicate in ids[1:]:
        if set(formats[keeper]) & set(formats[duplicate]):
            print("Ignorado: formatos sobrepostos", keeper, duplicate, flush=True)
            continue
        tasks.append((asin, keeper, duplicate))

print("Pares candidatos:", len(tasks), flush=True)
for asin, keeper, duplicate in tasks:
    print(asin, keeper, duplicate, flush=True)
if not arguments.apply:
    raise SystemExit(0)

db = LibraryDatabase(str(LIBRARY))
api = db.new_api
for asin, keeper, duplicate in tasks:
    current = dict(api.field_for("identifiers", keeper) or {})
    for kind, value in dict(api.field_for("identifiers", duplicate) or {}).items():
        if value in current.values():
            continue
        key = kind
        number = 2
        while key in current:
            key = f"pdoc-asin-{number}"
            number += 1
        current[key] = value
    if asin not in current.values():
        key = "amazon_br"
        number = 2
        while key in current:
            key = f"amazon_br_{number}"
            number += 1
        current[key] = asin
    api.set_field("identifiers", {keeper: current})
db.close()
del db, api

for asin, keeper, duplicate in tasks:
    for fmt, path in formats[duplicate].items():
        result = subprocess.run([str(CLI), "add_format", str(keeper), str(path), "--dont-replace",
                                 "--library-path", str(LIBRARY)], capture_output=True, text=True, errors="replace")
        if result.returncode:
            raise RuntimeError(f"Falha ao anexar {fmt} de {duplicate} a {keeper}: {result.stdout[-400:]} {result.stderr[-400:]}")
    with sqlite3.connect(LIBRARY / "metadata.db") as conn:
        present = {fmt for (fmt,) in conn.execute("SELECT format FROM data WHERE book=?", (keeper,))}
    if not set(formats[duplicate]).issubset(present):
        raise RuntimeError(f"Formatos ausentes após mesclagem: {duplicate} -> {keeper}")
    result = subprocess.run([str(CLI), "remove", str(duplicate), "--library-path", str(LIBRARY)],
                            capture_output=True, text=True, errors="replace")
    if result.returncode:
        raise RuntimeError(f"Falha ao remover registro duplicado {duplicate}: {result.stdout[-400:]}")
    record = {"asin": asin, "keeper": keeper, "duplicate": duplicate,
              "formats_preserved": sorted(formats[duplicate])}
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print("Mesclado", duplicate, "em", keeper, flush=True)

print("Total mesclado:", len(tasks), flush=True)
