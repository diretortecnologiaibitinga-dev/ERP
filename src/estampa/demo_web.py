"""Páginas da demonstração: pedidos do dia, painel da produção e testes com upload."""

from __future__ import annotations

import io
import json
import re
import uuid
from email.parser import BytesParser
from email.policy import default as politica_email
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

from .lote import ItemPedido, Lado, OpcoesExportacao, exportar_item, resolver_moldura
from .moldura import Ajuste, carregar_moldura, detectar_furos
from .painel import PainelHandler
from .produtos import carregar_catalogo

LIMITE_UPLOAD = 60 * 1024 * 1024
TIPOS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf",
         ".csv": "text/csv; charset=utf-8", ".toml": "text/plain; charset=utf-8"}
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}

NAV = """<nav class="demo"><b>Demonstração</b>
<a href="/" data-p="/">Pedidos do dia</a><a href="/painel" data-p="/painel">Painel da produção</a>
<a href="/testar" data-p="/testar">Testar com sua foto</a></nav>
<style>nav.demo{display:flex;gap:16px;flex-wrap:wrap;align-items:center;padding:10px 16px;background:#1f4e8c;color:#fff}
nav.demo a{color:#fff;text-decoration:none;opacity:.8}nav.demo a.ativo{opacity:1;font-weight:700;text-decoration:underline}</style>
<script>document.querySelectorAll("nav.demo a").forEach(a=>{if(a.dataset.p===location.pathname)a.classList.add("ativo")})</script>"""


def criar_servidor_demo(pasta: Path, host: str = "0.0.0.0", porta: int = 8080) -> ThreadingHTTPServer:
    pasta = pasta.resolve()
    catalogo = carregar_catalogo(pasta / "produtos.toml")
    handler = type("DemoHandler", (DemoHandler,), {
        "pasta_demo": pasta, "catalogo": catalogo, "pasta_os": catalogo.os.pasta, "miniaturas": {},
    })
    return ThreadingHTTPServer((host, porta), handler)


class DemoHandler(PainelHandler):
    pasta_demo: Path
    pagina_painel = "/painel"
    navegacao = NAV
    miniaturas: dict

    def _html(self, pagina: str) -> None:
        self._responder(200, pagina.replace("<!--NAV-->", NAV).encode(), "text/html; charset=utf-8")

    def _arquivo_seguro(self, relativo: str) -> Path | None:
        caminho = (self.pasta_demo / unquote(relativo)).resolve()
        if caminho.is_file() and caminho.is_relative_to(self.pasta_demo):
            return caminho
        return None

    def _resultado(self) -> dict:
        return json.loads((self.pasta_demo / "resultado.json").read_text(encoding="utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        caminho = self.path.split("?", 1)[0]
        if caminho == "/":
            return self._html(PAGINA_PEDIDOS)
        if caminho == "/testar":
            return self._html(PAGINA_TESTAR)
        if caminho == "/api/pedidos":
            return self._json(self._resultado())
        if caminho == "/api/catalogo":
            return self._json(self._catalogo())
        if caminho.startswith("/arquivo/"):
            arquivo = self._arquivo_seguro(caminho[len("/arquivo/"):])
            if not arquivo or arquivo.suffix.lower() not in TIPOS:
                return self._json({"erro": "arquivo não encontrado"}, HTTPStatus.NOT_FOUND)
            return self._responder(200, arquivo.read_bytes(), TIPOS[arquivo.suffix.lower()])
        if caminho.startswith("/mini/"):
            arquivo = self._arquivo_seguro(caminho[len("/mini/"):])
            if not arquivo or arquivo.suffix.lower() not in EXTENSOES_IMAGEM:
                return self._json({"erro": "imagem não encontrada"}, HTTPStatus.NOT_FOUND)
            return self._responder(200, self._miniatura(arquivo), "image/jpeg")
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/testar":
            return self._testar()
        super().do_POST()

    # ------------------------------------------------------------ apoio

    def _miniatura(self, arquivo: Path) -> bytes:
        chave = (str(arquivo), arquivo.stat().st_mtime)
        if chave not in self.miniaturas:
            img = Image.open(arquivo)
            img.draft("RGB", (700, 700))
            img.thumbnail((700, 700), Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "LA", "P"):  # transparência aparece como xadrez
                img = img.convert("RGBA")
                xadrez = Image.new("RGBA", img.size, (255, 255, 255, 255))
                passo = max(8, img.width // 24)
                for y in range(0, img.height, passo):
                    for x in range((y // passo) % 2 * passo, img.width, 2 * passo):
                        xadrez.paste((215, 215, 215, 255), (x, y, x + passo, y + passo))
                img = Image.alpha_composite(xadrez, img)
            img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=85)
            self.miniaturas[chave] = buf.getvalue()
        return self.miniaturas[chave]

    def _catalogo(self) -> dict:
        produtos = [{
            "codigo": p.codigo, "nome": p.nome, "sob_medida": p.sob_medida, "lados": p.lados,
            "largura_cm": p.largura_cm, "altura_cm": p.altura_cm, "margem_cm": p.margem_cm,
            "transferencia": p.transferencia,
        } for p in self.catalogo.produtos.values()]
        molduras = []
        for png in sorted(self.catalogo.pasta_molduras.glob("*.png")):
            try:
                furos = len(detectar_furos(carregar_moldura(png)))
            except ValueError:
                continue
            molduras.append({"codigo": png.stem, "espacos": furos,
                             "arquivo": str(png.resolve().relative_to(self.pasta_demo))})
        return {"produtos": produtos, "molduras": molduras}

    def _testar(self) -> None:
        tamanho = int(self.headers.get("Content-Length") or 0)
        if not tamanho or tamanho > LIMITE_UPLOAD:
            return self._json({"erro": "envie as imagens (até 60 MB no total)"}, HTTPStatus.BAD_REQUEST)
        corpo = self.rfile.read(tamanho)
        msg = BytesParser(policy=politica_email).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + corpo)
        campos: dict[str, str] = {}
        arquivos: dict[str, list[tuple[str, bytes]]] = {"frente": [], "verso": []}
        for parte in msg.iter_parts():
            nome = parte.get_param("name", header="content-disposition")
            if parte.get_filename() and nome in arquivos:
                dados = parte.get_payload(decode=True)
                if dados:
                    arquivos[nome].append((parte.get_filename(), dados))
            elif nome:
                campos[nome] = parte.get_content().strip()

        teste = f"TESTE-{uuid.uuid4().hex[:6].upper()}"
        pasta = self.pasta_demo / "testes" / teste
        try:
            cat = self.catalogo
            produto = cat.produto(campos.get("produto", ""))
            if produto.sob_medida:
                produto = produto.com_medidas(float(campos.get("largura") or 0), float(campos.get("altura") or 0))
            equipamento = cat.resolver_transferencia(produto, campos.get("transferencia") or None)
            ajuste = Ajuste(float(campos.get("zoom") or 1), float(campos.get("desloc_x") or 0),
                            float(campos.get("desloc_y") or 0))
            pasta.mkdir(parents=True)
            lados = []
            for lado in ("frente", "verso"):
                fotos = []
                for n, (nome, dados) in enumerate(arquivos[lado], start=1):
                    sufixo = Path(nome).suffix.lower()
                    if sufixo not in EXTENSOES_IMAGEM:
                        raise ValueError(f"{nome}: envie uma imagem (JPG, PNG…)")
                    destino = pasta / f"{lado}_{n}{sufixo}"
                    destino.write_bytes(dados)
                    fotos.append(destino)
                if fotos:
                    moldura = resolver_moldura(campos.get(f"moldura_{lado}", ""), pasta, cat)
                    lados.append(Lado(tuple(fotos), moldura, ajuste))
            if not lados or not arquivos["frente"]:
                raise ValueError("envie pelo menos a arte ou foto da frente")
            if len(lados) == 2 and produto.lados < 2:
                raise ValueError(f"{produto.nome} não aceita verso")
            item = ItemPedido(teste, produto, max(1, min(10, int(campos.get("quantidade") or 1))), lados, equipamento)
        except (KeyError, ValueError) as e:
            return self._json({"erro": e.args[0] if e.args else str(e)}, HTTPStatus.BAD_REQUEST)

        resumo = self._resultado()
        cfg = cat.config
        op = OpcoesExportacao(saida=pasta / "saida", formato="jpg", dpi=cfg.dpi, dpi_forcado=resumo.get("dpi_forcado"),
                              borda_mm=cfg.borda_mm, rosto=cfg.enquadrar_rosto and not campos.get("sem_rosto"))
        op.saida.mkdir(parents=True, exist_ok=True)
        r = exportar_item(item, op)
        self._json({
            "pedido": teste, "produto": produto.nome, "equipamento": equipamento,
            "peca_cm": f"{produto.largura_total_cm:g} x {produto.altura_total_cm:g}",
            "estampa_cm": f"{produto.largura_cm:g} x {produto.altura_cm:g}",
            "arquivos": [str(Path(a).relative_to(self.pasta_demo)) for a in r.arquivos],
            "avisos": [re.sub(r"^pedido [^:]+: ", "", a) for a in r.avisos], "erro": r.erro,
        })


ESTILO = """<style>
:root{--bg:#f4f4f2;--card:#fff;--txt:#1c1c1c;--sub:#666;--linha:#ddd;--calandra:#1f4e8c;--prensa:#b3261e;--aviso:#8a5a00;--avisobg:#fff4d6;--erro:#b3261e;--errobg:#fde8e6;--ok:#1e7a3c}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--card:#222;--txt:#eee;--sub:#aaa;--linha:#333;--avisobg:#3a2f12;--aviso:#f0c060;--errobg:#3d1714;--erro:#ff8a80;--ok:#6fcf8f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.4 system-ui,sans-serif}
main{max-width:1200px;margin:0 auto;padding:16px}h1{font-size:22px;margin:4px 0 4px}p.sub{color:var(--sub);margin:0 0 16px}
.resumo{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--linha);border-radius:10px;padding:10px 12px}.kpi b{display:block;font-size:24px}.kpi span{color:var(--sub);font-size:13px}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}
@media (max-width:420px){.grade{grid-template-columns:1fr}}
.item{background:var(--card);border:1px solid var(--linha);border-radius:10px;padding:12px;min-width:0}
.item.falhou{border-color:var(--erro)}.cab{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.ped{font-weight:700;overflow-wrap:anywhere}.canal{font-size:12px;color:var(--sub);white-space:nowrap}
.cen{margin:6px 0 8px;font-style:italic}.meta{color:var(--sub);font-size:13px}
.tag{display:inline-block;color:#fff;font-size:11px;font-weight:700;border-radius:4px;padding:1px 6px;vertical-align:middle}
.calandra{background:var(--calandra)}.prensa{background:var(--prensa)}
.minis{display:flex;gap:6px;overflow-x:auto;padding:8px 0 4px}.minis a{flex:0 0 auto}
.minis img{height:120px;border:1px solid var(--linha);border-radius:4px;background:#fff;display:block}
.mais{align-self:center;color:var(--sub);font-size:13px;white-space:nowrap}
.msg{border-radius:6px;padding:6px 8px;margin-top:6px;font-size:13px}.msg.aviso{background:var(--avisobg);color:var(--aviso)}
.msg.erro{background:var(--errobg);color:var(--erro);font-weight:600}.msg.ok{color:var(--ok)}
form{background:var(--card);border:1px solid var(--linha);border-radius:10px;padding:14px;display:grid;gap:12px}
label{display:grid;gap:4px;font-weight:600;min-width:0}label small{font-weight:400;color:var(--sub)}
select,input,button{font:inherit;padding:8px;border:1px solid var(--linha);border-radius:8px;background:var(--card);color:var(--txt);width:100%;min-width:0}
input[type=radio],input[type=checkbox]{width:auto}
button{background:#1f4e8c;color:#fff;border:0;font-weight:700;cursor:pointer;padding:10px}button:disabled{opacity:.6}
.linha{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.oculto{display:none}.dois{display:grid;grid-template-columns:minmax(0,380px) minmax(0,1fr);gap:16px;align-items:start}
@media (max-width:800px){.dois{grid-template-columns:1fr}}
.resultado img{max-width:100%;border:1px solid var(--linha);border-radius:6px;background:#fff}
.molduras{display:flex;gap:8px;flex-wrap:wrap}.molduras label{font-weight:400;display:flex;flex-direction:column;align-items:center;gap:2px;cursor:pointer}
.molduras img{width:90px;height:90px;border:2px solid var(--linha);border-radius:6px;background:repeating-conic-gradient(#ddd 0 25%,#fff 0 50%) 0/16px 16px}
.molduras input:checked+img{border-color:#1f4e8c}.molduras input{position:absolute;opacity:0}
details{margin-top:18px}summary{cursor:pointer;color:var(--sub)}
</style>"""

PAGINA_PEDIDOS = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Pedidos do Dia</title>""" + ESTILO + """</head><body>
<!--NAV--><main><h1>Pedidos do dia (fictícios)</h1>
<p class="sub">Cada cartão é um pedido de marketplace inventado para testar uma regra. As imagens são os arquivos que foram para a pasta do RIP — clique para ver em tamanho real.</p>
<div class="resumo" id="resumo"></div><div class="grade" id="itens"></div>
<details><summary>Arquivos usados na demonstração</summary><p>
<a href="/arquivo/pedidos_marketplace.csv">pedidos_marketplace.csv</a> ·
<a href="/arquivo/os_cliente_1.csv">os_cliente_1.csv</a> · <a href="/arquivo/os_cliente_2.csv">os_cliente_2.csv</a> ·
<a href="/arquivo/produtos.toml">produtos.toml</a> ·
<a href="/arquivo/time/jogadores.csv">jogadores do time</a> · <a href="/arquivo/moldes_exemplo.pdf">moldes de exemplo (PDF)</a> ·
<a href="/mini/moldes/exemplo_previa.png">moldes importados</a></p></details></main>
<script>
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const enc=p=>p.split("/").map(encodeURIComponent).join("/");
(async()=>{
  const r=await (await fetch("/api/pedidos")).json();
  const pecas=r.itens.reduce((s,i)=>s+i.arquivos.length,0);
  const eq=k=>r.itens.filter(i=>i.equipamento===k&&!i.erro).reduce((s,i)=>s+i.arquivos.length,0);
  const comAviso=r.itens.filter(i=>i.avisos.length).length, falhas=r.itens.filter(i=>i.erro).length;
  document.getElementById("resumo").innerHTML=[
    [r.itens.length,"pedidos"],[pecas,"arquivos gerados"],[eq("prensa"),"peças na prensa"],[eq("calandra"),"peças na calandra"],
    [comAviso,"pedidos com aviso"],[falhas,"pedidos com erro"],[r.tempo_lote_s+" s","tempo do lote"]]
    .map(([v,t])=>`<div class="kpi"><b>${v}</b><span>${t}</span></div>`).join("");
  document.getElementById("itens").innerHTML=r.itens.map(i=>{
    const lim=i.pedido==="TIME-FC"?20:6;
    const minis=i.arquivos.slice(0,lim).map(a=>`<a href="/arquivo/${enc(a)}" target="_blank" title="${esc(a.split("/").pop())}"><img loading="lazy" src="/mini/${enc(a)}" alt="${esc(a)}"></a>`).join("");
    const mais=i.arquivos.length>lim?`<span class="mais">+${i.arquivos.length-lim} arquivos</span>`:"";
    return `<div class="item${i.erro?" falhou":""}"><div class="cab"><span class="ped">${esc(i.pedido)}</span><span class="canal">${esc(i.canal)}</span></div>
      <div class="cen">${esc(i.cenario)}</div>
      <div class="meta">${i.quantidade}x ${esc(i.produto)}${i.lados==2?" · frente e verso":""} · <span class="tag ${esc(i.equipamento)}">${esc(i.equipamento).toUpperCase()}</span> · ${i.arquivos.length} arquivo(s)</div>
      ${i.arquivos.length?`<div class="minis">${minis}${mais}</div>`:""}
      ${i.avisos.map(a=>`<div class="msg aviso">⚠ ${esc(a.replace(/^pedido [^:]+: /,""))}</div>`).join("")}
      ${i.erro?`<div class="msg erro">✖ ${esc(i.erro)}</div>`:""}
      ${!i.erro&&!i.avisos.length?`<div class="msg ok">✔ pronto para o RIP</div>`:""}</div>`;}).join("");
})();
</script></body></html>"""

PAGINA_TESTAR = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Testar Peça</title>""" + ESTILO + """</head><body>
<!--NAV--><main><h1>Testar com sua foto ou arte</h1>
<p class="sub">Escolha o produto, envie a imagem e veja o arquivo exatamente como iria para o RIP.</p>
<div class="dois"><form id="f">
  <label>Produto <select name="produto" id="produto"></select></label>
  <div class="linha oculto" id="medidas"><label>Largura (cm) <input name="largura" type="number" step="0.1" value="70"></label>
    <label>Altura (cm) <input name="altura" type="number" step="0.1" value="200"></label></div>
  <label>Moldura da frente <small>(opcional — a imagem enviada vira a foto dentro da moldura)</small></label>
  <div class="molduras" id="molduras"></div>
  <label>Frente <small id="dica">arte pronta ou foto</small><input name="frente" type="file" accept="image/*" multiple required></label>
  <label id="lverso">Verso <small>(opcional)</small><input name="verso" type="file" accept="image/*"></label>
  <div class="linha"><label>Quantidade <input name="quantidade" type="number" min="1" max="10" value="1"></label>
    <label>Transferência <select name="transferencia"><option value="">automática</option><option value="prensa">prensa</option><option value="calandra">calandra (rolo a rolo)</option></select></label></div>
  <details><summary>Ajuste manual da foto na moldura</summary>
    <div class="linha"><label>Zoom <input name="zoom" type="number" step="0.1" min="1" value="1"></label>
    <label>Mover ← → <input name="desloc_x" type="number" step="0.1" min="-1" max="1" value="0"></label>
    <label>Mover ↑ ↓ <input name="desloc_y" type="number" step="0.1" min="-1" max="1" value="0"></label></div>
    <label style="display:flex;gap:6px;align-items:center;font-weight:400"><input type="checkbox" name="sem_rosto" value="1"> não enquadrar pelo rosto</label>
  </details>
  <button id="enviar">Gerar arquivo de produção</button>
</form><section class="resultado" id="res"><p class="sub">O resultado aparece aqui.</p></section></div></main>
<script>
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const enc=p=>p.split("/").map(encodeURIComponent).join("/");
let cat;
(async()=>{
  cat=await (await fetch("/api/catalogo")).json();
  const sel=document.getElementById("produto");
  sel.innerHTML=cat.produtos.map(p=>`<option value="${esc(p.codigo)}">${esc(p.nome)}${p.sob_medida?" (sob medida)":` — ${p.largura_cm}x${p.altura_cm}`}</option>`).join("");
  document.getElementById("molduras").innerHTML=`<label><input type="radio" name="moldura_frente" value="" checked><img alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E">sem moldura</label>`+
    cat.molduras.map(m=>`<label><input type="radio" name="moldura_frente" value="${esc(m.codigo)}"><img src="/mini/${enc(m.arquivo)}" alt="">${esc(m.codigo)}<small>${m.espacos} foto(s)</small></label>`).join("");
  sel.onchange=atualizar; document.getElementById("molduras").onchange=atualizar; atualizar();
})();
function atualizar(){
  const p=cat.produtos.find(x=>x.codigo===document.getElementById("produto").value);
  document.getElementById("medidas").classList.toggle("oculto",!p.sob_medida);
  document.getElementById("lverso").classList.toggle("oculto",p.lados<2);
  const m=cat.molduras.find(x=>x.codigo===(document.querySelector("[name=moldura_frente]:checked")||{}).value);
  document.getElementById("dica").textContent=m?`${m.espacos} foto(s) — selecione ${m.espacos>1?"todas de uma vez, na ordem esquerda → direita":"a foto"}`:"arte pronta ou foto";
}
document.getElementById("f").onsubmit=async e=>{
  e.preventDefault(); const b=document.getElementById("enviar"), res=document.getElementById("res");
  b.disabled=true; b.textContent="Gerando…"; res.innerHTML='<p class="sub">Processando a imagem…</p>';
  try{
    const r=await fetch("/api/testar",{method:"POST",body:new FormData(e.target)}); const d=await r.json();
    if(!r.ok||d.erro&&!d.arquivos?.length){res.innerHTML=`<div class="msg erro">✖ ${esc(d.erro)}</div>`;return;}
    res.innerHTML=`<h2 style="font-size:17px;margin:0 0 4px">${esc(d.produto)}</h2>
      <p class="sub">Estampa ${esc(d.estampa_cm)} cm → peça ${esc(d.peca_cm)} cm · <span class="tag ${esc(d.equipamento)}">${esc(d.equipamento).toUpperCase()}</span> · ${d.arquivos.length} arquivo(s)</p>
      ${d.avisos.map(a=>`<div class="msg aviso">⚠ ${esc(a)}</div>`).join("")}${d.erro?`<div class="msg erro">✖ ${esc(d.erro)}</div>`:""}
      ${!d.avisos.length&&!d.erro?'<div class="msg ok">✔ pronto para o RIP</div>':""}
      ${d.arquivos.map(a=>`<p><a href="/arquivo/${enc(a)}" target="_blank">${esc(a.split("/").pop())}</a><br><a href="/arquivo/${enc(a)}" target="_blank"><img src="/mini/${enc(a)}" alt=""></a></p>`).join("")}`;
  }catch(err){res.innerHTML=`<div class="msg erro">✖ ${esc(err)}</div>`;}
  finally{b.disabled=false;b.textContent="Gerar arquivo de produção";}
};
</script></body></html>"""
