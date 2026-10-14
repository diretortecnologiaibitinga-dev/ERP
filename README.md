# Estampa — arquivos de produção para personalizados

Primeira fase do sistema de produção (planejamento completo em
[docs/PLANEJAMENTO.md](docs/PLANEJAMENTO.md)).

A partir da arte do cliente, gera o arquivo de impressão do jeito que hoje é
feito no Corel:

- peça com o tamanho total (estampa + 1 cm de margem de cada lado) e **borda preta**;
- arte enquadrada **dentro** da área visível (como o PowerClip), sem distorcer;
- **código do pedido** na margem branca, com FRENTE/VERSO e cópia (ex.: `2/3`);
- cores sempre em **sRGB** (converte CMYK, Adobe RGB etc.; corrige a rotação de fotos de celular);
- aviso quando a arte tem resolução baixa para o tamanho final;
- **lote**: gera **um arquivo por peça** para a pasta do RIP (que faz o
  aproveitamento do rolo), em paralelo — ~1000 almofadas em poucos minutos;
  um item com problema não para o lote e aparece no relatório;
- produtos **sob medida** (capa de porta, fachada) com a medida vinda do pedido;
- **sem espelhamento** por padrão (o RIP espelha); `--espelhar` quando precisar;
- **fotomoldura**: PNG com transparência onde vai a foto (ex.: o coração); a
  foto do cliente entra por baixo, enquadrada no espaço, e a moldura vai por cima;
- **ordem de serviço** para clientes que mandam a arte pronta: número
  sequencial, arquivos para o RIP, ficha em PDF para a produção e aviso automático;
- recusa peças que não cabem em 1,80 m (rolo/calandra) em nenhuma direção;
- opcional `--montar-rolo`: monta as peças no rolo de 1,80 m em PDF no tamanho real.

| Produto | Estampa | Peça impressa |
|---|---|---|
| `almofada-45` | 45 × 45 cm | 47 × 47 cm |
| `travesseiro-40x70` | 40 × 70 cm | 42 × 72 cm |
| `capa-porta` | sob medida, até 150 × 300 cm (100 DPI) | + 3 cm de cada lado (elástico) |
| `fachada` | sob medida (100 DPI) | + 1 cm de cada lado |

Novos produtos e parâmetros (DPI, largura do rolo, espaçamento, espessura da
borda, espelhamento) ficam em [`produtos.toml`](produtos.toml).

## Instalação

```bash
pip install -e ".[dev]"
```

## Uso

```bash
estampa produtos

# um item: frente e verso, 2 unidades -> 4 PNGs
estampa peca --produto almofada-45 --pedido 250101ABC \
  --frente gato.jpg --verso flores.jpg --quantidade 2 --saida saida/

# sob medida: largura x altura da estampa em cm
estampa peca --produto capa-porta --largura 70 --altura 200 --pedido 250104 --frente porta.jpg

# todos os pedidos da planilha: um arquivo por peça na pasta do RIP
estampa lote exemplos/pedidos.csv --saida /caminho/da/pasta-do-rip
estampa lote exemplos/pedidos.csv --formato jpg      # ~3x mais rápido e leve

# alternativa: peças já encaixadas no rolo de 1,80 m (PDF)
estampa lote exemplos/pedidos.csv --montar-rolo --saida lotes/
```

### Fotomoldura

```bash
# molduras/coracao-boyfriend.png com o coração transparente
estampa peca --produto almofada-45 --pedido 250201 --moldura coracao-boyfriend --frente foto.jpg
# ajuste fino do enquadramento: aproximar e subir a foto
estampa peca ... --zoom 1.3 --desloc-y -0.5
estampa molduras   # lista as molduras e os espaços para foto
```

Na planilha: colunas `moldura` / `moldura_verso` (código ou caminho do PNG),
foto em `arte_frente` (várias fotos separadas por `|`) e, opcionalmente,
`zoom`, `desloc_x`, `desloc_y`. Veja [molduras/LEIAME.md](molduras/LEIAME.md).

### Ordem de serviço (cliente local com arte pronta)

```bash
estampa os exemplos/os_cliente_local.csv --cliente "Loja do João" \
  --entrega 20/10 --obs "Embalar em pares" --saida /caminho/da/pasta-do-rip
```

- numeração `OS-000001`, `OS-000002`… (o número sai na margem de cada peça);
- arquivos de produção direto na pasta do RIP;
- `ordens/OS-000001/` com a **ficha em PDF** (miniaturas, quantidades e campos
  Impresso / Prensado / Costurado / Conferido), `os.json` e a planilha;
- aviso para a produção via `webhook_url` na seção `[os]` do `produtos.toml`
  (JSON com `text` pronto: funciona com n8n, Make, ntfy, Discord ou um robô
  de WhatsApp/Telegram). Se o aviso falhar, a OS é criada mesmo assim.

Os arquivos começam pelo produto, para a fila do RIP ficar agrupada:
`almofada-45_250101ABC_frente_1de2.png`.

Formato do CSV (caminhos relativos à pasta do CSV; `arte_verso` vazio = só
frente; `largura_cm`/`altura_cm` só para produtos sob medida, aceita vírgula):

```csv
pedido,produto,quantidade,arte_frente,arte_verso,largura_cm,altura_cm
250101ABC,almofada-45,2,gato.jpg,flores.jpg,,
250102XYZ,travesseiro-40x70,3,flores.jpg,,,
250104POR,capa-porta,1,flores.jpg,,70,200
```

### Ampliação por IA

`--ampliador realesrgan` usa o [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN/releases)
(`realesrgan-ncnn-vulkan` precisa estar no PATH). Sem ele, a arte é
redimensionada com Lanczos e o sistema só avisa a baixa resolução.

## Testes

```bash
pytest
```
