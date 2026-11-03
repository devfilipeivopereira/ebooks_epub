# Biblioteca de ebooks

Repositório organizado de ebooks exportados da biblioteca Calibre local. O inventário acompanha os arquivos para facilitar consulta por título, autoria, formato e hash.

## Conteúdo

- `EPUB/`: livros EPUB, organizados por autor.
- `Kindle/`: formatos Kindle organizados em `AZW`, `AZW3`, `KFX` e `MOBI`, depois por autor.
- `PDF/`: livros em PDF, organizados por autor.
- `capas/`: capas JPG associadas aos livros que têm capa na biblioteca de origem.
- `INDICE.md`: índice legível com título, autores, formatos e links para os arquivos.
- `catalogo.csv`: índice tabular, inclui tamanho e SHA-256 de cada arquivo.
- `catalogo.json`: catálogo estruturado por livro, com formatos disponíveis.
- `TEMAS.md`: relação por tema e subtema, com links para os livros.
- `DESCRICOES_PENDENTES.csv`: livros sem descrição verificável nos metadados do Calibre.
- `AMAZON_A_VERIFICAR.csv`: busca individual na Amazon e estado de verificação de cada livro.

## Números da exportação

A pasta contém 2.092 registros de livro e 2.446 arquivos, em seis formatos: AZW, AZW3, EPUB, KFX, MOBI e PDF. Todos os registros têm capa. O catálogo foi conferido por SHA-256 e não contém arquivos de ebook idênticos. Os metadados e as capas foram obtidos da biblioteca Calibre local.

O catálogo contém descrição ou sinopse utilizável para 1.341 livros. Os outros 751 estão identificados em `DESCRICOES_PENDENTES.csv`. Foram verificadas 1.085 fichas da Amazon para os registros atuais; cada descrição coletada tem URL da ficha, título e autoria conferidos em `dados_amazon.jsonl`. As rejeições manuais ficam em `DECISOES_AMAZON.csv`.

A classificação temática cobre todos os registros; 384 estão em `Outros / A classificar` por falta de dados suficientes para uma atribuição confiável.

## Como localizar

Use a busca do GitHub em `INDICE.md` para localizar por título ou autor. Para filtragem automática, abra `catalogo.csv` em uma planilha ou consuma `catalogo.json`.

## Observações

- Os arquivos KFX/AZW são mantidos no formato de origem da biblioteca e podem exigir software ou dispositivo compatível.
- Os metadados do catálogo refletem a biblioteca local em 2 de novembro de 2026; correções posteriores precisam ser exportadas novamente.
- O repositório contém cópias de ebooks. Compartilhe e use apenas arquivos para os quais você tenha os direitos e permissões necessários.
