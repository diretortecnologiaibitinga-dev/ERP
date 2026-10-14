import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from estampa import ordem
from estampa.cli import main


def test_numeracao_sequencial(tmp_path):
    assert ordem.proximo_numero(tmp_path) == "OS-000001"
    assert ordem.proximo_numero(tmp_path) == "OS-000002"
    assert ordem.proximo_numero(tmp_path, "PED") == "PED-000003"


def _servidor():
    recebidos = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            recebidos.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, recebidos


def test_cli_os_gera_arquivos_ficha_e_avisa(arte, tmp_path, capsys):
    toml = tmp_path / "produtos.toml"
    toml.write_text('[os]\npasta = "ordens"\n'
                    '[produtos.almofada-45]\nnome = "Almofada 45x45"\nlargura_cm = 45\naltura_cm = 45\nlados = 2\n')
    csv = tmp_path / "itens.csv"
    csv.write_text("produto,quantidade,arte_frente,arte_verso\nalmofada-45,2,arte.png,arte.png\n"
                   "almofada-45,1,arte.png,\n")
    srv, recebidos = _servidor()
    try:
        codigo = main(["--catalogo", str(toml), "os", str(csv), "--cliente", "Loja do João",
                       "--entrega", "20/10", "--saida", str(tmp_path / "rip"), "--dpi", "20", "--processos", "1",
                       "--webhook", f"http://127.0.0.1:{srv.server_port}/"])
    finally:
        srv.shutdown()
    assert codigo == 0
    assert sorted(f.name for f in (tmp_path / "rip").iterdir())[0] == "almofada-45_OS-000001.png"
    assert len(list((tmp_path / "rip").iterdir())) == 5

    pasta = tmp_path / "ordens" / "OS-000001"
    assert (pasta / "OS-000001_ficha.pdf").read_bytes().startswith(b"%PDF")
    dados = json.loads((pasta / "os.json").read_text())
    assert dados["cliente"] == "Loja do João" and len(dados["arquivos"]) == 5

    assert len(recebidos) == 1
    assert "OS-000001 — Loja do João" in recebidos[0]["text"]
    assert recebidos[0]["total_pecas"] == 5
    assert "produção avisada" in capsys.readouterr().out


def test_etiqueta_da_os(catalogo, arte):
    from estampa.imagem import preparar_arte
    from estampa.peca import Peca
    p = Peca(catalogo.produto("almofada-45"), preparar_arte(arte, 45, 45, 10), "OS-000012")
    assert p.etiqueta == "OS-000012"


def test_aviso_falho_nao_derruba_a_os(arte, tmp_path, capsys):
    toml = tmp_path / "produtos.toml"
    toml.write_text('[produtos.almofada-45]\nnome = "A"\nlargura_cm = 45\naltura_cm = 45\n')
    csv = tmp_path / "itens.csv"
    csv.write_text("produto,quantidade,arte_frente\nalmofada-45,1,arte.png\n")
    assert main(["--catalogo", str(toml), "os", str(csv), "--cliente", "X", "--saida", str(tmp_path / "rip"),
                 "--dpi", "20", "--webhook", "http://127.0.0.1:9/"]) == 0
    assert "não foi possível avisar" in capsys.readouterr().err
