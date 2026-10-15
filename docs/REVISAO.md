# Revisão do projeto — outubro/2026

**Motivo.** O cliente rejeitou o protótipo: *"ficou muito grosseiro e nada intuitivo a ferramenta, os moldes ficaram muito feios"*. Pediu para revisar o projeto, entender a lógica dos moldes SpeedCorel (canal @SpeedcorelBR) e tratar as **duas situações de almofada** (com e sem fotomoldura), com um PRD para orientar o trabalho.

**Base.** Branch `claude/vigilant-volta-8iplfp`, commit `29575cb`. Cinco revisões paralelas: lógica SpeedCorel (medida nos 8 PDFs do cliente), fidelidade dos moldes, auditoria do código, UX do protótipo (capturas em desktop e celular), modelo de domínio e benchmark de mercado. O YouTube e o site da SpeedCorel estão bloqueados no nosso ambiente; a lógica foi **medida nos PDFs** que o cliente enviou e confrontada com material público citado no [PRD](PRD.md).

**Resultado.** O [PRD](PRD.md) passa a ser o documento de referência. Ele tem duas partes: a **Parte A**, para a dona aprovar, e a **Parte B**, o anexo técnico. Esta revisão explica o que existe, o que está bom, o que está errado e por quê, e o que muda.

**Versão 0.2 (15/10/2026).** O PRD e esta revisão passaram por três críticas: a da dona do negócio, a de engenharia e a de completude contra o briefing. O que foi aceito, o que foi aceito em parte e o que foi recusado, com o motivo, está na seção 9, "Decisões da revisão".

---

## 1. Resumo em 8 pontos

1. **O motor de imagem das peças planas é bom** (margem, borda, código, cor, frente e verso, prensa/calandra, entrega no Flexi sem arquivo pela metade): 79 testes passam. Ressalva: a entrega é segura **por arquivo**, não por item (seção 4.5, O4).
2. **Os moldes "feios" têm causa concreta e medida:** (a) a tela mostrava moldes **fictícios** que nem parecem camiseta; (b) a regra de encaixe da arte é **o contrário** da SpeedCorel — recorte 1:1 de um quadro do maior tamanho, alinhado no topo, em vez de escala por tamanho a partir do quadro do M; (c) a saída raster tem linha de corte serrilhada e etiqueta sobre a arte; (d) o importador **joga fora** gola e faixas de punho, o que deixa o "esportivo" idêntico ao "casual".
3. **O "nada intuitivo" vem de não existir interface real:** só a linha de comando com CSV funciona; o React é uma maquete com dados que se contradizem e vocabulário de programador.
4. **Almofada simples e fotomoldura estavam misturadas** numa só tela; só a fotomoldura tinha ajuste, e ajuste por barras deslizantes.
5. **Há um bug grave de perda de arte:** dois itens do mesmo pedido e produto geram o mesmo nome de arquivo e o segundo sobrescreve o primeiro na pasta do RIP (reproduzido).
6. **Não existe etapa de aprovação, banco, estados nem API**; o lote grava direto na pasta do Flexi.
7. **A documentação diverge** (FastAPI × Laravel) e havia uma descrição errada da regra dos moldes em `docs/UNIFORMES.md`.
8. **O que muda:** seção 6 desta revisão — lista priorizada, ligada aos requisitos do PRD.

---

## 2. O que existe hoje

| Parte | O que faz | Estado |
|---|---|---|
| `src/estampa/produtos.py` + `produtos.toml` | Catálogo (fixo e sob medida), configuração, prensa/calandra, pastas do RIP | Funciona |
| `imagem.py` | Leitura, EXIF, sRGB, recorte central, DPI, Real-ESRGAN opcional | Funciona |
| `peca.py` | Peça com margem, borda preta, código; PNG/JPG/PDF; nome do arquivo | Funciona, **com bug de nome** |
| `lote.py` | CSV → itens, geração paralela, entrega no Flexi, distribuição entre impressoras, modo `--montar-rolo` com encaixe próprio (`lote.py:79-102`) | Funciona; CSV frágil |
| `moldura.py` + `rosto.py` | Furos da fotomoldura, composição, rosto (Haar; YuNet sem o modelo instalado) | Funciona, com halo e ajuste por lado inteiro |
| `ordem.py`, `avisos.py`, `painel.py` | OS com ficha PDF, avisos Telegram/WhatsApp/webhook, painel HTTP | Funciona, sem login |
| `moldes.py` | Importador de PDF SpeedCorel → JSON (11 modelos) | Heurístico; perde partes e curvas |
| `uniforme.py` | Arte por parte no molde, logos, nome/número por grade | **Regra de encaixe errada** |
| `cli.py` | Única interface real; também orquestra a OS | — |
| `demo.py`, `demo_web.py` | Demonstração com dados fictícios e upload | Riscos de segurança e de apagar pasta |
| `frontend/` | Protótipo React, 8 telas, dados de `mock.ts`, sem API | Maquete |
| `docs/` | PLANEJAMENTO, FLEXI, UNIFORMES | Desatualizados em pontos-chave |

Números: 3.913 linhas de Python, 1.073 de testes, ~1.290 de TS/TSX. `pytest`: 79 passaram em 43,7 s. `tsc -b`: sem erros.

---

## 3. O que está bom (manter)

- **Regras das peças planas** corretas e testadas: margem, borda de 1 mm, código na margem, frente e verso, cópias, sob medida, limite de 180 cm, prensa/calandra automática (`produtos.py:95-119`).
- **Cor:** conversão para sRGB com perfil ICC e correção de EXIF (`imagem.py:25-48`).
- **Entrega no Flexi atômica por arquivo** (`lote.py:311-327`: grava em `_gravando/` e move com `os.replace`); item com erro não envia nada; carga dividida entre duas pastas. **Ressalva:** os arquivos de um item são movidos um por vez (`lote.py:319-320`), e a subpasta `_gravando/` fica dentro da pasta monitorada. Ver 4.5, O4.
- **Modo `--montar-rolo`** (`lote.py:79-102`, `cli.py:313-330`): encaixa as peças em folhas mantendo a ordem dos pedidos. Pode ser a saída da almofada se o Flexi não mantiver frente e verso juntos (PRD RF-130).
- **Paralelismo com `spawn`**, que se comporta igual no Windows. Desempenho atende o volume: ~0,35 s por peça PNG (4 núcleos) → 2.000 peças em ~11,5 min; 80 peças de uniforme em 9,7 s.
- **Fotomoldura:** detecção automática de furos, várias fotos por moldura, rosto no centro de massa do furo.
- **Avisos** independentes (um canal falhar não derruba os outros); tokens por variável de ambiente.
- **Contorno dos moldes casual, esportivo, polo e basquete fiel** ao PDF (erro ≤ 0,071 mm).
- **Moldes licenciados fora do git** (`.gitignore: moldes/*.json`); a macro protegida por senha não foi aberta.
- **Frontend** com TypeScript estrito e versões fixas — os componentes podem ser reaproveitados; o que precisa mudar é o conteúdo e o fluxo.

---

## 4. O que está errado ou feio, e por quê

### 4.1 Moldes de vestuário (a queixa principal)

| # | Problema | Evidência | Por que importa |
|---|---|---|---|
| M1 | **Moldes fictícios na tela.** `frontend/src/data/moldes-exemplo.json` vem de `src/estampa/moldes_exemplo.py` ("camiseta simplificada"): corpo sem cava (arco convexo em `moldes_exemplo.py:30`), manga em meia-lua. Só 4 tamanhos (8, BLM, M, XGG) | Sobreposição com o molde real: frente 0,931, manga curta BLM **0,635**, manga longa XGG 0,776; desvio de até **11 cm**. 37 pontos contra 147 do real | É a primeira coisa que o cliente vê; parece colete, não camiseta |
| M2 | **Tamanho trocado na prévia.** `tamanhoExemplo` (`frontend/src/components/Molde.tsx:24-29`) manda todo infantil para o 8, todo feminino para o BLM e G para M | Legenda mostra "57×75 cm" para qualquer adulto | "Escala real entre tamanhos" é falso na tela |
| M3 | **Mesmo desenho para todos os modelos.** `Catalogo.tsx:21` | Raglan, polo, regata e shorts aparecem como a mesma camiseta | Nenhum modelo se reconhece |
| M4 | **Regra de encaixe da arte invertida.** `Modelo.quadro()` (`moldes.py:79-85`) usa o **maior** molde da grade; `uniforme.py:299-303` recorta 1:1 alinhado no topo (`produtos.toml:36`: `alinhamento = "topo"`) | SpeedCorel (medido): quadro mestre = **M**, escala por tamanho de **0,634 (tam. 2) a 1,214 (XGG)**, centralizado. Nas costas do tamanho 2 o sistema mostra 51 % × 55 % do quadro (~28 % da arte); o SpeedCorel mostraria ~98 % × 100 % | O escudo e o centro da arte saem cortados nos tamanhos pequenos — "feio" |
| M5 | **Documentação descreve a regra errada.** `docs/UNIFORMES.md:9-13` diz "quadro do tamanho do maior molde… recorta em escala real" | Contradiz a medição nos PDFs | Orientou a implementação errada |
| M6 | **Gola e faixas de punho/barra descartadas pelo importador.** `_retangulo` exclui retângulos (`moldes.py:172-192`); o que está dentro de outra peça é "decoração" (`moldes.py:198-202`); a gola fica acima dos títulos e é pulada (`:350`) | `esportivo.json` = `casual.json` (só mudam `codigo` e `origem`); os PDFs diferem só nas 43 faixas cinza → amarelo | O modelo perde identidade; o motor imprime arte onde deveria haver faixa de cor |
| M7 | **Curvas Bézier achatadas em 8 retas** (`moldes.py:104-119`) | Erro de **3,29 mm** na regata (cava de ~37 cm numa só curva) e 2,28 mm na raglan | Cava facetada visível |
| M8 | **Saída raster grosseira.** Linha de corte com `ImageDraw.line` sem antialias, 3 px a 150 DPI, metade fora da imagem nas bordas (`uniforme.py:338-340`); máscara com só 3 níveis intermediários de cinza na borda (`uniforme.py:245-251`) | Zoom 4×: 844 px pretos puros, nenhum intermediário | Borda serrilhada; no Corel a borda é vetorial e o RIP rasteriza na resolução da máquina |
| M9 | **Etiqueta sobre a arte e longa demais** (`uniforme.py:327-333`): "TIME-01  M  FRENTE CARECA  99 Maximiliano Fernandes" (~10 cm), 1,6 cm acima da barra, centralizada | No Corel: "M FRENTE", 0,47 cm, na margem de costura; na gola/vivo a nossa sai truncada | Polui a peça |
| M10 | **Nome e número por fração da peça**, sem área útil (`uniforme.py:66-73`, `:311-325`) | Regata EXG costas: "AXIMILIANO FERNANDE" cortado pelas cavas; patrocínio invade o decote nos tamanhos pequenos | Em tamanho grande o número desce; em pequeno, invade |
| M11 | **Fonte genérica** (`produtos.toml:39`, `fonte = ""` → DejaVu no Linux, Arial no Windows) | Saída diferente por máquina | Número com cara de genérico |
| M12 | **Tamanhos nomeados por palpite** quando o rótulo está em curvas (`moldes.py:139-169`, `:432-434`) | Polo homem: o sistema gravou XG/EXG (`moldes/polo-homem.json`), mas os rótulos ampliados no PDF dizem **"Gg1" e "Gg2"**. Na polo mulher, o sistema gravou BLXG/BLXGG, e o maior rótulo do PDF é **"Gg2"**, sem o prefixo BL. A versão anterior desta revisão dizia "G1/G2", o que também era palpite. EXG não está em `TAMANHOS_CONHECIDOS` (`:25-29`) | Camiseta do tamanho errado, em silêncio. Nome final: confirmar com a dona (PRD Q-11, RF-135) |
| M13 | **Gerador de padrões em vez de arte real.** Seletor listras/faixas/degradê + 3 cores (`frontend/src/pages/Uniformes.tsx:110-116`); escudo "FC" e "AUTO PEÇAS" fixos (`:185,191,193`; `Molde.tsx:64-87`) | A dona traz a arte pronta do Lovart/Corel | Parece brinquedo; não é o trabalho dela |
| M14 | **Sem vista prévia montada nem resultado por tamanho**; peças soltas lado a lado (`Uniformes.tsx:171-176`) | O SpeedCorel tem Menu de edição → Vista prévia → páginas por tamanho | Falta o fluxo que ela conhece |
| M15 | **Venda/evento sem nomes recusados** (`uniforme.py:146-147`, `:160-161`) | Planilha só com Tamanho e Quantidade dá erro; com Nome e Número vazios, 0 peças sem aviso | Contradiz "moldes para outros usos além do esportivo" |
| M16 | **"Gerar arquivos para o RIP" direto da edição** (`Uniformes.tsx:154`), sem prova nem trava da lista; validação de tamanho é só um ponto vermelho (`:144`) | — | Arquivo errado vai para a impressora |
| M17 | **Regras duplicadas no front já divergem** (`Uniformes.tsx:37-41`, `:191`) | Patrocínio de baixo: 25,2×5,3 cm no front × 26×7 cm em `produtos.toml:68-72` | Prévia ≠ produção |

### 4.2 Almofadas

| # | Problema | Evidência |
|---|---|---|
| A1 | **Bug de colisão de arquivos:** `nome_arquivo` (`peca.py:107-114`) = produto + pedido [+ lado] [+ cópia], **sem o item** | 2 itens `SHP-1` de `almofada-45` com artes diferentes → a CLI diz "2 arquivo(s)", mas só existe `almofada-45_SHP-1.png` (o segundo sobrescreve via `os.replace`, `lote.py:320`). Mesmo problema em `uniforme.py:283` (linhas sem nome) e na demo, que usa o mesmo `peca.nome_arquivo` por meio de `exportar_itens` (`demo.py:304`). A referência anterior, `demo.py:303`, apontava para `ler_pedidos_csv` |
| A2 | **Simples e fotomoldura misturadas** na mesma grade; "Ajustar" só para fotomoldura (`Aprovacao.tsx:45-46`) | Simples não tem rosto nem ajuste no back (`lote.py:229`, `imagem.py:51`): foto em retrato perde cabeças |
| A3 | **Ajuste por barras deslizantes** "Mover para os lados / cima-baixo" de −1 a 1 e zoom só 1×–2× (`Aprovacao.tsx:90-92`) | No Corel ela arrasta o conteúdo do PowerClip |
| A4 | **Miniatura não é o arquivo de produção:** degradês com círculos e palavras (`Miniatura.tsx:127-155`); coração desenhado em vez da moldura real | O card "I ♥ My Boyfriend" mostra "Te Amo" |
| A5 | **Halo na fotomoldura:** onde a moldura tem alpha entre 128 e 254, a foto não vai por baixo (`moldura.py:177`) | Medido: (219,107,113) contra (108,16,22) ao lado |
| A6 | **Ajuste por lado inteiro**, o verso herda o ajuste da frente (`Ajuste` por `Lado`, `lote.py:211`) | — |
| A7 | **Haar na prática** (YuNet aceito em `rosto.py:3-4,38-41`, mas o modelo não está em `modelos/`) | Teste da OpenCV: YuNet 37 rostos × Haar 7 na mesma imagem |
| A8 | **DPI sem contexto** ("58 DPI" sem tamanho nem ação: `Aprovacao.tsx:42`, `mock.ts:111`) | — |
| A9 | **Aprovar não registra nada** (`Aprovacao.tsx:16-20` só mostra um aviso) e envia "na hora" ao Flexi | Sem versão, sem quem, sem desfazer |
| A10 | **Capa de porta sem validação de mínimo** (70×200) | `produtos.py:43-46` só valida o máximo |

### 4.3 Interface e coerência

| # | Problema | Evidência |
|---|---|---|
| U1 | **Só a CLI funciona**; React sem API; duas UIs paralelas (HTML do Python com barra azul e botões em inglês "Choose Files" × React com menu escuro) | `cli.py`, `painel.py`, `demo_web.py`, `frontend/` |
| U2 | **Dados contraditórios** gerados por aritmética modular (`mock.ts:62,109`) | TT-5775300 "Arte não recebida" + "Para aprovar"; "Rosto não encontrado" em capa de porta e almofada simples; SHP-251021H7 "Baixa resolução" + "Expedido" |
| U3 | **Painel com seis números coloridos, nenhum clicável** (`Painel.tsx:10-17`; só 2 botões em `:68,83`), unidades misturadas (pedidos × peças × arquivos) | "Precisa de atenção" fica abaixo da dobra em 1440×900 |
| U4 | **Cards da Aprovação se sobrepõem** (item de `.grade-artes` sem `min-width:0`, `styles.css:189-194`); celular com rolagem lateral (página de 404 px em 390) | Capturas da revisão |
| U5 | **Jargão:** "Painel do sistema aberto dentro do Chatwoot (Dashboard App)" (`Atendimento.tsx:48`), "Evolution API", "_gravando/", slugs e nomes de PDF | — |
| U6 | **Vínculo de arte manual e sem escolher item/furo/lado** ("Usar como arte de…", `Atendimento.tsx:33-36`), inclusive para pedido já "No RIP" | — |
| U7 | **Produção** com kanban genérico de 3 colunas (`Producao.tsx:5`); "Impressora 2" duplicada como prensa e rolo (`mock.ts:149-150`) | Sem lotes, etapas físicas, leitura de código |
| U8 | **Configurações sem botão Salvar** | `Configuracoes.tsx` |
| U9 | **Pedidos sem miniatura e com status por pedido**, quando o trabalho é por item (`Pedidos.tsx:141`); "Ver arquivo"/"Trocar arte" sem ação (`:175`); DPI fixo "64 DPI" (`:171`) | — |

### 4.4 Arquitetura, robustez e segurança

| # | Problema | Evidência |
|---|---|---|
| T1 | **Sem banco, estados, API ou aprovação**; estado em `os.json`, `sequencia.txt`, `resultado.json` com ler-alterar-gravar sem trava | `ordem.py`, `lote.py` |
| T2 | **Três modelos de estado diferentes**: OS com 3 (`ordem.py:54`), front com 6 (`mock.ts:6`), planejamento com 8 | — |
| T3 | **Orquestração na CLI** (`cli.py:130-151`); número da OS reservado **antes** de validar | CSV inválido "queima" números |
| T4 | **`estampa demo --pasta X` apaga a pasta** (`cli.py:278` → `demo.py:273`: `shutil.rmtree`) | `--pasta .` apaga o diretório atual |
| T5 | **Painel e demo em `0.0.0.0` sem login nem CSRF**; upload de 60 MB síncrono; `Image.MAX_IMAGE_PIXELS = None` (`imagem.py:15`, `uniforme.py:37`); a demo serve `produtos.toml` | `painel.py:83`, `demo_web.py:36` |
| T6 | **CSV do Excel pt-BR não é lido** (`;` + cp1252); `int(quantidade)` fora do try, erro sem linha (`lote.py:186`, `:217`) | `erro: utf-8` |
| T7 | **Windows frágil:** `parents[2]` exige `pip install -e` (`produtos.py:13`, `rosto.py:19`); "→" na saída pode quebrar em cp1252; `msvcrt.locking` não liberado (`ordem.py:31-36`) | Não testado no PC do RIP |
| T8 | **Documentação divergente:** FastAPI + Redis/RQ (`PLANEJAMENTO.md`) × Laravel + Inertia (`frontend/README.md`) × Laravel + RabbitMQ (recomendação dada); nenhum registro de decisão | — |
| T9 | **Sem CI, lint, testes de front, LICENSE/NOTICE**; testes de moldes só com PDFs sintéticos feitos para casar com as heurísticas | — |
| T10 | **Licenças:** Evolution API exige aviso visível (não há); foto NASA da demo sem NOTICE; termos SpeedCorel para uso automatizado não confirmados | — |

### 4.5 Omissões encontradas nas críticas à versão 0.1

| # | Problema | Evidência | Onde o PRD trata |
|---|---|---|---|
| O1 | **Modo `--montar-rolo` com encaixe próprio** não era citado | `lote.py:79-102`, `cli.py:313-330` | RF-130 (alternativa para a almofada), RF-144 |
| O2 | **A OS é registrada e avisada mesmo com itens que falharam** | `cli.py:139-151`: registra, gera a ficha e chama `_avisar`, e só depois devolve 1 se houver erros | RF-113 (correção na E0) |
| O3 | **Protótipo mostra capa de porta 70×200 na prensa** | `frontend/src/data/mock.ts:55`; a menor peça (76×206) não cabe em 120×200 | PRD 6.5 |
| O4 | **Entrega "atômica" só por arquivo.** Os arquivos de um item são movidos um por vez, e a subpasta temporária fica dentro da pasta monitorada | `lote.py:316` (`pasta / _gravando`), `lote.py:319-320` (laço de `os.replace`); `docs/FLEXI.md` marca como [conferir] se o Flexi ignora subpastas | RF-96 (critério novo), teste na E0 |
| O5 | **CMYK sem perfil** convertido sem perfil | `imagem.py:41`: só converte com perfil quando há ICC embutido | RN-04, RF-22 |
| O6 | **PDF e HEIC não são lidos** pelo motor, embora a v0.1 exigisse | `imagem.py:25-48` abre tudo com o Pillow | RF-142 (renderizador escolhido pela licença) |
| O7 | **Fotomoldura:** um PNG em 47×47 é aceito sem aviso e ajustado à estampa; um espaço da foto que toca o canto é tratado como fundo e descartado; a ordem dos espaços é por faixas de cima para baixo e depois da esquerda para a direita, e não como dizia o glossário | `lote.py:229-232`; `moldura.py:64-66`; `moldura.py:94-95` | PRD 6.3, RF-31, glossário 5.1 |

---

## 5. Por que o cliente achou "grosseiro e nada intuitivo" — em uma tabela

Os defeitos da seção 4 foram medidos. Que **eles** causaram a rejeição é **suposição nossa**, até a dona responder a Q-18 do PRD olhando as telas antigas.

| Sensação do cliente | Causas (seção 4) | Onde o PRD resolve |
|---|---|---|
| "Os moldes ficaram muito feios" | M1, M2, M3, M4, M6, M7, M8, M9, M10, M11, M13 | PRD 6.8.3 (lógica SpeedCorel), RF-58 a RF-94, RNF-04/05 |
| "Grosseiro" | M8, M13, A4, U2, U4, U5 | PRD Parte A (A4, esboços e "antes × depois"), 10.1 (princípios P1, P4, P8) e 10.2 (aprovação visual antes de programar) |
| "Nada intuitivo" | U1, M14, A3, U3, U6, U9 | PRD Parte A (A3, o dia da dona), 7 (jornadas), 10.3 (menu), RF-36, RF-66, RF-119, RF-126 |
| "Duas situações de almofada" | A2, A3, A5, A6 | PRD 6.2, 6.3, RF-27 a RF-43 |

---

## 6. O que muda a partir do PRD (na mesma ordem das entregas do PRD)

O critério de prioridade é o do PRD (B0): **primeiro o que tira as 1.000 almofadas do Corel**. A prova dos moldes vem já na E0, porque é a queixa principal e só precisa do motor. Datas e critérios de pronto estão no PRD, seção 13.

| Entrega (datas) | Correções e construções | Requisitos do PRD | Itens desta revisão |
|---|---|---|---|
| **E0** (19/10–30/10) | Bug de colisão de nomes e "nunca sobrescrever" (`peca.py:107`, `uniforme.py:283`); limite de pixels; `estampa demo` só apaga pasta que criou; painel e demo em `127.0.0.1`; OS só com número e aviso depois de validar; **prova dos moldes** (antigo × novo × Corel, duas versões de encaixe) e esboços das telas; testes no Flexi; observação de um dia de produção; medição do DPI de ~200 pedidos; 12 perguntas para a dona; corrigir `docs/UNIFORMES.md` | RF-26, RF-52, RF-53, RF-110, RF-113, RF-69 (prova), RF-130 e RF-144 (testes) | A1, T3, T4, T5, M4, M5, O2, O4 |
| **E1** (03/11–13/11) | **Primeiro ganho:** almofada simples pela pasta de artes, com o motor existente, conferência por miniatura real, código com o nº do pedido no canal, frente e verso juntos (ou folha montada), entrega sem item incompleto; em paralelo ao Corel | RF-126, RF-18, RF-20, RF-22–24, RF-28, RF-44, RF-46, RF-54, RF-56, RF-95, RF-96, RF-99, RF-101, RF-130 | A4, A8, O1, O5 |
| **E2** (16/11–27/11) | Banco e login; rodadas de importação do UpSeller; regras de SKU e kit; arte por unidade; mensagens prontas; plano do dia e fim de rolo; PDF e HEIC; agente de entrega; teste das APIs dos canais (P8) | RF-01–08, RF-09 (teste), RF-16, RF-21, RF-97, RF-103, RF-121, RF-125, RF-127, RF-128, RF-131, RF-132, RF-142 | T1, T6, T7, O6 |
| **E3** (30/11–11/12) | Tela Hoje; conferência por exceção (aba da almofada simples); liberação automática e piloto com dois tipos de erro; desfazer; reimpressão pelo arquivo guardado; identificação depois da costura; janelas de liberação; estados em dois níveis | RF-05, RF-27, RF-29, RF-30, RF-41–43, RF-45, RF-47–49, RF-98, RF-100, RF-118, RF-119, RF-122, RF-124, RF-129, RF-143 | A2, A3, A6, A9, U2, U3, U9, T2 |
| **E4** (14/12–08/01) | Fotomoldura: cadastro com validações, YuNet, editor por arrasto, sem halo, texto (se Q-20), ativar/desativar | RF-31–40, RF-57, RF-138 | A5, A7, O7 |
| **E5** (11/01–22/01) | Importador v2 (Bézier, cópias do quadro, gola, faixas, marcadores, nomes de tamanho confirmados); tabela de tamanhos; Menu de edição; encaixe com os três nomes; resultado por tamanho com geometria no navegador; frontend sem moldes fictícios | RF-58–63, RF-65–69, RF-71–75, RF-85, RF-86, RF-135 | M1–M7, M12, M13, M14, M17 |
| **E6** (25/01–05/02) | Lista com tamanho por peça e variação (goleiro, uniforme 2); nomes e números em cm a partir da gola; fonte obrigatória; tamanho sem molde anexado do Corel; prova com aprovação pelo WhatsApp | RF-64, RF-70, RF-76–84, RF-87–89, RF-133, RF-134, RF-136 | M10, M11, M15, M16 |
| **E7** (10/02–23/02) | Saída vetorial do vestuário, etiqueta curta, decisão de encaixe do vestuário; Nova OS na tela; avisos com chip separado; projeto ligado a OS/pedido | RF-90–94, RF-102, RF-109, RF-111, RF-112, RF-114, RF-137, RF-141, RF-144 | M8, M9, U1, U5, T10 |
| **E8** (24/02–09/03) | TV por equipamento; marcação por lote ou prensada; console; relatórios; CI e regressão visual | RF-115–117, RF-120, RF-140, RNF-16 | U7, U8, T9 |
| **E9** (10/03–23/03) | Recepção automática conforme o teste das APIs (ML, Shopee, TikTok) ou Chatwoot e portal só para WhatsApp; Rapid Mockup × construir | RF-10, RF-12, RF-14, RF-15, RF-17, RF-19, RF-50, RF-139; ADR-005 | U6 |
| Depois | Mockups 2D/3D (se não contratar), canecas, DTF, calça | RF-104–108, RF-11, RF-13, RF-25 | — |

Os ADRs (registros de decisão) entram na E0 (ADR-001 a 003 e 006) e na entrega em que cada tema aparece: ADR-004 na E7, ADR-005 na E9 e ADR-007 na E7.

---

## 7. Documentos a atualizar depois da validação

| Documento | Mudança |
|---|---|
| `docs/UNIFORMES.md` | Trocar "quadro do maior molde / escala real / topo" pela regra de escala por tamanho a partir do quadro do M (PRD 6.8.3) |
| `docs/PLANEJAMENTO.md` | Apontar para o PRD; remover a seção de arquitetura (vai para ADRs) e as fases (substituídas pelo roadmap do PRD) |
| `frontend/README.md` | Alinhar a arquitetura com o ADR-001/002 |
| `produtos.toml` | `alinhamento` → `encaixe` por parte; fonte obrigatória; espessura da borda confirmada (Q-62) |
| `frontend/src/data/mock.ts` | Remover a capa de porta 70×200 na prensa (linha 55) e os dados contraditórios |

---

## 8. Evidências

Os arquivos de evidência foram gerados durante a revisão numa pasta temporária de trabalho e **não são versionados** (vários contêm contornos licenciados da SpeedCorel). O que eles mostram:

| Evidência | O que comprova |
|---|---|
| Comparação das costas nos tamanhos 2, 10, BLM, M e XGG — sistema atual × lógica SpeedCorel | M4: arte cortada nos tamanhos pequenos |
| Tabela de instâncias do quadro por tamanho (camiseta tradicional) e medidas dos marcadores | Seção 6.8.3 do PRD |
| Sobreposição molde real × molde do protótipo | M1 |
| Zoom 4× da cava (motor × Corel × PDF vetorial) | M7, M8 |
| PDF vetorial de prova de conceito (regata EXG costas, 0,52 s, 249 KB × ~2 s e 1,5 MB do PNG) | Viabilidade de RF-90; precisa ser testado no Flexi |
| CSV de reprodução da colisão de arquivos | A1 |
| Capturas de 8 telas em desktop e celular + estados interativos | U2 a U9, A2 a A4 |
| `pytest` (79 passaram) e `tsc` sem erros | Seção 2 |
| Medição de halo na moldura esfumada | A5 |
| Ampliação dos rótulos em curvas da polo (`polo_lbl-1.png`, `polo_lbl6-1.png`, `polom_small.png`) | M12: os rótulos são "Gg1" e "Gg2" |
| Contas de capacidade (prensa, papel, conferência) e de resolução (WhatsApp, Lovart) | PRD 6.2, 6.8.3 e 14 |

Fontes web e a lógica SpeedCorel completa estão no [PRD](PRD.md), seção 6.8.3 e Anexo A.

---

## 9. Decisões da revisão (versão 0.2 do PRD)

Três críticas foram aplicadas ao PRD 0.1: a da **dona** (o PRD lido como dona do negócio), a de **engenharia** (viabilidade, conferida no código) e a de **completude** (PRD × briefing e PDFs).

### 9.1 O que mudou no PRD

1. **Duas partes no mesmo arquivo.** A **Parte A** é para a dona (≈ 230 linhas), em linguagem de produção: como é hoje, como vai ser o dia, 5 esboços de tela, "antes × depois", o calendário por mês, as 12 perguntas e uma lista de palavras. A **Parte B** é o anexo técnico, com glossário de termos técnicos explicado (5.2) e as fórmulas só onde quem programa precisa delas.
2. **Recepção de arte do marketplace refeita.** Sai a "mensagem automática com link"; entram a **pasta de artes** (RF-126, 100 fotos em ≤ 5 min), a Caixa de artes com várias fotos de uma vez e as **mensagens prontas para copiar** (RF-132). Nada de link no chat da Shopee ou do ML. O portal fica só para WhatsApp e balcão, na E9.
3. **Rodadas de importação** do UpSeller (3 por dia, com responsável), no lugar de "a cada 15 minutos" (RF-08). A chave do item agora é estável e testada com linhas reordenadas (RF-03). SKU mapeado **por regra e por planilha**, com kit (RF-04, RF-131). **Arte por unidade** (RF-128).
4. **Capacidade.** Prensa com **6 almofadas por prensada** (e não 8), ≈ 334 prensadas e ≈ 8 h por dia; ≈ 317 m de papel por dia; plano para o pico de 3×. Novos requisitos: **plano do dia** (RF-103, que subiu de C para P1) e **fim de rolo** (RF-127); escolha do equipamento por lote ou por dia (RF-101). Seção 14 nova.
5. **Produção física.** Identificação da almofada depois da costura (RF-129); frente e verso juntos e na ordem, ou folha montada (RF-130); marcação **por lote** e etapas configuráveis (RF-140). O sistema termina em `separada`, e a expedição continua no UpSeller.
6. **Resolução.** Separação entre "DPI do arquivo de saída" (fixo) e "DPI mínimo da arte" (calibrado com ~200 pedidos já impressos). Padrão provisório da almofada: **imprime com aviso**, com bloqueio só abaixo de 40 DPI. A meta O1 será recalculada. Vestuário: aviso só abaixo de 100 DPI no maior tamanho, com o PDF do Corel como entrada preferida.
7. **Uniforme.** Tamanho por peça (camisa e short) e variação (goleiro, uniforme 2), com número repetido como aviso (RF-77, RF-78, RF-133). Tamanho sem molde anexado do Corel (RF-134) e tabela de tamanhos (RF-135), o que traz bebê e XXXG para a E6. Aprovação pelo WhatsApp com print (RF-136). Projeto ligado a OS ou pedido (RF-137). Encaixe com nomes que a dona entende e escolha **vendo as duas versões** (RF-69, Q-01). Corte de 28 % da manga BLXG no modo "Sem esticar" documentado.
8. **Estados** em dois níveis com regra de agregação, nomes únicos e todas as transições de cancelamento (7.1).
9. **Arquitetura.** Fila no Postgres; sem MinIO comunitário; híbrido local + borda na nuvem; editor em duas camadas (geometria no navegador, arquivo no motor); backup (RNF-17), monitoramento (RNF-18) e disco (RNF-19); entrega sem item incompleto por mais de 5 s (RF-96); janelas de liberação (RF-143); PDF/HEIC com renderizador escolhido pela licença (RF-142).
10. **Prioridades.** O MoSCoW foi trocado por P1–P4 pelo critério "tirar as almofadas do Corel primeiro", com a entrega de cada requisito. Ficaram 61 requisitos P1, mas a primeira entrega útil (E1, 13/11) depende de 22.
11. **Roadmap** em entregas de 2 semanas com datas (E0 19/10/2026 a E9 23/03/2027), um **ganho rápido** na E1 em paralelo ao Corel e uma seção de transição (13.2).
12. **Marcas de origem revisadas.**
    - A borda de 1 mm e a regra prensa/calandra viraram [PROPOSTA].
    - O RN-06 virou [WEB, a conferir].
    - Os motivos da rejeição viraram hipóteses (1.3).
    - Os rótulos da polo foram corrigidos para "Gg1/Gg2".
    - A fotomoldura foi descrita com o texto completo do briefing.
    - "Vestuário sempre na calandra" virou suposição (Q-60).
    - O volume passou a ser "> 1.000 por dia" [FATO], com o pior caso declarado.
    - A capa de porta passou a ir sempre para a calandra.
    - A recusa na seção 3 passou a valer para "em nenhuma direção".
13. **Perguntas** consolidadas em uma tabela, com destinatário (dona, marido, observação, teste) e prioridade. A Q-17 foi reescrita: o link do tutorial (https://youtu.be/iGNAD_WMnoo) e a opção "EDITAR PRINCIPAL" vêm da página "Menu de edição" que o cliente enviou e são o ponto de partida do estudo dos vídeos. Entraram também as Q-57 a Q-66.
14. **Fontes**: canal @SpeedcorelBR e Rapid Mockup registrados como referências do cliente; fontes novas de ML, UpSeller SAC, Shopee, TikTok, WhatsApp, Lovart, Flexi e MinIO no Anexo A.

### 9.2 Críticas aceitas em parte ou recusadas

| Crítica | Decisão | Por quê |
|---|---|---|
| Dona: "versão de 3–4 páginas **com imagens** e anexo técnico **separado**" | **Em parte** | Nesta rodada só o PRD.md e a REVISAO.md podiam ser alterados. Por isso a versão da dona é a Parte A do mesmo arquivo, com esboços em texto. As **imagens reais** (prova dos moldes, antes × depois) usam moldes licenciados (RF-65) e não podem ir para o git: são entrega da E0, numa pasta privada, aprovadas antes de programar. Separar a Parte A num arquivo próprio fica recomendado depois da validação. A Parte A tem ~230 linhas com 5 esboços, um pouco acima de 4 páginas impressas. |
| Dona: trocar todas as fórmulas por imagens | **Em parte** | Na Parte A não há fórmula. No anexo, a fórmula da escala ficou só como linha "para quem programa", porque o critério de aceite da RF-59 depende dela. |
| Engenharia: "Fase 1a com o editor de vestuário antes das almofadas" | **Recusada** | A dona pediu explicitamente para priorizar "tirar as almofadas do Corel primeiro", e é onde está o volume (> 1.000 por dia). A queixa dos moldes é tratada já na E0, com a prova lado a lado e a escolha do encaixe. O editor vem na E5 (11/01), e os tamanhos que faltam entram na E6 por anexo do Corel. Aceitamos a outra metade da crítica: entregas de 2 semanas, cada uma com demonstração. |
| Engenharia: teste rápido das APIs dos canais **na Fase 0** | **Em parte** | O teste foi para a E2, feito pelo P8 em paralelo. A E0 já está cheia com o que a dona precisa ver, e o fluxo J1 não depende mais das APIs. O resultado reclassifica RF-09 e RF-13 antes da E9. |
| Engenharia: trazer a OS para a Fase 1 | **Em parte** | A OS continua pela linha de comando, que já funciona. As duas correções de risco entram na E0: número reservado só depois de validar (RF-110) e nada de aviso com item falho (RF-113). A tela fica na E7, porque o volume de balcão é pequeno perto das almofadas. |
| Dona: "seção com o **custo mensal estimado** de cada item" | **Em parte** | A seção 14.3 lista cada item de custo e do que ele depende, sem valores: não demos preço sem orçamento nem fonte. O orçamento é tarefa do P8 na E0. O plano de pico (14.2) foi feito com números. |
| Dona: "meu marido baixa os **vídeos** do canal" | **Em parte** | Pedimos as **legendas**, ou que ele assista e anote os minutos, se os termos do YouTube não permitirem baixar os vídeos. O objetivo (estudar o canal sem a dona gravar o YouTube) fica mantido. |
| Dona: bloquear só abaixo de ~40 DPI | **Aceita como provisória** | Virou o padrão até a medição da E0. O número 40 é exemplo da própria dona e será confirmado com 3 provas impressas (A6, pergunta 5). |
| Completude: Groups API oficial com limite de 8 participantes | **Em parte** | A fonte é secundária, e a crítica de engenharia diz que o grupo pela API oficial exige conta OBA. As duas informações estão registradas como [WEB, a conferir] e a decisão fica no ADR-007 (Q-61). Em qualquer caso: chip separado, com Telegram e TV como canais principais. |
| Engenharia: avaliar o modo "conter" por parte | **Em parte** | Fica em avaliação (6.8.3), sem aparecer na tela, para manter três opções simples. Entra se a dona pedir. |
| Dona: padrão de escala escolhido por ela | **Aceita, com padrão provisório** | Até a escolha, o padrão é "Igual ao SpeedCorel", porque é o que ela vende hoje. Isso conflita com o fato "sem esticar nem amassar", e por isso a decisão é dela, na E0, vendo a manga BLXG nas duas versões. |
| Engenharia: "O2 (≤ 10 s) e 300 itens/h (= 12 s) não fecham" | **Crítica parcialmente incorreta** | Mediana de ≤ 10 s por exceção e 300 por hora (12 s em média, incluindo navegação e casos longos) são compatíveis. Corrigimos só o que faltava: a métrica vale para **exceções de almofada simples**. |
| Engenharia: tamanho em disco (12 MB por PNG) | **Aceita, sem nova medição** | O número vem da medição da revisão de engenharia e está marcado assim no PRD (RNF-19). A medição com 50 peças reais na E0 confirma. |
| Dona: "Shopee: regras citadas não são da Shopee Brasil" | **Aceita** | A busca desta rodada também não achou o texto oficial da Shopee Brasil, só um blog brasileiro não oficial (https://gosmarter.com.br/penalidade-shopee/). A regra "nenhum link no chat do marketplace" fica como proposta conservadora até a conferência na Central do Vendedor (Q-46). |
| Completude: Rapid Mockup | **Aceita** | Registrado como referência do cliente e como opção "contratar" no ADR-005 (Q-59). A busca na web não achou página do produto, então o que ele oferece vem só do briefing. |

Todas as demais críticas (de gravidade alta, média e baixa) foram aplicadas como pedido; os pontos estão em 9.1 e nos IDs citados.

### 9.3 Fontes consultadas nesta rodada

- Mercado Livre, mensagens pós-venda e anexos: https://developers.mercadolivre.com.br/pt-br/mensagens-post-venda · https://developers.mercadolivre.com.br/pt-br/motivos-para-se-comunicar · https://developers.mercadolivre.com.br/pt-br/mensagens-bloqueadas
- UpSeller SAC: https://upseller.com/pt/help-doc-article-3174 · https://upseller.com/pt/help-doc-article-533 · https://upseller.com/pt/help-doc-article-1772
- Shopee Brasil (não oficial): https://gosmarter.com.br/penalidade-shopee/
- As demais fontes das críticas estão no Anexo A do PRD.
