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


def test_layout_em_linhas_um_modelo_por_linha(tmp_path):
    from estampa.moldes import importar_pdf_modelos
    from estampa.moldes_exemplo import gerar_pdf_moldes_linhas
    pdf = gerar_pdf_moldes_linhas(tmp_path / "polo.pdf")
    homem, mulher = importar_pdf_modelos(pdf, "polo")
    assert (homem.codigo, mulher.codigo) == ("polo-homem", "polo-mulher")
    assert list(homem.tamanhos) == ["PP", "P", "M"] and list(mulher.tamanhos) == ["BLP", "BLM", "BLG"]
    assert {t.grade for t in mulher.tamanhos.values()} == {"feminino"}
    pp = homem.tamanho("PP")  # menor escala (0.9)
    assert sorted(pp.partes) == ["costas", "frente", "gola", "manga_curta_dir", "manga_curta_esq"]
    assert pp.partes["frente"].largura_cm == pytest.approx(45, abs=0.2)  # contorno externo, não o de costura
    assert "3" in pp.partes["manga_curta_esq"].logos
    nomes = importar_pdf_modelos(pdf, "polo", {"polo-homem": ["P", "M", "G"]})[0]
    assert list(nomes.tamanhos) == ["P", "M", "G"]
    with pytest.raises(ValueError, match="3 tamanhos no PDF"):
        importar_pdf_modelos(pdf, "polo", {"polo-homem": ["P", "M"]})


def test_importar_pdf_com_varios_modelos_avisa(tmp_path):
    from estampa.moldes_exemplo import gerar_pdf_moldes_linhas
    with pytest.raises(ValueError, match="2 modelos"):
        importar_pdf(gerar_pdf_moldes_linhas(tmp_path / "polo.pdf"), "polo")


def test_shorts_grupos_lado_a_lado_e_marcadores_coloridos(tmp_path):
    """Layout dos shorts: Feminino | Masculino na mesma linha, peças só preenchidas
    (sem contorno), retângulos azul-marinho (perna direita) e vermelhos (esquerda)."""
    from reportlab.lib.colors import Color
    from reportlab.lib.units import cm
    from reportlab.pdfgen.canvas import Canvas

    from estampa.moldes import importar_pdf_modelos

    H = 260
    c = Canvas(str(tmp_path / "shorts.pdf"), pagesize=(400 * cm, H * cm))
    c.setFont("Helvetica-Bold", 900)
    c.setFillColor(Color(0.2, 0.2, 0.2))
    c.drawString(5 * cm, (H - 30) * cm, "Feminino")
    c.drawString(210 * cm, (H - 30) * cm, "Masculino")

    def perna(x, y, w, h, cor):
        p = c.beginPath()
        pts = [(0, 0), (w, 0), (w, h * 0.6), (w * 1.05, h), (-w * 0.05, h), (0, h * 0.6)]
        p.moveTo((x + pts[0][0]) * cm, (H - y - pts[0][1]) * cm)
        for px, py in pts[1:]:
            p.lineTo((x + px) * cm, (H - y - py) * cm)
        p.close()
        c.setFillColor(Color(0.29, 0.29, 0.3))
        c.drawPath(p, stroke=0, fill=1)
        c.setFillColor(cor)
        for rx, rw in ((0.2, 0.25), (0.6, 0.12)):
            c.rect((x + w * rx) * cm, (H - y - h * 0.85) * cm, w * rw * cm, 0.12 * h * cm, stroke=0, fill=1)

    for gx, escalas in ((5, (0.9, 1.0)), (210, (0.95, 1.05, 1.15))):
        for linha, s in enumerate(escalas):
            y = 40 + linha * 70
            perna(gx, y, 60 * s, 45 * s, Color(0, 0, 0.4))
            perna(gx + 90, y, 60 * s, 45 * s, Color(0.93, 0.2, 0.22))
    c.save()

    fem, masc = sorted(importar_pdf_modelos(tmp_path / "shorts.pdf", "shorts"), key=lambda m: m.codigo)
    assert (fem.codigo, masc.codigo) == ("shorts-feminino", "shorts-masculino")
    assert len(fem.tamanhos) == 2 and len(masc.tamanhos) == 3
    t = next(iter(masc.tamanhos.values()))
    assert sorted(t.partes) == ["short_dir", "short_esq"]
    assert sorted(t.partes["short_dir"].logos) == ["D1", "D2"] and sorted(t.partes["short_esq"].logos) == ["E1", "E2"]
