from PIL import Image, ImageCms

from estampa.imagem import carregar_rgb, cm_para_px, enquadrar, preparar_arte


def test_cm_para_px():
    assert cm_para_px(47, 150) == 2776
    assert cm_para_px(2.54, 300) == 300


def test_enquadrar_corta_pelo_centro():
    img = Image.new("RGB", (1200, 800))
    assert enquadrar(img, 1.0).size == (800, 800)
    assert enquadrar(img, 40 / 70).size == (457, 800)
    assert enquadrar(Image.new("RGB", (800, 1200)), 1.0).size == (800, 800)


def test_transparencia_vira_branco(tmp_path):
    caminho = tmp_path / "t.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(caminho)
    assert carregar_rgb(caminho).getpixel((5, 5)) == (255, 255, 255)


def test_cmyk_vira_rgb(tmp_path):
    caminho = tmp_path / "c.jpg"
    Image.new("CMYK", (10, 10), (0, 0, 0, 0)).save(caminho)
    img = carregar_rgb(caminho)
    assert img.mode == "RGB"


def test_converte_perfil_para_srgb(tmp_path):
    caminho = tmp_path / "lab.png"
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    Image.new("RGB", (4, 4), (10, 200, 30)).save(caminho, icc_profile=icc)
    assert carregar_rgb(caminho).getpixel((0, 0)) == (10, 200, 30)


def test_preparar_arte_tamanho_exato(arte):
    pronta = preparar_arte(arte, 45, 45, 150)
    assert pronta.imagem.size == (cm_para_px(45, 150),) * 2
    # 800 px cobrindo 45 cm ≈ 45 DPI
    assert round(pronta.dpi_original) == 45
    assert pronta.baixa_resolucao
