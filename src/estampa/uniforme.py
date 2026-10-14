"""Uniformes: a arte do time em todos os tamanhos, com nome e número de cada jogador.

Como no modelo do Corel, a arte de cada parte (frente, costas, mangas) é feita
uma vez, no **quadro de edição** — do tamanho do maior molde da grade. Cada
molde recorta o seu pedaço da arte **na escala real**, sem esticar: um P e um
XGG mostram o mesmo desenho, só que o XGG mostra mais dele.

Por cima entram os elementos posicionados:
- logos 1 a 4 nos marcadores do molde (peito direito/esquerdo, mangas), com o
  tamanho que o molde define para cada tamanho;
- elementos configurados em [uniformes.elementos] (nome, número, patrocínios),
  com posição relativa à peça e tamanho em cm por grade (infantil/feminino/adulto).

Cada peça sai como um arquivo para o RIP, com a linha de corte e uma etiqueta
(pedido, tamanho, parte, número e nome) dentro da peça.
"""

from __future__ import annotations

import csv
import functools
import multiprocessing
import os
import re
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .imagem import SRGB_ICC, carregar_rgb, cm_para_px, enquadrar
from .lote import PASTA_GRAVANDO, publicar
from .moldes import Modelo, Parte, normalizar_tamanho
from .peca import _fonte

Image.MAX_IMAGE_PIXELS = None

LADOS_ARTE = ("frente", "costas", "manga_esq", "manga_dir")


# ---------------------------------------------------------------- configuração

@dataclass(frozen=True)
class Elemento:
    nome: str
    tipo: str                         # "nome" | "numero" | "imagem"
    parte: str                        # "frente", "costas", "manga_esq"... (prefixo da parte do molde)
    centro: tuple[float, float]       # fração da largura e da altura da peça
    altura_cm: dict[str, float] = field(default_factory=dict)   # por grade (texto)
    largura_cm: dict[str, float] = field(default_factory=dict)  # por grade (imagem: caixa)
    largura_max: float = 0.85         # texto: fração máxima da largura da peça
    ativo: bool = True

    def medida(self, tabela: dict[str, float], grade: str) -> float | None:
        return tabela.get(grade, tabela.get("adulto"))


ELEMENTOS_PADRAO = {
    "nome": Elemento("nome", "nome", "costas", (0.5, 0.20), {"infantil": 3.5, "feminino": 4.0, "adulto": 5.0},
                     largura_max=0.75),
    "numero": Elemento("numero", "numero", "costas", (0.5, 0.44), {"infantil": 15, "feminino": 18, "adulto": 22}),
    "numero_frente": Elemento("numero_frente", "numero", "frente", (0.5, 0.45),
                              {"infantil": 6, "feminino": 7, "adulto": 9}, ativo=False),
    "patrocinio_costas_topo": Elemento("patrocinio_costas_topo", "imagem", "costas", (0.5, 0.10),
                                       {"infantil": 4, "feminino": 5, "adulto": 6},
                                       {"infantil": 16, "feminino": 20, "adulto": 24}),
    "patrocinio_costas_base": Elemento("patrocinio_costas_base", "imagem", "costas", (0.5, 0.80),
                                       {"infantil": 5, "feminino": 6, "adulto": 7},
                                       {"infantil": 16, "feminino": 20, "adulto": 26}),
}


@dataclass(frozen=True)
class ConfigUniformes:
    pasta_moldes: Path = Path("moldes")
    transferencia: str = "calandra"
    alinhamento: str = "topo"         # como o molde se encaixa no quadro: topo | centro
    contorno_mm: float = 0.5
    cor_contorno: str = "#000000"
    fonte: str = ""                   # TTF dos nomes/números (vazio = padrão)
    cor_texto: str = "#FFFFFF"
    cor_contorno_texto: str = "#000000"
    contorno_texto_mm: float = 1.2
    nome_maiusculo: bool = True
    elementos: tuple[Elemento, ...] = tuple(ELEMENTOS_PADRAO.values())


def carregar_config(dados: dict, base: Path) -> ConfigUniformes:
    dados = dict(dados)
    elementos = dict(ELEMENTOS_PADRAO)
    for nome, e in dados.pop("elementos", {}).items():
        atual = elementos.get(nome)
        campos = {"tipo": "imagem", **({} if atual is None else atual.__dict__), **e, "nome": nome}
        campos["centro"] = tuple(campos.get("centro", (0.5, 0.5)))
        for k in ("altura_cm", "largura_cm"):
            v = campos.get(k, {})
            campos[k] = v if isinstance(v, dict) else {"infantil": v, "feminino": v, "adulto": v}
        elementos[nome] = Elemento(**campos)
    if "pasta_moldes" in dados:
        dados["pasta_moldes"] = base / dados["pasta_moldes"]
    else:
        dados["pasta_moldes"] = base / "moldes"
    return ConfigUniformes(elementos=tuple(elementos.values()), **dados)


# ---------------------------------------------------------------- jogadores

@dataclass(frozen=True)
class Jogador:
    nome: str
    numero: str
    tamanho: str
    quantidade: int = 1


def _coluna(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().strip().lower()
    t = {"qtd": "quantidade", "qtde": "quantidade", "quant": "quantidade", "num": "numero", "n": "numero"}.get(t, t)
    return t[:-1] if t.endswith("s") and t[:-1] in ("nome", "numero", "tamanho") else t


def ler_jogadores(caminho: Path | str, tamanho_padrao: str | None = None) -> list[Jogador]:
    """Planilha (XLSX ou CSV) com Nome, Número e, se tiver, Tamanho e Quantidade.

    Aceita a planilha do modelo SpeedCorel (só Nomes e Números): o tamanho vem
    de `tamanho_padrao`. Números ficam como texto, para manter o zero à esquerda.
    """
    caminho = Path(caminho)
    if caminho.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        planilha = openpyxl.load_workbook(caminho, read_only=True, data_only=True).worksheets[0]
        linhas = [list(r) for r in planilha.iter_rows(values_only=True)]
    else:
        with open(caminho, newline="", encoding="utf-8-sig") as f:
            amostra = f.read(2048)
            f.seek(0)
            linhas = list(csv.reader(f, delimiter=";" if amostra.count(";") > amostra.count(",") else ","))
    if not linhas:
        raise ValueError(f"{caminho.name}: planilha vazia")
    cab = [_coluna(c) for c in linhas[0]]
    if "nome" not in cab and "numero" not in cab:
        raise ValueError(f"{caminho.name}: a primeira linha precisa ter as colunas Nome e Número")
    idx = {c: i for i, c in enumerate(cab) if c}

    def valor(linha, coluna):
        i = idx.get(coluna)
        if i is None or i >= len(linha) or linha[i] is None:
            return ""
        v = linha[i]
        return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()

    jogadores = []
    for n, linha in enumerate(linhas[1:], start=2):
        nome, numero = valor(linha, "nome"), valor(linha, "numero")
        if not nome and not numero:
            continue
        tamanho = valor(linha, "tamanho") or tamanho_padrao
        if not tamanho:
            raise ValueError(f"linha {n} ({nome or numero}): sem tamanho — inclua a coluna Tamanho ou use --tamanho")
        qtd = valor(linha, "quantidade")
        jogadores.append(Jogador(nome, numero, normalizar_tamanho(tamanho), int(float(qtd)) if qtd else 1))
    return jogadores


# ---------------------------------------------------------------- pedido de uniforme

@dataclass(frozen=True)
class PedidoUniforme:
    pedido: str
    modelo: Path                      # JSON da biblioteca de moldes
    artes: dict[str, Path]            # frente / costas / manga_esq / manga_dir
    logos: dict[str, Path] = field(default_factory=dict)      # "1".."4"
    imagens: dict[str, Path] = field(default_factory=dict)    # elementos do tipo imagem (patrocínios)
    manga: str = "curta"              # curta | longa | sem (regata)
    gola: str = "careca"              # careca | v
    numero_frente: bool = False

    def partes(self, modelo: Modelo, tamanho: str) -> list[tuple[str, str]]:
        """(parte do molde, lado da arte) que formam a peça."""
        partes = modelo.tamanho(tamanho).partes
        frente = f"frente_{self.gola}" if f"frente_{self.gola}" in partes else next(
            (p for p in partes if p.startswith("frente")), None)
        lista = [(frente, "frente"), ("costas", "costas")]
        if self.manga != "sem":
            lista += [(f"manga_{self.manga}_esq", "manga_esq"), (f"manga_{self.manga}_dir", "manga_dir")]
        faltando = [p for p, _ in lista if p is None or p not in partes]
        if faltando:
            raise ValueError(f"o tamanho {tamanho} do modelo {modelo.codigo} não tem: {', '.join(map(str, faltando))}")
        return lista


@functools.lru_cache(maxsize=4)
def _modelo(caminho: str) -> Modelo:
    return Modelo.carregar(Path(caminho))


@functools.lru_cache(maxsize=16)
def _arte_no_quadro(caminho: str, largura_cm: float, altura_cm: float, dpi: int) -> Image.Image:
    """Arte do time ajustada ao quadro de edição, sem distorcer (corte pelo centro)."""
    img = enquadrar(carregar_rgb(caminho), largura_cm / altura_cm)
    return img.resize((cm_para_px(largura_cm, dpi), cm_para_px(altura_cm, dpi)), Image.Resampling.LANCZOS)


@functools.lru_cache(maxsize=32)
def _imagem_rgba(caminho: str) -> Image.Image:
    from PIL import ImageOps
    return ImageOps.exif_transpose(Image.open(caminho)).convert("RGBA")


@functools.lru_cache(maxsize=8)
def _fonte_texto(caminho: str, tamanho: int) -> ImageFont.FreeTypeFont:
    if caminho:
        return ImageFont.truetype(caminho, tamanho)
    return _fonte(tamanho)


def _mascara(parte: Parte, dpi: int) -> Image.Image:
    """Máscara do molde com borda suave (desenhada em 2x e reduzida)."""
    w, h = cm_para_px(parte.largura_cm, dpi), cm_para_px(parte.altura_cm, dpi)
    k = 2 * dpi / 2.54
    grande = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(grande).polygon([(x * k, y * k) for x, y in parte.contorno], fill=255)
    return grande.resize((w, h), Image.Resampling.BOX)


def _colar_contido(base: Image.Image, img: Image.Image, cx: float, cy: float, w: float, h: float) -> None:
    """Cola a imagem dentro da caixa (w x h px) centrada em (cx, cy), sem esticar."""
    escala = min(w / img.width, h / img.height)
    nova = img.resize((max(1, round(img.width * escala)), max(1, round(img.height * escala))), Image.Resampling.LANCZOS)
    base.alpha_composite(nova, (round(cx - nova.width / 2), round(cy - nova.height / 2)))


def _texto(base: Image.Image, texto: str, cx: float, cy: float, altura_px: int, largura_max_px: int,
           cfg: ConfigUniformes, dpi: int) -> None:
    if not texto:
        return
    contorno = max(1, cm_para_px(cfg.contorno_texto_mm / 10, dpi))
    tamanho = altura_px
    fonte = _fonte_texto(cfg.fonte, tamanho)
    caixa = ImageDraw.Draw(base).textbbox((0, 0), texto, font=fonte, stroke_width=contorno)
    alt_real, larg = caixa[3] - caixa[1], caixa[2] - caixa[0]
    # a altura pedida é a altura visível dos algarismos/letras; nome comprido encolhe para caber
    fator = min(altura_px / max(1, alt_real), largura_max_px / max(1, larg))
    tamanho = max(8, round(tamanho * fator))
    fonte = _fonte_texto(cfg.fonte, tamanho)
    ImageDraw.Draw(base).text((cx, cy), texto, font=fonte, fill=cfg.cor_texto, anchor="mm",
                              stroke_width=contorno, stroke_fill=cfg.cor_contorno_texto)


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-") or "sem-nome"


def nome_arquivo(pedido: str, jogador: Jogador, parte: str, copia: int = 1) -> str:
    base = f"uniforme_{pedido}_{jogador.tamanho}_{jogador.numero or 'sn'}-{_slug(jogador.nome)}_{parte}"
    return base + (f"_{copia}de{jogador.quantidade}" if jogador.quantidade > 1 else "")


def renderizar_parte(ped: PedidoUniforme, jogador: Jogador, parte_molde: str, lado: str,
                     cfg: ConfigUniformes, dpi: int, copia: int = 1) -> Image.Image:
    modelo = _modelo(str(ped.modelo))
    tam = modelo.tamanho(jogador.tamanho)
    parte = tam.partes[parte_molde]
    w, h = cm_para_px(parte.largura_cm, dpi), cm_para_px(parte.altura_cm, dpi)
    k = dpi / 2.54
    peca = Image.new("RGBA", (w, h), (255, 255, 255, 0))

    if lado in ped.artes:
        qw, qh = modelo.quadro(parte_molde)
        quadro = _arte_no_quadro(str(ped.artes[lado]), qw, qh, dpi)
        x0 = (quadro.width - w) // 2
        y0 = 0 if cfg.alinhamento == "topo" else (quadro.height - h) // 2
        peca.paste(quadro.crop((x0, y0, x0 + w, y0 + h)), (0, 0))
    else:
        peca.paste((255, 255, 255, 255), (0, 0, w, h))

    for slot, (cx, cy, lw, lh) in parte.logos.items():
        if slot in ped.logos:
            _colar_contido(peca, _imagem_rgba(str(ped.logos[slot])), cx * k, cy * k, lw * k, lh * k)

    for e in cfg.elementos:
        if not lado.startswith(e.parte) and not parte_molde.startswith(e.parte):
            continue
        cx, cy = e.centro[0] * w, e.centro[1] * h
        if e.tipo == "imagem" and e.nome in ped.imagens:
            caixa_w = (e.medida(e.largura_cm, tam.grade) or parte.largura_cm * 0.5) * k
            caixa_h = (e.medida(e.altura_cm, tam.grade) or caixa_w / k * 0.4) * k
            _colar_contido(peca, _imagem_rgba(str(ped.imagens[e.nome])), cx, cy, caixa_w, caixa_h)
        elif e.tipo in ("nome", "numero"):
            ativo = ped.numero_frente if e.nome == "numero_frente" else e.ativo
            texto = jogador.nome.upper() if (e.tipo == "nome" and cfg.nome_maiusculo) else (
                jogador.nome if e.tipo == "nome" else jogador.numero)
            if ativo:
                _texto(peca, texto, cx, cy, round((e.medida(e.altura_cm, tam.grade) or 5) * k),
                       round(w * e.largura_max), cfg, dpi)

    # etiqueta de identificação, pequena, perto da barra (como as do modelo do Corel)
    etiqueta = f"{ped.pedido}  {tam.nome}  {parte_molde.upper().replace('_', ' ')}  {jogador.numero} {jogador.nome}".strip()
    if jogador.quantidade > 1:
        etiqueta += f"  {copia}/{jogador.quantidade}"
    fonte = _fonte(max(8, round(0.45 * k)))
    ImageDraw.Draw(peca).text((w / 2, h - 1.6 * k), etiqueta, font=fonte, fill="#222222", anchor="mm",
                              stroke_width=max(1, round(0.06 * k)), stroke_fill="#FFFFFF")

    mascara = _mascara(parte, dpi)
    final = Image.new("RGB", (w, h), "white")
    final.paste(peca.convert("RGB"), (0, 0), mascara)
    linha = max(1, cm_para_px(cfg.contorno_mm / 10, dpi))
    ImageDraw.Draw(final).line([(x * k, y * k) for x, y in parte.contorno + parte.contorno[:1]],
                               fill=cfg.cor_contorno, width=linha, joint="curve")
    return final


@dataclass
class ResultadoJogador:
    jogador: Jogador
    arquivos: list[Path] = field(default_factory=list)
    erro: str | None = None


def exportar_jogador(ped: PedidoUniforme, jogador: Jogador, cfg: ConfigUniformes, dpi: int,
                     pasta: Path, formato: str = "png") -> ResultadoJogador:
    """Todas as partes de um jogador, entregues juntas na pasta do RIP."""
    r = ResultadoJogador(jogador)
    try:
        modelo = _modelo(str(ped.modelo))
        partes = ped.partes(modelo, jogador.tamanho)

        def gravar(temporaria: Path) -> list[str]:
            nomes = []
            for copia in range(1, jogador.quantidade + 1):
                for parte_molde, lado in partes:
                    img = renderizar_parte(ped, jogador, parte_molde, lado, cfg, dpi, copia)
                    nome = f"{nome_arquivo(ped.pedido, jogador, parte_molde, copia)}.{formato}"
                    if formato == "jpg":
                        img.save(temporaria / nome, "JPEG", quality=95, subsampling=0, dpi=(dpi, dpi), icc_profile=SRGB_ICC)
                    else:
                        img.save(temporaria / nome, "PNG", compress_level=1, dpi=(dpi, dpi), icc_profile=SRGB_ICC)
                    nomes.append(nome)
            return nomes

        r.arquivos = publicar(pasta, gravar)
    except FileNotFoundError as e:
        r.erro = f"arquivo não encontrado: {Path(e.filename or '').name or e}"
    except ValueError as e:
        r.erro = str(e)
    except Exception as e:  # noqa: BLE001
        r.erro = f"{type(e).__name__}: {e}"
    return r


def exportar_time(ped: PedidoUniforme, jogadores: list[Jogador], cfg: ConfigUniformes, dpi: int,
                  pasta: Path, formato: str = "png", processos: int | None = None):
    """Gera as peças de todos os jogadores, em paralelo."""
    modelo = _modelo(str(ped.modelo))
    for j in jogadores:  # erro de tamanho aparece antes de gastar tempo gerando
        modelo.tamanho(j.tamanho)
    pasta.mkdir(parents=True, exist_ok=True)
    processos = min(processos or os.cpu_count() or 1, max(1, len(jogadores)))
    if processos == 1:
        for j in jogadores:
            yield exportar_jogador(ped, j, cfg, dpi, pasta, formato)
        return
    with ProcessPoolExecutor(max_workers=processos, mp_context=multiprocessing.get_context("spawn")) as pool:
        n = len(jogadores)
        yield from pool.map(exportar_jogador, [ped] * n, jogadores, [cfg] * n, [dpi] * n, [pasta] * n, [formato] * n)
