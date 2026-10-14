import { useState } from "react";
import { MODELOS, MOLDURAS, PRODUTOS } from "../data/mock";
import { Miniatura } from "../components/Miniatura";
import { type ArteTime, BIBLIOTECA, Peca } from "../components/Molde";

const ARTE: ArteTime = { padrao: "liso", cor1: "#cfd8dc", cor2: "#cfd8dc", manga: "#b0bec5" };

export function Catalogo() {
  const [aba, setAba] = useState<"vestuario" | "produtos" | "molduras">("vestuario");
  return (
    <>
      <div className="abas" role="tablist">
        {([["vestuario", `Moldes de vestuário (${MODELOS.length})`], ["produtos", "Produtos"], ["molduras", "Fotomolduras"]] as const).map(([v, r]) =>
          <button key={v} role="tab" aria-selected={aba === v} className={aba === v ? "ativo" : ""} onClick={() => setAba(v)}>{r}</button>)}
      </div>
      {aba === "vestuario" && <>
        <div className="linha"><span className="fraco">Importados dos PDFs do Corel (layout SpeedCorel). Os mesmos moldes servem para esportivo, empresa, evento e venda.</span>
          <span className="espaco" /><button className="btn">Importar PDF de moldes</button></div>
        <div className="grade-3">
          {MODELOS.map(m => {
            const exemplo = BIBLIOTECA["M"].partes[m.familia === "Regata" ? "costas" : "frente_careca"];
            return (
              <section key={m.codigo} className="painel" style={{ display: "grid", gridTemplateColumns: "84px minmax(0,1fr)", gap: 12 }}>
                <Peca parte={exemplo} nomeParte={m.familia === "Regata" ? "costas" : "frente_careca"} arte={ARTE} pxPorCm={1.3} />
                <div style={{ display: "grid", gap: 6, alignContent: "start", minWidth: 0 }}>
                  <div className="linha"><h3>{m.nome}</h3><span className="mono fraco">{m.codigo}</span></div>
                  <span className="fraco">{m.grade} · {m.partes.join(", ")}</span>
                  <div className="tamanhos">{m.tamanhos.map(t => <span key={t} className="tam">{t}</span>)}</div>
                  <span className="fraco mono" style={{ overflowWrap: "anywhere" }}>{m.origem}</span>
                </div>
              </section>
            );
          })}
        </div>
      </>}
      {aba === "produtos" && <div className="tabela-wrap"><table>
        <thead><tr><th>Código</th><th>Produto</th><th>Estampa</th><th>Peça impressa</th><th>Margem</th><th>Lados</th><th>Transferência</th></tr></thead>
        <tbody>{PRODUTOS.map(p => <tr key={p.codigo}><td className="mono">{p.codigo}</td><td>{p.nome}</td><td>{p.estampa}</td><td>{p.peca}</td><td>{p.margem}</td><td>{p.lados}</td><td>{p.transferencia}</td></tr>)}</tbody>
      </table></div>}
      {aba === "molduras" && <div className="grade-artes">
        {MOLDURAS.map((m, i) => <div key={m.codigo} className="arte" style={{ cursor: "default" }}>
          <Miniatura tipo={m.espacos > 1 ? "casal" : "moldura"} semente={i + 3} largura={168} />
          <b>{m.nome}</b><span className="fraco">{m.espacos} espaço(s) para foto · <span className="mono">{m.codigo}</span></span>
        </div>)}
      </div>}
    </>
  );
}
