"""Montagem de uma peça de produção.

Reproduz o fechamento feito hoje no Corel: um quadrado do tamanho total
(estampa + margem) com borda preta, a arte recortada dentro da área visível
(como um PowerClip) e o código do pedido escrito na margem branca.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.colors import black, white
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from .imagem import SRGB_ICC, ArtePreparada, cm_para_px
from .produtos import Produto

FONTES = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf")
LADOS = ("FRENTE", "VERSO")


@dataclass
class Peca:
    produto: Produto
    arte: ArtePreparada
    pedido: str
    lado: int = 0           # 0 = frente, 1 = verso
    copia: int = 1
    total_copias: int = 1
    frente_verso: bool = False
    espelhar: bool | None = None  # None = usa o padrão do produto

    @property
    def largura_cm(self) -> float:
        return self.produto.largura_total_cm

    @property
    def altura_cm(self) -> float:
        return self.produto.altura_total_cm

    @property
    def deve_espelhar(self) -> bool:
        return self.produto.espelhar if self.espelhar is None else self.espelhar

    @property
    def etiqueta(self) -> str:
        # números de OS já vêm identificados (OS-000123); pedidos de marketplace não
        partes = [self.pedido if self.pedido.startswith("OS-") else f"PEDIDO {self.pedido}"]
        if self.frente_verso:
            partes.append(LADOS[self.lado])
        if self.total_copias > 1:
            partes.append(f"{self.copia}/{self.total_copias}")
        return "  |  ".join(partes)

    @property
    def tamanho_fonte_cm(self) -> float:
        return self.produto.margem_cm * 0.45


def _base_png(peca: Peca, dpi: int, borda_mm: float) -> Image.Image:
    """Peça sem a etiqueta. Fica guardada na arte: as cópias e o mesmo lado
    repetido só reescrevem o texto, o que pesa em lotes de centenas de peças."""
    cache = peca.arte.__dict__.setdefault("_bases", {})
    chave = (peca.produto.codigo, dpi, borda_mm)
    if chave not in cache:
        p = peca.produto
        w, h = cm_para_px(peca.largura_cm, dpi), cm_para_px(peca.altura_cm, dpi)
        m = cm_para_px(p.margem_cm, dpi)
        img = Image.new("RGB", (w, h), "white")
        arte = peca.arte.imagem
        alvo = (w - 2 * m, h - 2 * m)
        if arte.size != alvo:
            arte = arte.resize(alvo, Image.Resampling.LANCZOS)
        img.paste(arte, (m, m))
        borda = max(1, cm_para_px(borda_mm / 10, dpi))
        ImageDraw.Draw(img).rectangle((0, 0, w - 1, h - 1), outline="black", width=borda)
        cache[chave] = img
    return cache[chave]


def _fonte(tamanho: int) -> ImageFont.FreeTypeFont:
    for nome in FONTES:  # Linux, Windows (arial está na pasta de fontes do sistema), macOS
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(tamanho)


def renderizar_png(peca: Peca, dpi: int, borda_mm: float) -> Image.Image:
    img = _base_png(peca, dpi, borda_mm).copy()
    m = cm_para_px(peca.produto.margem_cm, dpi)
    tamanho = max(8, cm_para_px(peca.tamanho_fonte_cm, dpi))
    fonte = _fonte(tamanho)
    ImageDraw.Draw(img).text((img.width / 2, img.height - m / 2), peca.etiqueta,
                             fill="black", font=fonte, anchor="mm")
    if peca.deve_espelhar:
        img = ImageOps.mirror(img)
    return img


def nome_arquivo(peca: Peca) -> str:
    """Nome começando pelo produto, para o RIP agrupar a fila por produto."""
    nome = f"{peca.produto.codigo}_{peca.pedido}"
    if peca.frente_verso:
        nome += f"_{('frente', 'verso')[peca.lado]}"
    if peca.total_copias > 1:
        nome += f"_{peca.copia}de{peca.total_copias}"
    return nome


def salvar_imagem(peca: Peca, destino: Path | str, dpi: int, borda_mm: float) -> None:
    """Salva em PNG (sem perdas) ou JPG, conforme a extensão do destino.

    PNG usa compressão rápida: no nível padrão do zlib uma almofada a 150 DPI
    leva ~4x mais tempo para salvar, com arquivo só um pouco menor.
    """
    img = renderizar_png(peca, dpi, borda_mm)
    if str(destino).lower().endswith((".jpg", ".jpeg")):
        img.save(destino, "JPEG", quality=95, subsampling=0, dpi=(dpi, dpi), icc_profile=SRGB_ICC)
    else:
        img.save(destino, "PNG", compress_level=1, dpi=(dpi, dpi), icc_profile=SRGB_ICC)


def desenhar_pdf(c: Canvas, peca: Peca, x_cm: float, y_cm: float, rotacionar: bool, borda_mm: float) -> None:
    """Desenha a peça com o canto inferior esquerdo em (x_cm, y_cm).

    Com `rotacionar`, a peça é girada 90° e ocupa altura x largura.
    """
    p = peca.produto
    w, h, m = peca.largura_cm * cm, peca.altura_cm * cm, p.margem_cm * cm
    c.saveState()
    c.translate(x_cm * cm, y_cm * cm)
    if rotacionar:
        c.translate(h, 0)
        c.rotate(90)
    if peca.deve_espelhar:
        c.translate(w, 0)
        c.scale(-1, 1)

    c.setFillColor(white)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.drawImage(ImageReader(io.BytesIO(peca.arte.jpeg)), m, m, w - 2 * m, h - 2 * m)

    borda = borda_mm * mm
    c.setStrokeColor(black)
    c.setLineWidth(borda)
    c.rect(borda / 2, borda / 2, w - borda, h - borda, stroke=1, fill=0)

    tamanho = peca.tamanho_fonte_cm * cm
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", tamanho)
    c.drawCentredString(w / 2, m / 2 - tamanho * 0.35, peca.etiqueta)
    c.restoreState()


def salvar_pdf(peca: Peca, destino: Path | str, borda_mm: float) -> None:
    c = Canvas(str(destino), pagesize=(peca.largura_cm * cm, peca.altura_cm * cm))
    c.setTitle(peca.etiqueta)
    desenhar_pdf(c, peca, 0, 0, False, borda_mm)
    c.showPage()
    c.save()
