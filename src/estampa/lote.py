"""Lote de impressão: monta as peças dos pedidos no rolo de 1,80 m.

O encaixe usa prateleiras (linhas): as peças mais altas abrem as linhas e as
menores aproveitam as sobras. Cada produto é girado ou não conforme cabe
mais área útil por linha (ex.: capa 42x72 em pé cabe 4 por linha).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

from .imagem import Ampliador, ArtePreparada, preparar_arte
from .peca import Peca, desenhar_pdf
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


def ler_pedidos_csv(caminho: Path | str, catalogo: Catalogo) -> list[ItemPedido]:
    """CSV com colunas: pedido, produto, quantidade, arte_frente, arte_verso.

    Caminhos de arte relativos são resolvidos a partir da pasta do CSV.
    """
    base = Path(caminho).resolve().parent
    itens = []
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        for n, linha in enumerate(csv.DictReader(f), start=2):
            produto = catalogo.produto(linha["produto"].strip())
            verso = (linha.get("arte_verso") or "").strip()
            if verso and produto.lados < 2:
                raise ValueError(f"linha {n}: {produto.nome} não aceita verso")
            itens.append(ItemPedido(
                pedido=linha["pedido"].strip(),
                produto=produto,
                quantidade=int(linha.get("quantidade") or 1),
                arte_frente=base / linha["arte_frente"].strip(),
                arte_verso=base / verso if verso else None,
            ))
    return itens


def gerar_pecas(itens: list[ItemPedido], dpi: int, ampliador: Ampliador | None = None,
                espelhar: bool | None = None) -> tuple[list[Peca], list[str]]:
    """Expande cada item em peças (cópias x lados). Retorna também avisos."""
    cache: dict[tuple[Path, str], ArtePreparada] = {}
    avisos: list[str] = []

    def arte(caminho: Path, produto: Produto, pedido: str) -> ArtePreparada:
        chave = (caminho, produto.codigo)
        if chave not in cache:
            cache[chave] = preparar_arte(caminho, produto.largura_cm, produto.altura_cm, dpi, ampliador)
            if cache[chave].dpi_original < dpi:
                avisos.append(
                    f"pedido {pedido}: {caminho.name} tem {cache[chave].dpi_original:.0f} DPI "
                    f"no tamanho final (alvo {dpi})"
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
