export function Configuracoes() {
  const pastas = [["Prensa", "\\\\PC-RIP\\Flexi\\Impressora1-Prensa", "\\\\PC-RIP\\Flexi\\Impressora2-Prensa"], ["Calandra (rolo a rolo)", "\\\\PC-RIP\\Flexi\\Impressora2-Rolo", ""]];
  return (
    <div className="grade-2" style={{ alignItems: "start" }}>
      <section className="painel" style={{ display: "grid", gap: 12 }}>
        <h2>Flexi — pastas monitoradas</h2>
        {pastas.map(([eq, a, b]) => (
          <div key={eq} style={{ display: "grid", gap: 6 }}>
            <b>{eq}</b>
            <input className="busca mono" id={`pasta-${eq}`} defaultValue={a} />
            {b && <input className="busca mono" id={`pasta2-${eq}`} defaultValue={b} />}
          </div>
        ))}
        <span className="fraco">Com duas pastas, os itens são divididos entre as impressoras. Os arquivos chegam completos (gravados em _gravando/ e movidos de uma vez).</span>
      </section>
      <section className="painel" style={{ display: "grid", gap: 12 }}>
        <h2>Regras de produção</h2>
        <div className="grade-3" style={{ gap: 10 }}>
          <label className="campo">Resolução padrão<input id="dpi" defaultValue="150 DPI" /></label>
          <label className="campo">Peças grandes<input id="dpi-grande" defaultValue="100 DPI" /></label>
          <label className="campo">Largura do rolo<input id="rolo" defaultValue="180 cm" /></label>
          <label className="campo">Mesa da prensa<input id="prensa" defaultValue="120 × 200 cm" /></label>
          <label className="campo">Espelhamento<select id="espelhar" defaultValue="rip"><option value="rip">Feito pelo RIP</option><option value="sistema">Pelo sistema</option></select></label>
          <label className="campo">Rosto na fotomoldura<select id="rosto" defaultValue="auto"><option value="auto">Automático</option><option value="centro">Centralizar</option></select></label>
        </div>
      </section>
      <section className="painel" style={{ display: "grid", gap: 10 }}>
        <h2>Avisos de nova OS</h2>
        {[["Telegram", "Grupo Produção · robô @estampa_bot", true], ["WhatsApp (Evolution API)", "Grupo Produção · número dedicado", false], ["Painel da produção", "TV da produção · http://192.168.0.20:8080", true]].map(([n, d, on]) => (
          <label key={String(n)} className="linha" style={{ justifyContent: "space-between" }}>
            <span><b>{n}</b><br /><span className="fraco">{d}</span></span>
            <input type="checkbox" id={`aviso-${n}`} defaultChecked={Boolean(on)} style={{ width: 20, height: 20, accentColor: "var(--accent)" }} />
          </label>
        ))}
      </section>
      <section className="painel" style={{ display: "grid", gap: 10 }}>
        <h2>Integrações</h2>
        {[["UpSeller", "Importação da planilha de pedidos (sem API pública)"], ["Chatwoot", "Caixa única: WhatsApp, Shopee, Mercado Livre, TikTok"],
          ["Mercado Livre", "Mensagens pós-venda ligadas ao pedido"], ["Shopee", "Chat do Open Platform (parceiro aprovado)"]].map(([n, d]) => (
          <div key={n} className="linha"><b style={{ minWidth: 120 }}>{n}</b><span className="fraco">{d}</span></div>
        ))}
      </section>
    </div>
  );
}
