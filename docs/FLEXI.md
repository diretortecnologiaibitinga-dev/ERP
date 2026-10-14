# Integração com o Flexi (SAi / thinkSAI)

O sistema entrega os arquivos nas **pastas monitoradas (hot folders)** dos
Setups do Flexi Production Manager. O Flexi cuida do espelhamento, do encaixe
no rolo e da conversão para o formato da impressora (PRN).

> Este guia foi montado a partir da central de ajuda da SAi e de relatos de
> usuários; os nomes das opções podem variar conforme a versão do Flexi.
> Os itens marcados com **[conferir]** precisam ser testados na versão instalada.

## Como o sistema entrega

- Um arquivo por peça (frente/verso e cada cópia), PNG ou JPG em **sRGB**, com
  o perfil embutido e DPI fixo por produto — todos os arquivos de um mesmo
  produto têm as mesmas configurações, o que o Flexi exige para encaixar
  trabalhos juntos.
- Nome do arquivo = trabalho no Flexi: `almofada-45_SHP-250114A1_frente_1de2.png`
  (começa pelo produto, para a fila ficar agrupada).
- Cada item é gravado em `<pasta>/_gravando/` e só então movido para a pasta
  monitorada, **todos os arquivos do item de uma vez**. O Flexi nunca pega um
  arquivo pela metade, e um item com erro não manda nada para impressão.
  **[conferir]** que o Flexi não monitora subpastas (a `_gravando` deve ser ignorada).
- Pastas por equipamento em `[rip]` no `produtos.toml`. Com duas pastas para o
  mesmo equipamento (uma por impressora), os itens são divididos pela carga.

## Configuração sugerida no Production Manager

Crie **um Setup por impressora e destino** (ex.: `Impressora1-Prensa`,
`Impressora2-Prensa`, `Impressora1-Rolo`), cada um com sua pasta:

1. **Setup Properties → pasta monitorada (hot folder)**: aponte para a pasta
   configurada em `[rip]`. Se o Flexi roda em outro computador, compartilhe a
   pasta na rede e use o caminho `\\PC-RIP\...`.
2. **After Receive**: comece com *segurar* (hold) para conferir os primeiros
   lotes; depois de validado, mude para processar direto.
3. **Automatic Nesting**: ligue o encaixe automático, disparando por número de
   trabalhos ou por minutos (ex.: a cada 20 trabalhos ou 10 minutos), ou por
   porcentagem de cobertura do rolo. A opção de **girar** as peças economiza
   papel; a etiqueta do pedido gira junto e continua legível.
4. **Espelhamento**: deixe o espelho ligado no Setup (o sistema não espelha).
   Segundo a SAi, o *Mirror Image* espelha sempre na vertical; para o outro
   sentido, gire 90° antes. **[conferir]** o sentido correto para o papel de sublimação.
5. **Cor**: perfil de entrada RGB = **sRGB** em todos os Setups. O Flexi só
   encaixa juntos trabalhos com o mesmo perfil e as mesmas opções.

## Pontos em aberto

- **Cópias**: hoje cada cópia é um arquivo próprio (a margem mostra `2/3`).
  Com centenas de cópias iguais, avaliar o tempo de RIP; a alternativa é um
  arquivo por item com a quantidade definida no Flexi — mas a pasta monitorada
  não recebe a quantidade, então seria manual. **[conferir]** o tempo com 1000 arquivos.
- **Formato**: PNG é sem perdas; JPG (qualidade 95) é ~3x mais rápido e leve.
  **[conferir]** se há diferença visível na impressão.
