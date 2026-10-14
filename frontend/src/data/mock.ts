// Dados fictícios para o protótipo. Os formatos espelham o que o backend
// (estampa) já produz: pedidos, itens, artes, OS, moldes e equipamentos.

export type Canal = "Shopee" | "Mercado Livre" | "TikTok" | "WhatsApp" | "Cliente local";
export type Equipamento = "prensa" | "calandra";
export type StatusPedido = "aguardando_arte" | "tratamento" | "aprovacao" | "no_rip" | "producao" | "expedido";
export type Aviso = "baixa_resolucao" | "sem_rosto" | "arte_faltando" | "proporcao";

export const CANAIS: Record<Canal, string> = {
  Shopee: "#ee4d2d", "Mercado Livre": "#e6b800", TikTok: "#1f2937", WhatsApp: "#25a35a", "Cliente local": "#0b6f78",
};

export const STATUS: Record<StatusPedido, { rotulo: string; tom: string; cor: string }> = {
  aguardando_arte: { rotulo: "Aguardando arte", tom: "warn", cor: "#c98a12" },
  tratamento: { rotulo: "Em tratamento", tom: "acc", cor: "#3aa1a9" },
  aprovacao: { rotulo: "Para aprovar", tom: "warn", cor: "#e3a72f" },
  no_rip: { rotulo: "No RIP", tom: "acc", cor: "#0b6f78" },
  producao: { rotulo: "Em produção", tom: "acc", cor: "#3546a0" },
  expedido: { rotulo: "Expedido", tom: "ok", cor: "#1f7a43" },
};

export type TipoArte = "almofada" | "travesseiro" | "moldura" | "casal" | "porta" | "uniforme";

export interface Item {
  produto: string;
  tipo: TipoArte;
  quantidade: number;
  frenteVerso?: boolean;
  medida?: string;
  equipamento: Equipamento;
  aviso?: Aviso;
  arte: number; // semente da miniatura
}

export interface Pedido {
  id: string;
  canal: Canal;
  cliente: string;
  criado: string;
  prazo: string;
  status: StatusPedido;
  itens: Item[];
}

const nomes = ["Mariana Souza", "Carlos Lima", "Juliana Prado", "Rafael Mendes", "Ana Beatriz", "Lucas Ferreira", "Patrícia Rocha",
  "Diego Martins", "Fernanda Alves", "Bruno Costa", "Camila Ribeiro", "Thiago Nunes", "Larissa Gomes", "Eduardo Pires",
  "Beatriz Lopes", "Gustavo Reis", "Aline Teixeira", "Rodrigo Barros", "Natália Freitas", "Vinícius Araújo"];

const modelos: Omit<Item, "arte" | "quantidade" | "aviso">[] = [
  { produto: "Almofada 45x45", tipo: "almofada", frenteVerso: true, equipamento: "prensa" },
  { produto: "Almofada 45x45", tipo: "almofada", equipamento: "prensa" },
  { produto: "Almofada fotomoldura Te Amo", tipo: "moldura", equipamento: "prensa" },
  { produto: "Almofada casal (2 fotos)", tipo: "casal", equipamento: "prensa" },
  { produto: "Capa de travesseiro 40x70", tipo: "travesseiro", equipamento: "prensa" },
  { produto: "Capa de porta", tipo: "porta", medida: "70x200", equipamento: "prensa" },
  { produto: "Capa de porta", tipo: "porta", medida: "150x300", equipamento: "calandra" },
];

const canais: Canal[] = ["Shopee", "Shopee", "Mercado Livre", "TikTok", "Shopee", "Mercado Livre", "WhatsApp"];
const statusSeq: StatusPedido[] = ["aprovacao", "no_rip", "aguardando_arte", "producao", "aprovacao", "tratamento", "no_rip",
  "expedido", "aprovacao", "producao"];
const avisos: (Aviso | undefined)[] = [undefined, undefined, "baixa_resolucao", undefined, "sem_rosto", undefined, undefined,
  "baixa_resolucao", undefined, undefined, "arte_faltando", undefined];

function idPedido(canal: Canal, n: number): string {
  if (canal === "Shopee") return `SHP-2510${(14 + n) % 30}${String.fromCharCode(65 + (n % 26))}${n % 9}`;
  if (canal === "Mercado Livre") return `ML-20000${12345 + n * 37}`;
  if (canal === "TikTok") return `TT-577${(n * 53) % 1000}`.padEnd(10, "0");
  return `WA-${1000 + n}`;
}

export const PEDIDOS: Pedido[] = Array.from({ length: 36 }, (_, n) => {
  const canal = canais[n % canais.length];
  const m = modelos[(n * 3) % modelos.length];
  const status = statusSeq[n % statusSeq.length];
  const aviso = status === "aguardando_arte" ? "arte_faltando" : avisos[n % avisos.length];
  const itens: Item[] = [{ ...m, quantidade: [1, 2, 1, 3, 1, 1, 4][n % 7], arte: n * 7 + 1, aviso }];
  if (n % 5 === 0) itens.push({ ...modelos[1], quantidade: 2, arte: n * 7 + 3 });
  const h = 8 + (n % 10);
  return {
    id: idPedido(canal, n), canal, cliente: nomes[n % nomes.length], status, itens,
    criado: `14/10 ${String(h).padStart(2, "0")}:${String((n * 17) % 60).padStart(2, "0")}`,
    prazo: n % 9 === 4 ? "Hoje" : n % 3 === 0 ? "15/10" : "16/10",
  };
});

// ---- números do dia (o protótipo mostra uma operação do tamanho real: ~1300 pedidos)
export const DIA = {
  pedidos: 1284, pecas: 1932, aguardandoArte: 96, paraAprovar: 142, noRip: 1540, atrasados: 7,
  porStatus: [["aguardando_arte", 96], ["tratamento", 38], ["aprovacao", 142], ["no_rip", 611], ["producao", 274], ["expedido", 123]] as [StatusPedido, number][],
  porCanal: [["Shopee", 602], ["Mercado Livre", 371], ["TikTok", 188], ["WhatsApp", 79], ["Cliente local", 44]] as [Canal, number][],
  porProduto: [["Almofada 45x45", 1034, 0], ["Fotomoldura", 318, 0], ["Travesseiro 40x70", 241, 0], ["Uniformes (peças)", 212, 212],
    ["Capa de porta", 87, 21], ["Fachada", 40, 40]] as [string, number, number][], // nome, peças, das quais na calandra
};

export interface ArteParaAprovar {
  id: number;
  pedido: string;
  canal: Canal;
  tipo: TipoArte;
  produto: string;
  aviso?: Aviso;
  dpi: number;
}

export const ARTES: ArteParaAprovar[] = Array.from({ length: 24 }, (_, n) => {
  const tipos: TipoArte[] = ["almofada", "moldura", "almofada", "travesseiro", "casal", "almofada", "moldura", "porta"];
  const tipo = tipos[n % tipos.length];
  const aviso: Aviso | undefined = n % 7 === 2 ? "baixa_resolucao" : n % 11 === 5 ? "sem_rosto" : n === 9 ? "proporcao" : undefined;
  const ped = PEDIDOS[(n * 5) % PEDIDOS.length];
  const produto = { almofada: "Almofada 45x45", moldura: "Fotomoldura Te Amo", travesseiro: "Travesseiro 40x70",
    casal: "Almofada casal", porta: "Capa de porta 70x200", uniforme: "Uniforme" }[tipo];
  return { id: n, pedido: ped.id, canal: ped.canal, tipo, produto, aviso, dpi: aviso === "baixa_resolucao" ? 58 + (n % 30) : 150 + (n % 4) * 20 };
});

export const AVISOS: Record<Aviso, string> = {
  baixa_resolucao: "Baixa resolução",
  sem_rosto: "Rosto não encontrado",
  arte_faltando: "Arte não recebida",
  proporcao: "Proporção diferente",
};

// ---- ordens de serviço (clientes locais)
export interface OS {
  numero: string;
  cliente: string;
  entrega: string;
  obs?: string;
  status: "aberta" | "em produção" | "concluída";
  itens: { qtd: number; produto: string; fv?: boolean; equipamento: Equipamento }[];
}

export const ORDENS: OS[] = [
  { numero: "OS-000214", cliente: "Ateliê Maria", entrega: "16/10", obs: "Separar por cor", status: "em produção",
    itens: [{ qtd: 12, produto: "Almofada 45x45", fv: true, equipamento: "prensa" }, { qtd: 6, produto: "Travesseiro 40x70", equipamento: "prensa" }] },
  { numero: "OS-000215", cliente: "Festas & Cia", entrega: "18/10", obs: "Urgente — feira no sábado", status: "aberta",
    itens: [{ qtd: 30, produto: "Almofada 45x45", equipamento: "prensa" }, { qtd: 2, produto: "Capa de porta 150x300", equipamento: "calandra" }] },
  { numero: "OS-000216", cliente: "Esporte Clube União", entrega: "22/10", status: "aberta",
    itens: [{ qtd: 18, produto: "Uniforme esportivo (camisa + short)", equipamento: "calandra" }] },
  { numero: "OS-000211", cliente: "Colégio Horizonte", entrega: "14/10", status: "concluída",
    itens: [{ qtd: 120, produto: "Camiseta formatura (raglan)", equipamento: "calandra" }] },
  { numero: "OS-000217", cliente: "Clínica Bem Viver", entrega: "24/10", obs: "Logo no peito e costas", status: "aberta",
    itens: [{ qtd: 25, produto: "Polo corporativa", equipamento: "calandra" }] },
];

// ---- filas do RIP (Flexi): uma pasta monitorada por Setup
export const FILAS = [
  { setup: "Impressora 1 · Prensa", equipamento: "prensa" as Equipamento, aguardando: 214, impressos: 512, metros: 41.6, papel: 300, usado: 182 },
  { setup: "Impressora 2 · Prensa", equipamento: "prensa" as Equipamento, aguardando: 198, impressos: 486, metros: 39.2, papel: 500, usado: 351 },
  { setup: "Impressora 2 · Rolo (calandra)", equipamento: "calandra" as Equipamento, aguardando: 133, impressos: 212, metros: 58.4, papel: 500, usado: 351 },
];

// ---- atendimento (Chatwoot)
export interface Conversa {
  id: number;
  canal: Canal;
  cliente: string;
  pedido?: string;
  hora: string;
  naoLidas: number;
  mensagens: { de: "cliente" | "loja"; texto?: string; imagem?: { tipo: TipoArte; semente: number; nome: string } }[];
}

export const CONVERSAS: Conversa[] = [
  { id: 1, canal: "WhatsApp", cliente: "Juliana Prado", pedido: "SHP-251016C2", hora: "10:42", naoLidas: 2, mensagens: [
    { de: "cliente", texto: "Oi! Comprei a almofada Te Amo na Shopee, segue a foto 😊" },
    { de: "cliente", imagem: { tipo: "moldura", semente: 4, nome: "IMG_2041.jpg" } },
    { de: "cliente", texto: "Dá pra deixar o rosto bem no meio do coração?" }] },
  { id: 2, canal: "Shopee", cliente: "Carlos Lima", pedido: "SHP-251015B1", hora: "10:31", naoLidas: 1, mensagens: [
    { de: "loja", texto: "Olá Carlos! Para personalizar, envie a imagem por aqui ou pelo link do pedido." },
    { de: "cliente", imagem: { tipo: "almofada", semente: 9, nome: "arte_frente.png" } }] },
  { id: 3, canal: "Mercado Livre", cliente: "Rafael Mendes", pedido: "ML-2000012456", hora: "09:58", naoLidas: 0, mensagens: [
    { de: "cliente", texto: "Vou mandar duas fotos, uma para cada coração." },
    { de: "cliente", imagem: { tipo: "casal", semente: 12, nome: "nos_dois.jpg" } }] },
  { id: 4, canal: "TikTok", cliente: "Ana Beatriz", hora: "09:20", naoLidas: 3, mensagens: [
    { de: "cliente", texto: "Vocês fazem capa de porta 80x210?" },
    { de: "loja", texto: "Fazemos sim! Vai com 3 cm de elástico de cada lado." }] },
  { id: 5, canal: "WhatsApp", cliente: "E.C. União (Marcos)", pedido: "OS-000216", hora: "Ontem", naoLidas: 0, mensagens: [
    { de: "cliente", texto: "Segue a lista dos jogadores com tamanho." },
    { de: "cliente", texto: "📎 jogadores_uniao.xlsx" }] },
];

// ---- catálogo
export const PRODUTOS = [
  { codigo: "almofada-45", nome: "Almofada 45x45", estampa: "45 × 45 cm", peca: "47 × 47 cm", margem: "1 cm", lados: 2, transferencia: "auto → prensa" },
  { codigo: "travesseiro-40x70", nome: "Capa de travesseiro 40x70", estampa: "40 × 70 cm", peca: "42 × 72 cm", margem: "1 cm", lados: 2, transferencia: "auto → prensa" },
  { codigo: "capa-porta", nome: "Capa de porta", estampa: "sob medida, até 150 × 300", peca: "+ 3 cm (elástico)", margem: "3 cm", lados: 1, transferencia: "auto (prensa se couber)" },
  { codigo: "fachada", nome: "Fachada", estampa: "sob medida", peca: "+ 1 cm", margem: "1 cm", lados: 1, transferencia: "auto (prensa se couber)" },
];

export const MOLDURAS = [
  { codigo: "coracao-boyfriend", nome: "I ♥ My Boyfriend", espacos: 1 },
  { codigo: "coracao-girlfriend", nome: "I ♥ My Girlfriend", espacos: 1 },
  { codigo: "casal-dois-coracoes", nome: "Nosso Amor (2 fotos)", espacos: 2 },
];

export interface ModeloVestuario {
  codigo: string;
  nome: string;
  familia: "Camiseta" | "Polo" | "Raglan" | "Regata" | "Basquete" | "Short";
  grade: string;
  tamanhos: string[];
  partes: string[];
  origem: string;
}

const ADULTO = ["PP", "P", "M", "G", "GG", "XG", "XGG"];
const INFANTIL = ["2", "4", "6", "8", "10", "12", "14"];
const FEM = ["BLPP", "BLP", "BLM", "BLG", "BLGG", "BLXG"];

export const MODELOS: ModeloVestuario[] = [
  { codigo: "casual", nome: "Camiseta casual", familia: "Camiseta", grade: "Infantil · Feminino · Adulto", tamanhos: [...INFANTIL, ...FEM, ...ADULTO],
    partes: ["frente careca", "frente V", "costas", "manga curta", "manga longa"], origem: "SPEEDCOREL_CASUAL_tradicionais.pdf" },
  { codigo: "esportivo", nome: "Camiseta esportiva", familia: "Camiseta", grade: "Infantil · Feminino · Adulto", tamanhos: [...INFANTIL, ...FEM, ...ADULTO],
    partes: ["frente careca", "frente V", "costas", "manga curta", "manga longa"], origem: "SPEEDCOREL_ESPORTIVO_camisetas.pdf" },
  { codigo: "polo-homem", nome: "Polo masculina", familia: "Polo", grade: "Adulto", tamanhos: ["PP", "P", "M", "G", "GG", "XG", "EXG"],
    partes: ["frente", "costas", "gola", "manga curta", "manga com barra"], origem: "SPEEDCOREL_CASUAL_POLO.pdf" },
  { codigo: "polo-mulher", nome: "Polo feminina", familia: "Polo", grade: "Feminino", tamanhos: [...FEM, "BLXGG"],
    partes: ["frente", "costas", "gola", "manga curta", "manga com barra"], origem: "SPEEDCOREL_CASUAL_POLO.pdf" },
  { codigo: "raglan-unissex", nome: "Raglan unissex", familia: "Raglan", grade: "Adulto", tamanhos: ["PP", "P", "M", "G", "GG", "XG", "EXG"],
    partes: ["frente", "costas", "manga raglan"], origem: "SPEEDCOREL_CASUAL_raglan.pdf" },
  { codigo: "raglan-infantil", nome: "Raglan infantil", familia: "Raglan", grade: "Infantil", tamanhos: [...INFANTIL, "16"],
    partes: ["frente", "costas", "manga raglan"], origem: "SPEEDCOREL_CASUAL_raglan.pdf" },
  { codigo: "raglan-mulher", nome: "Raglan feminina", familia: "Raglan", grade: "Feminino", tamanhos: ["BLP", "BLM", "BLG", "BLGG"],
    partes: ["frente", "costas", "manga raglan"], origem: "SPEEDCOREL_CASUAL_raglan.pdf" },
  { codigo: "regata", nome: "Regata", familia: "Regata", grade: "Adulto", tamanhos: ["PP", "P", "M", "G", "GG", "XG", "EXG"],
    partes: ["frente", "costas"], origem: "SPEEDCOREL_CASUAL_regata.pdf" },
  { codigo: "basquete", nome: "Conjunto basquete", familia: "Basquete", grade: "Adulto", tamanhos: ["PP", "P", "M", "G", "GG", "XG"],
    partes: ["frente", "costas", "gola", "filetes", "short (4 painéis + faixas)"], origem: "SPEEDCOREL_ESPORTIVO_basquete.pdf" },
  { codigo: "shorts-masculino", nome: "Short masculino", familia: "Short", grade: "Adulto", tamanhos: ["PP", "P", "M", "G", "GG", "XG"],
    partes: ["perna direita", "perna esquerda"], origem: "SPEEDCOREL_ESPORTIVO_shorts.pdf" },
  { codigo: "shorts-feminino", nome: "Short feminino", familia: "Short", grade: "Feminino", tamanhos: ["P", "M", "G", "GG", "XG"],
    partes: ["perna direita", "perna esquerda"], origem: "SPEEDCOREL_ESPORTIVO_shorts.pdf" },
];

// ---- pedido de uniforme de exemplo
export interface Pessoa { nome: string; numero: string; tamanho: string; qtd: number }

export const JOGADORES: Pessoa[] = [
  { nome: "Lucas", numero: "10", tamanho: "M", qtd: 1 },
  { nome: "Rafael", numero: "08", tamanho: "XGG", qtd: 1 },
  { nome: "Matheus", numero: "06", tamanho: "G", qtd: 1 },
  { nome: "Bruno", numero: "11", tamanho: "GG", qtd: 1 },
  { nome: "Felipe", numero: "15", tamanho: "M", qtd: 1 },
  { nome: "Thiago", numero: "18", tamanho: "P", qtd: 1 },
  { nome: "Daniel", numero: "19", tamanho: "G", qtd: 1 },
  { nome: "André", numero: "02", tamanho: "XG", qtd: 1 },
  { nome: "Leonardo", numero: "23", tamanho: "M", qtd: 1 },
  { nome: "Pedro", numero: "13", tamanho: "GG", qtd: 1 },
  { nome: "Joãozinho", numero: "7", tamanho: "8", qtd: 1 },
  { nome: "Ana", numero: "9", tamanho: "BLM", qtd: 1 },
];
