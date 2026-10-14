import { CANAIS, DIA, FILAS, PEDIDOS, STATUS } from "../data/mock";
import { AvisoChip, CanalTag, Equip, Kpi, fmt } from "../components/ui";

export function Painel({ ir }: { ir: (tela: string) => void }) {
  const totalStatus = DIA.porStatus.reduce((s, [, n]) => s + n, 0);
  const maxCanal = Math.max(...DIA.porCanal.map(([, n]) => n));
  const maxProd = Math.max(...DIA.porProduto.map(([, n]) => n));
  const alertas = PEDIDOS.filter(p => p.itens.some(i => i.aviso)).slice(0, 6);
  return (
    <>
      <div className="kpis">
        <Kpi valor={fmt(DIA.pedidos)} rotulo="pedidos hoje" />
        <Kpi valor={fmt(DIA.pecas)} rotulo="peças para imprimir" />
        <Kpi valor={DIA.aguardandoArte} rotulo="aguardando arte do cliente" tom="alerta" />
        <Kpi valor={DIA.paraAprovar} rotulo="artes para aprovar" tom="alerta" />
        <Kpi valor={fmt(DIA.noRip)} rotulo="peças enviadas ao Flexi" />
        <Kpi valor={DIA.atrasados} rotulo="pedidos atrasados" tom="erro" />
      </div>

      <section className="painel">
        <header><h2>Onde estão os pedidos de hoje</h2><span className="fraco num">{fmt(totalStatus)} pedidos</span></header>
        <div className="fluxo" aria-label="Pedidos por etapa">
          {DIA.porStatus.map(([s, n]) => (
            <div key={s} style={{ width: `${(n / totalStatus) * 100}%`, background: STATUS[s].cor }} title={`${STATUS[s].rotulo}: ${n}`}>
              {n / totalStatus > 0.07 ? n : ""}
            </div>
          ))}
        </div>
        <div className="legenda">
          {DIA.porStatus.map(([s, n]) => <span key={s}><i style={{ background: STATUS[s].cor }} />{STATUS[s].rotulo} <b className="num">{n}</b></span>)}
        </div>
      </section>

      <div className="grade-2">
        <section className="painel">
          <header><h2>Pedidos por canal</h2></header>
          <div className="barras">
            {DIA.porCanal.map(([c, n]) => (
              <div className="barra" key={c}>
                <CanalTag canal={c} />
                <div className="barra-trilho"><span style={{ width: `${(n / maxCanal) * 100}%`, background: CANAIS[c] }} /></div>
                <span className="num">{fmt(n)}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="painel">
          <header><h2>Peças por produto</h2>
            <span className="legenda" style={{ margin: 0 }}><span><i style={{ background: "var(--prensa)" }} />prensa</span><span><i style={{ background: "var(--calandra)" }} />calandra</span></span>
          </header>
          <div className="barras">
            {DIA.porProduto.map(([nome, n, cal]) => (
              <div className="barra" key={nome}>
                <span>{nome}</span>
                <div className="barra-trilho">
                  <span style={{ width: `${((n - cal) / maxProd) * 100}%`, background: "var(--prensa)" }} />
                  <span style={{ width: `${(cal / maxProd) * 100}%`, background: "var(--calandra)" }} />
                </div>
                <span className="num">{fmt(n)}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grade-2">
        <section className="painel">
          <header><h2>Precisa de atenção</h2><button className="btn peq" onClick={() => ir("aprovacao")}>Abrir aprovação</button></header>
          <div className="tabela-wrap">
            <table><tbody>
              {alertas.map(p => (
                <tr key={p.id}>
                  <td className="mono">{p.id}</td>
                  <td><CanalTag canal={p.canal} /></td>
                  <td>{p.itens[0].produto}</td>
                  <td><AvisoChip aviso={p.itens.find(i => i.aviso)?.aviso} /></td>
                </tr>
              ))}
            </tbody></table>
          </div>
        </section>
        <section className="painel">
          <header><h2>Filas no Flexi</h2><button className="btn peq" onClick={() => ir("producao")}>Ver produção</button></header>
          <div className="barras">
            {FILAS.map(f => (
              <div key={f.setup} style={{ display: "grid", gap: 4 }}>
                <div className="linha"><b>{f.setup}</b><Equip e={f.equipamento} /><span className="espaco" />
                  <span className="fraco num">{f.aguardando} aguardando · {f.impressos} impressos</span></div>
                <div className="barra-trilho" title={`${f.usado} de ${f.papel} m de papel`}>
                  <span style={{ width: `${(f.usado / f.papel) * 100}%`, background: f.equipamento === "prensa" ? "var(--prensa)" : "var(--calandra)" }} />
                </div>
                <span className="fraco num">Rolo: {f.papel - f.usado} m restantes de {f.papel} m · lote atual {f.metros.toLocaleString("pt-BR")} m</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
