"""Demonstração com dados fictícios.

    estampa demo [--pasta demo] [--porta 8080]

Cria uma pasta com catálogo, molduras, artes, fotos e planilhas de pedidos
fictícios (Shopee, Mercado Livre, TikTok e clientes locais), roda o fluxo
real — arquivos para o RIP, ordens de serviço e fichas — e abre uma página
para conferir o resultado e testar com as próprias fotos.

Cada linha da planilha de pedidos tem uma coluna `cenario` explicando a
regra que ela exercita (o sistema ignora colunas que não conhece).
"""

from __future__ import annotations

import csv
import json
import math
import random
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import ordem
from .lote import OpcoesExportacao, exportar_itens, ler_pedidos_csv
from .peca import _fonte
from .produtos import CATALOGO_PADRAO, carregar_catalogo

ROSTO = Path(__file__).parent / "demo_dados" / "rosto.jpg"


# ---------------------------------------------------------------- imagens

def _coracao(cx: float, cy: float, escala: float, passos: int = 240) -> list[tuple[float, float]]:
    pontos = []
    for i in range(passos):
        t = 2 * math.pi * i / passos
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pontos.append((cx + x * escala, cy - y * escala))
    return pontos


def _texto(d: ImageDraw.ImageDraw, xy, texto: str, tamanho: int, cor, contorno=None) -> None:
    fonte = _fonte(tamanho)
    d.text(xy, texto, font=fonte, fill=cor, anchor="mm",
           stroke_width=max(2, tamanho // 14) if contorno else 0, stroke_fill=contorno)


def gerar_moldura_coracao(destino: Path, lado: int, titulo: str) -> None:
    """Moldura com um coração transparente (onde entra a foto)."""
    img = Image.new("RGBA", (lado, lado), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    s = lado / 45
    d.polygon(_coracao(lado * 0.5, lado * 0.43, s * 1.15), fill=(205, 20, 40, 255))
    d.polygon(_coracao(lado * 0.5, lado * 0.43, s * 1.02), fill=(240, 210, 150, 255))
    d.polygon(_coracao(lado * 0.5, lado * 0.43, s * 0.97), fill=(0, 0, 0, 0))
    _texto(d, (lado * 0.5, lado * 0.88), titulo, round(lado * 0.09), (205, 20, 40), (255, 255, 255))
    img.save(destino)


def gerar_moldura_casal(destino: Path, lado: int) -> None:
    """Dois corações lado a lado: uma foto em cada."""
    img = Image.new("RGBA", (lado, lado), (250, 244, 236, 255))
    d = ImageDraw.Draw(img)
    s = lado / 75
    for cx in (0.29, 0.71):
        d.polygon(_coracao(lado * cx, lado * 0.45, s * 1.2), fill=(150, 30, 80, 255))
        d.polygon(_coracao(lado * cx, lado * 0.45, s), fill=(0, 0, 0, 0))
    _texto(d, (lado * 0.5, lado * 0.86), "Nosso Amor", round(lado * 0.085), (150, 30, 80), (255, 255, 255))
    img.save(destino)


def gerar_arte(destino: Path, tamanho: tuple[int, int], titulo: str, cores: tuple, semente: int) -> None:
    """Arte "pronta" fictícia: fundo em degradê, formas e um título."""
    rnd = random.Random(semente)
    w, h = tamanho
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    c1, c2 = cores
    for y in range(h):
        t = y / max(1, h - 1)
        d.line((0, y, w, y), fill=tuple(round(a + (b - a) * t) for a, b in zip(c1, c2)))
    for _ in range(18):
        r = rnd.randint(min(w, h) // 20, min(w, h) // 6)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 255, 255), width=max(2, r // 10))
    _texto(d, (w / 2, h / 2), titulo, round(min(w, h) * 0.12), (255, 255, 255), (0, 0, 0))
    img.save(destino, quality=92)


def gerar_foto(destino: Path, tamanho: tuple[int, int], pos: tuple[float, float], escala: float,
               espelhar: bool = False, fundo=(120, 140, 170)) -> None:
    """Foto de "celular" com o rosto fora do centro (para testar o enquadramento)."""
    w, h = tamanho
    foto = Image.new("RGB", tamanho, fundo)
    d = ImageDraw.Draw(foto)
    for y in range(h):
        d.line((0, y, w, y), fill=tuple(max(0, c - y * 60 // h) for c in fundo))
    pessoa = Image.open(ROSTO).convert("RGB")
    if espelhar:
        pessoa = ImageOps.mirror(pessoa)
    lado = round(min(w, h) * escala)
    pessoa = pessoa.resize((lado, lado), Image.Resampling.LANCZOS)
    mascara = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(mascara).ellipse((lado * 0.06, 0, lado * 0.94, lado * 1.2), fill=255)
    foto.paste(pessoa, (round(w * pos[0] - lado / 2), round(h * pos[1] - lado / 2)),
               mascara.filter(ImageFilter.GaussianBlur(lado / 40)))
    foto.save(destino, quality=90)


def gerar_paisagem(destino: Path, tamanho: tuple[int, int]) -> None:
    w, h = tamanho
    img = Image.new("RGB", tamanho, (135, 190, 235))
    d = ImageDraw.Draw(img)
    d.rectangle((0, h * 0.62, w, h), fill=(70, 140, 70))
    d.ellipse((w * 0.7, h * 0.1, w * 0.85, h * 0.1 + w * 0.15), fill=(250, 220, 90))
    img.save(destino, quality=90)


# ---------------------------------------------------------------- planilhas

PEDIDOS = [
    # canal, pedido, produto, qtd, frente, verso, moldura, larg, alt, transferencia, cenario
    ("Shopee", "SHP-250114A1", "almofada-45", 2, "artes/mae.jpg", "artes/flores.jpg", "", "", "", "",
     "Frente e verso, 2 unidades: 4 arquivos, cada um com lado e cópia na margem"),
    ("Shopee", "SHP-250114B7", "almofada-45", 1, "fotos/foto_rosto_direita.jpg", "", "coracao-namorados", "", "", "",
     "Fotomoldura: rosto no canto da foto é centralizado no coração"),
    ("Mercado Livre", "ML-2000012345", "almofada-45", 1, "fotos/casal_ele.jpg|fotos/casal_ela.jpg", "",
     "casal-dois-coracoes", "", "", "", "Moldura de casal: duas fotos, uma em cada coração"),
    ("Mercado Livre", "ML-2000012399", "almofada-45", 1, "fotos/paisagem.jpg", "", "coracao-namorados", "", "", "",
     "Foto sem rosto: centraliza e avisa para conferir"),
    ("TikTok", "TT-5770019", "travesseiro-40x70", 3, "artes/pet.jpg", "", "", "", "", "",
     "Capa de travesseiro 40x70 → peça 42x72, 3 cópias numeradas"),
    ("TikTok", "TT-5770044", "almofada-45", 1, "artes/whatsapp_baixa.jpg", "", "", "", "", "",
     "Arte de WhatsApp em baixa resolução: gera, mas avisa"),
    ("Shopee", "SHP-250114C3", "capa-porta", 1, "artes/porta.jpg", "", "", "100", "190", "",
     "Porta 100x190 + 3 cm de elástico = 106x196: cabe na prensa (auto)"),
    ("Mercado Livre", "ML-2000012777", "capa-porta", 1, "artes/porta.jpg", "", "", "150", "300", "",
     "Porta 150x300 = 156x306: não cabe na prensa, vai para a calandra (auto)"),
    ("Shopee", "SHP-250114D9", "almofada-45", 20, "artes/time.jpg", "", "", "", "", "calandra",
     "Rolo a rolo: 20 almofadas escolhidas para a calandra"),
    ("TikTok", "TT-5770088", "almofada-45", 1, "artes/nao_enviada.jpg", "", "", "", "", "",
     "Arte não recebida: o item falha sozinho e o resto do lote segue"),
]

OS_CLIENTES = [
    ("Ateliê Maria", "16/10", "Separar por cor", "em produção", [
        ("almofada-45", 12, "artes/flores.jpg", "artes/mae.jpg", ""),
        ("travesseiro-40x70", 6, "artes/pet.jpg", "", ""),
    ]),
    ("Festas & Cia", "18/10", "Urgente — feira no sábado", "aberta", [
        ("almofada-45", 30, "artes/time.jpg", "", ""),
        ("capa-porta", 2, "artes/porta.jpg", "", "70x200"),
    ]),
]


def _escrever_planilhas(pasta: Path) -> None:
    with open(pasta / "pedidos_marketplace.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["canal", "pedido", "produto", "quantidade", "arte_frente", "arte_verso", "moldura",
                    "largura_cm", "altura_cm", "transferencia", "cenario"])
        w.writerows(PEDIDOS)
    for n, (cliente, _, _, _, itens) in enumerate(OS_CLIENTES, start=1):
        with open(pasta / f"os_cliente_{n}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["produto", "quantidade", "arte_frente", "arte_verso", "largura_cm", "altura_cm"])
            for produto, qtd, frente, verso, medida in itens:
                larg, alt = medida.split("x") if medida else ("", "")
                w.writerow([produto, qtd, frente, verso, larg, alt])


def _catalogo_demo(pasta: Path) -> Path:
    texto = CATALOGO_PADRAO.read_text(encoding="utf-8")
    destino = pasta / "produtos.toml"
    destino.write_text(texto, encoding="utf-8")
    return destino


# ---------------------------------------------------------------- execução

@dataclass
class ItemDemo:
    canal: str
    pedido: str
    produto: str
    quantidade: int
    lados: int
    equipamento: str
    cenario: str
    arquivos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    erro: str | None = None


def criar_demo(pasta: Path, dpi: int | None = None, processos: int | None = None) -> dict:
    """Gera os dados fictícios e roda o fluxo completo. Devolve o resumo salvo em resultado.json."""
    pasta = pasta.resolve()
    if pasta.exists():
        shutil.rmtree(pasta)
    for sub in ("artes", "fotos", "molduras"):
        (pasta / sub).mkdir(parents=True)

    toml = _catalogo_demo(pasta)
    cat = carregar_catalogo(toml)
    lado_moldura = round(45 / 2.54 * cat.config.dpi)
    gerar_moldura_coracao(pasta / "molduras" / "coracao-namorados.png", lado_moldura, "Te Amo")
    gerar_moldura_casal(pasta / "molduras" / "casal-dois-coracoes.png", lado_moldura)

    gerar_arte(pasta / "artes" / "mae.jpg", (3000, 3000), "MÃE", ((240, 120, 160), (140, 40, 120)), 1)
    gerar_arte(pasta / "artes" / "flores.jpg", (3000, 3000), "FLORES", ((80, 170, 120), (20, 90, 60)), 2)
    gerar_arte(pasta / "artes" / "pet.jpg", (2400, 4200), "MEU PET", ((250, 190, 90), (200, 90, 30)), 3)
    gerar_arte(pasta / "artes" / "time.jpg", (3000, 3000), "CAMPEÃO", ((40, 60, 160), (10, 20, 60)), 4)
    gerar_arte(pasta / "artes" / "porta.jpg", (6000, 12000), "BEM-VINDOS", ((60, 140, 200), (20, 40, 90)), 5)
    gerar_arte(pasta / "artes" / "whatsapp_baixa.jpg", (640, 640), "OI", ((200, 60, 60), (90, 20, 20)), 6)

    gerar_foto(pasta / "fotos" / "foto_rosto_direita.jpg", (2400, 1600), (0.78, 0.42), 0.55)
    gerar_foto(pasta / "fotos" / "casal_ele.jpg", (1600, 2000), (0.4, 0.38), 0.5, fundo=(110, 150, 120))
    gerar_foto(pasta / "fotos" / "casal_ela.jpg", (1600, 2000), (0.6, 0.4), 0.5, espelhar=True, fundo=(170, 130, 150))
    gerar_paisagem(pasta / "fotos" / "paisagem.jpg", (2400, 1600))
    _escrever_planilhas(pasta)

    op = OpcoesExportacao(saida=pasta / "rip", formato="jpg", dpi=cat.config.dpi, dpi_forcado=dpi,
                          borda_mm=cat.config.borda_mm, rosto=cat.config.enquadrar_rosto)
    inicio = time.monotonic()
    planilha = pasta / "pedidos_marketplace.csv"
    with open(planilha, encoding="utf-8") as f:
        extras = {l["pedido"]: l for l in csv.DictReader(f)}
    itens = ler_pedidos_csv(planilha, cat)
    resultados = {r.pedido: r for r in exportar_itens(itens, op, processos)}
    demo_itens = []
    for item in itens:
        r = resultados[item.pedido]
        demo_itens.append(ItemDemo(
            canal=extras[item.pedido]["canal"], pedido=item.pedido, produto=item.produto.nome,
            quantidade=item.quantidade, lados=len(item.lados), equipamento=item.equipamento,
            cenario=extras[item.pedido]["cenario"],
            arquivos=[str(Path(a).relative_to(pasta)) for a in r.arquivos], avisos=r.avisos, erro=r.erro,
        ))
    tempo_lote = time.monotonic() - inicio

    numeros = []
    for n, (cliente, entrega, obs, status, _) in enumerate(OS_CLIENTES, start=1):
        numero = ordem.proximo_numero(cat.os.pasta, cat.os.prefixo)
        csv_os = pasta / f"os_cliente_{n}.csv"
        itens_os = ler_pedidos_csv(csv_os, cat, pedido_padrao=numero)
        arquivos, avisos_os, erros = [], [], []
        for r in exportar_itens(itens_os, op, processos):
            arquivos += r.arquivos
            avisos_os += r.avisos
            if r.erro:
                erros.append(r.erro)
        os_ = ordem.OrdemServico(numero=numero, cliente=cliente, criada_em=ordem.agora(), entrega=entrega,
                                 observacoes=obs, itens=ordem.resumir(itens_os),
                                 arquivos=[str(a) for a in arquivos], avisos=avisos_os, erros=erros)
        ordem.registrar(cat.os.pasta, os_, itens_os, csv_os, op.rosto)
        if status != "aberta":
            ordem.mudar_status(cat.os.pasta, numero, status)
        numeros.append(numero)

    resumo = {
        "gerado_em": ordem.agora(),
        "tempo_lote_s": round(tempo_lote, 1),
        "dpi": dpi or cat.config.dpi,
        "dpi_forcado": dpi,
        "itens": [asdict(i) for i in demo_itens],
        "os": numeros,
    }
    (pasta / "resultado.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumo
