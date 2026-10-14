import { useEffect, useState } from "react";
import { DIA } from "./data/mock";
import { useToast } from "./components/ui";
import { Aprovacao } from "./pages/Aprovacao";
import { Atendimento } from "./pages/Atendimento";
import { Catalogo } from "./pages/Catalogo";
import { Configuracoes } from "./pages/Configuracoes";
import { Painel } from "./pages/Painel";
import { Pedidos } from "./pages/Pedidos";
import { Producao } from "./pages/Producao";
import { Uniformes } from "./pages/Uniformes";

const TELAS = {
  painel: { titulo: "Painel do dia", sub: "Terça, 14 de outubro · operação de hoje", grupo: "Operação" },
  pedidos: { titulo: "Pedidos", sub: "Shopee, Mercado Livre, TikTok e WhatsApp", grupo: "Operação", cont: DIA.pedidos },
  aprovacao: { titulo: "Aprovação de artes", sub: "Confira, ajuste e aprove em lote antes de ir para o RIP", grupo: "Operação", cont: DIA.paraAprovar },
  atendimento: { titulo: "Atendimento", sub: "Conversas do Chatwoot com as imagens dos clientes", grupo: "Operação", cont: 6 },
  uniformes: { titulo: "Uniformes e vestuário", sub: "Times, empresas, eventos e coleções — moldes em toda a grade", grupo: "Produção" },
  producao: { titulo: "Produção", sub: "Filas do Flexi e ordens de serviço", grupo: "Produção" },
  catalogo: { titulo: "Catálogo", sub: "Produtos, moldes de vestuário e fotomolduras", grupo: "Cadastros" },
  configuracoes: { titulo: "Configurações", sub: "RIP, regras de produção, avisos e integrações", grupo: "Cadastros" },
} as const;
type Tela = keyof typeof TELAS;

function telaDoEndereco(): Tela {
  const h = location.hash.replace("#", "");
  return (h in TELAS ? h : "painel") as Tela;
}

export function App() {
  const [tela, setTela] = useState<Tela>(telaDoEndereco);
  const [toast, avisar] = useToast();
  useEffect(() => {
    const f = () => setTela(telaDoEndereco());
    addEventListener("hashchange", f);
    return () => removeEventListener("hashchange", f);
  }, []);
  const ir = (t: string) => { location.hash = t; };
  const info = TELAS[tela];
  const grupos = [...new Set(Object.values(TELAS).map(t => t.grupo))];
  return (
    <div className="app">
      <aside className="lateral">
        <div className="marca"><div className="marca-sinal"><span /></div><div><b>Estampa</b><small>Produção de personalizados</small></div></div>
        <nav className="nav" aria-label="Telas">
          {grupos.map(g => (
            <div key={g} style={{ display: "contents" }}>
              <div className="nav-grupo">{g}</div>
              {(Object.keys(TELAS) as Tela[]).filter(k => TELAS[k].grupo === g).map(k => {
                const t = TELAS[k];
                return <a key={k} href={`#${k}`} className={tela === k ? "ativo" : ""}>{t.titulo}
                  {"cont" in t && <span className="cont">{t.cont.toLocaleString("pt-BR")}</span>}</a>;
              })}
            </div>
          ))}
        </nav>
        <div className="lateral-rodape">Protótipo com dados fictícios</div>
      </aside>
      <main className="principal">
        <header className="topo">
          <div><h1>{info.titulo}</h1><div className="sub">{info.sub}</div></div>
          <span className="aviso-demo">Dados fictícios</span>
        </header>
        <div className="conteudo">
          {tela === "painel" && <Painel ir={ir} />}
          {tela === "pedidos" && <Pedidos />}
          {tela === "aprovacao" && <Aprovacao avisar={avisar} />}
          {tela === "atendimento" && <Atendimento avisar={avisar} />}
          {tela === "uniformes" && <Uniformes avisar={avisar} />}
          {tela === "producao" && <Producao avisar={avisar} />}
          {tela === "catalogo" && <Catalogo />}
          {tela === "configuracoes" && <Configuracoes />}
        </div>
      </main>
      {toast}
    </div>
  );
}
