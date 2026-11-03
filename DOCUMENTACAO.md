# Como atualizar o catálogo

O arquivo `catalogo.csv` tem um registro por arquivo de ebook. O arquivo `catalogo.json` agrupa as versões disponíveis por registro da biblioteca de origem.

Campos do CSV:

- ID Calibre: ID do registro na biblioteca de origem.
- Título e Autores: metadados exportados do Calibre.
- Idiomas e Identificadores: quando disponíveis nos metadados.
- Formato e Arquivo: tipo e caminho relativo no repositório.
- Tamanho (bytes): tamanho do arquivo publicado.
- SHA-256: impressão digital do conteúdo para conferir integridade.
- Capa: caminho relativo da imagem de capa, se houver.
- Descrição: texto existente no campo de comentários do Calibre, convertido de HTML para texto simples.
- Fonte da descrição: `Calibre` ou `indisponível`.
- Tema e subtema: classificação automática a partir do título, tags e descrição disponíveis.
- Busca Amazon, URL do produto e status: uma busca sugerida por livro; `não verificado` não significa que o produto foi encontrado.

`TEMAS.md` agrupa os 2.091 livros. A categoria `Outros / A classificar` reúne títulos sem pistas suficientes para uma classificação confiável. `DESCRICOES_PENDENTES.csv` lista as descrições ainda não localizadas. `AMAZON_A_VERIFICAR.csv` registra a busca a conferir para cada livro, sem preencher dados editoriais não confirmados.
`dados_amazon.jsonl` guarda as tentativas e os resultados verificados por ID do Calibre. O último registro de cada ID é o estado atual. `mesclagens_amazon.jsonl` registra os pares com o mesmo ASIN que foram reunidos no Calibre.
`REVISAO_AMAZON.csv` registra fichas rejeitadas por título ou idioma incompatível após nova validação; elas não são tratadas como descrições confirmadas.

Para continuar a coleta pelo Edge e aplicar os resultados verificados:

```powershell
python -m pip install -r requirements-scraping.txt
python tools/coletar_amazon.py --limit 100
"C:\Program Files\Calibre2\calibre-debug.exe" -e tools/aplicar_descricoes_calibre.py
python tools/gerar_metadados_temas.py D:\CalibreLibrary
```

O coletor respeita verificações humanas e interrompe a execução quando a Amazon as apresenta. Resultados sem título e autoria compatíveis ficam pendentes de revisão.

Para recriar esses índices a partir da biblioteca local:

```powershell
python tools/gerar_metadados_temas.py D:\CalibreLibrary
```

A estrutura evita incluir o banco de dados do Calibre e suas configurações pessoais.
