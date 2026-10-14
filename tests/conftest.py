from pathlib import Path

import pytest
from PIL import Image

from estampa.produtos import CATALOGO_PADRAO, carregar_catalogo


@pytest.fixture
def catalogo():
    return carregar_catalogo(CATALOGO_PADRAO)


@pytest.fixture
def arte(tmp_path: Path):
    """Arte 1200x800 com metade esquerda vermelha e direita azul."""
    img = Image.new("RGB", (1200, 800), (0, 0, 255))
    img.paste((255, 0, 0), (0, 0, 600, 800))
    caminho = tmp_path / "arte.png"
    img.save(caminho)
    return caminho
