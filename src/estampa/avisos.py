"""Avisos de nova OS para a produção.

Canais (configurados em `[avisos.*]` no produtos.toml; podem ser usados juntos):

- telegram: robô do Telegram (oficial e gratuito) — mensagem + ficha em PDF;
- whatsapp: grupo de WhatsApp via Evolution API — mensagem + ficha em PDF.
  É uma API NÃO oficial: use um número dedicado à produção (há risco de bloqueio);
- webhook: POST JSON para n8n, Make, ntfy, Discord etc.

A tela da produção é o painel (`estampa painel`), que lê as OS direto da pasta.

Valores no formato "env:NOME" são lidos da variável de ambiente NOME, para
não deixar token e senha no arquivo.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
import urllib.request
from dataclasses import asdict
from pathlib import Path

from .ordem import OrdemServico

TIMEOUT = 15


def _valor(v: str | None) -> str:
    v = (v or "").strip()
    if v.startswith("env:"):
        return os.environ.get(v[4:], "")
    return v


def _post_json(url: str, corpo: dict, cabecalhos: dict | None = None) -> bytes:
    req = urllib.request.Request(
        url, data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **(cabecalhos or {})},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _post_multipart(url: str, campos: dict[str, str], arquivo: tuple[str, str, bytes]) -> bytes:
    fronteira = uuid.uuid4().hex
    partes = []
    for nome, valor in campos.items():
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n{valor}\r\n'.encode())
    campo, nome_arquivo, conteudo = arquivo
    partes.append(
        f'--{fronteira}\r\nContent-Disposition: form-data; name="{campo}"; filename="{nome_arquivo}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n".encode() + conteudo + b"\r\n")
    partes.append(f"--{fronteira}--\r\n".encode())
    req = urllib.request.Request(url, data=b"".join(partes), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={fronteira}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


class Canal:
    nome = "canal"

    def enviar(self, os_: OrdemServico, ficha: Path | None) -> None:
        raise NotImplementedError


class Telegram(Canal):
    nome = "telegram"

    def __init__(self, token: str, chat_id: str, api: str = "https://api.telegram.org"):
        if not token or not chat_id:
            raise ValueError("telegram: informe token e chat_id")
        self.base = f"{api.rstrip('/')}/bot{token}"
        self.chat_id = chat_id

    def enviar(self, os_: OrdemServico, ficha: Path | None) -> None:
        _post_json(f"{self.base}/sendMessage", {"chat_id": self.chat_id, "text": os_.resumo_texto()})
        if ficha and ficha.exists():
            _post_multipart(f"{self.base}/sendDocument", {"chat_id": self.chat_id, "caption": os_.numero},
                            ("document", ficha.name, ficha.read_bytes()))


class WhatsAppEvolution(Canal):
    nome = "whatsapp"

    def __init__(self, url: str, instancia: str, apikey: str, grupo: str):
        if not (url and instancia and grupo):
            raise ValueError("whatsapp: informe url, instancia e grupo")
        self.base = url.rstrip("/")
        self.instancia = instancia
        self.cabecalhos = {"apikey": apikey}
        self.grupo = grupo

    def enviar(self, os_: OrdemServico, ficha: Path | None) -> None:
        _post_json(f"{self.base}/message/sendText/{self.instancia}",
                   {"number": self.grupo, "text": os_.resumo_texto()}, self.cabecalhos)
        if ficha and ficha.exists():
            _post_json(f"{self.base}/message/sendMedia/{self.instancia}", {
                "number": self.grupo, "mediatype": "document", "mimetype": "application/pdf",
                "caption": os_.numero, "fileName": ficha.name,
                "media": base64.b64encode(ficha.read_bytes()).decode(),
            }, self.cabecalhos)


class Webhook(Canal):
    nome = "webhook"

    def __init__(self, url: str):
        if not url:
            raise ValueError("webhook: informe url")
        self.url = url

    def enviar(self, os_: OrdemServico, ficha: Path | None) -> None:
        texto = os_.resumo_texto()
        _post_json(self.url, {"text": texto, "content": texto, "os": asdict(os_),
                              "total_pecas": os_.total_pecas, "ficha": str(ficha) if ficha else None})


def canais(config: dict) -> list[Canal]:
    """Canais ativos a partir da seção [avisos] (seções vazias são ignoradas)."""
    ativos: list[Canal] = []
    tg = {k: _valor(v) for k, v in config.get("telegram", {}).items()}
    if any(tg.values()):
        ativos.append(Telegram(tg.get("token", ""), tg.get("chat_id", ""), tg.get("api") or "https://api.telegram.org"))
    wa = {k: _valor(v) for k, v in config.get("whatsapp", {}).items()}
    if any(wa.values()):
        ativos.append(WhatsAppEvolution(wa.get("url", ""), wa.get("instancia", ""), wa.get("apikey", ""), wa.get("grupo", "")))
    wh = _valor(config.get("webhook", {}).get("url"))
    if wh:
        ativos.append(Webhook(wh))
    return ativos


def avisar(lista: list[Canal], os_: OrdemServico, ficha: Path | None) -> list[tuple[str, str | None]]:
    """Envia por todos os canais; a falha de um não impede os outros.
    Devolve (canal, erro ou None)."""
    resultado = []
    for canal in lista:
        try:
            canal.enviar(os_, ficha)
            resultado.append((canal.nome, None))
        except OSError as e:
            resultado.append((canal.nome, str(e)))
    return resultado
