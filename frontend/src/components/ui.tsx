import { useEffect, useState } from "react";
import { AVISOS, type Aviso, CANAIS, type Canal, type Equipamento, STATUS, type StatusPedido } from "../data/mock";

export function Chip({ tom, children, ponto = true }: { tom?: string; children: React.ReactNode; ponto?: boolean }) {
  return <span className={`chip ${tom ?? ""} ${ponto ? "" : "sem-ponto"}`}>{children}</span>;
}

export function StatusChip({ status }: { status: StatusPedido }) {
  const s = STATUS[status];
  return <Chip tom={s.tom}>{s.rotulo}</Chip>;
}

export function AvisoChip({ aviso }: { aviso?: Aviso }) {
  if (!aviso) return <Chip tom="ok">Pronto</Chip>;
  return <Chip tom={aviso === "arte_faltando" ? "err" : "warn"}>{AVISOS[aviso]}</Chip>;
}

export function Equip({ e }: { e: Equipamento }) {
  return <span className={`equip ${e}`}>{e}</span>;
}

export function CanalTag({ canal }: { canal: Canal }) {
  return <span className="canal"><i style={{ background: CANAIS[canal] }} />{canal}</span>;
}

export function Kpi({ valor, rotulo, tom }: { valor: React.ReactNode; rotulo: string; tom?: "alerta" | "erro" }) {
  return <div className={`kpi ${tom ?? ""}`}><b>{valor}</b><span>{rotulo}</span></div>;
}

export const fmt = (n: number) => n.toLocaleString("pt-BR");

// aviso flutuante: useToast() → [elemento, mostrar(texto)]
export function useToast(): [React.ReactNode, (t: string) => void] {
  const [texto, setTexto] = useState<string | null>(null);
  useEffect(() => {
    if (!texto) return;
    const t = setTimeout(() => setTexto(null), 3200);
    return () => clearTimeout(t);
  }, [texto]);
  return [texto ? <div className="toast" role="status">{texto}</div> : null, setTexto];
}
