"""Linha de comando.

    estampa peca --produto almofada-45 --pedido 12345 --frente arte.jpg [--verso verso.jpg]
    estampa lote pedidos.csv --saida lotes/
    estampa produtos
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .imagem import criar_ampliador
from .lote import ItemPedido, encaixar, gerar_pecas, ler_pedidos_csv, salvar_folha_pdf
from .peca import salvar_pdf, salvar_png
from .produtos import CATALOGO_PADRAO, carregar_catalogo


def _espelhar(args: argparse.Namespace) -> bool | None:
    return True if args.espelhar else False if args.nao_espelhar else None


def cmd_produtos(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    for p in cat.produtos.values():
        print(f"{p.codigo:22} {p.nome:30} estampa {p.largura_cm:g}x{p.altura_cm:g} cm"
              f" -> peça {p.largura_total_cm:g}x{p.altura_total_cm:g} cm, {p.lados} lado(s)")
    return 0


def cmd_peca(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    cfg = cat.config
    dpi = args.dpi or cfg.dpi
    item = ItemPedido(args.pedido, cat.produto(args.produto), args.quantidade,
                      Path(args.frente), Path(args.verso) if args.verso else None)
    pecas, avisos = gerar_pecas([item], dpi, criar_ampliador(args.ampliador), _espelhar(args))
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    for peca in pecas:
        nome = f"{peca.pedido}_{peca.produto.codigo}"
        if peca.frente_verso:
            nome += f"_{('frente', 'verso')[peca.lado]}"
        if peca.total_copias > 1:
            nome += f"_{peca.copia}de{peca.total_copias}"
        destino = saida / f"{nome}.{args.formato}"
        if args.formato == "png":
            salvar_png(peca, destino, dpi, cfg.borda_mm)
        else:
            salvar_pdf(peca, destino, cfg.borda_mm)
        print(destino)
    for aviso in avisos:
        print(f"AVISO: {aviso}", file=sys.stderr)
    return 0


def cmd_lote(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    cfg = cat.config
    dpi = args.dpi or cfg.dpi
    largura = args.largura or cfg.largura_rolo_cm
    itens = ler_pedidos_csv(args.csv, cat)
    pecas, avisos = gerar_pecas(itens, dpi, criar_ampliador(args.ampliador), _espelhar(args))
    folhas = encaixar(pecas, largura, cfg.espaco_entre_pecas_cm, args.comprimento_max or cfg.comprimento_max_cm)

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    prefixo = Path(args.csv).stem
    total = 0.0
    for i, folha in enumerate(folhas, start=1):
        destino = saida / f"{prefixo}_folha{i:02d}.pdf"
        salvar_folha_pdf(folha, destino, largura, cfg.borda_mm)
        total += folha.comprimento_cm
        print(f"{destino}: {len(folha.posicoes)} peças, {folha.comprimento_cm:.1f} cm de rolo, "
              f"aproveitamento {folha.aproveitamento(largura):.0%}")
    print(f"Total: {len(pecas)} peças em {len(folhas)} arquivo(s), {total / 100:.2f} m de rolo")
    for aviso in avisos:
        print(f"AVISO: {aviso}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="estampa", description="Arquivos de produção para sublimação")
    ap.add_argument("--catalogo", default=CATALOGO_PADRAO, help="arquivo produtos.toml")
    sub = ap.add_subparsers(dest="comando", required=True)

    sub.add_parser("produtos", help="lista os produtos cadastrados").set_defaults(func=cmd_produtos)

    def opcoes_imagem(p: argparse.ArgumentParser) -> None:
        p.add_argument("--dpi", type=int, help="resolução de saída (padrão do catálogo)")
        p.add_argument("--ampliador", choices=["lanczos", "realesrgan"], default="lanczos",
                       help="realesrgan usa IA (precisa do realesrgan-ncnn-vulkan instalado)")
        g = p.add_mutually_exclusive_group()
        g.add_argument("--espelhar", action="store_true", help="força espelhamento")
        g.add_argument("--nao-espelhar", action="store_true", help="força sem espelhamento")

    p = sub.add_parser("peca", help="gera os arquivos de um item de pedido")
    p.add_argument("--produto", required=True)
    p.add_argument("--pedido", required=True)
    p.add_argument("--frente", required=True, help="arte da frente")
    p.add_argument("--verso", help="arte do verso (frente e verso)")
    p.add_argument("--quantidade", type=int, default=1)
    p.add_argument("--formato", choices=["png", "pdf"], default="png")
    p.add_argument("--saida", default="saida")
    opcoes_imagem(p)
    p.set_defaults(func=cmd_peca)

    p = sub.add_parser("lote", help="monta os pedidos de um CSV no rolo")
    p.add_argument("csv")
    p.add_argument("--saida", default="saida")
    p.add_argument("--largura", type=float, help="largura útil do rolo em cm")
    p.add_argument("--comprimento-max", type=float, help="comprimento máximo de cada arquivo em cm")
    opcoes_imagem(p)
    p.set_defaults(func=cmd_lote)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
