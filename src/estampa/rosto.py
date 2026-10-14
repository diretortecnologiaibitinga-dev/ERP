"""Enquadramento automático da foto pelo rosto (fotomolduras).

Usa o YuNet (OpenCV) se o modelo estiver em `modelos/face_detection_yunet_2023mar.onnx`,
ou o detector clássico Haar que vem com o opencv-python-headless 4.x. Sem
OpenCV instalado, a foto volta a ser centralizada como antes.

O rosto (ou o grupo de rostos, em fotos de casal) é colocado no centro de
massa do espaço da moldura — num coração, um pouco acima do meio — e
ocupa uma fração fixa da altura do espaço.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image

MODELO_YUNET = Path(__file__).resolve().parents[2] / "modelos" / "face_detection_yunet_2023mar.onnx"
_LADO_DETECCAO = 1024

Caixa = tuple[float, float, float, float]


class SemDetector(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _detector():
    try:
        import cv2
    except ImportError:
        raise SemDetector("detecção de rosto indisponível: instale com  pip install -e \".[rosto]\"") from None
    if MODELO_YUNET.exists() and hasattr(cv2, "FaceDetectorYN"):
        return "yunet", cv2.FaceDetectorYN.create(str(MODELO_YUNET), "", (320, 320), 0.8)
    data = getattr(cv2, "data", None)
    if data is None:
        raise SemDetector("este OpenCV não traz o detector Haar; use opencv-python-headless 4.x "
                          "ou coloque o modelo YuNet na pasta modelos/")
    return "haar", cv2.CascadeClassifier(data.haarcascades + "haarcascade_frontalface_default.xml")


def detectar_rostos(img: Image.Image) -> list[Caixa]:
    """Caixas (x0, y0, x1, y1) dos rostos, nas coordenadas da imagem."""
    import cv2
    import numpy as np

    tipo, det = _detector()
    escala = min(1.0, _LADO_DETECCAO / max(img.size))
    pequena = img.convert("RGB").resize((max(1, round(img.width * escala)), max(1, round(img.height * escala))))
    bgr = np.asarray(pequena)[:, :, ::-1].copy()

    if tipo == "yunet":
        det.setInputSize((bgr.shape[1], bgr.shape[0]))
        _, achados = det.detect(bgr)
        caixas = [] if achados is None else [(f[0], f[1], f[0] + f[2], f[1] + f[3]) for f in achados]
    else:
        cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        minimo = max(24, round(min(cinza.shape) * 0.05))
        caixas = []
        # do mais rígido (menos falsos positivos) ao mais tolerante (foto escura, contraste baixo)
        for imagem, vizinhos in ((cinza, 6), (cinza, 4), (cv2.equalizeHist(cinza), 4)):
            achados = det.detectMultiScale(imagem, scaleFactor=1.1, minNeighbors=vizinhos,
                                           minSize=(minimo, minimo))
            caixas = [(x, y, x + w, y + h) for x, y, w, h in achados]
            if caixas:
                break

    if not caixas:
        return []
    # descarta detecções bem menores que o maior rosto (fundo, estampas, falsos positivos)
    maior = max((c[2] - c[0]) * (c[3] - c[1]) for c in caixas)
    caixas = [c for c in caixas if (c[2] - c[0]) * (c[3] - c[1]) >= 0.25 * maior]
    return [tuple(float(v) / escala for v in c) for c in caixas]


def centro_de_massa(mascara: Image.Image) -> tuple[float, float]:
    """Centro de massa de uma máscara "L", em fração (0-1) da largura e altura."""
    pequena = mascara.resize((64, 64), Image.Resampling.BOX)
    dados = pequena.load()
    total = sx = sy = 0.0
    for y in range(64):
        for x in range(64):
            v = dados[x, y]
            total += v
            sx += v * (x + 0.5)
            sy += v * (y + 0.5)
    if not total:
        return 0.5, 0.5
    return sx / total / 64, sy / total / 64


def recorte_pelo_rosto(
    img: Image.Image,
    proporcao: float,
    rostos: list[Caixa],
    alvo: tuple[float, float] = (0.5, 0.45),
    altura_cabeca: float = 0.5,
) -> Image.Image:
    """Recorte com a proporção do espaço, com a(s) cabeça(s) em `alvo`.

    A caixa do detector pega só o rosto; a cabeça (cabelo, queixo) é estimada
    ampliando a caixa. `altura_cabeca` é a fração da altura do espaço ocupada
    pela cabeça; fotos de grupo abrem o recorte para caber todo mundo.
    """
    x0 = min(c[0] for c in rostos)
    y0 = min(c[1] for c in rostos)
    x1 = max(c[2] for c in rostos)
    y1 = max(c[3] for c in rostos)
    rw, rh = x1 - x0, y1 - y0
    cabeca_w, cabeca_h = rw * 1.3, rh * 1.7
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - rh * 0.1  # cabelo pesa mais que o queixo

    ch = max(cabeca_h / altura_cabeca, cabeca_w / 0.8 / proporcao)
    ch = min(ch, img.height, img.width / proporcao)  # nunca maior que a foto
    cw = ch * proporcao
    left = min(max(0.0, cx - alvo[0] * cw), img.width - cw)
    top = min(max(0.0, cy - alvo[1] * ch), img.height - ch)
    return img.crop((round(left), round(top), round(left + cw), round(top + ch)))
