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
- **lote**: monta as peças de vários pedidos no rolo de **1,80 m**, em PDF no tamanho real,
  girando cada produto para caber mais por linha e dividindo em arquivos de até 3 m.

| Produto | Estampa | Peça impressa |
|---|---|---|
| `almofada-45` | 45 × 45 cm | 47 × 47 cm |
| `travesseiro-40x70` | 40 × 70 cm | 42 × 72 cm |

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

# vários pedidos montados no rolo (PDF)
estampa lote exemplos/pedidos.csv --saida saida/
```

Formato do CSV (caminhos relativos à pasta do CSV; `arte_verso` vazio = só frente):

```csv
pedido,produto,quantidade,arte_frente,arte_verso
250101ABC,almofada-45,2,gato.jpg,flores.jpg
250102XYZ,travesseiro-40x70,3,flores.jpg,
```

### Ampliação por IA

`--ampliador realesrgan` usa o [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN/releases)
(`realesrgan-ncnn-vulkan` precisa estar no PATH). Sem ele, a arte é
redimensionada com Lanczos e o sistema só avisa a baixa resolução.

## Testes

```bash
pytest
```
