import { useMemo, useState } from "react";
import { JOGADORES, MODELOS, type Pessoa } from "../data/mock";
import { type ArteTime, BIBLIOTECA, type Caixa, type Grade, type Logo, Peca, type Texto, grade, tamanhoExemplo } from "../components/Molde";
import { Chip, Equip, fmt } from "../components/ui";

type Finalidade = "esportivo" | "empresa" | "evento" | "venda";

const FINALIDADES: Record<Finalidade, { nome: string; desc: string; colunas: ("nome" | "numero")[]; rotuloNome: string }> = {
  esportivo: { nome: "Esportivo", desc: "Nome e número por jogador, escudo e patrocínios", colunas: ["nome", "numero"], rotuloNome: "Nome nas costas" },
  empresa: { nome: "Uniforme de empresa", desc: "Logo no peito, marca nas costas, nome do funcionário opcional", colunas: ["nome"], rotuloNome: "Nome no peito" },
  evento: { nome: "Evento, família, formatura", desc: "Mesma arte para todos, nome nas costas opcional", colunas: ["nome"], rotuloNome: "Nome nas costas" },
  venda: { nome: "Estampa total (venda)", desc: "Arte única para loja e marketplace: só tamanhos e quantidades", colunas: [], rotuloNome: "" },
};

interface PedidoUniforme {
  id: string; cliente: string; finalidade: Finalidade; modelo: string; gola: "careca" | "v"; manga: "curta" | "longa";
  arte: ArteTime; marca: string; numeroFrente: boolean; pessoas: Pessoa[];
}

const INICIAIS: PedidoUniforme[] = [
  { id: "OS-000216", cliente: "Esporte Clube União", finalidade: "esportivo", modelo: "esportivo", gola: "careca", manga: "curta",
    arte: { padrao: "listras", cor1: "#0d3d8c", cor2: "#1a73d6", manga: "#f2c230" }, marca: "MERCADO BOM", numeroFrente: true, pessoas: JOGADORES },
  { id: "OS-000217", cliente: "Clínica Bem Viver", finalidade: "empresa", modelo: "polo-mulher", gola: "careca", manga: "curta",
    arte: { padrao: "liso", cor1: "#0b6f78", cor2: "#0b6f78", manga: "#0b6f78" }, marca: "BEM VIVER", numeroFrente: false, pessoas: [
      { nome: "Dra. Ana", numero: "", tamanho: "BLM", qtd: 2 }, { nome: "Paula", numero: "", tamanho: "BLG", qtd: 2 },
      { nome: "Rita", numero: "", tamanho: "BLP", qtd: 3 }, { nome: "Dr. João", numero: "", tamanho: "G", qtd: 2 }] },
  { id: "OS-000218", cliente: "Família Silva", finalidade: "evento", modelo: "casual", gola: "careca", manga: "curta",
    arte: { padrao: "degrade", cor1: "#f6b13d", cor2: "#c2185b", manga: "#c2185b" }, marca: "FAMÍLIA SILVA 2026", numeroFrente: false, pessoas: [
      { nome: "Vovó Lia", numero: "", tamanho: "G", qtd: 1 }, { nome: "Pedro", numero: "", tamanho: "M", qtd: 1 },
      { nome: "Bia", numero: "", tamanho: "BLP", qtd: 1 }, { nome: "Theo", numero: "", tamanho: "6", qtd: 1 }, { nome: "Malu", numero: "", tamanho: "4", qtd: 1 }] },
  { id: "LOJA-TIEDYE", cliente: "Coleção Tie-dye (marketplace)", finalidade: "venda", modelo: "casual", gola: "v", manga: "curta",
    arte: { padrao: "faixas", cor1: "#9b7be0", cor2: "#36b3c1", manga: "#9b7be0" }, marca: "", numeroFrente: false, pessoas: [
      { nome: "", numero: "", tamanho: "P", qtd: 6 }, { nome: "", numero: "", tamanho: "M", qtd: 10 }, { nome: "", numero: "", tamanho: "G", qtd: 10 },
      { nome: "", numero: "", tamanho: "GG", qtd: 4 }, { nome: "", numero: "", tamanho: "BLM", qtd: 6 }] },
];

const ALTURAS: Record<string, Record<Grade, number>> = {
  numero: { infantil: 15, feminino: 18, adulto: 22 }, nome: { infantil: 3.5, feminino: 4, adulto: 5 },
  numeroFrente: { infantil: 6, feminino: 7, adulto: 9 },
};
const PATROCINIO: Record<Grade, number> = { infantil: 16, feminino: 20, adulto: 24 };

export function Uniformes({ avisar }: { avisar: (t: string) => void }) {
  const [pedidos, setPedidos] = useState(INICIAIS);
  const [atual, setAtual] = useState(0);
  const [pessoaSel, setPessoaSel] = useState(0);
  const [colando, setColando] = useState(false);
  const [texto, setTexto] = useState("");
  const ped = pedidos[atual];
  const fin = FINALIDADES[ped.finalidade];
  const modelo = MODELOS.find(m => m.codigo === ped.modelo)!;
  const alterar = (m: Partial<PedidoUniforme>) => setPedidos(ps => ps.map((p, i) => (i === atual ? { ...p, ...m } : p)));
  const alterarPessoa = (n: number, m: Partial<Pessoa>) => alterar({ pessoas: ped.pessoas.map((p, i) => (i === n ? { ...p, ...m } : p)) });

  const semMangas = modelo.familia === "Regata";
  const nomesPartes = [`frente_${ped.gola}`, "costas", ...(semMangas ? [] : [`manga_${ped.manga}_esq`, `manga_${ped.manga}_dir`])];
  const resumo = useMemo(() => {
    const porTam = new Map<string, number>();
    let area = 0;
    for (const p of ped.pessoas) {
      porTam.set(p.tamanho, (porTam.get(p.tamanho) ?? 0) + p.qtd);
      const t = BIBLIOTECA[tamanhoExemplo(p.tamanho)];
      area += p.qtd * nomesPartes.reduce((s, n) => s + (t.partes[n] ? t.partes[n].w * t.partes[n].h : 0), 0);
    }
    const unidades = ped.pessoas.reduce((s, p) => s + p.qtd, 0);
    return { porTam, unidades, pecas: unidades * nomesPartes.length, metros: area / (180 * 0.82) / 100 };
  }, [ped, nomesPartes.join()]);

  const pessoa = ped.pessoas[Math.min(pessoaSel, ped.pessoas.length - 1)];
  const colar = () => {
    const linhas = texto.split(/\r?\n/).map(l => l.split(/[;\t,]/).map(c => c.trim())).filter(c => c.some(Boolean));
    const novas = linhas.filter(c => !/^nome/i.test(c[0])).map(c => ped.finalidade === "esportivo"
      ? { nome: c[0] ?? "", numero: c[1] ?? "", tamanho: (c[2] || "M").toUpperCase(), qtd: +(c[3] || 1) }
      : fin.colunas.length ? { nome: c[0] ?? "", numero: "", tamanho: (c[1] || "M").toUpperCase(), qtd: +(c[2] || 1) }
        : { nome: "", numero: "", tamanho: (c[0] || "M").toUpperCase(), qtd: +(c[1] || 1) });
    if (novas.length) { alterar({ pessoas: [...ped.pessoas, ...novas] }); avisar(`${novas.length} linha(s) adicionada(s) da planilha`); }
    setColando(false); setTexto("");
  };

  return (
    <>
      <div className="abas" role="tablist">
        {pedidos.map((p, i) => <button key={p.id} role="tab" aria-selected={i === atual} className={i === atual ? "ativo" : ""}
                                       onClick={() => { setAtual(i); setPessoaSel(0); }}>{p.cliente}</button>)}
      </div>

      <div className="grade-2" style={{ alignItems: "start" }}>
        <section className="painel" style={{ display: "grid", gap: 14 }}>
          <header style={{ margin: 0 }}><h2>Configuração</h2><span className="mono sub">{ped.id}</span></header>
          <div className="finalidades">
            {(Object.keys(FINALIDADES) as Finalidade[]).map(f => (
              <button key={f} className={`finalidade ${ped.finalidade === f ? "ativa" : ""}`} onClick={() => alterar({ finalidade: f })}>
                <b>{FINALIDADES[f].nome}</b><span>{FINALIDADES[f].desc}</span>
              </button>
            ))}
          </div>
          <div className="campos">
            <label className="campo">Modelo
              <select id="modelo" value={ped.modelo} onChange={e => alterar({ modelo: e.target.value })}>
                {MODELOS.filter(m => m.familia !== "Short" && m.familia !== "Basquete").map(m => <option key={m.codigo} value={m.codigo}>{m.nome}</option>)}
              </select></label>
            <label className="campo">Gola
              <select id="gola" value={ped.gola} onChange={e => alterar({ gola: e.target.value as "careca" | "v" })}>
                <option value="careca">Careca</option><option value="v">V</option></select></label>
            <label className="campo">Manga
              <select id="manga" value={ped.manga} disabled={semMangas} onChange={e => alterar({ manga: e.target.value as "curta" | "longa" })}>
                <option value="curta">Curta</option><option value="longa">Longa</option></select></label>
          </div>
          <div className="campos">
            <label className="campo">Arte
              <select id="padrao" value={ped.arte.padrao} onChange={e => alterar({ arte: { ...ped.arte, padrao: e.target.value as ArteTime["padrao"] } })}>
                <option value="listras">Listras diagonais</option><option value="faixas">Faixas</option><option value="degrade">Degradê</option><option value="liso">Liso</option>
              </select></label>
            <label className="campo">Cor 1<input type="color" id="cor1" value={ped.arte.cor1} onChange={e => alterar({ arte: { ...ped.arte, cor1: e.target.value } })} /></label>
            <label className="campo">Cor 2<input type="color" id="cor2" value={ped.arte.cor2} onChange={e => alterar({ arte: { ...ped.arte, cor2: e.target.value } })} /></label>
            <label className="campo">Mangas<input type="color" id="cor-manga" value={ped.arte.manga} onChange={e => alterar({ arte: { ...ped.arte, manga: e.target.value } })} /></label>
            {ped.finalidade !== "venda" && <label className="campo">{ped.finalidade === "esportivo" ? "Patrocínio" : ped.finalidade === "empresa" ? "Marca da empresa" : "Texto nas costas"}
              <input id="marca" value={ped.marca} onChange={e => alterar({ marca: e.target.value })} /></label>}
            {ped.finalidade === "esportivo" && <label className="caixa-marcar">
              <input type="checkbox" id="numero-frente" checked={ped.numeroFrente} onChange={e => alterar({ numeroFrente: e.target.checked })} />
              Número na frente</label>}
          </div>
          <p className="fraco" style={{ margin: 0 }}>{modelo.nome}: {modelo.tamanhos.length} tamanhos ({modelo.grade}) · partes: {modelo.partes.join(", ")} · moldes de {modelo.origem}</p>
        </section>

        <section className="painel" style={{ display: "grid", gap: 12 }}>
          <header style={{ margin: 0 }}><h2>{ped.finalidade === "esportivo" ? "Jogadores" : ped.finalidade === "venda" ? "Grade da produção" : "Pessoas"}</h2>
            <div className="linha"><button className="btn peq" onClick={() => setColando(c => !c)}>Colar da planilha</button>
              <button className="btn peq" onClick={() => alterar({ pessoas: [...ped.pessoas, { nome: "", numero: "", tamanho: "M", qtd: 1 }] })}>Adicionar linha</button></div></header>
          {colando && <div style={{ display: "grid", gap: 8 }}>
            <label className="campo">Cole as linhas do Excel ({[...fin.colunas.map(c => (c === "nome" ? "Nome" : "Número")), "Tamanho", "Qtd"].join(" ; ")})
              <textarea id="colar" rows={4} value={texto} onChange={e => setTexto(e.target.value)} placeholder={ped.finalidade === "esportivo" ? "Lucas;10;M\nRafael;08;XGG" : "M;10\nG;8"} /></label>
            <div className="linha"><button className="btn primario peq" onClick={colar}>Adicionar</button></div></div>}
          <div className="tabela-wrap" style={{ maxHeight: 300, overflowY: "auto" }}>
            <table>
              <thead><tr>{fin.colunas.includes("nome") && <th>{fin.rotuloNome}</th>}{fin.colunas.includes("numero") && <th>Número</th>}<th>Tamanho</th><th>Qtd</th></tr></thead>
              <tbody>
                {ped.pessoas.map((p, n) => (
                  <tr key={n} className={`clicavel ${n === pessoaSel ? "selecionado" : ""}`} onClick={() => setPessoaSel(n)}>
                    {fin.colunas.includes("nome") && <td><input id={`nome-${n}`} aria-label="Nome" value={p.nome} onChange={e => alterarPessoa(n, { nome: e.target.value })} /></td>}
                    {fin.colunas.includes("numero") && <td><input id={`num-${n}`} aria-label="Número" className="num" value={p.numero} onChange={e => alterarPessoa(n, { numero: e.target.value })} /></td>}
                    <td><select id={`tam-${n}`} aria-label="Tamanho" className="busca" style={{ padding: "3px 6px" }} value={p.tamanho} onChange={e => alterarPessoa(n, { tamanho: e.target.value })}>
                      {[...new Set([...modelo.tamanhos, p.tamanho])].map(t => <option key={t}>{t}</option>)}</select>
                      {!modelo.tamanhos.includes(p.tamanho) && <span title="Tamanho não existe neste modelo" style={{ color: "var(--err)", marginLeft: 6 }}>●</span>}</td>
                    <td><input id={`qtd-${n}`} aria-label="Quantidade" className="num" type="number" min={1} value={p.qtd} style={{ width: 64 }} onChange={e => alterarPessoa(n, { qtd: Math.max(1, +e.target.value) })} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="tamanhos">{[...resumo.porTam].map(([t, n]) => <span key={t} className="tam">{t} <b>{n}</b></span>)}</div>
          <div className="linha"><span className="num"><b>{fmt(resumo.unidades)}</b> unidades · <b>{fmt(resumo.pecas)}</b> peças · ≈ <b>{resumo.metros.toFixed(1).replace(".", ",")} m</b> de rolo</span>
            <Equip e="calandra" /><span className="espaco" />
            <button className="btn primario" onClick={() => avisar(`${fmt(resumo.pecas)} peças de ${ped.cliente} enviadas para Impressora 2 · Rolo (calandra)`)}>Gerar arquivos para o RIP</button></div>
        </section>
      </div>

      <section className="painel">
        <header><h2>Prévia {pessoa && fin.colunas.length ? `— ${[pessoa.nome, pessoa.numero].filter(Boolean).join(" · ")}` : ""} {pessoa && <span className="sub">({pessoa.tamanho})</span>}</h2>
          <span className="fraco">Ilustração com moldes de exemplo, na escala real entre tamanhos</span></header>
        {pessoa && <Previa ped={ped} pessoa={pessoa} nomesPartes={nomesPartes} />}
        <div className="linha" style={{ marginTop: 10 }}>
          {pessoa && <Chip tom="acc">Número {ALTURAS.numero[grade(pessoa.tamanho)]} cm · nome {ALTURAS.nome[grade(pessoa.tamanho)]} cm (grade {grade(pessoa.tamanho)})</Chip>}
          <span className="fraco">Clique em outra linha da tabela para comparar tamanhos: a arte não estica, só mostra mais ou menos do desenho.</span>
        </div>
      </section>
    </>
  );
}

function Previa({ ped, pessoa, nomesPartes }: { ped: PedidoUniforme; pessoa: Pessoa; nomesPartes: string[] }) {
  const g = grade(pessoa.tamanho);
  const t = BIBLIOTECA[tamanhoExemplo(pessoa.tamanho)];
  const esportivo = ped.finalidade === "esportivo";
  return (
    <div className="pecas">
      {nomesPartes.map(n => {
        const parte = t.partes[n];
        if (!parte) return null;
        const frente = n.startsWith("frente"), costas = n === "costas", manga = n.startsWith("manga");
        const textos: Texto[] = [];
        const logos: Logo[] = [];
        const caixas: Caixa[] = [];
        if (esportivo) {
          if (frente) { logos.push({ slot: "1", tipo: "escudo", texto: "FC" }, { slot: "2", tipo: "patrocinio", texto: ped.marca });
            if (ped.numeroFrente) textos.push({ texto: pessoa.numero, cx: 0.5, cy: 0.45, alturaCm: ALTURAS.numeroFrente[g] }); }
          if (costas) {
            textos.push({ texto: pessoa.nome.toUpperCase(), cx: 0.5, cy: 0.2, alturaCm: ALTURAS.nome[g] },
                        { texto: pessoa.numero, cx: 0.5, cy: 0.44, alturaCm: ALTURAS.numero[g] });
            if (ped.marca) caixas.push({ cx: 0.5, cy: 0.09, w: PATROCINIO[g], h: PATROCINIO[g] * 0.25, texto: ped.marca });
            caixas.push({ cx: 0.5, cy: 0.8, w: PATROCINIO[g] * 1.05, h: PATROCINIO[g] * 0.22, texto: "AUTO PEÇAS", escura: true });
          }
          if (manga) logos.push({ slot: n.endsWith("esq") ? "3" : "4", tipo: "escudo", texto: "FC" });
        } else if (ped.finalidade === "empresa") {
          if (frente) { logos.push({ slot: "2", tipo: "empresa", texto: ped.marca });
            const m = parte.logos["1"];
            if (m && pessoa.nome) textos.push({ texto: pessoa.nome, cx: m[0] / parte.w, cy: m[1] / parte.h, alturaCm: 2.2, larguraMax: 0.3 }); }
          if (costas && ped.marca) caixas.push({ cx: 0.5, cy: 0.27, w: PATROCINIO[g] * 1.1, h: PATROCINIO[g] * 0.4, texto: ped.marca });
        } else if (ped.finalidade === "evento") {
          if (costas) { if (pessoa.nome) textos.push({ texto: pessoa.nome.toUpperCase(), cx: 0.5, cy: 0.17, alturaCm: ALTURAS.nome[g] });
            if (ped.marca) caixas.push({ cx: 0.5, cy: 0.38, w: PATROCINIO[g] * 1.2, h: PATROCINIO[g] * 0.3, texto: ped.marca }); }
        }
        const nome = n.replace("_careca", " careca").replace("_v", " V").replace(/_/g, " ");
        return (
          <figure key={n}>
            <Peca parte={parte} nomeParte={n} arte={ped.arte} textos={textos} logos={logos} caixas={caixas} pxPorCm={3.1} corManga={manga}
                  rotulo={`${ped.id} ${pessoa.tamanho} ${n.toUpperCase()}`} />
            <figcaption>{nome} · <span className="num">{parte.w.toFixed(0)}×{parte.h.toFixed(0)} cm</span></figcaption>
          </figure>
        );
      })}
    </div>
  );
}
