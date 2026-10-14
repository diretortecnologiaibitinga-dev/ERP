import pytest
from PIL import Image, ImageDraw

from estampa.cli import main
from estampa.imagem import cm_para_px
from estampa.lote import Lado, preparar_lado
from estampa.moldura import Ajuste, compor, detectar_furos, recortar_cobrindo

VERMELHO, VERDE, AZUL = (220, 0, 0, 255), (0, 200, 0), (0, 0, 255)


def _moldura(tmp_path, furos, fundo_transparente=False, nome="m.png"):
    """Moldura 450x450 vermelha com furos elípticos transparentes."""
    img = Image.new("RGBA", (450, 450), VERMELHO)
    d = ImageDraw.Draw(img)
    if fundo_transparente:
        img = Image.new("RGBA", (450, 450), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle((40, 40, 410, 410), fill=VERMELHO)
    for caixa in furos:
        d.ellipse(caixa, fill=(0, 0, 0, 0))
    caminho = tmp_path / nome
    img.save(caminho)
    return caminho


def _foto(tmp_path, cor, nome, tamanho=(600, 400)):
    caminho = tmp_path / nome
    Image.new("RGB", tamanho, cor).save(caminho)
    return caminho


def test_detecta_um_furo(tmp_path):
    furos = detectar_furos(Image.open(_moldura(tmp_path, [(100, 80, 350, 330)])).convert("RGBA"))
    assert len(furos) == 1
    x0, y0, x1, y1 = furos[0].caixa
    assert abs(x0 - 100) <= 4 and abs(y1 - 330) <= 4


def test_ignora_fundo_externo_transparente_e_ordena(tmp_path):
    m = _moldura(tmp_path, [(250, 100, 380, 230), (70, 100, 200, 230)], fundo_transparente=True)
    furos = detectar_furos(Image.open(m).convert("RGBA"))
    assert len(furos) == 2
    assert furos[0].caixa[0] < furos[1].caixa[0]  # esquerda primeiro


def test_foto_por_baixo_da_moldura(tmp_path):
    m = _moldura(tmp_path, [(100, 100, 350, 350)])
    comp = compor(m, [_foto(tmp_path, VERDE, "f.jpg")], largura_cm=45, largura_px_min=450)
    img = comp.imagem
    assert img.mode == "RGB"
    assert img.getpixel((225, 225))[:3] == pytest.approx(VERDE, abs=3)  # foto no furo
    assert img.getpixel((20, 20)) == VERMELHO[:3]                          # moldura por cima


def test_duas_fotos_em_dois_furos(tmp_path):
    m = _moldura(tmp_path, [(250, 100, 380, 230), (70, 100, 200, 230)])
    comp = compor(m, [_foto(tmp_path, VERDE, "a.jpg"), _foto(tmp_path, AZUL, "b.jpg")], 45, 450)
    assert comp.imagem.getpixel((135, 165))[:3] == pytest.approx(VERDE, abs=3)
    assert comp.imagem.getpixel((315, 165))[:3] == pytest.approx(AZUL, abs=3)


def test_quantidade_de_fotos_errada(tmp_path):
    m = _moldura(tmp_path, [(100, 100, 350, 350)])
    with pytest.raises(ValueError, match="1 espaço"):
        compor(m, [_foto(tmp_path, VERDE, "a.jpg"), _foto(tmp_path, AZUL, "b.jpg")], 45, 450)


def test_moldura_sem_transparencia(tmp_path):
    caminho = tmp_path / "x.jpg"
    Image.new("RGB", (100, 100)).save(caminho)
    with pytest.raises(ValueError, match="transparência"):
        compor(caminho, [caminho], 45, 100)


def test_recorte_com_ajuste():
    img = Image.new("RGB", (1000, 500))
    assert recortar_cobrindo(img, 1.0).size == (500, 500)
    assert recortar_cobrindo(img, 1.0, Ajuste(zoom=2)).size == (250, 250)
    esquerda = recortar_cobrindo(img, 1.0, Ajuste(desloc_x=-1))
    assert esquerda.size == (500, 500)


def test_lado_com_moldura_no_tamanho_de_producao(catalogo, tmp_path):
    produto = catalogo.produto("almofada-45")
    lado = Lado((_foto(tmp_path, VERDE, "f.jpg"),), _moldura(tmp_path, [(100, 100, 350, 350)]))
    arte = preparar_lado(lado, produto, dpi=30)
    assert arte.imagem.size == (cm_para_px(45, 30),) * 2
    # foto de 400 px no furo de ~25 cm
    assert 35 < arte.dpi_original < 45


def test_cli_peca_com_moldura_da_biblioteca(tmp_path, monkeypatch, capsys):
    (tmp_path / "molduras").mkdir()
    _moldura(tmp_path / "molduras", [(100, 100, 350, 350)], nome="coracao.png")
    (tmp_path / "produtos.toml").write_text(
        '[produtos.almofada-45]\nnome = "Almofada"\nlargura_cm = 45\naltura_cm = 45\nlados = 2\n')
    foto = _foto(tmp_path, VERDE, "foto.jpg")
    args = ["--catalogo", str(tmp_path / "produtos.toml")]
    assert main(args + ["molduras"]) == 0
    assert "1 espaço(s)" in capsys.readouterr().out
    assert main(args + ["peca", "--produto", "almofada-45", "--pedido", "7", "--moldura", "coracao",
                        "--frente", str(foto), "--saida", str(tmp_path / "out"), "--dpi", "20"]) == 0
    img = Image.open(tmp_path / "out" / "almofada-45_7.png")
    centro = img.getpixel((img.width // 2, img.height // 2))
    assert centro == pytest.approx(VERDE, abs=3)


def test_aviso_de_moldura_em_baixa_resolucao(catalogo, tmp_path):
    from estampa.lote import ItemPedido, gerar_pecas
    lado = Lado((_foto(tmp_path, VERDE, "f.jpg", (3000, 3000)),), _moldura(tmp_path, [(100, 100, 350, 350)]))
    _, avisos = gerar_pecas([ItemPedido("1", catalogo.produto("almofada-45"), 1, [lado])], dpi=150)
    assert any("moldura m.png tem 25 DPI" in a for a in avisos)
