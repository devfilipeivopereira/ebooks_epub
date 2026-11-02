"""Exporta sinopses verificadas do Calibre e cria um índice temático.

Uso: python tools/gerar_metadados_temas.py <caminho-da-biblioteca-Calibre>
"""
import csv
import html
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\CalibreLibrary")


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "li", "div", "h1", "h2", "h3"}:
            self.parts.append("\n")


def plain(value):
    parser = TextParser()
    parser.feed(value or "")
    return re.sub(r"\n{3,}", "\n\n", html.unescape("".join(parser.parts))).strip()


def usable_description(value):
    if len(value) < 35:
        return False
    lowered = norm(value)
    if lowered.startswith(("downloaded from", "isbn", "1. ", "2. ")):
        return False
    if lowered in {"nao ha.", "null"}:
        return False
    return True


def norm(value):
    value = unicodedata.normalize("NFKD", value.lower())
    return value.encode("ascii", "ignore").decode("ascii")


# Specific subjects precede broader ones. The title receives priority over tags
# and the publisher description; no claim is made from the ebook body.
RULES = [
    ("Religião e espiritualidade", "Bíblia e interpretação", r"biblia|biblico|genesis|exodo|salmo|proverbio|evangelho|novo testamento|antigo testamento|hebraico|hermeneutica|exegese|apocalipse|paulo apostolo|eclesiastes|romanos|corintios|mateus|lucas|marcos|joao\b|daniel\b|jonas\b|josue\b|samuel\b|comentario expositiv|escrituras|texto sagrado"),
    ("Religião e espiritualidade", "Pregação e ministério", r"pregac|pregando|pregador|sermao|sermoes|homiletic|pastor|ministerio|lideranca crist|igreja em celula|discipulad|igreja|culto|grupo celular|celulas saudaveis|discipulos|fazer discipulos"),
    ("Religião e espiritualidade", "Teologia e doutrina", r"teologia|doutrina|reforma protestante|calvin|cristologia|escatologia|apologetica|cosmovisao|cristianismo|trindade|aliancismo|cre\b|ceticismo|fe na era"),
    ("Religião e espiritualidade", "Vida cristã e devoção", r"devocion|orac|fe crist|espirito santo|santidade|graca de deus|jesus|deus|cristao|espiritual|perdao|profecia|crente|graca\b|fe\b|semear|colher|vida perfeita|dons espirituais"),
    ("Tecnologia e computação", "Inteligência artificial e dados", r"inteligencia artificial|machine learning|aprendizado de maquina|data science|ciencia de dados|deep learning|redes neurais|estatistica|analise de dados|big data"),
    ("Tecnologia e computação", "Programação e desenvolvimento", r"python|javascript|typescript|node\.?js|programac|algoritmo|software|codigo|git\b|regex|express[ao]es regulares|desenvolvimento web|java\b|c#|sql\b|api\b"),
    ("Tecnologia e computação", "UX, produtos e tecnologia", r"ux\b|experiencia do usuario|design de produto|produto digital|inovacao tecnolog|tecnologia"),
    ("Negócios e carreira", "Finanças e investimentos", r"invest|bolsa de valores|mercado financeiro|financ|dinheiro|acoes\b|renda|economia|bitcoin|criptomoed|riqueza|prosperidade|contabilidade|milionario|day trading|bolsa\b"),
    ("Negócios e carreira", "Marketing e vendas", r"marketing|vendas|vender|venda\b|persuas|cliente|negociac|marca\b|branding|copywriting|publicidade|consumidor|contagio|midias sociais"),
    ("Negócios e carreira", "Gestão, liderança e empreendedorismo", r"empreend|empresa|negocio|gestao|lideranc|liderando|estrategia|startup|executivo|administrac|produtividade|trabalho|carreira|equipe|habitos|onboarding|networking|inovacao|organizac"),
    ("Saúde e bem-estar", "Nutrição e exercício", r"nutric|dieta|aliment|musculac|exercicio|emagrec|treino|fitness|metabolismo"),
    ("Saúde e bem-estar", "Saúde física e medicina", r"medicina|saude|doenca|cancer|sono|corpo humano|biomed|medic|inflamac|enfermagem"),
    ("Saúde e bem-estar", "Saúde mental e emoções", r"ansiedade|depressao|emoc|terapia|estresse|mental|autoestima|trauma|psicologia|narcisismo|felicidade"),
    ("Educação e desenvolvimento pessoal", "Aprendizagem e ensino", r"educac|aprendiz|ensino|professor|estud|pedagog|escola|didatic|universidade|curso|ler\b|leitura|notas inteligentes"),
    ("Educação e desenvolvimento pessoal", "Desenvolvimento pessoal", r"autoconhec|sucesso|proposito|motivac|disciplina|foco\b|foque|pensamento|criatividade|comunicac|oratoria|escrever|leitura|escolhas|reinventar|perfeic|expectativas|carisma|maestria|resultados|mente\b|cerebro|segundo cerebro|um dia por vez"),
    ("Humanidades e sociedade", "História e biografias", r"historia|biografia|memoria|guerra|imperio|revoluc|civilizac|seculo|vida de\b|sapiens|humanidade|nexus|harari"),
    ("Humanidades e sociedade", "Filosofia e ética", r"filosof|etica|moral|virtude|estoic|aristot|platao|socra|existencial|seneca|maquiavel|princepe|lac an"),
    ("Humanidades e sociedade", "Política, direito e sociedade", r"politic|direito|lei\b|justica|sociedade|cultura|racismo|social|estado|democracia|poder\b"),
    ("Ciência e natureza", "Ciências exatas e naturais", r"matematic|fisica|quimica|biologia|ciencia|astronom|natureza|evolucao|ecologia"),
    ("Artes e literatura", "Quadrinhos e mangá", r"dragon ball|manga|quadrinho|hq\b|comic"),
    ("Artes e literatura", "Ficção e romances", r"romance|conto|ficcao|fantasia|suspense|poesia|novela|literatura"),
    ("Artes e literatura", "Arte, música e design", r"arte\b|musica|cinema|fotografia|desenho|design|pintura"),
    ("Família e relacionamentos", "Parentalidade e família", r"familia|filhos|pais\b|crianca|bebe|adolescente|casamento|maternidade|paternidade"),
    ("Família e relacionamentos", "Relacionamentos", r"relacionamento|amor\b|amizade|seduc|conversa|comportamento"),
    ("Referência e idiomas", "Dicionários e idiomas", r"dicionario|gramatica|portugues|ingles|idioma|lingua|traduc|espanhol"),
]
COMPILED = [(theme, subtheme, re.compile(pattern)) for theme, subtheme, pattern in RULES]


def classify(title, tags, description):
    fields = [(norm(title), 5), (norm(tags), 3), (norm(description[:500]), 1)]
    scored = []
    for index, (theme, subtheme, pattern) in enumerate(COMPILED):
        score = sum(weight * len(pattern.findall(text)) for text, weight in fields)
        if score:
            scored.append((score, -index, theme, subtheme))
    if scored:
        _, _, theme, subtheme = max(scored)
        return theme, subtheme
    return "Outros", "A classificar"


def main():
    books = json.loads((ROOT / "catalogo.json").read_text(encoding="utf-8"))
    db = sqlite3.connect(f"file:{LIBRARY / 'metadata.db'}?mode=ro", uri=True)
    comments = {}
    for book, text in db.execute("SELECT book,text FROM comments"):
        cleaned = plain(text)
        if usable_description(cleaned):
            comments[book] = cleaned
    tags = defaultdict(list)
    for book, tag in db.execute("SELECT l.book,t.name FROM books_tags_link l JOIN tags t ON t.id=l.tag"):
        tags[book].append(tag)
    rows = []
    for book in books:
        book_id = book["id"]
        description = comments.get(book_id, "")
        theme, subtheme = classify(book["title"], "; ".join(tags[book_id]), description)
        book["description"] = description
        book["description_source"] = "Calibre" if description else "indisponível"
        book["theme"] = theme
        book["subtheme"] = subtheme
        book["tags"] = tags[book_id]
        book["amazon_search_url"] = "https://www.amazon.com.br/s?k=" + quote_plus(book["title"] + " " + book["authors"].split(";")[0])
        book["amazon_product_url"] = ""
        book["amazon_status"] = "não verificado"
        rows.append(book)
    (ROOT / "catalogo.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with (ROOT / "catalogo.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID Calibre", "Título", "Autores", "Idiomas", "Identificadores", "Tema", "Subtema", "Tags Calibre", "Descrição", "Fonte da descrição", "Busca Amazon", "URL do produto Amazon", "Status Amazon", "Formato", "Arquivo", "Tamanho (bytes)", "SHA-256", "Capa"])
        for book in rows:
            for item in book["files"]:
                writer.writerow([book["id"], book["title"], book["authors"], book["languages"], book["identifiers"], book["theme"], book["subtheme"], "; ".join(book["tags"]), book["description"], book["description_source"], book["amazon_search_url"], book["amazon_product_url"], book["amazon_status"], item["format"], item["path"], item["bytes"], item["sha256"], book["cover"]])
    grouped = defaultdict(list)
    for book in rows:
        grouped[(book["theme"], book["subtheme"])].append(book)
    with (ROOT / "TEMAS.md").open("w", encoding="utf-8") as f:
        f.write("# Livros por tema e subtema\n\nClassificação editorial automática a partir do título, tags e descrição disponíveis no Calibre. Revise os casos em **Outros / A classificar**.\n\n")
        counts = Counter(book["theme"] for book in rows)
        f.write("## Resumo\n\n| Tema | Livros |\n|---|---:|\n")
        for theme, count in sorted(counts.items()):
            f.write(f"| {theme} | {count} |\n")
        for theme, subtheme in sorted(grouped):
            f.write(f"\n## {theme} · {subtheme} ({len(grouped[(theme, subtheme)])})\n\n")
            for book in sorted(grouped[(theme, subtheme)], key=lambda b: b["title"].casefold()):
                link = book["files"][0]["path"].replace(" ", "%20")
                title = book["title"].replace("[", "\\[").replace("]", "\\]")
                f.write(f"- [{title}]({link}) — {book['authors']}\n")
    with (ROOT / "DESCRICOES_PENDENTES.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID Calibre", "Título", "Autores", "Identificadores", "Tema", "Subtema"])
        for book in rows:
            if not book["description"]:
                writer.writerow([book["id"], book["title"], book["authors"], book["identifiers"], book["theme"], book["subtheme"]])
    with (ROOT / "AMAZON_A_VERIFICAR.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID Calibre", "Título", "Autores", "Identificadores", "Busca Amazon", "URL do produto verificada", "Descrição Amazon", "Status"])
        for book in rows:
            writer.writerow([book["id"], book["title"], book["authors"], book["identifiers"], book["amazon_search_url"], "", "", "não verificado"])
    print(json.dumps({"books": len(rows), "with_description": sum(bool(b["description"]) for b in rows), "without_description": sum(not b["description"] for b in rows), "themes": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
