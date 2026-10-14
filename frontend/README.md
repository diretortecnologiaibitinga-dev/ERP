# Frontend (protótipo com dados fictícios)

React 18 + TypeScript + Vite. É a base das telas do sistema; por enquanto
lê dados fictícios de `src/data/mock.ts` (a próxima etapa é ligar à API do
backend — Laravel + Inertia, conforme a arquitetura).

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
npm run build:pagina   # dist-pagina/estampa.html: página única para demonstração
```

## Telas

| Tela | O que mostra |
|---|---|
| Painel do dia | Pedidos por etapa, canal e produto (prensa × calandra), alertas, filas do Flexi |
| Pedidos | Lista filtrável por canal/etapa; detalhe com artes, avisos e andamento |
| Aprovação de artes | Grade para aprovar em lote; editor de enquadramento da fotomoldura |
| Atendimento | Conversas do Chatwoot com as imagens; "usar como arte do pedido" |
| Uniformes e vestuário | Mesmo motor de moldes para esportivo, empresa, evento e venda; planilha de pessoas, grade, prévia em escala real |
| Produção | Filas por Setup do Flexi e ordens de serviço (kanban) |
| Catálogo | Moldes importados, produtos e fotomolduras |
| Configurações | Pastas do Flexi, regras de produção, avisos e integrações |

A prévia das peças de uniforme usa os **moldes fictícios** de
`src/data/moldes-exemplo.json` (gerados por `estampa.moldes_exemplo`), com a
mesma regra do motor: a arte é recortada em escala real (alinhada pelo centro
e pelo topo do quadro de edição) e número/nome têm altura em cm por grade.
Os moldes licenciados da SpeedCorel não entram no frontend nem no git.
