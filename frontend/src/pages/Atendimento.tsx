import { useState } from "react";
import { CONVERSAS, PEDIDOS } from "../data/mock";
import { Miniatura } from "../components/Miniatura";
import { CanalTag, Chip, StatusChip } from "../components/ui";

export function Atendimento({ avisar }: { avisar: (t: string) => void }) {
  const [ativa, setAtiva] = useState(CONVERSAS[0].id);
  const [vinculadas, setVinculadas] = useState<Set<string>>(new Set());
  const c = CONVERSAS.find(x => x.id === ativa)!;
  const pedidos = PEDIDOS.filter(p => p.cliente === c.cliente || p.id === c.pedido).slice(0, 3);
  const doPedido = c.pedido ? (PEDIDOS.find(p => p.id === c.pedido) ?? { ...PEDIDOS[c.id], id: c.pedido }) : undefined;
  const lista = doPedido && !pedidos.some(p => p.id === doPedido.id) ? [doPedido, ...pedidos] : pedidos;
  return (
    <div className="inbox">
      <div className="conversas">
        {CONVERSAS.map(x => (
          <div key={x.id} className={`conversa ${x.id === ativa ? "ativa" : ""}`} onClick={() => setAtiva(x.id)} role="button" tabIndex={0}
               onKeyDown={e => e.key === "Enter" && setAtiva(x.id)}>
            <div className="linha"><b>{x.cliente}</b><span className="espaco" /><span className="fraco">{x.hora}</span></div>
            <div className="linha"><CanalTag canal={x.canal} />{x.naoLidas > 0 && <Chip tom="acc" ponto={false}>{x.naoLidas}</Chip>}</div>
            <p>{x.mensagens[x.mensagens.length - 1].texto ?? "📷 imagem"}</p>
          </div>
        ))}
      </div>
      <div className="mensagens">
        {c.mensagens.map((m, i) => (
          <div key={i} className={`msg ${m.de}`}>
            {m.texto}
            {m.imagem && <div className="anexo">
              <Miniatura tipo={m.imagem.tipo} semente={m.imagem.semente} largura={180} rotulo={m.imagem.nome} />
              <span className="fraco mono">{m.imagem.nome}</span>
              {vinculadas.has(`${c.id}-${i}`) ? <Chip tom="ok">Vinculada ao pedido {c.pedido}</Chip> :
                <button className="btn peq primario" disabled={!c.pedido} onClick={() => {
                  setVinculadas(v => new Set(v).add(`${c.id}-${i}`));
                  avisar(`Imagem usada como arte do pedido ${c.pedido}: foi para a aprovação`);
                }}>{c.pedido ? `Usar como arte de ${c.pedido}` : "Sem pedido vinculado"}</button>}
            </div>}
          </div>
        ))}
        <div className="linha" style={{ marginTop: "auto" }}>
          <input className="busca" id="resposta" placeholder="Responder (via Chatwoot)" />
          <button className="btn" onClick={() => avisar("Mensagem enviada")}>Enviar</button>
        </div>
      </div>
      <aside className="lado-cliente">
        <h3>{c.cliente}</h3>
        <CanalTag canal={c.canal} />
        <span className="fraco">Painel do sistema aberto dentro do Chatwoot (Dashboard App): pedidos deste cliente.</span>
        {lista.length ? lista.map(p => (
          <div key={p.id} className="cartao">
            <div className="linha"><b className="mono">{p.id}</b><span className="espaco" /><StatusChip status={p.status} /></div>
            <span className="fraco">{p.itens.map(i => `${i.quantidade}x ${i.produto}`).join(" + ")}</span>
          </div>
        )) : <span className="fraco">Nenhum pedido encontrado para este contato.</span>}
        <button className="btn peq">Enviar link de envio de arte</button>
      </aside>
    </div>
  );
}
