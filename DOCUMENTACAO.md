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

A estrutura evita incluir o banco de dados do Calibre e suas configurações pessoais.
