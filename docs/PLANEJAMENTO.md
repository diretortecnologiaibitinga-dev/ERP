# Planejamento — sistema de produção de personalizados

## Contexto

A empresa produz artigos personalizados por sublimação, DTF, gravação a laser
e impressão 3D (almofadas, capas de travesseiro, capas de porta etc.) e vende
pela Shopee, Mercado Livre e TikTok Shop, com o **UpSeller** como ERP.

Problemas a resolver:

1. As artes chegam espalhadas pelos chats dos marketplaces e pelo WhatsApp.
2. Cada arte precisa ser tratada (enquadramento, ampliação) e fechada no
   tamanho de produção, com margem de costura, código do pedido, quantidade e
   frente/verso. Hoje isso é feito à mão no Lovart + Corel.
3. Os anúncios precisam de mockups.

## Padrões de produção (definidos com a operação)

- Duas impressoras com **área útil de 1,80 m**, rolos de 300 a 500 m.
- O **RIP faz o espelhamento e o aproveitamento do rolo**: o sistema entrega
  um arquivo por peça (espelhar fica como opção). Aceita PNG, PDF e JPG e
  converte para PRN.
- **Sem emenda de painéis**: transferência na calandra até 1,80 m de largura;
  prensa plana de 2,00 × 1,20 m. Toda peça precisa caber em 1,80 m em uma direção.
- Resolução: 150 DPI (almofadas, travesseiros), 100 DPI (porta, fachada).
- Volume: **mais de 1000 almofadas por dia** — geração em paralelo é requisito.
- Peça = estampa + **1 cm de margem de cada lado** (segurança e costura).
  A arte fica **somente dentro** da área visível; a margem é branca, com
  **borda preta** no limite externo e o **código do pedido** escrito nela.
  - Almofada 45×45 → peça 47×47
  - Capa de travesseiro 40×70 → peça 42×72
  - Capa de porta: sob medida, de 0,70 × 2,00 m a 1,50 × 3,00 m, **margem de 3 cm** (elástico)
  - Fachadas: sob medida
- Saída em **PDF ou PNG**, cores sempre em **RGB** (sRGB).

## Tipos de entrada

1. **Marketplace (personalizado)**: pedido no UpSeller + arte/foto do cliente.
2. **Fotomoldura**: arte da loja (PNG com o espaço da foto transparente) +
   foto do cliente por baixo. Ex.: almofadas "I ♥ My Boyfriend/Girlfriend".
3. **Cliente local (arte pronta)**: abre uma **ordem de serviço**, gera os
   arquivos para o RIP e a ficha da produção, e avisa a produção.

## Ideia central: template com áreas de arte

O mesmo conceito serve para produção e para mockup:

| | Template de produção | Template de mockup |
|---|---|---|
| Base | Peça no tamanho real (ex.: 47×47 cm) | Foto ou modelo 3D do produto |
| Área de arte | Área visível 45×45, deslocada 1 cm | Área com perspectiva/dobras, ou a textura do modelo 3D |
| Por cima | Borda preta, código do pedido | Sombras e luz |

A arte é tratada uma vez e gera as duas saídas. Num mockup 3D (como o
[Rapid Mockup](https://rapidmockup.net/en)), a textura aplicada no modelo pode
ser o próprio arquivo de produção: a margem de costura some na dobra da
almofada e o cliente vê exatamente como a peça vai ficar.

## Fluxo de um pedido

aguardando arte → arte recebida → tratamento → aguardando aprovação →
pronto para impressão → impresso → costura → expedido

## Integrações

| Canal | Situação |
|---|---|
| UpSeller | Sem API pública (jan/2026). Pedidos via exportação em planilha ou direto das APIs dos marketplaces (só leitura). |
| WhatsApp | Chatwoot + WhatsApp Cloud API oficial. Evolution API/WAHA são não oficiais (risco de bloqueio do número). |
| Mercado Livre | API de mensagens pós-venda: conversa já ligada ao pedido (pack). Há limite de mensagens iniciadas pelo vendedor e bloqueio de links. |
| Shopee | API de chat no Open Platform, requer conta de parceiro aprovada. |
| TikTok Shop | API de atendimento, requer aprovação de parceiro. |

O Chatwoot não tem conectores para Shopee/Mercado Livre: um serviço próprio
faz a ponte com o canal de API do Chatwoot, e um webhook avisa o sistema quando
chega uma imagem.

**Ligar arte ao pedido** é o ponto mais difícil fora do Mercado Livre. Solução
proposta: um **portal de envio de arte** com link por pedido — o cliente envia a
imagem original (sem a compressão do WhatsApp), indica frente/verso, vê a prévia
e aprova.

## Arquitetura

- Backend Python (FastAPI) — o processamento de imagem é todo Python
  (Pillow, pyvips, OpenCV, Real-ESRGAN).
- Fila de tarefas (Redis + RQ/Celery) para ampliação e geração de arquivos.
- PostgreSQL; imagens em MinIO/S3.
- Frontend React com Konva.js/Fabric.js (recorte e posicionamento) e
  Three.js (mockups 3D e prévia para o cliente).
- Saída: pasta monitorada pelo RIP.

Modelo de dados: Produto (dimensões, margem, lados, espelhamento) ·
mapeamento SKU → produto/variação · Pedido / ItemPedido · Arte (original,
tratada, lado) · Peça / arquivo de produção · Lote (rolo) · Template de mockup.

## Fases

1. **Gerador de arquivos de produção** ✅ *(este repositório, `estampa`)*:
   catálogo de produtos (fixos e sob medida), tratamento de cor,
   enquadramento, aviso de resolução, ampliação por IA opcional, um arquivo
   por peça para o RIP (PNG/JPG/PDF) em paralelo e montagem opcional no rolo;
   fotomolduras com detecção automática do espaço da foto; ordem de serviço
   com ficha em PDF e aviso por webhook.
2. **Fila de pedidos**: importar a planilha do UpSeller, mapear SKU → produto,
   tela web para recortar/aprovar a arte, gerar lotes.
3. **Mockups**: (a) 3D com Three.js para almofada e travesseiro — imagens em
   vários ângulos e vídeo girando; (b) mockup 2D a partir de foto para cenas e
   capa de porta.
4. **Omnichannel**: Chatwoot + WhatsApp Cloud API; depois Mercado Livre e Shopee.
5. **Portal do cliente**: envio da arte e aprovação na prévia 3D.

Laser e 3D têm fluxos próprios (vetor/tons de cinza, STL) e ficam para depois;
o modelo de produto já prevê outros processos.

## Pendências

- Margem da fachada (hoje 1 cm) e se leva bainha/ilhós.
- Canal do aviso da OS para a produção (grupo de WhatsApp, Telegram, tela na produção?).
- Fotomoldura: enquadrar automaticamente pelo rosto (detecção facial) em vez
  do centro da foto.
- Indicar na ficha se a peça vai para a calandra ou para a prensa (2,00 × 1,20 m).
- Com 1000+ peças/dia, a etapa de conferência humana vira o gargalo: a tela
  de aprovação da Fase 2 precisa ser em grade, com aprovação em massa.
