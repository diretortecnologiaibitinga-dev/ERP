import { useState } from "react";
import { ARTES, AVISOS, type ArteParaAprovar } from "../data/mock";
import { Miniatura, coracao } from "../components/Miniatura";
import { CanalTag, Chip } from "../components/ui";

type Filtro = "todas" | "avisos" | "prontas";

export function Aprovacao({ avisar }: { avisar: (t: string) => void }) {
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [aprovadas, setAprovadas] = useState<Set<number>>(new Set());
  const [editando, setEditando] = useState<ArteParaAprovar | null>(null);
  const lista = ARTES.filter(a => filtro === "todas" || (filtro === "avisos" ? a.aviso : !a.aviso));
  const pendentes = lista.filter(a => !aprovadas.has(a.id));
  const alternar = (id: number) => setSel(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const aprovar = (ids: number[]) => {
    setAprovadas(a => new Set([...a, ...ids]));
    setSel(new Set());
    avisar(`${ids.length} arte(s) aprovada(s) — arquivos enviados para a pasta do Flexi`);
  };
  return (
    <>
      <div className="linha">
        <div className="segmentos" role="group" aria-label="Filtro">
          {([["todas", "Todas"], ["avisos", "Com aviso"], ["prontas", "Sem aviso"]] as const).map(([v, r]) =>
            <button key={v} className={filtro === v ? "ativo" : ""} onClick={() => setFiltro(v)}>{r}</button>)}
        </div>
        <span className="fraco num">{pendentes.length} para aprovar · {aprovadas.size} aprovadas</span>
        <span className="espaco" />
        <button className="btn" onClick={() => setSel(new Set(pendentes.filter(a => !a.aviso).map(a => a.id)))}>Selecionar as sem aviso</button>
        <button className="btn primario" disabled={!sel.size} onClick={() => aprovar([...sel])}>Aprovar {sel.size || ""} selecionada(s)</button>
      </div>
      <div className="grade-artes">
        {lista.map(a => {
          const aprovada = aprovadas.has(a.id);
          return (
            <div key={a.id} className={`arte ${sel.has(a.id) ? "sel" : ""} ${aprovada ? "aprovada" : ""}`} onClick={() => !aprovada && alternar(a.id)}>
              {!aprovada && <input type="checkbox" className="marcar" id={`arte-${a.id}`} aria-label={`Selecionar ${a.pedido}`}
                                   checked={sel.has(a.id)} onChange={() => alternar(a.id)} onClick={e => e.stopPropagation()} />}
              <Miniatura tipo={a.tipo} semente={a.id * 7 + 1} largura={168} rotulo={`${a.produto} ${a.pedido}`} />
              <div className="rodape"><span className="mono">{a.pedido}</span><CanalTag canal={a.canal} /></div>
              <div className="rodape"><span className="fraco">{a.produto}</span><span className="fraco num">{a.dpi} DPI</span></div>
              <div className="rodape">
                {aprovada ? <Chip tom="ok">Aprovada</Chip> : a.aviso ? <Chip tom="warn">{AVISOS[a.aviso]}</Chip> : <Chip tom="ok">Pronta</Chip>}
                {!aprovada && (a.tipo === "moldura" || a.tipo === "casal") &&
                  <button className="btn peq" onClick={e => { e.stopPropagation(); setEditando(a); }}>Ajustar</button>}
              </div>
            </div>
          );
        })}
      </div>
      {editando && <Enquadramento arte={editando} fechar={() => setEditando(null)}
                                  aprovar={() => { aprovar([editando.id]); setEditando(null); }} />}
    </>
  );
}

function Enquadramento({ arte, fechar, aprovar }: { arte: ArteParaAprovar; fechar: () => void; aprovar: () => void }) {
  const [zoom, setZoom] = useState(1);
  const [dx, setDx] = useState(0);
  const [dy, setDy] = useState(0);
  const auto = zoom === 1 && dx === 0 && dy === 0;
  // a "foto" do cliente: o rosto fica fora do centro; no automático ele vai para o centro do coração
  const rostoX = auto ? 50 : 50 + dx * 18, rostoY = auto ? 44 : 44 + dy * 14;
  const k = (arte.aviso === "sem_rosto" && auto ? 0.8 : 1) * zoom;
  return (
    <div className="modal-fundo" onClick={fechar}>
      <div className="modal" onClick={e => e.stopPropagation()} role="dialog" aria-label="Ajustar enquadramento">
        <div className="linha"><h2>Ajustar foto na moldura</h2><span className="mono sub">{arte.pedido}</span><span className="espaco" />
          <button className="btn peq" onClick={fechar}>Fechar</button></div>
        <div className="lado-a-lado">
          <svg viewBox="0 0 100 100" style={{ width: "100%", maxWidth: 420, background: "#fff", borderRadius: 10, border: "1px solid var(--line)" }}>
            <defs><clipPath id="furo"><polygon points={coracao(50, 42, 2.05)} /></clipPath></defs>
            <g clipPath="url(#furo)">
              <rect width="100" height="100" fill="#7fa6c9" />
              <rect y="60" width="100" height="40" fill="#5f8a63" />
              <g transform={`translate(${rostoX} ${rostoY}) scale(${k}) translate(${-rostoX} ${-rostoY})`}>
                <ellipse cx={rostoX} cy={rostoY + 34} rx="26" ry="20" fill="#2c3e64" />
                <ellipse cx={rostoX} cy={rostoY} rx="12" ry="15" fill="#f0c9a5" />
                <path d={`M${rostoX - 12.5},${rostoY - 3} Q${rostoX},${rostoY - 26} ${rostoX + 12.5},${rostoY - 3} Q${rostoX + 8},${rostoY - 13} ${rostoX},${rostoY - 13} Q${rostoX - 8},${rostoY - 13} ${rostoX - 12.5},${rostoY - 3}`} fill="#5a3a22" />
              </g>
            </g>
            <polygon points={coracao(50, 42, 2.05)} fill="none" stroke="#c8102e" strokeWidth="4.5" />
            <polygon points={coracao(50, 42, 2.25)} fill="none" stroke="#e9cf9a" strokeWidth="1" />
            <text x="50" y="91" textAnchor="middle" fontSize="11" fontWeight="800" fill="#c8102e" fontFamily="Archivo, sans-serif">Te Amo</text>
          </svg>
          <div style={{ display: "grid", gap: 12 }}>
            {auto ? <Chip tom={arte.aviso === "sem_rosto" ? "warn" : "ok"}>{arte.aviso === "sem_rosto" ? "Rosto não encontrado: foto centralizada" : "Rosto encontrado: enquadrado automaticamente"}</Chip>
              : <Chip tom="acc">Ajuste manual</Chip>}
            <label className="campo">Aproximar ({zoom.toFixed(1)}x)<input type="range" id="zoom" min="1" max="2" step="0.1" value={zoom} onChange={e => setZoom(+e.target.value)} /></label>
            <label className="campo">Mover para os lados<input type="range" id="desloc-x" min="-1" max="1" step="0.1" value={dx} onChange={e => setDx(+e.target.value)} /></label>
            <label className="campo">Mover para cima/baixo<input type="range" id="desloc-y" min="-1" max="1" step="0.1" value={dy} onChange={e => setDy(+e.target.value)} /></label>
            <p className="fraco" style={{ margin: 0 }}>A borda interna da moldura fica sempre por cima da foto. Mexer em qualquer controle desliga o enquadramento automático desta foto.</p>
            <div className="linha"><button className="btn" onClick={() => { setZoom(1); setDx(0); setDy(0); }}>Voltar ao automático</button>
              <span className="espaco" /><button className="btn primario" onClick={aprovar}>Aprovar e enviar</button></div>
          </div>
        </div>
      </div>
    </div>
  );
}
