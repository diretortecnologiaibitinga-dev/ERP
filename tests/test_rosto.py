from pathlib import Path

import pytest
from PIL import Image, ImageDraw

pytest.importorskip("cv2")

from estampa.moldura import Ajuste, compor  # noqa: E402
from estampa.rosto import centro_de_massa, detectar_rostos, recorte_pelo_rosto  # noqa: E402

ROSTO = Path(__file__).parents[1] / "src" / "estampa" / "demo_dados" / "rosto.jpg"  # Eileen Collins, NASA (domínio público)


def _foto_com_rosto_no_canto(tmp_path):
    """Rosto bem à direita de uma foto larga: o corte pelo centro erraria."""
    foto = Image.new("RGB", (1600, 900), (90, 110, 140))
    foto.paste(Image.open(ROSTO).resize((640, 640)), (950, 130))
    caminho = tmp_path / "foto.jpg"
    foto.save(caminho, quality=92)
    return caminho


def test_detecta_rosto():
    rostos = detectar_rostos(Image.open(ROSTO))
    assert len(rostos) == 1
    x0, y0, x1, y1 = rostos[0]
    assert 90 < x0 < 130 and 20 < y0 < 60


def test_sem_rosto():
    assert detectar_rostos(Image.new("RGB", (400, 300), (200, 200, 200))) == []


def test_recorte_centraliza_o_rosto_no_alvo():
    img = Image.new("RGB", (1600, 900))
    recorte = recorte_pelo_rosto(img, 1.0, [(1100, 300, 1300, 500)], alvo=(0.5, 0.45))
    assert recorte.width == recorte.height
    assert recorte.width <= 900


def test_centro_de_massa_do_coracao_fica_acima_do_meio():
    mascara = Image.new("L", (200, 200), 0)
    d = ImageDraw.Draw(mascara)
    d.ellipse((0, 0, 110, 110), fill=255)
    d.ellipse((90, 0, 200, 110), fill=255)
    d.polygon([(5, 75), (195, 75), (100, 200)], fill=255)
    cx, cy = centro_de_massa(mascara)
    assert abs(cx - 0.5) < 0.02 and cy < 0.5


def _moldura(tmp_path):
    img = Image.new("RGBA", (450, 450), (220, 0, 0, 255))
    ImageDraw.Draw(img).ellipse((120, 80, 330, 330), fill=(0, 0, 0, 0))
    caminho = tmp_path / "m.png"
    img.save(caminho)
    return caminho


def _pele_no_centro(img):
    """Fração de pixels com cor de pele no centro do espaço da foto."""
    centro = img.crop((190, 150, 260, 240)).convert("RGB")
    px = centro.tobytes()
    trios = (px[i:i + 3] for i in range(0, len(px), 3))
    pele = sum(1 for r, g, b in trios if r > 150 and g > 100 and b > 80 and r > b + 20)
    return pele / (centro.width * centro.height)


def test_moldura_enquadra_pelo_rosto(tmp_path):
    foto = _foto_com_rosto_no_canto(tmp_path)
    auto = compor(_moldura(tmp_path), [foto], 45, 450)
    centro = compor(_moldura(tmp_path), [foto], 45, 450, rosto=False)
    assert _pele_no_centro(auto.imagem) > 0.4
    assert _pele_no_centro(centro.imagem) < 0.1
    assert auto.avisos == []


def test_ajuste_manual_desliga_o_automatico(tmp_path):
    foto = _foto_com_rosto_no_canto(tmp_path)
    manual = compor(_moldura(tmp_path), [foto], 45, 450, Ajuste(desloc_x=-1))
    assert _pele_no_centro(manual.imagem) < 0.1


def test_avisa_quando_nao_acha_rosto(tmp_path):
    foto = tmp_path / "paisagem.jpg"
    Image.new("RGB", (800, 600), (30, 160, 60)).save(foto)
    comp = compor(_moldura(tmp_path), [foto], 45, 450)
    assert any("rosto não encontrado" in a for a in comp.avisos)
