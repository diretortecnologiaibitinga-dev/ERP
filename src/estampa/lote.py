"""Lote de impressão a partir de uma planilha de pedidos.

O padrão é exportar um arquivo por peça para a pasta do RIP, que faz o
aproveitamento do rolo. Opcionalmente, `encaixar` monta as peças no rolo de
1,80 m por prateleiras (linhas): as peças mais altas abrem as linhas e as
menores aproveitam as sobras; cada produto é girado ou não conforme cabe
mais área útil por linha (ex.: capa 42x72 em pé cabe 4 por linha).
"""

from __future__ import annotations

import csv
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

from .imagem import Ampliador, ArtePreparada, criar_ampliador, preparar_arte
from .peca import Peca, desenhar_pdf, nome_arquivo, salvar_imagem, salvar_pdf
from .produtos import Catalogo, Produto


@dataclass
class Posicao:
    peca: Peca
    x_cm: float
    y_cm: float          # distância do início do rolo (topo do arquivo)
    rotacionada: bool

    @property
    def largura_cm(self) -> float:
        return self.peca.altura_cm if self.rotacionada else self.peca.largura_cm

    @property
    def altura_cm(self) -> float:
        return self.peca.largura_cm if self.rotacionada else self.peca.altura_cm


@dataclass
class Folha:
    posicoes: list[Posicao] = field(default_factory=list)

    @property
    def comprimento_cm(self) -> float:
        return max((p.y_cm + p.altura_cm for p in self.posicoes), default=0.0)

    def aproveitamento(self, largura_rolo_cm: float) -> float:
        area = sum(p.peca.largura_cm * p.peca.altura_cm for p in self.posicoes)
        return area / (largura_rolo_cm * self.comprimento_cm) if self.posicoes else 0.0


@dataclass
class _Linha:
    y: float
    altura: float
    x_livre: float


def _girar(produto: Produto, largura: float, espaco: float) -> bool:
    def area_por_linha(w: float) -> float:
        n = int((largura + espaco) // (w + espaco))
        return n * w

    em_pe, deitada = produto.largura_total_cm, produto.altura_total_cm
    if em_pe > largura and deitada > largura:
        raise ValueError(f"{produto.nome} não cabe na largura do rolo ({largura} cm)")
    if em_pe > largura:
        return True
    return area_por_linha(deitada) > area_por_linha(em_pe)


def encaixar(pecas: list[Peca], largura_cm: float, espaco_cm: float, comprimento_max_cm: float) -> list[Folha]:
    girar = {p.produto.codigo: _girar(p.produto, largura_cm, espaco_cm) for p in pecas}

    def altura(p: Peca) -> float:
        return p.largura_cm if girar[p.produto.codigo] else p.altura_cm

    folhas: list[Folha] = []
    linhas: list[_Linha] = []
    for peca in sorted(pecas, key=altura, reverse=True):  # sorted é estável: mantém a ordem dos pedidos
        rot = girar[peca.produto.codigo]
        w = peca.altura_cm if rot else peca.largura_cm
        h = altura(peca)
        linha = next((l for l in linhas if h <= l.altura and l.x_livre + w <= largura_cm), None)
        if linha is None:
            y = linhas[-1].y + linhas[-1].altura + espaco_cm if linhas else 0.0
            if not folhas or y + h > comprimento_max_cm:
                folhas.append(Folha())
                linhas, y = [], 0.0
            linha = _Linha(y=y, altura=h, x_livre=0.0)
            linhas.append(linha)
        folhas[-1].posicoes.append(Posicao(peca, linha.x_livre, linha.y, rot))
        linha.x_livre += w + espaco_cm
    return folhas


def salvar_folha_pdf(folha: Folha, destino: Path | str, largura_cm: float, borda_mm: float) -> None:
    comprimento = folha.comprimento_cm
    c = Canvas(str(destino), pagesize=(largura_cm * cm, comprimento * cm))
    for pos in folha.posicoes:
        y_base = comprimento - pos.y_cm - pos.altura_cm  # PDF tem origem embaixo
        desenhar_pdf(c, pos.peca, pos.x_cm, y_base, pos.rotacionada, borda_mm)
    c.showPage()
    c.save()


@dataclass
class ItemPedido:
    pedido: str
    produto: Produto
    quantidade: int
    arte_frente: Path
    arte_verso: Path | None = None


def _medida(valor: str | None) -> float | None:
    valor = (valor or "").strip().replace(",", ".")
    return float(valor) if valor else None


def ler_pedidos_csv(caminho: Path | str, catalogo: Catalogo) -> list[ItemPedido]:
    """CSV com colunas: pedido, produto, quantidade, arte_frente, arte_verso
    e, para produtos sob medida, largura_cm e altura_cm da estampa.

    Caminhos de arte relativos são resolvidos a partir da pasta do CSV.
    """
    base = Path(caminho).resolve().parent
    itens = []
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        for n, linha in enumerate(csv.DictReader(f), start=2):
            try:
                produto = catalogo.produto(linha["produto"].strip())
                largura, altura = _medida(linha.get("largura_cm")), _medida(linha.get("altura_cm"))
                if produto.sob_medida:
                    if largura is None or altura is None:
                        raise ValueError(f"{produto.nome} é sob medida: informe largura_cm e altura_cm")
                    produto = produto.com_medidas(largura, altura)
                elif largura is not None or altura is not None:
                    raise ValueError(f"{produto.nome} tem medida fixa; deixe largura_cm e altura_cm vazias")
                verso = (linha.get("arte_verso") or "").strip()
                if verso and produto.lados < 2:
                    raise ValueError(f"{produto.nome} não aceita verso")
            except (KeyError, ValueError) as e:
                raise ValueError(f"linha {n}: {e.args[0]}") from None
            itens.append(ItemPedido(
                pedido=linha["pedido"].strip(),
                produto=produto,
                quantidade=int(linha.get("quantidade") or 1),
                arte_frente=base / linha["arte_frente"].strip(),
                arte_verso=base / verso if verso else None,
            ))
    return itens


def dpi_do_produto(produto: Produto, padrao: int, forcado: int | None = None) -> int:
    """Prioridade: DPI pedido na hora > DPI do produto > DPI geral."""
    return forcado or produto.dpi or padrao


def gerar_pecas(itens: list[ItemPedido], dpi: int, ampliador: Ampliador | None = None,
                espelhar: bool | None = None, dpi_forcado: int | None = None) -> tuple[list[Peca], list[str]]:
    """Expande cada item em peças (cópias x lados). Retorna também avisos.

    `dpi` é o padrão geral; produtos com DPI próprio (peças grandes) usam o
    seu, a não ser que `dpi_forcado` seja informado.
    """
    cache: dict[tuple[Path, str], ArtePreparada] = {}
    avisos: list[str] = []

    def arte(caminho: Path, produto: Produto, pedido: str) -> ArtePreparada:
        chave = (caminho, produto.codigo)
        if chave not in cache:
            alvo = dpi_do_produto(produto, dpi, dpi_forcado)
            cache[chave] = preparar_arte(caminho, produto.largura_cm, produto.altura_cm, alvo, ampliador)
            if cache[chave].dpi_original < alvo:
                avisos.append(
                    f"pedido {pedido}: {caminho.name} tem {cache[chave].dpi_original:.0f} DPI "
                    f"no tamanho final (alvo {alvo})"
                )
        return cache[chave]

    pecas: list[Peca] = []
    for item in itens:
        lados = [item.arte_frente] + ([item.arte_verso] if item.arte_verso else [])
        for copia in range(1, item.quantidade + 1):
            for lado, caminho in enumerate(lados):
                pecas.append(Peca(
                    produto=item.produto,
                    arte=arte(caminho, item.produto, item.pedido),
                    pedido=item.pedido,
                    lado=lado,
                    copia=copia,
                    total_copias=item.quantidade,
                    frente_verso=len(lados) == 2,
                    espelhar=espelhar,
                ))
    return pecas, avisos


@dataclass(frozen=True)
class OpcoesExportacao:
    saida: Path
    formato: str = "png"      # png | jpg | pdf
    dpi: int = 150                # DPI geral do catálogo
    dpi_forcado: int | None = None
    borda_mm: float = 1.0
    ampliador: str = "lanczos"
    espelhar: bool | None = None


@dataclass
class ResultadoItem:
    pedido: str
    arquivos: list[Path] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    erro: str | None = None


def exportar_item(item: ItemPedido, op: OpcoesExportacao) -> ResultadoItem:
    """Gera os arquivos de um item. Roda em processo separado, então um
    arquivo de arte com problema não derruba o lote inteiro."""
    resultado = ResultadoItem(item.pedido)
    try:
        pecas, resultado.avisos = gerar_pecas([item], op.dpi, criar_ampliador(op.ampliador), op.espelhar, op.dpi_forcado)
        for peca in pecas:
            destino = op.saida / f"{nome_arquivo(peca)}.{op.formato}"
            if op.formato == "pdf":
                salvar_pdf(peca, destino, op.borda_mm)
            else:
                salvar_imagem(peca, destino, dpi_do_produto(peca.produto, op.dpi, op.dpi_forcado), op.borda_mm)
            resultado.arquivos.append(destino)
    except Exception as e:  # noqa: BLE001 — o erro vai para o relatório do lote
        resultado.erro = f"{type(e).__name__}: {e}"
    return resultado


def exportar_itens(itens: list[ItemPedido], op: OpcoesExportacao, processos: int | None = None):
    """Exporta os itens em paralelo, devolvendo os resultados conforme ficam prontos."""
    op.saida.mkdir(parents=True, exist_ok=True)
    processos = processos or os.cpu_count() or 1
    if processos == 1:
        for item in itens:
            yield exportar_item(item, op)
        return
    with ProcessPoolExecutor(max_workers=processos) as pool:
        yield from pool.map(exportar_item, itens, [op] * len(itens))
