import json
import threading
import urllib.request
import uuid

import pytest

from estampa.demo import criar_demo
from estampa.demo_web import criar_servidor_demo


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("demo")
    resumo = criar_demo(pasta, dpi=12, processos=1)
    return pasta, resumo


def _item(resumo, pedido):
    return next(i for i in resumo["itens"] if i["pedido"] == pedido)


def test_cenarios_da_demo(demo):
    _, r = demo
    assert len(_item(r, "SHP-250114A1")["arquivos"]) == 4                 # frente e verso x 2
    assert _item(r, "TT-5770019")["arquivos"][2].endswith("_3de3.jpg")     # cópias numeradas
    assert _item(r, "SHP-250114C3")["equipamento"] == "prensa"             # porta 106x196 cabe
    assert _item(r, "ML-2000012777")["equipamento"] == "calandra"          # porta 156x306 não cabe
    assert _item(r, "SHP-250114D9")["equipamento"] == "calandra"           # rolo a rolo
    assert "não encontrado" in _item(r, "TT-5770088")["erro"]              # falha isolada
    assert any("rosto não encontrado" in a for a in _item(r, "ML-2000012399")["avisos"])
    assert len(_item(r, "ML-2000012345")["arquivos"]) == 1                 # casal: 2 fotos, 1 peça
    assert r["os"] == ["OS-000001", "OS-000002"]
    time = _item(r, "TIME-FC")
    assert time["erro"] is None and len(time["arquivos"]) == 20 and time["equipamento"] == "calandra"


def _multipart(campos, arquivos):
    fronteira = uuid.uuid4().hex
    partes = [f'--{fronteira}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
              for k, v in campos.items()]
    for nome, caminho in arquivos:
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{nome}"; '
                      f'filename="{caminho.name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
                      + caminho.read_bytes() + b"\r\n")
    partes.append(f"--{fronteira}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={fronteira}"


def test_paginas_e_teste_com_upload(demo):
    pasta, _ = demo
    srv = criar_servidor_demo(pasta, "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def postar(campos, arquivos):
        corpo, tipo = _multipart(campos, arquivos)
        req = urllib.request.Request(base + "/api/testar", data=corpo, method="POST", headers={"Content-Type": tipo})
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

    try:
        for rota in ("/", "/painel", "/testar", "/api/pedidos", "/api/os", "/ficha/OS-000001",
                     "/mini/molduras/coracao-namorados.png"):
            assert urllib.request.urlopen(base + rota).status == 200
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/arquivo/..%2F..%2Fsegredo.txt")
        cat = json.loads(urllib.request.urlopen(base + "/api/catalogo").read())
        assert {m["codigo"]: m["espacos"] for m in cat["molduras"]} == {"casal-dois-coracoes": 2, "coracao-namorados": 1}

        foto = pasta / "fotos" / "foto_rosto_direita.jpg"
        r = postar({"produto": "almofada-45", "moldura_frente": "coracao-namorados", "quantidade": "2"},
                   [("frente", foto)])
        assert r["erro"] is None and len(r["arquivos"]) == 2 and r["equipamento"] == "prensa"
        assert urllib.request.urlopen(base + "/arquivo/" + r["arquivos"][0]).status == 200

        r = postar({"produto": "capa-porta", "largura": "150", "altura": "300", "transferencia": "prensa"},
                   [("frente", pasta / "artes" / "porta.jpg")])
        assert "não cabe na prensa" in r["erro"]

        r = postar({"produto": "almofada-45", "moldura_frente": "casal-dois-coracoes"}, [("frente", foto)])
        assert "2 espaço(s)" in r["erro"]
    finally:
        srv.shutdown()
