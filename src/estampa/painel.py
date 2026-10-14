"""Painel da produção: tela com as OS abertas, para deixar num monitor/TV.

    estampa painel --porta 8080

Abra http://<ip-do-computador>:8080 em qualquer navegador da rede local. A
tela atualiza sozinha, destaca (e toca um aviso sonoro) quando chega OS nova
e deixa mover a OS entre Aberta → Em produção → Concluída. Sem senha: use só
na rede interna.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import ordem

_NUMERO = re.compile(r"^[A-Za-z]+-\d+$")


class PainelHandler(BaseHTTPRequestHandler):
    """Rotas do painel. Subclasses definem `pasta_os` (e podem acrescentar rotas)."""

    pasta_os: Path
    pagina_painel = "/"
    navegacao = ""

    def _responder(self, status: int, corpo: bytes, tipo: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, dados, status: int = 200) -> None:
        self._responder(status, json.dumps(dados, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        pasta_os = self.pasta_os
        if self.path in (self.pagina_painel, self.pagina_painel + "index.html"):
            pagina = PAGINA.replace("<!--NAV-->", self.navegacao)
            self._responder(200, pagina.encode(), "text/html; charset=utf-8")
        elif self.path == "/api/os":
            lista = []
            for os_ in ordem.listar(pasta_os):
                d = asdict(os_)
                d["total_pecas"] = os_.total_pecas
                d.pop("arquivos", None)
                lista.append(d)
            self._json(lista[-200:])
        elif self.path.startswith("/ficha/"):
            numero = self.path.rsplit("/", 1)[-1]
            ficha = pasta_os / numero / f"{numero}_ficha.pdf"
            if _NUMERO.match(numero) and ficha.exists():
                self._responder(200, ficha.read_bytes(), "application/pdf")
            else:
                self._json({"erro": "ficha não encontrada"}, HTTPStatus.NOT_FOUND)
        else:
            self._json({"erro": "não encontrado"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        pasta_os = self.pasta_os
        m = re.match(r"^/api/os/([^/]+)/status$", self.path)
        if not m or not _NUMERO.match(m.group(1)):
            return self._json({"erro": "não encontrado"}, HTTPStatus.NOT_FOUND)
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
            status = json.loads(self.rfile.read(tamanho) or b"{}").get("status", "")
            os_ = ordem.mudar_status(pasta_os, m.group(1), status)
        except (ValueError, json.JSONDecodeError) as e:
            return self._json({"erro": str(e)}, HTTPStatus.BAD_REQUEST)
        self._json({"numero": os_.numero, "status": os_.status})

    def log_message(self, *args) -> None:
        pass


def criar_servidor(pasta_os: Path, host: str = "0.0.0.0", porta: int = 8080) -> ThreadingHTTPServer:
    handler = type("Handler", (PainelHandler,), {"pasta_os": pasta_os})
    return ThreadingHTTPServer((host, porta), handler)


PAGINA = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel da Produção</title>
<style>
:root{--bg:#f4f4f2;--card:#fff;--txt:#1c1c1c;--sub:#666;--linha:#ddd;--calandra:#1f4e8c;--prensa:#b3261e;--novo:#fff3c4}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--card:#222;--txt:#eee;--sub:#aaa;--linha:#333;--novo:#4a3f12}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.35 system-ui,sans-serif}
header{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--linha)}
h1{font-size:22px;margin:0}#hora{color:var(--sub)}button{font:inherit;cursor:pointer;border:1px solid var(--linha);background:var(--card);color:var(--txt);border-radius:8px;padding:6px 12px}
main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:12px 16px}
@media (max-width:800px){main{grid-template-columns:1fr}}
.col h2{font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:var(--sub);margin:4px 0 8px}
.os{background:var(--card);border:1px solid var(--linha);border-radius:10px;padding:12px;margin-bottom:10px}
.os.novo{background:var(--novo);animation:pisca 1s 6}@keyframes pisca{50%{outline:3px solid #e0a800}}
.topo{display:flex;justify-content:space-between;gap:8px}.num{font-weight:700;font-size:20px}.entrega{font-weight:600}
.cli{color:var(--sub);margin-bottom:6px}ul{margin:6px 0;padding-left:18px}li{margin:2px 0}
.tag{display:inline-block;color:#fff;font-size:11px;font-weight:700;border-radius:4px;padding:1px 6px;margin-left:4px;vertical-align:middle}
.calandra{background:var(--calandra)}.prensa{background:var(--prensa)}
.acoes{display:flex;gap:8px;justify-content:space-between;align-items:center;margin-top:8px}.acoes a{color:inherit}
.erro{color:var(--prensa);font-weight:600}.vazio{color:var(--sub);font-style:italic}
</style></head><body>
<!--NAV--><header><h1>Produção</h1><div><span id="hora"></span> <button id="som">🔔 Ativar som</button></div></header>
<main>
<section class="col"><h2>Abertas</h2><div id="aberta"></div></section>
<section class="col"><h2>Em produção</h2><div id="em produção"></div></section>
<section class="col"><h2>Concluídas</h2><div id="concluída"></div></section>
</main>
<script>
const PROXIMO={"aberta":"em produção","em produção":"concluída"};
let conhecidas=null, somAtivo=false, ctx=null;
document.getElementById("som").onclick=()=>{ctx=ctx||new AudioContext();somAtivo=true;document.getElementById("som").textContent="🔔 Som ativo";bip();};
function bip(){if(!somAtivo||!ctx)return;[0,.25,.5].forEach(t=>{const o=ctx.createOscillator(),g=ctx.createGain();o.frequency.value=880;o.connect(g);g.connect(ctx.destination);g.gain.setValueAtTime(.2,ctx.currentTime+t);o.start(ctx.currentTime+t);o.stop(ctx.currentTime+t+.15);});}
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function cartao(o,novo){
  const itens=o.itens.map(i=>`<li>${i.quantidade}x ${esc(i.produto)}${i.lados==2?" (frente e verso)":""}<span class="tag ${esc(i.transferencia)}">${esc(i.transferencia).toUpperCase()}</span></li>`).join("");
  const prox=PROXIMO[o.status];
  return `<div class="os${novo?" novo":""}"><div class="topo"><span class="num">${esc(o.numero)}</span><span class="entrega">${o.entrega?"Entrega "+esc(o.entrega):""}</span></div>
  <div class="cli">${esc(o.cliente)} · ${o.total_pecas} peça(s) · ${esc(o.criada_em)}</div>
  ${o.observacoes?`<div>Obs.: ${esc(o.observacoes)}</div>`:""}<ul>${itens}</ul>
  ${o.erros&&o.erros.length?`<div class="erro">⚠ ${o.erros.length} item(ns) com erro nos arquivos</div>`:""}
  <div class="acoes"><a href="/ficha/${encodeURIComponent(o.numero)}" target="_blank">Ficha</a>
  ${prox?`<button data-n="${esc(o.numero)}" data-s="${prox}">→ ${prox[0].toUpperCase()+prox.slice(1)}</button>`:""}</div></div>`;
}
async function atualizar(){
  document.getElementById("hora").textContent=new Date().toLocaleTimeString("pt-BR");
  let lista; try{lista=await (await fetch("/api/os")).json();}catch(e){return;}
  const numeros=new Set(lista.map(o=>o.numero));
  const novas=conhecidas?lista.filter(o=>!conhecidas.has(o.numero)).map(o=>o.numero):[];
  if(novas.length)bip();
  conhecidas=numeros;
  for(const st of ["aberta","em produção","concluída"]){
    let grupo=lista.filter(o=>o.status===st);
    if(st==="concluída")grupo=grupo.slice(-15).reverse();
    document.getElementById(st).innerHTML=grupo.map(o=>cartao(o,novas.includes(o.numero))).join("")||'<div class="vazio">nada aqui</div>';
  }
}
document.addEventListener("click",async e=>{const b=e.target.closest("button[data-n]");if(!b)return;
  await fetch(`/api/os/${encodeURIComponent(b.dataset.n)}/status`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:b.dataset.s})});atualizar();});
atualizar();setInterval(atualizar,10000);
</script></body></html>
"""
