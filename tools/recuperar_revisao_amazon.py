"""Recupera fichas antigas cuja correspondência passou nas regras atuais.

Execute sem argumentos para prévia. Use --apply só após o coletor terminar,
pois ambos escrevem no mesmo arquivo JSONL.
"""
import argparse
import csv
import json
from pathlib import Path

from coletar_amazon import clean_title, description_language_ok, title_score

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    books = {book["id"]: book for book in json.loads((ROOT / "catalogo.json").read_text(encoding="utf-8"))}
    decisions = {}
    with (ROOT / "DECISOES_AMAZON.csv").open(encoding="utf-8-sig", newline="") as stream:
        decisions = {int(row["ID Calibre"]): row["Decisão"] for row in csv.DictReader(stream)}
    latest, verified = {}, {}
    checkpoint = ROOT / "dados_amazon.jsonl"
    for line in checkpoint.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        latest[item["id"]] = item
        if item.get("status") == "verificado":
            verified[item["id"]] = item
    recover = []
    for book_id, item in latest.items():
        if (item.get("status") != "revisao_pendente" or book_id not in books
                or book_id not in verified or book_id in decisions):
            continue
        book, prior = books[book_id], verified[book_id]
        score = title_score(clean_title(book["title"], book.get("authors", "")),
                            prior["amazon_title"], prior.get("amazon_authors", ""))
        if (score >= 95 and prior.get("author_match") is True
                and description_language_ok(book, prior["description"])
                and len(prior["description"].strip()) >= 90
                and prior.get("product_url", "").startswith("https://www.amazon.com.br/dp/")):
            recover.append(prior)
    print("Fichas recuperáveis:", len(recover), "IDs:", [item["id"] for item in recover])
    if args.apply and recover:
        with checkpoint.open("a", encoding="utf-8") as stream:
            for item in recover:
                stream.write(json.dumps({**item, "recovered_from_review": True}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
