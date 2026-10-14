// Miniaturas ilustrativas das artes (SVG gerado), no formato real de cada produto.
import type { TipoArte } from "../data/mock";

const PALETAS = [["#f0789e", "#7d2a6e"], ["#4fb38a", "#165c46"], ["#f6b13d", "#b8541c"], ["#5b8fe0", "#1d3a7a"],
  ["#9b7be0", "#41286f"], ["#36b3c1", "#0f4f63"], ["#e86a5a", "#7a1f1f"]];
const TEXTOS = ["MÃE", "FLORES", "VOVÓ", "MEU PET", "AMOR", "CAMPEÃO", "BEM-VINDOS", "FAMÍLIA"];

function aleatorio(semente: number) {
  let s = semente * 9301 + 49297;
  return () => ((s = (s * 9301 + 49297) % 233280) / 233280);
}

export function coracao(cx: number, cy: number, k: number, passos = 64): string {
  const pts: string[] = [];
  for (let i = 0; i < passos; i++) {
    const t = (2 * Math.PI * i) / passos;
    const x = 16 * Math.sin(t) ** 3;
    const y = 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t);
    pts.push(`${(cx + x * k).toFixed(2)},${(cy - y * k).toFixed(2)}`);
  }
  return pts.join(" ");
}

function Arte({ w, h, semente }: { w: number; h: number; semente: number }) {
  const r = aleatorio(semente);
  const [c1, c2] = PALETAS[Math.floor(r() * PALETAS.length)];
  const titulo = TEXTOS[Math.floor(r() * TEXTOS.length)];
  const id = `g${semente}-${w}`;
  const circulos = Array.from({ length: 7 }, () => ({ x: r() * w, y: r() * h, raio: (0.08 + r() * 0.16) * Math.min(w, h) }));
  return (
    <g>
      <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={c1} /><stop offset="1" stopColor={c2} /></linearGradient></defs>
      <rect width={w} height={h} fill={`url(#${id})`} />
      {circulos.map((c, i) => <circle key={i} cx={c.x} cy={c.y} r={c.raio} fill="none" stroke="#fff" strokeOpacity=".75" strokeWidth={Math.min(w, h) * 0.012} />)}
      <text x={w / 2} y={h / 2} textAnchor="middle" dominantBaseline="middle" fontFamily="Archivo, sans-serif" fontWeight="800"
            fontSize={Math.min(w, h) * 0.15} fill="#fff" stroke="#000" strokeOpacity=".35" strokeWidth={Math.min(w, h) * 0.006}>
        {titulo}
      </text>
    </g>
  );
}

function Pessoa({ cx, cy, k, tom }: { cx: number; cy: number; k: number; tom: string }) {
  return (
    <g>
      <rect x={cx - 30 * k} y={cy - 26 * k} width={60 * k} height={60 * k} fill={tom} />
      <ellipse cx={cx} cy={cy + 26 * k} rx={22 * k} ry={14 * k} fill="#2c3e64" />
      <ellipse cx={cx} cy={cy - 4 * k} rx={9 * k} ry={11 * k} fill="#f0c9a5" />
      <path d={`M${cx - 9.5 * k},${cy - 6 * k} Q${cx},${cy - 22 * k} ${cx + 9.5 * k},${cy - 6 * k} Q${cx + 6 * k},${cy - 13 * k} ${cx},${cy - 13 * k} Q${cx - 6 * k},${cy - 13 * k} ${cx - 9.5 * k},${cy - 6 * k}`} fill="#5a3a22" />
    </g>
  );
}

const MEDIDAS: Record<TipoArte, [number, number]> = {
  almofada: [47, 47], moldura: [47, 47], casal: [47, 47], travesseiro: [42, 72], porta: [76, 206], uniforme: [57, 75],
};

export function Miniatura({ tipo, semente, faltando, rotulo, largura = 160 }: {
  tipo: TipoArte; semente: number; faltando?: boolean; rotulo?: string; largura?: number;
}) {
  const [W, H] = MEDIDAS[tipo];
  const m = tipo === "porta" ? 3 : 1;
  const escala = Math.max(W, H);
  const altura = (largura * H) / Math.max(W, H * 0.9);
  return (
    <svg className="mini" viewBox={`${-(escala - W) / 2} 0 ${escala} ${Math.max(H, escala * 0.9)}`} width={largura} height={altura}
         role="img" aria-label={rotulo ?? tipo}>
      <rect x="0" y="0" width={W} height={H} fill="#fff" />
      {faltando ? (
        <g>
          <rect x={m} y={m} width={W - 2 * m} height={H - 2 * m} fill="#f5f6f7" stroke="#b9c2c8" strokeDasharray="1.5 1.2" strokeWidth=".4" />
          <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={W * 0.075} fill="#84919a" fontFamily="Source Sans 3, sans-serif">aguardando arte</text>
        </g>
      ) : tipo === "moldura" || tipo === "casal" ? (
        <g>
          <defs>
            <clipPath id={`h${semente}`}>
              {tipo === "moldura" ? <polygon points={coracao(23.5, 20, 0.95)} /> : <>
                <polygon points={coracao(14, 20, 0.62)} /><polygon points={coracao(33, 20, 0.62)} /></>}
            </clipPath>
          </defs>
          <g clipPath={`url(#h${semente})`}>
            {tipo === "moldura" ? <Pessoa cx={23.5} cy={20} k={0.42} tom={PALETAS[Math.floor(aleatorio(semente)() * PALETAS.length)][0]} /> : <>
              <Pessoa cx={14} cy={20} k={0.28} tom="#8fb8de" /><Pessoa cx={33} cy={20} k={0.28} tom="#e9a8c0" /></>}
          </g>
          {tipo === "moldura" ? <polygon points={coracao(23.5, 20, 0.95)} fill="none" stroke="#c8102e" strokeWidth="2.2" /> : <>
            <polygon points={coracao(14, 20, 0.62)} fill="none" stroke="#9b1d5a" strokeWidth="1.6" />
            <polygon points={coracao(33, 20, 0.62)} fill="none" stroke="#9b1d5a" strokeWidth="1.6" /></>}
          <text x={23.5} y={41} textAnchor="middle" fontSize="5" fontWeight="800" fill="#c8102e" fontFamily="Archivo, sans-serif">
            {tipo === "moldura" ? "Te Amo" : "Nosso Amor"}</text>
        </g>
      ) : (
        <g transform={`translate(${m},${m})`}><Arte w={W - 2 * m} h={H - 2 * m} semente={semente} /></g>
      )}
      <rect x=".15" y=".15" width={W - 0.3} height={H - 0.3} fill="none" stroke="#000" strokeWidth=".3" />
    </svg>
  );
}
