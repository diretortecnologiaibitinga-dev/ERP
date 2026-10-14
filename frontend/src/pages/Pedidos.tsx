import { useMemo, useState } from "react";
import { type Canal, PEDIDOS, type Pedido, STATUS, type StatusPedido } from "../data/mock";
import { Miniatura } from "../components/Miniatura";
import { AvisoChip, CanalTag, Equip, StatusChip } from "../components/ui";

const ETAPAS: StatusPedido[] = ["aguardando_arte", "tratamento", "aprovacao", "no_rip", "producao", "expedido"];

export function Pedidos() {
  const [canal, setCanal] = useState<Canal | "todos">("todos");
  const [status, setStatus] = useState<StatusPedido | "todos">("todos");
  const [busca, setBusca] = useState("");
  const [aberto, setAberto] = useState<Pedido | null>(null);
  const lista = useMemo(() => PEDIDOS.filter(p =>
    (canal === "todos" || p.canal === canal) && (status === "todos" || p.status === status) &&
    (!busca || `${p.id} ${p.cliente}`.toLowerCase().includes(busca.toLowerCase()))), [canal, status, busca]);
  return (
    <>
      <div className="linha">
        <input className="busca" style={{ maxWidth: 260 }} id="busca-pedidos" placeholder="Buscar pedido ou cliente" value={busca} onChange={e => setBusca(e.target.value)} />
        <div className="segmentos" role="group" aria-label="Canal">
          {(["todos", "Shopee", "Mercado Livre", "TikTok", "WhatsApp"] as const).map(c =>
            <button key={c} className={canal === c ? "ativo" : ""} onClick={() => setCanal(c)}>{c === "todos" ? "Todos" : c}</button>)}
        </div>
        <select className="busca" style={{ maxWidth: 200 }} id="filtro-status" value={status} onChange={e => setStatus(e.target.value as StatusPedido | "todos")}>
          <option value="todos">Todas as etapas</option>
          {ETAPAS.map(s => <option key={s} value={s}>{STATUS[s].rotulo}</option>)}
        </select>
        <span className="espaco" /><span className="fraco num">{lista.length} pedidos</span>
      </div>
      <div className="tabela-wrap">
        <table>
          <thead><tr><th>Pedido</th><th>Canal</th><th>Cliente</th><th>Itens</th><th>Arte</th><th>Etapa</th><th>Prazo</th><th>Transferência</th></tr></thead>
          <tbody>
            {lista.map(p => (
              <tr key={p.id} className="clicavel" onClick={() => setAberto(p)}>
                <td className="mono">{p.id}</td>
                <td><CanalTag canal={p.canal} /></td>
                <td>{p.cliente}</td>
                <td>{p.itens.map(i => `${i.quantidade}x ${i.produto}${i.medida ? ` ${i.medida}` : ""}`).join(" + ")}</td>
                <td><AvisoChip aviso={p.itens.find(i => i.aviso)?.aviso} /></td>
                <td><StatusChip status={p.status} /></td>
                <td className={p.prazo === "Hoje" ? "num" : "num sub"} style={p.prazo === "Hoje" ? { color: "var(--err)", fontWeight: 700 } : undefined}>{p.prazo}</td>
                <td>{[...new Set(p.itens.map(i => i.equipamento))].map(e => <Equip key={e} e={e} />)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {aberto && <DetalhePedido pedido={aberto} fechar={() => setAberto(null)} />}
    </>
  );
}

function DetalhePedido({ pedido, fechar }: { pedido: Pedido; fechar: () => void }) {
  const idx = ETAPAS.indexOf(pedido.status);
  return (
    <div className="gaveta-fundo" onClick={fechar}>
      <aside className="gaveta" onClick={e => e.stopPropagation()} aria-label={`Pedido ${pedido.id}`}>
        <div className="linha"><h2 className="mono" style={{ fontSize: 17 }}>{pedido.id}</h2><StatusChip status={pedido.status} />
          <span className="espaco" /><button className="btn peq" onClick={fechar}>Fechar</button></div>
        <div className="linha sub"><CanalTag canal={pedido.canal} /> · {pedido.cliente} · criado {pedido.criado} · prazo {pedido.prazo}</div>
        {pedido.itens.map((i, n) => (
          <section key={n} className="painel" style={{ display: "grid", gridTemplateColumns: "120px minmax(0,1fr)", gap: 14 }}>
            <Miniatura tipo={i.tipo} semente={i.arte} faltando={i.aviso === "arte_faltando"} largura={120} />
            <div style={{ display: "grid", gap: 6, alignContent: "start" }}>
              <h3>{i.quantidade}x {i.produto}{i.medida ? ` ${i.medida}` : ""}</h3>
              <div className="linha"><Equip e={i.equipamento} />{i.frenteVerso && <span className="chip sem-ponto">frente e verso</span>}<AvisoChip aviso={i.aviso} /></div>
              <span className="fraco">
                {i.aviso === "arte_faltando" ? "Mensagem automática enviada ao cliente pedindo a arte." :
                  i.aviso === "baixa_resolucao" ? "A imagem tem 64 DPI no tamanho final (alvo 150). Pedir original ao cliente ou aprovar assim." :
                  i.aviso === "sem_rosto" ? "Nenhum rosto encontrado na foto: centralizada. Conferir o enquadramento." :
                  `${i.quantidade * (i.frenteVerso ? 2 : 1)} arquivo(s) · peça com margem de costura e código do pedido.`}
              </span>
              <div className="linha"><button className="btn peq">Ver arquivo</button><button className="btn peq">Trocar arte</button></div>
            </div>
          </section>
        ))}
        <section>
          <h3 style={{ marginBottom: 10 }}>Andamento</h3>
          <div className="linha-tempo">
            {ETAPAS.map((s, n) => <div key={s} className={n > idx ? "pend" : ""}>{STATUS[s].rotulo}
              {n <= idx && <span className="fraco"> · 14/10 {String(9 + n).padStart(2, "0")}:{String((n * 13) % 60).padStart(2, "0")}</span>}</div>)}
          </div>
        </section>
      </aside>
    </div>
  );
}
