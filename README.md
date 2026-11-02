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

## Números da exportação

A pasta contém 2.106 registros de livro e 2.445 arquivos, em seis formatos: AZW, AZW3, EPUB, KFX, MOBI e PDF. Todos os registros têm capa. O catálogo foi conferido por SHA-256 e não contém arquivos de ebook idênticos. Os metadados e as capas foram obtidos da biblioteca Calibre local.

## Como localizar

Use a busca do GitHub em `INDICE.md` para localizar por título ou autor. Para filtragem automática, abra `catalogo.csv` em uma planilha ou consuma `catalogo.json`.

## Observações

- Os arquivos KFX/AZW são mantidos no formato de origem da biblioteca e podem exigir software ou dispositivo compatível.
- Os metadados do catálogo refletem a biblioteca local em 2 de novembro de 2026; correções posteriores precisam ser exportadas novamente.
- O repositório contém cópias de ebooks. Compartilhe e use apenas arquivos para os quais você tenha os direitos e permissões necessários.
