// Peça de uniforme desenhada a partir do contorno do molde (em cm), com a mesma regra
// do motor de produção: a arte do quadro de edição é recortada em escala real,
// alinhada pelo centro e pelo topo — o desenho não estica entre os tamanhos.
import moldes from "../data/moldes-exemplo.json";

export interface Parte { w: number; h: number; pts: number[][]; logos: Record<string, number[]> }
export type Grade = "infantil" | "feminino" | "adulto";
export interface ArteTime { padrao: "listras" | "faixas" | "degrade" | "liso"; cor1: string; cor2: string; manga: string }
export interface Texto { texto: string; cx: number; cy: number; alturaCm: number; larguraMax?: number }
export interface Logo { slot: string; tipo: "escudo" | "patrocinio" | "empresa"; texto: string }
/** Imagem posicionada livremente (patrocínio das costas, marca da empresa): centro em fração da peça, caixa em cm. */
export interface Caixa { cx: number; cy: number; w: number; h: number; texto: string; escura?: boolean }

type Biblioteca = Record<string, { grade: Grade; partes: Record<string, Parte> }>;
export const BIBLIOTECA = moldes as unknown as Biblioteca;

export function grade(tamanho: string): Grade {
  if (/^\d+$/.test(tamanho)) return "infantil";
  if (tamanho.startsWith("BL")) return "feminino";
  return "adulto";
}

/** Tamanho da biblioteca de exemplo usado na prévia (o sistema usa o molde exato). */
export function tamanhoExemplo(tamanho: string): string {
  const g = grade(tamanho);
  if (g === "infantil") return "8";
  if (g === "feminino") return "BLM";
  return ["GG", "XG", "XGG", "EXG", "EXGG"].includes(tamanho) ? "XGG" : "M";
}

export function quadro(parte: string): { w: number; h: number } {
  const ps = Object.values(BIBLIOTECA).map(t => t.partes[parte]).filter(Boolean);
  return { w: Math.max(...ps.map(p => p.w)), h: Math.max(...ps.map(p => p.h)) };
}

function Padrao({ id, arte, cor, dx }: { id: string; arte: ArteTime; cor?: string; dx: number }) {
  const c1 = cor ?? arte.cor1;
  if (arte.padrao === "liso") return null;
  if (arte.padrao === "degrade")
    return <linearGradient id={id} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="95"><stop offset="0" stopColor={c1} /><stop offset="1" stopColor={arte.cor2} /></linearGradient>;
  const largura = arte.padrao === "listras" ? 7 : 10;
  return (
    <pattern id={id} patternUnits="userSpaceOnUse" width={largura * 2} height="200"
             patternTransform={`translate(${dx},0) ${arte.padrao === "listras" ? "rotate(35)" : ""}`}>
      <rect width={largura * 2} height="200" fill={c1} />
      <rect width={largura} height="200" fill={arte.cor2} />
    </pattern>
  );
}

export function Peca({ parte, nomeParte, arte, textos = [], logos = [], caixas = [], pxPorCm, corManga, rotulo }: {
  parte: Parte; nomeParte: string; arte: ArteTime; textos?: Texto[]; logos?: Logo[]; caixas?: Caixa[]; pxPorCm: number;
  corManga?: boolean; rotulo?: string;
}) {
  const q = quadro(nomeParte);
  const dx = -(q.w - parte.w) / 2;  // a peça é o recorte central do quadro, a partir do topo
  const id = `p-${nomeParte}-${parte.w}-${arte.padrao}-${arte.cor1}-${arte.cor2}-${corManga ? 1 : 0}`.replace(/[^a-z0-9-]/gi, "");
  const pontos = parte.pts.map(([x, y]) => `${x},${y}`).join(" ");
  const fundo = arte.padrao === "liso" ? (corManga ? arte.manga : arte.cor1) : `url(#${id}f)`;
  return (
    <svg viewBox={`-0.5 -0.5 ${parte.w + 1} ${parte.h + 1}`} width={(parte.w + 1) * pxPorCm} height={(parte.h + 1) * pxPorCm}
         role="img" aria-label={rotulo ?? nomeParte}>
      <defs>
        <clipPath id={`${id}c`}><polygon points={pontos} /></clipPath>
        <Padrao id={`${id}f`} arte={arte} cor={corManga ? arte.manga : undefined} dx={dx} />
      </defs>
      <g clipPath={`url(#${id}c)`}>
        <rect x="-1" y="-1" width={parte.w + 2} height={parte.h + 2} fill={fundo} />
        {logos.map(l => {
          const m = parte.logos[l.slot];
          if (!m) return null;
          const [cx, cy, w, h] = m;
          if (l.tipo === "escudo") {
            const r = Math.min(w, h) / 2;
            return <g key={l.slot}><circle cx={cx} cy={cy} r={r} fill="#fff" stroke={arte.cor2} strokeWidth={r * 0.14} />
              <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" fontSize={r * 0.9} fontWeight="800" fill={arte.cor2} fontFamily="Archivo, sans-serif">{l.texto}</text></g>;
          }
          return <g key={l.slot}><rect x={cx - w / 2} y={cy - h * 0.32} width={w} height={h * 0.64} rx={h * 0.12} fill="#fff" />
            <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" fontSize={Math.min(h * 0.32, (w * 1.6) / Math.max(4, l.texto.length))}
                  fontWeight="800" fill="#b4235f" fontFamily="Archivo, sans-serif">{l.texto}</text></g>;
        })}
        {caixas.map((c, i) => {
          const x = c.cx * parte.w - c.w / 2, y = c.cy * parte.h - c.h / 2;
          return <g key={`c${i}`}><rect x={x} y={y} width={c.w} height={c.h} rx={c.h * 0.18} fill={c.escura ? "#141414" : "#fff"} />
            <text x={c.cx * parte.w} y={c.cy * parte.h} textAnchor="middle" dominantBaseline="central"
                  fontSize={Math.min(c.h * 0.5, (c.w * 1.55) / Math.max(4, c.texto.length))} fontWeight="800"
                  fill={c.escura ? "#fff" : "#b4235f"} fontFamily="Archivo, sans-serif">{c.texto}</text></g>;
        })}
        {textos.filter(t => t.texto).map((t, i) => {
          // a altura pedida é a altura visível das letras (≈ 0,72 do corpo da fonte); nome comprido encolhe
          let corpo = t.alturaCm / 0.72;
          const maxLarg = (t.larguraMax ?? 0.75) * parte.w;
          corpo = Math.min(corpo, maxLarg / (0.62 * t.texto.length));
          return <text key={i} x={t.cx * parte.w} y={t.cy * parte.h} textAnchor="middle" dominantBaseline="central" fontSize={corpo}
                       fontWeight="800" fill="#fff" stroke="#000" strokeWidth={Math.max(0.12, corpo * 0.035)} paintOrder="stroke"
                       fontFamily="Archivo, sans-serif">{t.texto}</text>;
        })}
      </g>
      <polygon points={pontos} fill="none" stroke="#111" strokeWidth=".18" />
      {rotulo && <text x={parte.w / 2} y={parte.h - 1.4} textAnchor="middle" fontSize=".9" fill="#222" stroke="#fff" strokeWidth=".15" paintOrder="stroke" fontFamily="JetBrains Mono, monospace">{rotulo}</text>}
    </svg>
  );
}
