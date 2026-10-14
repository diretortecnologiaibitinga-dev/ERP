# Biblioteca de moldes

Os moldes de vestuário ficam aqui como JSON, um por modelo, importados do PDF
exportado pelo CorelDRAW:

    estampa moldes importar SPEEDCOREL_CASUAL_tradicionais.pdf --modelo casual
    estampa moldes listar
    estampa moldes previa casual --tamanhos 2 BLM XGG

A importação também gera `<modelo>_previa.png` para conferir contornos,
partes (frente gola careca / V, costas, mangas curta / longa) e marcadores de logo.

Os arquivos importados **não vão para o git** (`moldes/*.json`): os moldes
comerciais (ex.: SpeedCorel) são licenciados para uso da empresa.
