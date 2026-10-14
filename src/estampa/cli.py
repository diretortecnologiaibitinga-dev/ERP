"""Linha de comando.

    estampa produtos
    estampa peca --produto almofada-45 --pedido 12345 --frente arte.jpg [--verso verso.jpg]
    estampa peca --produto capa-porta --largura 70 --altura 200 --pedido 12345 --frente arte.jpg
    estampa lote pedidos.csv --saida pasta-do-rip/          # um arquivo por peça
    estampa lote pedidos.csv --montar-rolo --saida lotes/   # peças já encaixadas no rolo
    estampa peca --produto almofada-45 --pedido 1 --moldura coracao-boyfriend --frente foto.jpg
    estampa os itens.csv --cliente "Loja do João" --entrega 20/10   # cliente com arte pronta
    estampa molduras
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import ordem
from .imagem import criar_ampliador
from .lote import (ItemPedido, Lado, OpcoesExportacao, encaixar, exportar_itens, gerar_pecas,
                   ler_pedidos_csv, resolver_moldura, salvar_folha_pdf)
from .moldura import Ajuste, carregar_moldura, detectar_furos
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


def _exportar(itens: list[ItemPedido], op: OpcoesExportacao, processos: int | None):
    """Exporta e imprime o relatório. Devolve (arquivos, avisos, erros)."""
    inicio = time.monotonic()
    arquivos: list[Path] = []
    avisos: list[str] = []
    erros: list[str] = []
    for r in exportar_itens(itens, op, processos):
        arquivos += r.arquivos
        avisos += r.avisos
        if r.erro:
            erros.append(f"pedido {r.pedido}: {r.erro}")
    for aviso in avisos:
        print(f"AVISO: {aviso}", file=sys.stderr)
    for erro in erros:
        print(f"ERRO: {erro}", file=sys.stderr)
    print(f"{len(arquivos)} arquivo(s) em {op.saida} ({time.monotonic() - inicio:.1f}s)"
          + (f", {len(erros)} item(ns) com erro" if erros else ""))
    return arquivos, avisos, erros


def _relatorio(itens: list[ItemPedido], op: OpcoesExportacao, processos: int | None) -> int:
    return 1 if _exportar(itens, op, processos)[2] else 0


def cmd_peca(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    produto = cat.produto(args.produto)
    if produto.sob_medida:
        if not (args.largura and args.altura):
            raise ValueError(f"{produto.nome} é sob medida: informe --largura e --altura (cm)")
        produto = produto.com_medidas(args.largura, args.altura)
        cat.validar_impressao(produto)
    ajuste = Ajuste(args.zoom, args.desloc_x, args.desloc_y)
    lados = [Lado(tuple(map(Path, args.frente)), resolver_moldura(args.moldura or "", Path.cwd(), cat), ajuste)]
    if args.verso:
        lados.append(Lado(tuple(map(Path, args.verso)),
                          resolver_moldura(args.moldura_verso or "", Path.cwd(), cat), ajuste))
    item = ItemPedido(args.pedido, produto, args.quantidade, lados)
    return _relatorio([item], _opcoes(args, cat.config), processos=1)


def cmd_molduras(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    arquivos = sorted(cat.pasta_molduras.glob("*.png"))
    if not arquivos:
        print(f"nenhuma moldura em {cat.pasta_molduras}")
    for caminho in arquivos:
        try:
            img = carregar_moldura(caminho)
            furos = detectar_furos(img)
            info = f"{img.width}x{img.height} px, {len(furos)} espaço(s) para foto"
        except ValueError as e:
            info = f"INVÁLIDA: {e}"
        print(f"{caminho.stem:28} {info}")
    return 0


def cmd_os(args: argparse.Namespace) -> int:
    cat = carregar_catalogo(args.catalogo)
    numero = ordem.proximo_numero(cat.os.pasta, cat.os.prefixo)
    try:
        itens = ler_pedidos_csv(args.csv, cat, pedido_padrao=numero)
    except ValueError:
        print(f"(número {numero} não utilizado)", file=sys.stderr)
        raise
    arquivos, avisos, erros = _exportar(itens, _opcoes(args, cat.config), args.processos)
    os_ = ordem.OrdemServico(
        numero=numero, cliente=args.cliente, criada_em=ordem.agora(), entrega=args.entrega,
        observacoes=args.obs or "", itens=ordem.resumir(itens),
        arquivos=[str(a) for a in arquivos], avisos=avisos, erros=erros,
    )
    pasta = ordem.registrar(cat.os.pasta, os_, itens, Path(args.csv))
    print(f"{numero}: {os_.total_pecas} peça(s) — ficha em {pasta / f'{numero}_ficha.pdf'}")

    webhook = args.webhook or cat.os.webhook_url
    if webhook and not args.sem_aviso:
        try:
            ordem.notificar(webhook, os_)
            print("produção avisada")
        except OSError as e:
            print(f"AVISO: não foi possível avisar a produção ({e})", file=sys.stderr)
    return 1 if erros else 0


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
    p.add_argument("--frente", required=True, nargs="+",
                   help="arte da frente (com moldura: uma foto por espaço da moldura)")
    p.add_argument("--verso", nargs="+", help="arte do verso (frente e verso)")
    p.add_argument("--moldura", help="código da moldura (pasta molduras/) ou PNG; a frente vira a foto")
    p.add_argument("--moldura-verso", help="moldura do verso")
    p.add_argument("--zoom", type=float, default=1.0, help="aproxima a foto dentro da moldura (>= 1)")
    p.add_argument("--desloc-x", type=float, default=0.0, help="move a foto: -1 esquerda ... 1 direita")
    p.add_argument("--desloc-y", type=float, default=0.0, help="move a foto: -1 topo ... 1 base")
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

    p = sub.add_parser("os", help="abre uma ordem de serviço (cliente com arte pronta) e avisa a produção")
    p.add_argument("csv", help="itens da OS (mesmas colunas do lote; a coluna pedido é opcional)")
    p.add_argument("--cliente", required=True)
    p.add_argument("--entrega", help="data de entrega combinada")
    p.add_argument("--obs", help="observações para a produção")
    p.add_argument("--webhook", help="URL para avisar a produção (padrão: [os] webhook_url)")
    p.add_argument("--sem-aviso", action="store_true", help="não dispara o aviso")
    p.add_argument("--processos", type=int, help="processos em paralelo (padrão: nº de núcleos)")
    opcoes_comuns(p)
    p.set_defaults(func=cmd_os)

    sub.add_parser("molduras", help="lista as molduras e quantos espaços para foto cada uma tem"
                   ).set_defaults(func=cmd_molduras)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"erro: {e.args[0] if e.args else e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
