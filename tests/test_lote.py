import pytest

from estampa.cli import main
from estampa.imagem import cm_para_px, preparar_arte
from estampa.lote import encaixar, gerar_pecas, ler_pedidos_csv
from estampa.peca import Peca


def _pecas(catalogo, arte, codigo, n):
    produto = catalogo.produto(codigo)
    pronta = preparar_arte(arte, produto.largura_cm, produto.altura_cm, 20)
    return [Peca(produto=produto, arte=pronta, pedido=str(i)) for i in range(n)]


def _sem_sobreposicao(folha, largura):
    caixas = [(p.x_cm, p.y_cm, p.x_cm + p.largura_cm, p.y_cm + p.altura_cm) for p in folha.posicoes]
    for x0, y0, x1, y1 in caixas:
        assert x0 >= 0 and x1 <= largura + 1e-9
    for i, a in enumerate(caixas):
        for b in caixas[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


def test_almofadas_tres_por_linha(catalogo, arte):
    folhas = encaixar(_pecas(catalogo, arte, "almofada-45", 7), 180, 0.5, 300)
    assert len(folhas) == 1
    ys = sorted({p.y_cm for p in folhas[0].posicoes})
    assert ys == [0.0, 47.5, 95.0]
    assert folhas[0].comprimento_cm == pytest.approx(142)
    _sem_sobreposicao(folhas[0], 180)


def test_travesseiro_em_pe_cabe_quatro(catalogo, arte):
    folhas = encaixar(_pecas(catalogo, arte, "travesseiro-40x70", 4), 180, 0.5, 300)
    assert {p.y_cm for p in folhas[0].posicoes} == {0.0}
    assert not any(p.rotacionada for p in folhas[0].posicoes)


def test_mistura_e_divide_em_folhas(catalogo, arte):
    pecas = _pecas(catalogo, arte, "almofada-45", 10) + _pecas(catalogo, arte, "travesseiro-40x70", 9)
    folhas = encaixar(pecas, 180, 0.5, 150)
    assert sum(len(f.posicoes) for f in folhas) == 19
    for f in folhas:
        assert f.comprimento_cm <= 150
        _sem_sobreposicao(f, 180)


def test_csv_frente_verso_e_quantidade(catalogo, arte, tmp_path):
    csv = tmp_path / "pedidos.csv"
    csv.write_text(
        "pedido,produto,quantidade,arte_frente,arte_verso\n"
        "A1,almofada-45,2,arte.png,arte.png\n"
        "B2,travesseiro-40x70,1,arte.png,\n"
    )
    pecas, avisos = gerar_pecas(ler_pedidos_csv(csv, catalogo), dpi=20)
    assert [p.etiqueta for p in pecas] == [
        "PEDIDO A1  |  FRENTE  |  1/2", "PEDIDO A1  |  VERSO  |  1/2",
        "PEDIDO A1  |  FRENTE  |  2/2", "PEDIDO A1  |  VERSO  |  2/2",
        "PEDIDO B2",
    ]
    assert len({id(p.arte) for p in pecas[:4]}) == 1  # arte preparada uma vez
    assert avisos == []  # 800 px em 45 cm ≈ 45 DPI, acima do alvo de 20


def test_cli_lote_um_arquivo_por_peca(arte, tmp_path, capsys):
    csv = tmp_path / "pedidos.csv"
    csv.write_text("pedido,produto,quantidade,arte_frente,arte_verso\n"
                   "A1,almofada-45,2,arte.png,arte.png\nB2,travesseiro-40x70,1,arte.png,\n")
    assert main(["lote", str(csv), "--saida", str(tmp_path / "rip"), "--dpi", "20"]) == 0
    assert sorted(f.name for f in (tmp_path / "rip").iterdir()) == [
        "almofada-45_A1_frente_1de2.png", "almofada-45_A1_frente_2de2.png",
        "almofada-45_A1_verso_1de2.png", "almofada-45_A1_verso_2de2.png",
        "travesseiro-40x70_B2.png",
    ]
    assert "5 arquivo(s)" in capsys.readouterr().out


def test_cli_lote_erro_em_um_item_nao_para_o_lote(arte, tmp_path, capsys):
    csv = tmp_path / "pedidos.csv"
    csv.write_text("pedido,produto,quantidade,arte_frente\n"
                   "A1,almofada-45,1,nao-existe.png\nB2,almofada-45,1,arte.png\n")
    assert main(["lote", str(csv), "--saida", str(tmp_path / "rip"), "--dpi", "20"]) == 1
    assert [f.name for f in (tmp_path / "rip").iterdir()] == ["almofada-45_B2.png"]
    assert "pedido A1" in capsys.readouterr().err


def test_cli_lote_montar_rolo(arte, tmp_path, capsys):
    csv = tmp_path / "pedidos.csv"
    csv.write_text("pedido,produto,quantidade,arte_frente\nA1,almofada-45,4,arte.png\n")
    assert main(["lote", str(csv), "--montar-rolo", "--saida", str(tmp_path / "out"), "--dpi", "20"]) == 0
    assert (tmp_path / "out" / "pedidos_folha01.pdf").exists()
    assert "4 peças" in capsys.readouterr().out


def test_sob_medida_no_csv(catalogo, arte, tmp_path):
    csv = tmp_path / "pedidos.csv"
    csv.write_text("pedido,produto,quantidade,arte_frente,largura_cm,altura_cm\n"
                   "P1,capa-porta,1,arte.png,\"70,5\",200\nP2,almofada-45,1,arte.png,,\n")
    itens = ler_pedidos_csv(csv, catalogo)
    porta = itens[0].produto
    assert (porta.codigo, porta.largura_total_cm, porta.altura_total_cm) == ("capa-porta-70.5x200", 72.5, 202)
    assert itens[1].produto.codigo == "almofada-45"


@pytest.mark.parametrize("linha, erro", [
    ("P1,capa-porta,1,arte.png,,", "informe largura_cm"),
    ("P1,capa-porta,1,arte.png,160,200", "acima do máximo"),
    ("P1,almofada-45,1,arte.png,50,50", "medida fixa"),
])
def test_sob_medida_validacao(catalogo, tmp_path, linha, erro):
    csv = tmp_path / "pedidos.csv"
    csv.write_text("pedido,produto,quantidade,arte_frente,largura_cm,altura_cm\n" + linha + "\n")
    with pytest.raises(ValueError, match=erro):
        ler_pedidos_csv(csv, catalogo)


def test_peca_maior_que_comprimento_max_fica_sozinha(catalogo, arte):
    porta = catalogo.produto("capa-porta").com_medidas(150, 300)
    pronta = preparar_arte(arte, 150, 300, 5)
    pecas = [Peca(produto=porta, arte=pronta, pedido="P")] + _pecas(catalogo, arte, "almofada-45", 3)
    folhas = encaixar(pecas, 180, 0.5, 300)
    assert len(folhas[0].posicoes) == 1 and folhas[0].comprimento_cm == 302
    assert len(folhas[1].posicoes) == 3


def test_cli_peca_sob_medida(arte, tmp_path):
    assert main(["peca", "--produto", "capa-porta", "--largura", "70", "--altura", "200",
                 "--pedido", "9", "--frente", str(arte), "--saida", str(tmp_path), "--dpi", "10"]) == 0
    from PIL import Image
    img = Image.open(tmp_path / "capa-porta-70x200_9.png")
    assert img.size == (cm_para_px(72, 10), cm_para_px(202, 10))


def test_cli_produto_inexistente(arte, tmp_path, capsys):
    assert main(["peca", "--produto", "xx", "--pedido", "1", "--frente", str(arte),
                 "--saida", str(tmp_path)]) == 1
    assert "não cadastrado" in capsys.readouterr().err
