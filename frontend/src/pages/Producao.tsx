import { useState } from "react";
import { FILAS, ORDENS, type OS } from "../data/mock";
import { Equip } from "../components/ui";

const COLUNAS: OS["status"][] = ["aberta", "em produção", "concluída"];
const PROXIMO: Partial<Record<OS["status"], OS["status"]>> = { aberta: "em produção", "em produção": "concluída" };

export function Producao({ avisar }: { avisar: (t: string) => void }) {
  const [ordens, setOrdens] = useState(ORDENS);
  const mover = (o: OS) => {
    const prox = PROXIMO[o.status];
    if (!prox) return;
    setOrdens(os => os.map(x => (x.numero === o.numero ? { ...x, status: prox } : x)));
    avisar(`${o.numero} → ${prox}`);
  };
  return (
    <>
      <div className="grade-3">
        {FILAS.map(f => (
          <section key={f.setup} className="painel" style={{ display: "grid", gap: 8 }}>
            <div className="linha"><h3>{f.setup}</h3><span className="espaco" /><Equip e={f.equipamento} /></div>
            <div className="kpis" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
              <div className="kpi"><b>{f.aguardando}</b><span>na fila</span></div>
              <div className="kpi"><b>{f.impressos}</b><span>impressos hoje</span></div>
              <div className="kpi"><b>{f.metros.toLocaleString("pt-BR")}</b><span>m no lote</span></div>
            </div>
            <div className="barra-trilho"><span style={{ width: `${(f.usado / f.papel) * 100}%`, background: f.equipamento === "prensa" ? "var(--prensa)" : "var(--calandra)" }} /></div>
            <span className="fraco num">Rolo de {f.papel} m: {f.papel - f.usado} m restantes · encaixe automático a cada 20 trabalhos</span>
          </section>
        ))}
      </div>
      <section>
        <div className="linha" style={{ marginBottom: 10 }}><h2>Ordens de serviço</h2><span className="fraco">clientes locais com arte pronta</span></div>
        <div className="kanban">
          {COLUNAS.map(c => (
            <div key={c} className="coluna">
              <h3><span>{c}</span><span className="num">{ordens.filter(o => o.status === c).length}</span></h3>
              {ordens.filter(o => o.status === c).map(o => (
                <article key={o.numero} className="cartao">
                  <div className="linha"><b className="mono" style={{ fontSize: 14 }}>{o.numero}</b><span className="espaco" /><span className="num" style={{ fontWeight: 600 }}>Entrega {o.entrega}</span></div>
                  <span className="sub">{o.cliente}</span>
                  {o.obs && <span className="fraco">Obs.: {o.obs}</span>}
                  <ul>{o.itens.map((i, n) => <li key={n}>{i.qtd}x {i.produto}{i.fv ? " (frente e verso)" : ""} <Equip e={i.equipamento} /></li>)}</ul>
                  <div className="linha"><button className="btn peq">Ficha (PDF)</button><span className="espaco" />
                    {PROXIMO[o.status] && <button className="btn peq" onClick={() => mover(o)}>→ {PROXIMO[o.status]}</button>}</div>
                </article>
              ))}
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
