# Uniformes de time

Camisetas (e depois regatas, polos, shorts, calças) em toda a grade de
tamanhos, com nome e número de cada jogador, a partir dos moldes do Corel.

## Como funciona

Igual ao modelo SpeedCorel que já é usado no Corel:

1. **Quadro de edição** — a arte de cada parte (frente, costas, mangas) é feita
   uma vez, num quadro do tamanho do **maior molde** da grade.
2. **Moldes por tamanho** — cada molde recorta o seu pedaço da arte **em escala
   real, sem esticar**: alinhado pelo centro e pelo topo (gola/ombro), o P mostra
   um pedaço menor do mesmo desenho que o XGG.
3. **Logos 1–4** — vão nos marcadores do molde (1 peito direito, 2 peito
   esquerdo, 3 manga esquerda, 4 manga direita), com o tamanho que o molde
   define para cada tamanho, sem distorcer a imagem.
4. **Nome, número e patrocínios** — posição relativa à peça e tamanho em cm
   **por grade** (infantil / feminino / adulto), em `[uniformes.elementos]` no
   `produtos.toml`. Nome comprido encolhe para caber, sem achatar.
5. **Saída** — uma imagem por peça (frente, costas, manga esq., manga dir.),
   com linha de corte e etiqueta (pedido, tamanho, parte, número e nome),
   entregue na pasta do Flexi; todas as peças de um jogador chegam juntas.

## Passo a passo

```bash
# 1. importar os moldes (uma vez por modelo) — gera moldes/casual.json e a prévia
estampa moldes importar SPEEDCOREL_CASUAL_tradicionais.pdf --modelo casual
estampa moldes listar        # tamanhos e medida de cada quadro de edição

# 2. gerar o time
estampa uniforme --modelo casual --pedido TIME-01 --jogadores time.xlsx \
  --frente frente.png --costas costas.png --manga manga.png \
  --logo 1=escudo.png --logo 2=patrocinio.png --logo 3=escudo.png --logo 4=escudo.png \
  --elemento patrocinio_costas_topo=marca1.png --elemento patrocinio_costas_base=marca2.png \
  --gola careca --tipo-manga curta --numero-frente

# basquete: regata + short, logos do short nos retângulos D1/D2 e E1/E2
estampa uniforme --modelo basquete --pedido BASQ-1 --jogadores time.xlsx \
  --frente frente.png --costas costas.png --short short.png \
  --logo 1=escudo.png --logo D1=patrocinio.png --logo E1=escudo.png
```

- **Planilha**: a mesma do SpeedCorel (`Nomes`, `Números`) funciona; acrescente
  a coluna `Tamanho` (e `Quantidade`, se precisar). Sem a coluna, use
  `--tamanho M` para todos. Números ficam como texto: `08` continua `08`.
- **Artes**: exporte cada quadro de edição do Corel em PNG, na medida que
  `estampa moldes listar` mostra (ou na mesma proporção). Arte em outra
  proporção é cortada pelo centro, nunca esticada.
- `--tipo-manga longa`, `--gola v`, `--tipo-manga sem` (regata).

## Modelos testados (PDFs SpeedCorel)

| PDF | Modelos gerados | Tamanhos |
|---|---|---|
| CASUAL tradicionais / ESPORTIVO camisetas | `casual`, `esportivo` | 2–14, BLPP–BLXG, PP–XGG |
| CASUAL POLO | `polo-homem`, `polo-mulher` (com gola e manga com barra) | PP–EXG, BLPP–BLXGG* |
| CASUAL raglan | `raglan-unissex`, `raglan-infantil`, `raglan-mulher` | PP–EXG, 2–16, BLP–BLGG |
| CASUAL regata | `regata` | PP–EXG |
| ESPORTIVO basquete | `basquete` (regata + short + gola + filetes) | PP–XG |
| ESPORTIVO shorts | `shorts-feminino`, `shorts-masculino` | P–XG, PP–XG |

\* Onde o PDF tem os tamanhos só desenhados em curvas, os nomes saem pela
ordem de tamanho da peça. Confira na prévia e corrija se precisar:
`estampa moldes importar POLO.pdf --modelo polo --nomes "polo-mulher=BLPP,BLP,BLM,BLG,BLGG,BLXG,BLXGG"`.

## Importação dos moldes (layouts SpeedCorel)

- peça = forma com contorno ou só preenchida; o que fica dentro de outra peça
  (marcador, faixa de punho, etiqueta, linha de costura) é ignorado;
- marcadores: elipse escura com 1–4 (peito e mangas); retângulo azul-marinho
  = perna direita do short (D1, D2), vermelho = perna esquerda (E1, E2);
- tamanho: título acima da coluna, ou escrito à esquerda da linha (basquete),
  ou pela ordem de tamanho (polo, raglan, regata, shorts), com o nome do
  grupo à esquerda (POLO HOMEM) ou acima (Feminino | Masculino);
- parte: 2 marcadores = frente (a de cima gola careca, a de baixo gola V),
  nenhum = costas ou gola (faixa), 1 = manga (3 = esquerda, 4 = direita;
  longa/curta pela altura; curta com barra na polo; raglan na raglan),
  short_dir/short_esq pelos retângulos, faixas estreitas = faixa do short
  ou filete (vivo).

Os moldes importados não vão para o git: são licenciados para a empresa.
A macro da SpeedCorel é protegida por senha e **não foi aberta**; o sistema
reproduz o comportamento (nome e número da planilha nas posições) por conta própria.

## A confirmar com a produção

- Posição e altura de **nome e número** por grade (hoje: número das costas 15 /
  18 / 22 cm, nome 3,5 / 4 / 5 cm) e a **fonte** do time (`fonte = "arquivo.ttf"`).
- Os moldes já incluem a **margem de costura**?
- Grade: **bebê** e **XXXG** (não estão no PDF atual) — importar de outro arquivo.
- Outros modelos: regata, raglan, polo, manga longa, shorts e calças —
  basta exportar cada PDF e importar.
