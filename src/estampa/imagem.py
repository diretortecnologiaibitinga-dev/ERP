"""Leitura, normalização para RGB, enquadramento e ampliação das artes."""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

Image.MAX_IMAGE_PIXELS = None  # artes de produção são grandes de propósito

_SRGB = ImageCms.createProfile("sRGB")
SRGB_ICC = ImageCms.ImageCmsProfile(_SRGB).tobytes()


def cm_para_px(cm: float, dpi: int) -> int:
    return round(cm / 2.54 * dpi)


def carregar_rgb(caminho: Path | str) -> Image.Image:
    """Abre a arte já na orientação correta e convertida para sRGB.

    Fotos de celular trazem a rotação no EXIF; PNG com transparência é
    aplicado sobre branco; CMYK ou RGB com outro perfil (Adobe RGB, P3)
    é convertido para sRGB, o padrão de cor da produção.
    """
    img = Image.open(caminho)
    img = ImageOps.exif_transpose(img)
    icc = img.info.get("icc_profile")

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        fundo = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(fundo, img)

    if icc and img.mode in ("RGB", "RGBA", "CMYK"):
        origem = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        modo = "CMYK" if img.mode == "CMYK" else "RGB"
        img = ImageCms.profileToProfile(
            img.convert(modo), origem, _SRGB, outputMode="RGB",
            renderingIntent=ImageCms.Intent.PERCEPTUAL,
        )
    return img.convert("RGB")


def enquadrar(img: Image.Image, proporcao: float) -> Image.Image:
    """Corta a arte pelo centro para a proporção largura/altura da estampa
    (equivalente a preencher o PowerClip sem distorcer)."""
    w, h = img.size
    if w / h > proporcao:
        novo_w = round(h * proporcao)
        x = (w - novo_w) // 2
        return img.crop((x, 0, x + novo_w, h))
    novo_h = round(w / proporcao)
    y = (h - novo_h) // 2
    return img.crop((0, y, w, y + novo_h))


def dpi_efetivo(img: Image.Image, largura_cm: float) -> float:
    return img.width / (largura_cm / 2.54)


class Ampliador:
    nome = "lanczos"

    def ampliar(self, img: Image.Image, fator: float) -> Image.Image:
        return img


class RealESRGAN(Ampliador):
    """Ampliação por IA usando o binário realesrgan-ncnn-vulkan
    (https://github.com/xinntao/Real-ESRGAN/releases)."""

    nome = "realesrgan"

    def __init__(self, executavel: str = "realesrgan-ncnn-vulkan", modelo: str = "realesrgan-x4plus"):
        caminho = shutil.which(executavel)
        if not caminho:
            raise RuntimeError(f"'{executavel}' não encontrado no PATH")
        self.executavel = caminho
        self.modelo = modelo

    def ampliar(self, img: Image.Image, fator: float) -> Image.Image:
        if fator <= 1:
            return img
        with tempfile.TemporaryDirectory() as tmp:
            entrada, saida = Path(tmp, "in.png"), Path(tmp, "out.png")
            img.save(entrada)
            subprocess.run(
                [self.executavel, "-i", str(entrada), "-o", str(saida), "-n", self.modelo, "-s", "4"],
                check=True, capture_output=True,
            )
            return Image.open(saida).convert("RGB")


def criar_ampliador(nome: str) -> Ampliador:
    if nome == "lanczos":
        return Ampliador()
    if nome == "realesrgan":
        return RealESRGAN()
    raise ValueError(f"ampliador desconhecido: {nome}")


@dataclass
class ArtePreparada:
    imagem: Image.Image
    dpi_original: float  # DPI que a arte do cliente teria no tamanho final
    avisos: list[str] = field(default_factory=list)

    @property
    def baixa_resolucao(self) -> bool:
        return self.dpi_original < 100

    @cached_property
    def jpeg(self) -> bytes:
        """JPEG para embutir no PDF; cópias da mesma arte reutilizam os bytes."""
        buf = io.BytesIO()
        self.imagem.save(buf, "JPEG", quality=95, subsampling=0, icc_profile=SRGB_ICC)
        return buf.getvalue()


def preparar_imagem(
    img: Image.Image,
    largura_cm: float,
    altura_cm: float,
    dpi: int,
    ampliador: Ampliador | None = None,
    dpi_original: float | None = None,
) -> ArtePreparada:
    """Deixa uma imagem RGB pronta para a área visível: enquadrada e no
    tamanho exato em pixels para o DPI de produção."""
    img = enquadrar(img, largura_cm / altura_cm)
    original = dpi_efetivo(img, largura_cm) if dpi_original is None else dpi_original
    alvo = (cm_para_px(largura_cm, dpi), cm_para_px(altura_cm, dpi))
    if ampliador and img.width < alvo[0]:
        img = ampliador.ampliar(img, alvo[0] / img.width)
    if img.size != alvo:
        img = img.resize(alvo, Image.Resampling.LANCZOS)
    return ArtePreparada(imagem=img, dpi_original=original)


def preparar_arte(
    caminho: Path | str,
    largura_cm: float,
    altura_cm: float,
    dpi: int,
    ampliador: Ampliador | None = None,
) -> ArtePreparada:
    return preparar_imagem(carregar_rgb(caminho), largura_cm, altura_cm, dpi, ampliador)
