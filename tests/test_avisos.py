import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from estampa import avisos, ordem
from estampa.painel import criar_servidor


@pytest.fixture
def servidor():
    recebidos = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            corpo = self.rfile.read(int(self.headers["Content-Length"]))
            recebidos.append((self.path, {k.lower(): v for k, v in self.headers.items()}, corpo))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", recebidos
    srv.shutdown()


def _os():
    return ordem.OrdemServico("OS-000009", "Loja X", "14/10/2026 10:00", "20/10",
                              itens=[ordem.ResumoItem("Almofada 45x45", "47x47", 3, 2, ["a.jpg", "b.jpg"], "prensa")])


def test_resumo_tem_transferencia():
    texto = _os().resumo_texto()
    assert "3x Almofada 45x45 (frente e verso) — prensa" in texto and "6 peça(s)" in texto


def test_telegram_mensagem_e_ficha(servidor, tmp_path):
    url, recebidos = servidor
    ficha = tmp_path / "OS-000009_ficha.pdf"
    ficha.write_bytes(b"%PDF-teste")
    [canal] = avisos.canais({"telegram": {"token": "abc", "chat_id": "-100", "api": url}})
    assert avisos.avisar([canal], _os(), ficha) == [("telegram", None)]
    assert recebidos[0][0] == "/botabc/sendMessage"
    assert json.loads(recebidos[0][2])["chat_id"] == "-100"
    assert recebidos[1][0] == "/botabc/sendDocument" and b"%PDF-teste" in recebidos[1][2]


def test_whatsapp_evolution(servidor, tmp_path, monkeypatch):
    url, recebidos = servidor
    monkeypatch.setenv("CHAVE_WA", "segredo")
    ficha = tmp_path / "f.pdf"
    ficha.write_bytes(b"%PDF")
    [canal] = avisos.canais({"whatsapp": {"url": url, "instancia": "prod", "apikey": "env:CHAVE_WA",
                                          "grupo": "123@g.us"}})
    avisos.avisar([canal], _os(), ficha)
    caminho, cabecalhos, corpo = recebidos[0]
    assert caminho == "/message/sendText/prod" and cabecalhos["apikey"] == "segredo"
    assert json.loads(corpo)["number"] == "123@g.us"
    assert json.loads(recebidos[1][2])["mediatype"] == "document"


def test_canais_vazios_e_falha_isolada(servidor):
    url, _ = servidor
    assert avisos.canais({"telegram": {}, "whatsapp": {"url": ""}}) == []
    lista = [avisos.Webhook("http://127.0.0.1:9/"), avisos.Webhook(url)]
    resultado = avisos.avisar(lista, _os(), None)
    assert resultado[0][1] is not None and resultado[1] == ("webhook", None)


def test_canal_incompleto():
    with pytest.raises(ValueError, match="chat_id"):
        avisos.canais({"telegram": {"token": "abc"}})


def test_painel(tmp_path):
    pasta = tmp_path / "ordens"
    ordem.registrar(pasta, _os(), [])
    srv = criar_servidor(pasta, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert b"Produ" in urllib.request.urlopen(base + "/").read()
        lista = json.loads(urllib.request.urlopen(base + "/api/os").read())
        assert lista[0]["numero"] == "OS-000009" and lista[0]["status"] == "aberta"
        assert lista[0]["total_pecas"] == 6

        req = urllib.request.Request(base + "/api/os/OS-000009/status", method="POST",
                                     data=json.dumps({"status": "em produção"}).encode())
        assert json.loads(urllib.request.urlopen(req).read())["status"] == "em produção"
        salvo = ordem.carregar(pasta / "OS-000009")
        assert salvo.status == "em produção" and len(salvo.historico) == 2

        assert urllib.request.urlopen(base + "/ficha/OS-000009").read().startswith(b"%PDF")
        for ruim in ("/ficha/..%2F..%2Fetc", "/api/os/../status"):
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(urllib.request.Request(base + ruim, method="POST" if "api" in ruim else "GET"))
        req = urllib.request.Request(base + "/api/os/OS-000009/status", method="POST",
                                     data=json.dumps({"status": "xyz"}).encode())
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(req)
    finally:
        srv.shutdown()
