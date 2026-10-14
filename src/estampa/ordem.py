"""Ordem de serviço (OS) para clientes que mandam a arte pronta.

Cada OS recebe um número sequencial, gera os arquivos de produção (com o
número da OS na margem), uma ficha em PDF para acompanhar a produção e
dispara um aviso por webhook (n8n, Make, ntfy, Discord, ou um robô de
WhatsApp/Telegram do grupo da produção).
"""

from __future__ import annotations

import io
import json
import shutil
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image
from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from .lote import ItemPedido, preparar_lado

try:
    import fcntl

    def _travar(f) -> None:
        fcntl.flock(f, fcntl.LOCK_EX)
except ImportError:  # Windows
    import msvcrt

    def _travar(f) -> None:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

DPI_MINIATURA = 12


def proximo_numero(pasta: Path, prefixo: str = "OS") -> str:
    """Numeração sequencial guardada em `pasta/sequencia.txt` (com trava de arquivo)."""
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "sequencia.txt", "a+") as f:
        _travar(f)
        f.seek(0)
        atual = int(f.read().strip() or 0) + 1
        f.seek(0)
        f.truncate()
        f.write(str(atual))
    return f"{prefixo}-{atual:06d}"


@dataclass
class ResumoItem:
    produto: str
    medida_cm: str
    quantidade: int
    lados: int
    artes: list[str]

    @property
    def pecas(self) -> int:
        return self.quantidade * self.lados


@dataclass
class OrdemServico:
    numero: str
    cliente: str
    criada_em: str
    entrega: str | None = None
    observacoes: str = ""
    itens: list[ResumoItem] = field(default_factory=list)
    arquivos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    @property
    def total_pecas(self) -> int:
        return sum(i.pecas for i in self.itens)

    def resumo_texto(self) -> str:
        linhas = [f"Nova {self.numero} — {self.cliente}"]
        if self.entrega:
            linhas.append(f"Entrega: {self.entrega}")
        for i in self.itens:
            lados = " (frente e verso)" if i.lados == 2 else ""
            linhas.append(f"• {i.quantidade}x {i.produto}{lados}")
        linhas.append(f"Total: {self.total_pecas} peça(s), arquivos já na pasta do RIP")
        if self.erros:
            linhas.append(f"ATENÇÃO: {len(self.erros)} item(ns) com erro")
        return "\n".join(linhas)


def resumir(itens: list[ItemPedido]) -> list[ResumoItem]:
    return [
        ResumoItem(
            produto=i.produto.nome,
            medida_cm=f"{i.produto.largura_total_cm:g}x{i.produto.altura_total_cm:g}",
            quantidade=i.quantidade,
            lados=len(i.lados),
            artes=[", ".join(f.name for f in lado.fotos) for lado in i.lados],
        )
        for i in itens
    ]


def _miniatura(item: ItemPedido, lado: int) -> ImageReader | None:
    try:
        arte = preparar_lado(item.lados[lado], item.produto, DPI_MINIATURA)
    except Exception:  # noqa: BLE001 — a ficha sai mesmo sem miniatura; o erro aparece no lote
        return None
    buf = io.BytesIO()
    arte.imagem.thumbnail((300, 300), Image.Resampling.LANCZOS)
    arte.imagem.save(buf, "JPEG", quality=85)
    buf.seek(0)
    return ImageReader(buf)


def gerar_ficha_pdf(os_: OrdemServico, itens: list[ItemPedido], destino: Path) -> None:
    """Ficha A4 com miniatura de cada item e campos de conferência."""
    c = Canvas(str(destino), pagesize=A4)
    largura, altura = A4
    cinza = HexColor("#666666")

    def cabecalho() -> float:
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1.5 * cm, altura - 2 * cm, os_.numero)
        c.setFont("Helvetica", 11)
        c.drawString(1.5 * cm, altura - 2.7 * cm, f"Cliente: {os_.cliente}")
        c.drawString(1.5 * cm, altura - 3.3 * cm, f"Criada em: {os_.criada_em}")
        if os_.entrega:
            c.setFont("Helvetica-Bold", 11)
            c.drawRightString(largura - 1.5 * cm, altura - 2.7 * cm, f"Entrega: {os_.entrega}")
        c.setFont("Helvetica", 11)
        c.drawRightString(largura - 1.5 * cm, altura - 3.3 * cm, f"Total: {os_.total_pecas} peça(s)")
        y = altura - 3.8 * cm
        if os_.observacoes:
            c.setFillColor(cinza)
            c.drawString(1.5 * cm, y - 0.2 * cm, f"Obs.: {os_.observacoes}")
            c.setFillColor(black)
            y -= 0.7 * cm
        c.line(1.5 * cm, y, largura - 1.5 * cm, y)
        return y - 0.4 * cm

    y = cabecalho()
    alto = 4.2 * cm
    for item, resumo in zip(itens, os_.itens):
        if y - alto < 1.5 * cm:
            c.showPage()
            y = cabecalho()
        x = 1.5 * cm
        for lado in range(len(item.lados)):
            mini = _miniatura(item, lado)
            if mini:
                c.drawImage(mini, x, y - 3.6 * cm, 3.6 * cm, 3.6 * cm, preserveAspectRatio=True)
            c.rect(x, y - 3.6 * cm, 3.6 * cm, 3.6 * cm)
            c.setFont("Helvetica", 7)
            c.drawCentredString(x + 1.8 * cm, y - 3.95 * cm, ("FRENTE", "VERSO")[lado])
            x += 3.9 * cm
        tx = 1.5 * cm + 2 * 3.9 * cm + 0.3 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(tx, y - 0.5 * cm, f"{resumo.quantidade}x  {resumo.produto}")
        c.setFont("Helvetica", 9)
        c.drawString(tx, y - 1.1 * cm, f"Peça {resumo.medida_cm} cm  ·  "
                                       f"{'frente e verso' if resumo.lados == 2 else 'só frente'}  ·  "
                                       f"{resumo.pecas} impressão(ões)")
        c.setFillColor(cinza)
        c.drawString(tx, y - 1.6 * cm, "Arte: " + " / ".join(resumo.artes)[:70])
        c.setFillColor(black)
        for n, etapa in enumerate(("Impresso", "Prensado", "Costurado", "Conferido")):
            bx = tx + n * 2.3 * cm
            c.rect(bx, y - 2.6 * cm, 0.35 * cm, 0.35 * cm)
            c.drawString(bx + 0.5 * cm, y - 2.53 * cm, etapa)
        y -= alto
        c.setStrokeColor(HexColor("#dddddd"))
        c.line(1.5 * cm, y + 0.2 * cm, largura - 1.5 * cm, y + 0.2 * cm)
        c.setStrokeColor(black)
    c.showPage()
    c.save()


def notificar(webhook_url: str, os_: OrdemServico, timeout: float = 10) -> None:
    """POST JSON com a OS e um campo `text`/`content` pronto para exibir."""
    texto = os_.resumo_texto()
    corpo = {"text": texto, "content": texto, "os": asdict(os_), "total_pecas": os_.total_pecas}
    req = urllib.request.Request(
        webhook_url, data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()


def registrar(pasta_os: Path, os_: OrdemServico, itens: list[ItemPedido], csv_origem: Path | None = None) -> Path:
    """Cria a pasta da OS com os.json, a ficha em PDF e a planilha de origem."""
    pasta = pasta_os / os_.numero
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "os.json").write_text(json.dumps(asdict(os_), ensure_ascii=False, indent=2), encoding="utf-8")
    gerar_ficha_pdf(os_, itens, pasta / f"{os_.numero}_ficha.pdf")
    if csv_origem:
        shutil.copy(csv_origem, pasta / f"{os_.numero}_itens.csv")
    return pasta


def agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")
