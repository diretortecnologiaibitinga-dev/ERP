import pytest

from estampa.moldes import Modelo, desenhar_previa, grade_do_tamanho, importar_pdf, normalizar_tamanho
from estampa.moldes_exemplo import gerar_pdf_moldes_exemplo


@pytest.fixture(scope="module")
def pdf(tmp_path_factory):
    return gerar_pdf_moldes_exemplo(tmp_path_factory.mktemp("moldes") / "exemplo.pdf")


def test_importa_tamanhos_grades_e_partes(pdf):
    m = importar_pdf(pdf, "exemplo")
    assert list(m.tamanhos) == ["8", "BLM", "M", "XGG"]
    assert [t.grade for t in m.tamanhos.values()] == ["infantil", "feminino", "adulto", "adulto"]
    assert sorted(m.tamanho("M").partes) == ["costas", "frente_careca", "frente_v", "manga_curta_dir",
                                             "manga_curta_esq", "manga_longa_dir", "manga_longa_esq"]


def test_medidas_em_cm_e_logos(pdf):
    m = importar_pdf(pdf, "exemplo")
    frente = m.tamanho("M").partes["frente_careca"]
    assert frente.largura_cm == pytest.approx(57, abs=0.1) and frente.altura_cm == pytest.approx(75, abs=0.1)
    cx, cy, w, h = frente.logos["1"]
    assert cx == pytest.approx(57 * 0.3, abs=0.2) and w == pytest.approx(11, abs=0.1)
    assert m.tamanho("XGG").partes["frente_careca"].logos["2"][2] == pytest.approx(13, abs=0.1)
    assert "3" in m.tamanho("8").partes["manga_curta_esq"].logos
    assert "4" in m.tamanho("8").partes["manga_curta_dir"].logos
    # o contorno fica dentro da caixa da peça
    xs = [x for x, _ in frente.contorno]
    assert min(xs) >= -0.1 and max(xs) <= frente.largura_cm + 0.1


def test_quadro_de_edicao_e_salvar_carregar(pdf, tmp_path):
    m = importar_pdf(pdf, "exemplo")
    assert m.quadro("costas") == pytest.approx((68.4, 93.6), abs=0.1)  # maior molde: XGG
    m.salvar(tmp_path / "exemplo.json")
    de_novo = Modelo.carregar(tmp_path / "exemplo.json")
    assert de_novo.tamanho("blm").partes["costas"].contorno == m.tamanho("BLM").partes["costas"].contorno
    desenhar_previa(de_novo, tmp_path / "previa.png", ["8", "XGG"])
    assert (tmp_path / "previa.png").exists()


def test_tamanho_inexistente(pdf):
    with pytest.raises(ValueError, match="disponíveis: 8, BLM, M, XGG"):
        importar_pdf(pdf, "exemplo").tamanho("XXXG")


def test_nomes_de_tamanho():
    assert normalizar_tamanho("blpp (s)") == "BLPP"
    assert [grade_do_tamanho(t) for t in ("2", "BLXG", "XGG")] == ["infantil", "feminino", "adulto"]


def test_pdf_sem_moldes(tmp_path):
    from reportlab.pdfgen.canvas import Canvas
    c = Canvas(str(tmp_path / "vazio.pdf"))
    c.drawString(100, 100, "nada aqui")
    c.save()
    with pytest.raises(ValueError, match="nenhum molde"):
        importar_pdf(tmp_path / "vazio.pdf")
