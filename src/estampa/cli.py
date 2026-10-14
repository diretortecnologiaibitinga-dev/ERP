"""Linha de comando.

    estampa produtos
    estampa peca --produto almofada-45 --pedido 12345 --frente arte.jpg [--verso verso.jpg]
    estampa peca --produto capa-porta --largura 70 --altura 200 --pedido 12345 --frente arte.jpg
    estampa lote pedidos.csv --saida pasta-do-rip/          # um arquivo por peça
    estampa lote pedidos.csv --montar-rolo --saida lotes/   # peças já encaixadas no rolo
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .lote import (ItemPedido, OpcoesExportacao, encaixar, exportar_itens, gerar_pecas,
                   ler_pedidos_csv, salvar_folha_pdf)
from .imagem import criar_ampliador
from .produtos import CATALOGO_PADRAO, carregar_catalogo


def _espelhar(args: argparse.Namespace) -> bool | None:
    """None = usa o padrão de cada produto (hoje o RIP espelha, então é não)."""
    return True if args.espelhar else False if args.nao_espelhar else None


def cmd_produtos(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    for p in cat.produtos.values():
        if p.sob_medida:
            medida = f"sob medida + {p.margem_cm:g} cm de margem"
        else:
            medida = (f"estampa {p.largura_cm:g}x{p.altura_cm:g} cm"
                      f" -> peça {p.largura_total_cm:g}x{p.altura_total_cm:g} cm")
        print(f"{p.codigo:20} {p.nome:28} {medida}, {p.lados} lado(s)")
    return 0


def _opcoes(args: argparse.Namespace, cfg) -> OpcoesExportacao:
    return OpcoesExportacao(
        saida=Path(args.saida), formato=args.formato, dpi=cfg.dpi, dpi_forcado=args.dpi,
        borda_mm=cfg.borda_mm, ampliador=args.ampliador, espelhar=_espelhar(args),
    )


def _relatorio(itens: list[ItemPedido], op: OpcoesExportacao, processos: int | None) -> int:
    inicio, arquivos, erros = time.monotonic(), 0, 0
    for r in exportar_itens(itens, op, processos):
        arquivos += len(r.arquivos)
        for aviso in r.avisos:
            print(f"AVISO: {aviso}", file=sys.stderr)
        if r.erro:
            erros += 1
            print(f"ERRO: pedido {r.pedido}: {r.erro}", file=sys.stderr)
    print(f"{arquivos} arquivo(s) em {op.saida} ({time.monotonic() - inicio:.1f}s)"
          + (f", {erros} item(ns) com erro" if erros else ""))
    return 1 if erros else 0


def cmd_peca(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    produto = cat.produto(args.produto)
    if produto.sob_medida:
        if not (args.largura and args.altura):
            raise ValueError(f"{produto.nome} é sob medida: informe --largura e --altura (cm)")
        produto = produto.com_medidas(args.largura, args.altura)
    item = ItemPedido(args.pedido, produto, args.quantidade,
                      Path(args.frente), Path(args.verso) if args.verso else None)
    return _relatorio([item], _opcoes(args, cat.config), processos=1)


def cmd_lote(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    cfg = cat.config
    itens = ler_pedidos_csv(args.csv, cat)
    if not args.montar_rolo:
        return _relatorio(itens, _opcoes(args, cfg), args.processos)

    largura = args.largura or cfg.largura_rolo_cm
    pecas, avisos = gerar_pecas(itens, cfg.dpi, criar_ampliador(args.ampliador), _espelhar(args), args.dpi)
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

    def opcoes_comuns(p: argparse.ArgumentParser) -> None:
        p.add_argument("--saida", default="saida", help="pasta de saída (ex.: pasta monitorada do RIP)")
        p.add_argument("--formato", choices=["png", "jpg", "pdf"], default="png",
                       help="png sem perdas (padrão), jpg qualidade 95 (mais rápido e leve) ou pdf")
        p.add_argument("--dpi", type=int, help="resolução de saída (padrão do catálogo/produto)")
        p.add_argument("--ampliador", choices=["lanczos", "realesrgan"], default="lanczos",
                       help="realesrgan usa IA (precisa do realesrgan-ncnn-vulkan instalado)")
        g = p.add_mutually_exclusive_group()
        g.add_argument("--espelhar", action="store_true",
                       help="sai espelhado (normalmente não: o RIP já espelha)")
        g.add_argument("--nao-espelhar", action="store_true", help="força sem espelhamento")

    p = sub.add_parser("peca", help="gera os arquivos de um item de pedido")
    p.add_argument("--produto", required=True)
    p.add_argument("--pedido", required=True)
    p.add_argument("--frente", required=True, help="arte da frente")
    p.add_argument("--verso", help="arte do verso (frente e verso)")
    p.add_argument("--quantidade", type=int, default=1)
    p.add_argument("--largura", type=float, help="largura da estampa em cm (produtos sob medida)")
    p.add_argument("--altura", type=float, help="altura da estampa em cm (produtos sob medida)")
    opcoes_comuns(p)
    p.set_defaults(func=cmd_peca)

    p = sub.add_parser("lote", help="gera as peças de todos os pedidos de um CSV")
    p.add_argument("csv")
    p.add_argument("--processos", type=int, help="processos em paralelo (padrão: nº de núcleos)")
    p.add_argument("--montar-rolo", action="store_true",
                   help="em vez de um arquivo por peça, monta as peças no rolo em PDF")
    p.add_argument("--largura", type=float, help="com --montar-rolo: largura útil do rolo em cm")
    p.add_argument("--comprimento-max", type=float, help="com --montar-rolo: comprimento máximo por arquivo")
    opcoes_comuns(p)
    p.set_defaults(func=cmd_lote)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"erro: {e.args[0] if e.args else e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
