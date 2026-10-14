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
```

- **Planilha**: a mesma do SpeedCorel (`Nomes`, `Números`) funciona; acrescente
  a coluna `Tamanho` (e `Quantidade`, se precisar). Sem a coluna, use
  `--tamanho M` para todos. Números ficam como texto: `08` continua `08`.
- **Artes**: exporte cada quadro de edição do Corel em PNG, na medida que
  `estampa moldes listar` mostra (ou na mesma proporção). Arte em outra
  proporção é cortada pelo centro, nunca esticada.
- `--tipo-manga longa`, `--gola v`, `--tipo-manga sem` (regata).

## Importação dos moldes (layout SpeedCorel)

- molde = forma com linha de contorno (o preenchimento pode ter qualquer cor);
- marcador de logo = forma escura com o número 1–4 dentro;
- tamanho = título acima da coluna (2, 4… 14, BLPP… BLXG, PP… XGG);
- parte: 2 marcadores = frente (a de cima gola careca, a de baixo gola V),
  nenhum = costas, 1 = manga (a mais alta é a longa; 3 = esquerda, 4 = direita).

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
