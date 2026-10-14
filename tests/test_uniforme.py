import pytest
from PIL import Image, ImageDraw

from estampa.cli import main
from estampa.imagem import cm_para_px
from estampa.moldes import importar_pdf
from estampa.moldes_exemplo import gerar_pdf_moldes_exemplo
from estampa.uniforme import (ConfigUniformes, Jogador, PedidoUniforme, carregar_config, exportar_time,
                              ler_jogadores, renderizar_parte)

DPI = 20


@pytest.fixture(scope="module")
def time(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("time")
    pdf = gerar_pdf_moldes_exemplo(pasta / "exemplo.pdf")
    modelo = importar_pdf(pdf, "exemplo")
    modelo.salvar(pasta / "moldes" / "exemplo.json")
    # arte com faixas verticais de 5 cm alternando vermelho/azul, no quadro da frente (68.4 x 90 cm)
    larg = cm_para_px(68.4, 40)
    arte = Image.new("RGB", (larg, cm_para_px(90, 40)), (0, 0, 255))
    d = ImageDraw.Draw(arte)
    faixa = cm_para_px(5, 40)
    for x in range(0, larg, 2 * faixa):
        d.rectangle((x, 0, x + faixa - 1, arte.height), fill=(255, 0, 0))
    arte.save(pasta / "frente.png")
    Image.new("RGB", (400, 540), (0, 120, 0)).save(pasta / "costas.png")
    Image.new("RGBA", (200, 200), (255, 255, 0, 255)).save(pasta / "escudo.png")
    return pasta


def _pedido(time, **kw):
    return PedidoUniforme("T1", time / "moldes" / "exemplo.json",
                          {"frente": time / "frente.png", "costas": time / "costas.png"},
                          logos={"1": time / "escudo.png"}, **kw)


def test_le_planilha_csv_e_xlsx(tmp_path):
    csv = tmp_path / "time.csv"
    csv.write_text("Nomes;Números;Tamanho;Qtd\nLucas;08;m;2\n;;;\nAna;7;BLM (S);\n")
    assert ler_jogadores(csv) == [Jogador("Lucas", "08", "M", 2), Jogador("Ana", "7", "BLM", 1)]

    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nomes", "Números", None, None, None])
    ws.append(["Rafael", "08"])
    ws.append(["Bruno", 11])
    ws.append([None, None, None, None, ";"])
    wb.save(tmp_path / "time.xlsx")
    assert ler_jogadores(tmp_path / "time.xlsx", "G") == [Jogador("Rafael", "08", "G"), Jogador("Bruno", "11", "G")]
    with pytest.raises(ValueError, match="sem tamanho"):
        ler_jogadores(tmp_path / "time.xlsx")


def test_peca_no_tamanho_do_molde_com_fora_branco(time):
    ped = _pedido(time)
    img = renderizar_parte(ped, Jogador("Lucas", "10", "M"), "frente_careca", "frente", ConfigUniformes(), DPI)
    assert img.size == (cm_para_px(57, DPI), cm_para_px(75, DPI))
    assert img.getpixel((img.width // 2, 1)) == (255, 255, 255)  # dentro do decote: fora do molde


def test_arte_nao_estica_entre_tamanhos(time):
    """A mesma posição física (a partir do centro e do topo) tem a mesma cor em todos os tamanhos."""
    ped = _pedido(time)
    cfg = ConfigUniformes()
    k = DPI / 2.54
    for dx_cm in (-12.5, -7.5, 2.5, 12.5):
        cores = set()
        for tam in ("8", "M", "XGG"):
            img = renderizar_parte(ped, Jogador("", "", tam), "frente_careca", "frente", cfg, DPI)
            cor = img.getpixel((round(img.width / 2 + dx_cm * k), round(30 * k)))
            cores.add("vermelho" if cor[0] > 200 and cor[2] < 60 else "azul" if cor[2] > 200 and cor[0] < 60 else cor)
        assert len(cores) == 1, (dx_cm, cores)


def test_logo_no_marcador_e_numero_nas_costas(time):
    ped = _pedido(time)
    cfg = ConfigUniformes()
    k = DPI / 2.54
    frente = renderizar_parte(ped, Jogador("Lucas", "10", "M"), "frente_careca", "frente", cfg, DPI)
    assert frente.getpixel((round(57 * 0.3 * k), round(75 * 0.3 * k))) == (255, 255, 0)
    costas = renderizar_parte(ped, Jogador("Lucas", "10", "M"), "costas", "costas", cfg, DPI)
    faixa = costas.crop((0, round(costas.height * 0.36), costas.width, round(costas.height * 0.52)))
    b = faixa.tobytes()
    brancos = sum(1 for i in range(0, len(b), 3) if b[i] > 240 and b[i + 1] > 240 and b[i + 2] > 240)
    assert brancos > 50  # número branco sobre o verde


def test_numero_maior_no_adulto(time):
    ped = _pedido(time)
    cfg = ConfigUniformes()

    def altura_numero(tam):
        img = renderizar_parte(ped, Jogador("", "10", tam), "costas", "costas", cfg, 40)
        faixa = img.crop((img.width // 4, round(img.height * 0.25), 3 * img.width // 4, round(img.height * 0.7)))
        linhas = [y for y in range(faixa.height) if any(faixa.getpixel((x, y)) == (255, 255, 255) for x in range(0, faixa.width, 3))]
        return (max(linhas) - min(linhas)) / 40 * 2.54

    assert altura_numero("8") == pytest.approx(15, abs=1.5)
    assert altura_numero("M") == pytest.approx(22, abs=1.5)


def test_exporta_time_entregue_por_jogador(time, tmp_path):
    js = [Jogador("Lucas", "10", "M"), Jogador("Ana", "7", "BLM", 2), Jogador("Zé", "1", "XXXG")]
    with pytest.raises(ValueError, match="XXXG"):
        list(exportar_time(_pedido(time), js, ConfigUniformes(), DPI, tmp_path, processos=1))
    rs = list(exportar_time(_pedido(time, manga="longa", gola="v"), js[:2], ConfigUniformes(), DPI, tmp_path, processos=1))
    assert [len(r.arquivos) for r in rs] == [4, 8]
    nomes = sorted(f.name for f in tmp_path.iterdir())
    assert "uniforme_T1_M_10-Lucas_frente_v.png" in nomes
    assert "uniforme_T1_BLM_7-Ana_manga_longa_esq_2de2.png" in nomes


def test_config_por_toml(tmp_path):
    cfg = carregar_config({"fonte": "", "elementos": {"numero": {"altura_cm": 20},
                                                       "logo_barra": {"parte": "frente", "centro": [0.5, 0.9]}}}, tmp_path)
    els = {e.nome: e for e in cfg.elementos}
    assert els["numero"].altura_cm == {"infantil": 20, "feminino": 20, "adulto": 20}
    assert els["logo_barra"].tipo == "imagem" and cfg.pasta_moldes == tmp_path / "moldes"


def test_cli_moldes_e_uniforme(time, tmp_path, capsys):
    toml = tmp_path / "produtos.toml"
    toml.write_text('[uniformes]\npasta_moldes = "moldes"\n')
    base = ["--catalogo", str(toml)]
    assert main(base + ["moldes", "importar", str(time / "exemplo.pdf"), "--modelo", "camisa"]) == 0
    assert (tmp_path / "moldes" / "camisa.json").exists() and (tmp_path / "moldes" / "camisa_previa.png").exists()
    planilha = tmp_path / "time.csv"
    planilha.write_text("Nome,Número,Tamanho\nLucas,10,M\nRafa,08,8\n")
    assert main(base + ["uniforme", "--modelo", "camisa", "--jogadores", str(planilha), "--pedido", "T9",
                        "--frente", str(time / "frente.png"), "--logo", f"1={time / 'escudo.png'}",
                        "--saida", str(tmp_path / "rip"), "--dpi", str(DPI), "--processos", "1"]) == 0
    assert len(list((tmp_path / "rip").iterdir())) == 8
    assert "1x M, 1x 8" in capsys.readouterr().out
    assert main(base + ["uniforme", "--modelo", "nao-existe", "--jogadores", str(planilha), "--pedido", "X"]) == 1
