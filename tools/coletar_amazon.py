"""Coleta fichas Amazon Brasil com navegador e checkpoint por livro.

Uso: python tools/coletar_amazon.py --limit 25
Requer: pip install playwright rapidfuzz; Edge instalado no Windows.
O script não usa CAPTCHA, login, proxies ou técnicas para contornar bloqueios.
"""
import argparse
import csv
import json
import random
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright
from rapidfuzz import fuzz
from langdetect import detect, LangDetectException

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalogo.json"
CHECKPOINT = ROOT / "dados_amazon.jsonl"
DECISIONS = ROOT / "DECISOES_AMAZON.csv"
DEFAULT_BROWSER = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
STOP_WORDS = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "um", "uma", "e", "the", "of", "and"}


def normalize(value):
    value = unicodedata.normalize("NFKD", value.lower())
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def title_tokens(value):
    return [token for token in normalize(value).split() if token not in STOP_WORDS]


def canonical(word):
    return word[:-1] if len(word) > 4 and word.endswith("s") else word


def clean_title(title, authors):
    title = re.sub(r"^\s*\(TRAD\)\s*", "", title, flags=re.I)
    title = re.sub(r"^\s*@BibliotecaCrista\s*", "", title, flags=re.I)
    title = re.sub(r"\s*(?:nodrm|compressed|ptbr|edição profissional|z-library)\s*$", "", title, flags=re.I)
    for author in re.split(r"[;|]", authors):
        author = author.strip()
        if len(author) >= 6:
            title = re.sub(r"\s*[-–]\s*" + re.escape(author) + r"\s*$", "", title, flags=re.I)
            title = re.sub(r"\s*\(\s*" + re.escape(author) + r"\s*\)\s*$", "", title, flags=re.I)
            title = re.sub(r"\s+" + re.escape(author) + r"\s*$", "", title, flags=re.I)
    # Imported filenames often contain an author/editor name after the title,
    # even when Calibre's author field is a placeholder.
    title = re.sub(r"\s*[-–]\s*(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*\s+){1,2}[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*\s*$", "", title)
    title = re.sub(r"\s*\((?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*\s+){1,2}[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç.]*\)\s*$", "", title)
    return title.strip(" -–_")


def title_score(expected, actual, byline=""):
    left_tokens = title_tokens(expected)
    byline_norm = normalize(byline)
    author = re.search(r"\bpor\s+(.+?)\s+autor\b", byline_norm)
    if author:
        author_tokens = title_tokens(author.group(1))
        if author_tokens and left_tokens[:len(author_tokens)] == author_tokens:
            left_tokens = left_tokens[len(author_tokens):]
        if author_tokens and left_tokens[-len(author_tokens):] == author_tokens:
            left_tokens = left_tokens[:-len(author_tokens)]
    right_tokens = title_tokens(actual)
    left, right = " ".join(left_tokens), " ".join(right_tokens)
    if not left or not right:
        return 0
    if re.search(r"\b(box|colecao|combo|kit)\b", right) and not re.search(r"\b(box|colecao|combo|kit)\b", left):
        return 0
    if re.search(r"\b(resumo|summary|guia de estudo)\b", right) and not re.search(r"\b(resumo|summary|guia de estudo)\b", left):
        return 0
    expected_words = {canonical(word) for word in left.split() if len(word) >= 3 or word.isdigit()}
    actual_words = {canonical(word) for word in right.split()}
    if expected_words:
        if len(expected_words) <= 3 and not right.startswith(left):
            return 0
        coverage = sum(any(word == candidate or len(word) >= 3 and candidate.startswith(word) for candidate in actual_words)
                       for word in expected_words) / len(expected_words)
        needed = 1.0 if len(expected_words) <= 2 else 0.75
        if coverage < needed:
            main = " ".join(title_tokens(expected.split(":", 1)[0]))
            main_words = {canonical(word) for word in main.split() if len(word) >= 3}
            if len(main_words) < 3 or not right.startswith(main):
                return 0
    # Require volume numbers to agree when both titles specify one.
    volume = re.search(r"\b(?:vol(?:ume)?|livro|book)\s*(\d+)\b", left)
    other_volume = re.search(r"\b(?:vol(?:ume)?|livro|book)\s*(\d+)\b", right)
    if volume and other_volume and volume.group(1) != other_volume.group(1):
        return 0
    if volume and not other_volume:
        product_numbers = set(re.findall(r"\b\d+\b", right))
        if product_numbers and volume.group(1) not in product_numbers:
            return 0
    return max(fuzz.WRatio(left, right), fuzz.token_set_ratio(left, right))


def author_ok(authors, byline):
    authors_norm = normalize(authors)
    if not authors_norm or any(x in authors_norm for x in ("unknown", "felipe ivo pereira", "desktop", "sem autor")):
        return None
    byline_norm = normalize(byline)
    if not byline_norm:
        return False
    names = re.split(r"[;|,]", authors)
    for name in names:
        words = [word for word in normalize(name).split() if len(word) >= 4]
        if words and words[-1] in byline_norm.split():
            return True
    return False


def description_language_ok(book, description):
    if "por" not in book.get("languages", "").split(";") or len(description) < 160:
        return True
    try:
        language = detect(description)
    except LangDetectException:
        return True
    if language == "pt":
        return True
    # An existing description in the same language is evidence that the
    # Calibre language field is inaccurate for this edition.
    existing = book.get("description", "")
    if existing:
        try:
            return detect(existing) == language
        except LangDetectException:
            pass
    return False


def existing_results():
    results = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                results[item["id"]] = item
            except (ValueError, KeyError):
                continue
    if DECISIONS.exists():
        with DECISIONS.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["Decisão"] == "rejeitar":
                    book_id = int(row["ID Calibre"])
                    if book_id in results:
                        results[book_id] = {"id": book_id, "status": "rejeitado_na_revisao"}
    return results


def save(item):
    item["checked_at"] = datetime.now(timezone.utc).isoformat()
    with CHECKPOINT.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        stream.flush()


def get_text(page, selector):
    node = page.locator(selector)
    return node.first.inner_text(timeout=1500).strip() if node.count() else ""


def blocked(page):
    text = page.locator("body").inner_text(timeout=5000)[:3000].lower()
    return any(term in text for term in ("digite os caracteres", "enter the characters", "robot check", "verifique se você é humano"))


def search(page, book):
    query = clean_title(book["title"], book.get("authors", ""))
    author = book.get("authors", "").split(";")[0]
    if author and author_ok(author, author) is not None:
        query += " " + author
    url = "https://www.amazon.com.br/s?k=" + quote_plus(query[:180])
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    if not response or response.status >= 500:
        raise RuntimeError("Amazon retornou erro HTTP na busca")
    if blocked(page):
        raise RuntimeError("Amazon bloqueou a busca com verificação humana")
    candidates = []
    for card in page.locator('[data-component-type="s-search-result"]').all()[:12]:
        asin = card.get_attribute("data-asin") or ""
        name = get_text(card, "h2")
        if not re.fullmatch(r"[A-Z0-9]{10}", asin) or not name:
            continue
        score = title_score(clean_title(book["title"], book.get("authors", "")), name)
        candidates.append((score, asin, name))
    candidates.sort(reverse=True)
    return url, candidates


def direct_ids(book):
    identifiers = book.get("identifiers", "")
    result = []
    for kind, value in re.findall(r"([\w-]+):([^;]+)", identifiers):
        cleaned = re.sub(r"[^A-Z0-9]", "", value.upper())
        if kind == "isbn" and len(cleaned) in (10, 13):
            result.append(cleaned)
        elif kind in ("asin", "mobi-asin") and len(cleaned) == 10:
            result.append(cleaned)
    return list(dict.fromkeys(result))


def get_product(page, asin):
    url = f"https://www.amazon.com.br/dp/{asin}"
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    if not response or response.status >= 500:
        raise RuntimeError("Amazon retornou erro HTTP na ficha")
    if blocked(page):
        raise RuntimeError("Amazon bloqueou a ficha com verificação humana")
    title = get_text(page, "#productTitle") or get_text(page, "#title")
    byline = get_text(page, "#bylineInfo")
    description = (get_text(page, "#bookDescription_feature_div")
                   or get_text(page, "#productDescription")
                   or get_text(page, "#bookDescription_feature_div noscript"))
    description = re.sub(r"\s+", " ", description).strip()
    return url, title, byline, description


def description_is_synopsis(value):
    """Descarta anúncios de estado físico e kits usados como falsa sinopse."""
    text = normalize(value)
    condition_prefixes = (
        "atencao ano correto do exemplar", "livros novos e fisicos este kit contem",
        "livro de capas em brochura", "livro em bom estado", "livro usado em bom estado",
        "brochura em bom estado", "brochura otimo estado",
    )
    return len(value.strip()) >= 90 and not text.startswith(condition_prefixes)


def process(page, book):
    cleaned_title = clean_title(book["title"], book.get("authors", ""))
    for asin in direct_ids(book):
        url, title, byline, description = get_product(page, asin)
        score = title_score(cleaned_title, title, byline)
        author_match = author_ok(book.get("authors", ""), byline)
        if score >= (92 if author_match is None else 83) and author_match is not False and description_is_synopsis(description) and description_language_ok(book, description):
            return {"id": book["id"], "status": "verificado", "asin": asin,
                    "product_url": url, "search_url": "", "amazon_title": title,
                    "amazon_authors": byline, "title_score": round(score, 1),
                    "author_match": author_match, "description": description}
    search_url, candidates = search(page, book)
    if not candidates:
        # Some editions are not returned when the author is part of the query.
        title_only = dict(book)
        title_only["authors"] = ""
        search_url, candidates = search(page, title_only)
    if not candidates:
        return {"id": book["id"], "status": "sem_resultado", "search_url": search_url}
    # Product-page checks are mandatory; search snippets are never descriptions.
    for search_score, asin, result_title in candidates[:3]:
        if search_score < 82:
            break
        time.sleep(random.uniform(0.7, 1.3))
        url, title, byline, description = get_product(page, asin)
        score = title_score(cleaned_title, title, byline)
        author_match = author_ok(book.get("authors", ""), byline)
        threshold = 92 if author_match is None else 83
        if score < threshold or author_match is False or not description_is_synopsis(description) or not description_language_ok(book, description):
            continue
        return {"id": book["id"], "status": "verificado", "asin": asin,
                "product_url": url, "search_url": search_url, "amazon_title": title,
                "amazon_authors": byline, "title_score": round(score, 1),
                "author_match": author_match, "description": description}
    return {"id": book["id"], "status": "sem_correspondencia_confiavel", "search_url": search_url,
            "candidates": [{"score": round(score, 1), "asin": asin, "title": name}
                           for score, asin, name in candidates[:3]]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--browser-path", type=Path, default=DEFAULT_BROWSER)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--retry-errors", action="store_true",
                        help="Reprocessa apenas falhas de rede e HTTP registradas")
    args = parser.parse_args()
    books = json.loads(CATALOG.read_text(encoding="utf-8"))
    seen = existing_results()
    if args.retry_errors:
        pending = [book for book in books if seen.get(book["id"], {}).get("status") == "erro"]
    else:
        pending = [book for book in books if book["id"] not in seen or
                   (args.retry_failed and seen[book["id"]]["status"] != "verificado")]
    print(f"Total: {len(books)}; já processados: {len(seen)}; pendentes: {len(pending)}", flush=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(args.browser_path), headless=True)
        page = browser.new_page(locale="pt-BR", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
        for book in pending[:args.limit]:
            for attempt in range(2):
                try:
                    item = process(page, book)
                    break
                except Exception as error:
                    message = str(error)
                    if attempt == 0 and any(term in message for term in
                                            ("net::ERR_", "Timeout", "erro HTTP")):
                        time.sleep(random.uniform(2, 4))
                        continue
                    item = {"id": book["id"], "status": "erro", "error": message[:250]}
                    break
            save(item)
            print(book["id"], item["status"], item.get("asin", ""), flush=True)
            if item["status"] == "erro" and "bloqueou" in item.get("error", ""):
                print("Acesso bloqueado; interrompendo para respeitar a fonte.", flush=True)
                break
            time.sleep(random.uniform(1.2, 2.4))
        browser.close()


if __name__ == "__main__":
    main()
