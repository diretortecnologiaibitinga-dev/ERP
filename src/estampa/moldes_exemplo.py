"""PDF de moldes fictícios no layout dos modelos SpeedCorel (para testes e demonstração).

Os moldes reais são licenciados e não vão para o repositório; este gerador
desenha uma camiseta simplificada em alguns tamanhos, com o mesmo layout:
título do tamanho acima da coluna, moldes com contorno e marcadores de logo
escuros numerados (1 e 2 no peito, 3 e 4 nas mangas).
"""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.colors import Color
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

# tamanho → (fator de escala sobre o M, largura e altura do marcador de logo)
TAMANHOS_EXEMPLO = {"8": (0.75, 7.2, 5.0), "BLM": (0.88, 9.4, 6.5), "M": (1.0, 11.0, 7.6), "XGG": (1.2, 13.0, 9.0)}


def _arco(cx, cy, rx, ry, a0, a1, passos=16):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / passos), cy + ry * math.sin(a0 + (a1 - a0) * i / passos))
            for i in range(passos + 1)]


def contorno_corpo(w: float, h: float, gola: str) -> list[tuple[float, float]]:
    """Frente/costas simplificada, em cm, origem no canto superior esquerdo."""
    pts = [(0.33 * w, 0.0), (0.08 * w, 0.05 * h)]
    pts += _arco(0.08 * w, 0.30 * h, 0.08 * w, 0.25 * h, -math.pi / 2, -math.pi, 8)[1:]  # cava esquerda
    pts += [(0.0, h), (w, h)]
    pts += _arco(0.92 * w, 0.30 * h, 0.08 * w, 0.25 * h, 0.0, -math.pi / 2, 8)
    pts += [(0.67 * w, 0.0)]
    if gola == "careca":
        pts += _arco(0.5 * w, 0.0, 0.17 * w, 0.12 * h, 0.0, math.pi, 16)[1:-1]
    elif gola == "v":
        pts += [(0.5 * w, 0.22 * h)]
    else:  # costas: decote raso
        pts += _arco(0.5 * w, 0.0, 0.17 * w, 0.03 * h, 0.0, math.pi, 12)[1:-1]
    return pts


def contorno_manga(w: float, h: float, longa: bool) -> list[tuple[float, float]]:
    copa = 0.45 * w if longa else 0.6 * h
    pts = [(0.0, copa)] + _arco(0.5 * w, copa, 0.5 * w, copa, math.pi, 2 * math.pi, 20)[1:]
    base = (0.2 * w, 0.8 * w) if longa else (0.05 * w, 0.95 * w)
    return pts + [(base[1], h), (base[0], h)]


def gerar_pdf_moldes_exemplo(destino: Path, tamanhos: dict | None = None) -> Path:
    tamanhos = tamanhos or TAMANHOS_EXEMPLO
    coluna = 150  # cm por coluna de tamanho
    altura = 330
    c = Canvas(str(destino), pagesize=(coluna * len(tamanhos) * cm, altura * cm))
    H = altura

    def poligono(pts, x0, y0, cinza=1.0):
        p = c.beginPath()
        p.moveTo((x0 + pts[0][0]) * cm, (H - y0 - pts[0][1]) * cm)
        for x, y in pts[1:]:
            p.lineTo((x0 + x) * cm, (H - y0 - y) * cm)
        p.close()
        c.setFillColor(Color(cinza, cinza, cinza))
        c.setStrokeColor(Color(0.22, 0.2, 0.21))
        c.setLineWidth(1)
        c.drawPath(p, stroke=1, fill=1)

    def marcador(cx, cy, w, h, numero):
        c.setFillColor(Color(0.184, 0.184, 0.184))
        c.ellipse((cx - w / 2) * cm, (H - cy - h / 2) * cm, (cx + w / 2) * cm, (H - cy + h / 2) * cm, stroke=0, fill=1)
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 40)
        c.drawCentredString(cx * cm, (H - cy) * cm - 14, numero)

    for i, (nome, (s, lw, lh)) in enumerate(tamanhos.items()):
        x = i * coluna + 5
        c.setFillColor(Color(0.4, 0.4, 0.4))
        c.setFont("Helvetica-Bold", 120)
        c.drawCentredString((x + 65) * cm, (H - 12) * cm, nome)
        y = 20
        mw, mlh, mch = 44 * s, 64 * s, 29 * s
        for longa, mh in ((True, mlh), (False, mch)):
            for j, num in enumerate(("3", "4")):
                mx = x + j * (mw + 6)
                poligono(contorno_manga(mw, mh, longa), mx, y)
                marcador(mx + mw / 2, y + mh * 0.3 if longa else y + mh * 0.45, lw, lh, num)
            y += mh + 10
        fw, fh, ch = 57 * s, 75 * s, 78 * s
        for gola in ("careca", "v"):
            poligono(contorno_corpo(fw, fh, gola), x, y)
            for fx, num in ((0.3, "1"), (0.7, "2")):
                marcador(x + fw * fx, y + fh * 0.3, lw, lh, num)
            poligono(contorno_corpo(fw, ch, "costas"), x + fw + 6, y)
            y += max(fh, ch) + 10
    c.showPage()
    c.save()
    return destino


def gerar_pdf_moldes_linhas(destino: Path) -> Path:
    """Layout em linhas (como polo/raglan/regata): nome da linha à esquerda e
    tamanhos sem texto. Duas linhas (POLO HOMEM e POLO MULHER), 3 tamanhos cada,
    com gola, manga de poucos pontos e uma frente com contorno interno (costura)."""
    largura, altura = 520, 360
    c = Canvas(str(destino), pagesize=(largura * cm, altura * cm))
    H = altura

    def poligono(pts, x0, y0):
        p = c.beginPath()
        p.moveTo((x0 + pts[0][0]) * cm, (H - y0 - pts[0][1]) * cm)
        for x, y in pts[1:]:
            p.lineTo((x0 + x) * cm, (H - y0 - y) * cm)
        p.close()
        c.setFillColor(Color(1, 1, 1))
        c.setStrokeColor(Color(0.2, 0.2, 0.2))
        c.drawPath(p, stroke=1, fill=1)

    def marcador(cx, cy, w, h, numero):
        c.setFillColor(Color(0.184, 0.184, 0.184))
        c.ellipse((cx - w / 2) * cm, (H - cy - h / 2) * cm, (cx + w / 2) * cm, (H - cy + h / 2) * cm, stroke=0, fill=1)
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 40)
        c.drawCentredString(cx * cm, (H - cy) * cm - 14, numero)

    for linha, (rotulo, escalas, y) in enumerate((("POLO HOMEM", (1.1, 0.9, 1.0), 10),
                                                  ("POLO MULHER", (0.85, 0.75, 0.8), 190))):
        c.setFillColor(Color(0.2, 0.2, 0.2))
        c.setFont("Helvetica-Bold", 200)
        c.drawString(1 * cm, (H - y - 80) * cm, rotulo)
        for col, s in enumerate(escalas):  # fora de ordem de propósito: o importador ordena pelo tamanho
            x = 120 + col * 130
            fw, fh = 50 * s, 66 * s
            poligono([(0, 2 * s), (50 * s, 0), (52 * s, 6 * s), (2 * s, 8 * s)], x, y)  # gola
            mw, mh = 38 * s, 22 * s
            for j, num in enumerate(("4", "3")):
                manga = [(0, mh * 0.5), (mw * 0.3, 0), (mw * 0.7, 0), (mw, mh * 0.5), (mw * 0.95, mh), (mw * 0.05, mh)]
                poligono(manga, x + j * (mw + 4), y + 12 * s)
                marcador(x + j * (mw + 4) + mw / 2, y + 12 * s + mh * 0.5, 9 * s, 6 * s, num)
            fy = y + 38 * s
            frente = contorno_corpo(fw, fh, "careca")
            poligono(frente, x, fy)
            interno = [(1.5 + px * (fw - 3) / fw, 1.5 + py * (fh - 3) / fh) for px, py in frente]
            poligono(interno, x, fy)
            for fx, num in ((0.3, "1"), (0.7, "2")):
                marcador(x + fw * fx, fy + fh * 0.3, 10 * s, 7 * s, num)
            poligono(contorno_corpo(fw, fh + 3, "costas"), x + fw + 2, fy)
    c.showPage()
    c.save()
    return destino
