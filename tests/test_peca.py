from PIL import Image

from estampa.imagem import cm_para_px, preparar_arte
from estampa.peca import Peca, renderizar_png, salvar_pdf

DPI = 50


def _peca(catalogo, arte, **kw):
    produto = catalogo.produto("almofada-45")
    return Peca(produto=produto, arte=preparar_arte(arte, 45, 45, DPI), pedido="12345", **kw)


def test_dimensoes_e_layout(catalogo, arte):
    img = renderizar_png(_peca(catalogo, arte), DPI, borda_mm=1)
    total, margem = cm_para_px(47, DPI), cm_para_px(1, DPI)
    assert img.size == (total, total)
    assert img.getpixel((0, total // 2)) == (0, 0, 0)            # borda preta
    assert img.getpixel((margem // 2, total // 3)) == (255, 255, 255)  # margem branca
    assert img.getpixel((margem + 5, total // 2)) == (255, 0, 0)  # arte começa na margem
    assert img.getpixel((total - margem - 5, total // 2)) == (0, 0, 255)


def test_codigo_do_pedido_na_margem_inferior(catalogo, arte):
    img = renderizar_png(_peca(catalogo, arte), DPI, borda_mm=1)
    total, margem = cm_para_px(47, DPI), cm_para_px(1, DPI)
    faixa = img.crop((margem, total - margem + 2, total - margem, total - 2))
    assert faixa.getextrema()[0][0] == 0  # há texto preto


def test_espelhar(catalogo, arte):
    img = renderizar_png(_peca(catalogo, arte, espelhar=True), DPI, borda_mm=1)
    margem = cm_para_px(1, DPI)
    assert img.getpixel((margem + 5, img.height // 2)) == (0, 0, 255)


def test_etiqueta(catalogo, arte):
    p = _peca(catalogo, arte, lado=1, copia=2, total_copias=3, frente_verso=True)
    assert p.etiqueta == "PEDIDO 12345  |  VERSO  |  2/3"
    assert _peca(catalogo, arte).etiqueta == "PEDIDO 12345"


def test_pdf_no_tamanho_real(catalogo, arte, tmp_path):
    destino = tmp_path / "p.pdf"
    salvar_pdf(_peca(catalogo, arte), destino, borda_mm=1)
    conteudo = destino.read_bytes()
    lado_pt = 47 / 2.54 * 72
    assert f"{lado_pt:.4g}".encode()[:5] in conteudo
