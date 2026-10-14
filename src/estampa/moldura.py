"""Fotomoldura: foto do cliente por baixo de uma moldura com furos transparentes.

A moldura é um PNG do tamanho da estampa (ex.: 45x45) com transparência só
onde vai a foto (o coração). Cada furo é detectado automaticamente; a foto é
enquadrada para cobrir o furo e a moldura é aplicada por cima, então a borda
interna da moldura fica sempre sobre a foto. Molduras com vários furos
(casal, colagem) recebem uma foto por furo, da esquerda para a direita e de
cima para baixo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import rosto as _rosto
from .imagem import Ampliador, carregar_rgb

_MAX_LADO_DETECCAO = 512


@dataclass(frozen=True)
class Ajuste:
    """Ajuste fino do enquadramento da foto dentro do furo.

    zoom >= 1 aproxima; desloc_x/desloc_y de -1 a 1 movem o recorte até o
    limite da foto (-1 = esquerda/topo, 1 = direita/base). Informar qualquer
    ajuste desliga o enquadramento automático pelo rosto.
    """
    zoom: float = 1.0
    desloc_x: float = 0.0
    desloc_y: float = 0.0

    @property
    def manual(self) -> bool:
        return self != Ajuste()


@dataclass
class Furo:
    caixa: tuple[int, int, int, int]  # (x0, y0, x1, y1) na resolução da moldura
    mascara: Image.Image              # "L" do tamanho da moldura, 255 dentro do furo


def carregar_moldura(caminho: Path | str) -> Image.Image:
    img = Image.open(caminho)
    if "A" not in img.getbands() and "transparency" not in img.info:
        raise ValueError(f"{Path(caminho).name}: a moldura precisa ser PNG com transparência onde vai a foto")
    return img.convert("RGBA")


def detectar_furos(moldura: Image.Image, limiar: int = 128) -> list[Furo]:
    """Regiões transparentes que não tocam os cantos da imagem.

    Se o fundo externo da moldura também for transparente, ele é ignorado.
    A detecção roda numa cópia reduzida e as máscaras voltam ao tamanho real.
    """
    w, h = moldura.size
    escala = min(1.0, _MAX_LADO_DETECCAO / max(w, h))
    pequena = moldura.getchannel("A").resize(
        (max(1, round(w * escala)), max(1, round(h * escala))), Image.Resampling.BOX)
    # dilata 1 px na escala reduzida: faixas finas do mesmo furo continuam ligadas
    mascara = pequena.point(lambda a: 255 if a < limiar else 0).filter(ImageFilter.MaxFilter(3))
    pw, ph = mascara.size

    for canto in ((0, 0), (pw - 1, 0), (0, ph - 1), (pw - 1, ph - 1)):
        if mascara.getpixel(canto) == 255:
            ImageDraw.floodfill(mascara, canto, 0)

    regioes = []
    rotulo = 1
    while rotulo < 255:
        restante = mascara.point(lambda v: 255 if v == 255 else 0).getbbox()
        if not restante:
            break
        semente = _primeiro_pixel(mascara, restante)
        ImageDraw.floodfill(mascara, semente, rotulo)
        regiao = mascara.point(lambda v, r=rotulo: 255 if v == r else 0)
        caixa = regiao.getbbox()
        if caixa and (caixa[2] - caixa[0]) * (caixa[3] - caixa[1]) >= 0.01 * pw * ph:  # ignora respingos
            regioes.append(regiao)
        rotulo += 1

    furos = []
    for regiao in regioes:
        cheia = regiao.resize((w, h), Image.Resampling.NEAREST).filter(ImageFilter.MaxFilter(5))
        furos.append(Furo(caixa=cheia.getbbox(), mascara=cheia))
    linha = max(1, h // 10)
    furos.sort(key=lambda f: (f.caixa[1] // linha, f.caixa[0]))
    return furos


def _primeiro_pixel(mascara: Image.Image, caixa: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = caixa
    for y in range(y0, y1):
        for x in range(x0, x1):
            if mascara.getpixel((x, y)) == 255:
                return x, y
    raise AssertionError("caixa sem pixel marcado")


def recortar_cobrindo(img: Image.Image, proporcao: float, ajuste: Ajuste = Ajuste()) -> Image.Image:
    """Recorte com a proporção pedida, aplicando zoom e deslocamento."""
    w, h = img.size
    if w / h > proporcao:
        cw, ch = h * proporcao, h
    else:
        cw, ch = w, w / proporcao
    zoom = max(1.0, ajuste.zoom)
    cw, ch = cw / zoom, ch / zoom
    livre_x, livre_y = (w - cw) / 2, (h - ch) / 2
    cx = w / 2 + max(-1.0, min(1.0, ajuste.desloc_x)) * livre_x
    cy = h / 2 + max(-1.0, min(1.0, ajuste.desloc_y)) * livre_y
    return img.crop((round(cx - cw / 2), round(cy - ch / 2), round(cx + cw / 2), round(cy + ch / 2)))


@dataclass
class Composicao:
    imagem: Image.Image
    dpi_fotos: float    # menor DPI entre as fotos, considerando o tamanho do furo na peça
    dpi_moldura: float  # DPI do PNG da moldura no tamanho da estampa
    avisos: list[str] = field(default_factory=list)


def compor(
    moldura_caminho: Path | str,
    fotos: list[Path] | tuple[Path, ...],
    largura_cm: float,
    largura_px_min: int,
    ajuste: Ajuste = Ajuste(),
    ampliador: Ampliador | None = None,
    rosto: bool = True,
) -> Composicao:
    """Monta foto(s) + moldura. A composição é feita com a moldura ampliada
    para pelo menos `largura_px_min`, para a moldura não perder nitidez."""
    moldura = carregar_moldura(moldura_caminho)
    dpi_moldura = moldura.width / (largura_cm / 2.54)
    if moldura.width < largura_px_min:
        fator = largura_px_min / moldura.width
        moldura = moldura.resize((largura_px_min, round(moldura.height * fator)), Image.Resampling.LANCZOS)

    furos = detectar_furos(moldura)
    nome = Path(moldura_caminho).name
    if not furos:
        raise ValueError(f"{nome}: nenhuma área transparente para a foto")
    if len(fotos) != len(furos):
        raise ValueError(f"{nome} tem {len(furos)} espaço(s) para foto, mas vieram {len(fotos)} foto(s)")

    base = Image.new("RGBA", moldura.size, (255, 255, 255, 255))
    dpis = []
    avisos: list[str] = []
    for furo, caminho in zip(furos, fotos):
        x0, y0, x1, y1 = furo.caixa
        fw, fh = x1 - x0, y1 - y0
        original = carregar_rgb(caminho)
        foto = None
        if rosto and not ajuste.manual:
            try:
                rostos = _rosto.detectar_rostos(original)
            except _rosto.SemDetector as e:
                rostos = []
                if str(e) not in avisos:
                    avisos.append(str(e))
            if rostos:
                alvo = _rosto.centro_de_massa(furo.mascara.crop(furo.caixa))
                foto = _rosto.recorte_pelo_rosto(original, fw / fh, rostos, alvo)
            elif not avisos:
                avisos.append(f"{Path(caminho).name}: rosto não encontrado, foto centralizada — confira")
        if foto is None:
            foto = recortar_cobrindo(original, fw / fh, ajuste)
        dpis.append(foto.width / (fw / moldura.width * largura_cm / 2.54))
        if ampliador and foto.width < fw:
            foto = ampliador.ampliar(foto, fw / foto.width)
        foto = foto.resize((fw, fh), Image.Resampling.LANCZOS)
        base.paste(foto, (x0, y0), furo.mascara.crop(furo.caixa))
    base.alpha_composite(moldura)
    return Composicao(imagem=base.convert("RGB"), dpi_fotos=min(dpis), dpi_moldura=dpi_moldura, avisos=avisos)
