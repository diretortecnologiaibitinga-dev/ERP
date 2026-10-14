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

FONTE_TTF = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
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
        partes = [f"PEDIDO {self.pedido}"]
        if self.frente_verso:
            partes.append(LADOS[self.lado])
        if self.total_copias > 1:
            partes.append(f"{self.copia}/{self.total_copias}")
        return "  |  ".join(partes)

    @property
    def tamanho_fonte_cm(self) -> float:
        return self.produto.margem_cm * 0.45


def renderizar_png(peca: Peca, dpi: int, borda_mm: float) -> Image.Image:
    p = peca.produto
    w, h = cm_para_px(peca.largura_cm, dpi), cm_para_px(peca.altura_cm, dpi)
    m = cm_para_px(p.margem_cm, dpi)
    img = Image.new("RGB", (w, h), "white")

    arte = peca.arte.imagem
    alvo = (w - 2 * m, h - 2 * m)
    if arte.size != alvo:
        arte = arte.resize(alvo, Image.Resampling.LANCZOS)
    img.paste(arte, (m, m))

    draw = ImageDraw.Draw(img)
    borda = max(1, cm_para_px(borda_mm / 10, dpi))
    draw.rectangle((0, 0, w - 1, h - 1), outline="black", width=borda)

    tamanho = max(8, cm_para_px(peca.tamanho_fonte_cm, dpi))
    fonte = ImageFont.truetype(str(FONTE_TTF), tamanho) if FONTE_TTF.exists() else ImageFont.load_default(tamanho)
    draw.text((w / 2, h - m / 2), peca.etiqueta, fill="black", font=fonte, anchor="mm")

    if peca.deve_espelhar:
        img = ImageOps.mirror(img)
    return img


def salvar_png(peca: Peca, destino: Path | str, dpi: int, borda_mm: float) -> None:
    renderizar_png(peca, dpi, borda_mm).save(destino, dpi=(dpi, dpi), icc_profile=SRGB_ICC)


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
