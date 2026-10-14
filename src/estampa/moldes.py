"""Biblioteca de moldes de vestuário (camisetas, regatas, polos...).

Um **modelo** (ex.: camiseta casual) tem uma **grade** de tamanhos (infantil,
feminino, adulto) e, em cada tamanho, as **partes** do molde (frente, costas,
mangas...). Cada parte guarda o contorno em cm, em escala real, e as
**posições de logo** (os marcadores 1 a 4 do modelo do Corel).

Os moldes são importados do PDF exportado pelo CorelDRAW, no layout dos
modelos SpeedCorel: título do tamanho acima de cada coluna, moldes com
preenchimento branco e marcadores de logo escuros com o número dentro.
A biblioteca vira um JSON em `moldes/<modelo>.json`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

PT_PARA_CM = 2.54 / 72

# nomes de tamanho reconhecidos nos títulos das colunas
TAMANHOS_CONHECIDOS = [
    "RN", "BB", "1", "2", "3", "4", "6", "8", "10", "12", "14", "16",
    "BLPP", "BLP", "BLM", "BLG", "BLGG", "BLXG", "BLXGG",
    "PP", "P", "M", "G", "GG", "XG", "XGG", "XXG", "XXGG", "XXXG", "EG", "EGG", "G1", "G2", "G3", "G4",
]
GRADES = ("infantil", "feminino", "adulto")
ORDEM = {t: i for i, t in enumerate(TAMANHOS_CONHECIDOS)}


def grade_do_tamanho(tamanho: str) -> str:
    if tamanho.isdigit() or tamanho in ("RN", "BB"):
        return "infantil"
    if tamanho.startswith("BL"):
        return "feminino"
    return "adulto"


def normalizar_tamanho(texto: str) -> str:
    """'blpp (s)' → 'BLPP'; 'xxxg' → 'XXXG'."""
    t = re.sub(r"\(.*?\)", "", str(texto)).strip().upper().replace(" ", "")
    return t


@dataclass
class Parte:
    largura_cm: float
    altura_cm: float
    contorno: list[tuple[float, float]]          # polígono em cm, origem no canto superior esquerdo
    logos: dict[str, tuple[float, float, float, float]] = field(default_factory=dict)  # slot → (cx, cy, w, h)


@dataclass
class Tamanho:
    nome: str
    grade: str
    partes: dict[str, Parte]


@dataclass
class Modelo:
    codigo: str
    origem: str
    tamanhos: dict[str, Tamanho]

    def tamanho(self, nome: str) -> Tamanho:
        chave = normalizar_tamanho(nome)
        if chave not in self.tamanhos:
            raise ValueError(f"tamanho '{nome}' não existe no modelo {self.codigo} "
                             f"(disponíveis: {', '.join(self.tamanhos)})")
        return self.tamanhos[chave]

    def partes(self) -> list[str]:
        return sorted({p for t in self.tamanhos.values() for p in t.partes})

    def quadro(self, parte: str) -> tuple[float, float]:
        """Maior largura e altura da parte em toda a grade: o "quadro de edição"
        onde a arte do time é feita."""
        medidas = [t.partes[parte] for t in self.tamanhos.values() if parte in t.partes]
        if not medidas:
            raise ValueError(f"o modelo {self.codigo} não tem a parte '{parte}'")
        return max(m.largura_cm for m in medidas), max(m.altura_cm for m in medidas)

    def salvar(self, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(asdict(self), ensure_ascii=False), encoding="utf-8")

    @classmethod
    def carregar(cls, caminho: Path) -> Modelo:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        tamanhos = {}
        for nome, t in dados["tamanhos"].items():
            partes = {p: Parte(v["largura_cm"], v["altura_cm"], [tuple(pt) for pt in v["contorno"]],
                               {k: tuple(l) for k, l in v["logos"].items()}) for p, v in t["partes"].items()}
            tamanhos[nome] = Tamanho(t["nome"], t["grade"], partes)
        return cls(dados["codigo"], dados["origem"], tamanhos)


# ---------------------------------------------------------------- importação do PDF

def _bezier(p0, p1, p2, p3, passos: int = 8):
    for i in range(1, passos + 1):
        t = i / passos
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        yield (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def _poligono(curva: dict) -> list[tuple[float, float]]:
    """Caminho do PDF (m/l/c/h) → lista de pontos em pt, curvas aproximadas por retas."""
    pontos: list[tuple[float, float]] = []
    for cmd, *pts in curva["path"]:
        if cmd in ("m", "l"):
            pontos.append(pts[0])
        elif cmd == "c" and pontos:
            pontos.extend(_bezier(pontos[-1], *pts))
    return pontos


def _cinza(cor) -> float | None:
    if cor is None or isinstance(cor, str):
        return None
    cor = tuple(cor) if isinstance(cor, (list, tuple)) else (cor,)
    return sum(cor[:3]) / len(cor[:3]) if cor else None


def _dentro(a, b, folga: float = 2.0) -> bool:
    return a["x0"] >= b["x0"] - folga and a["x1"] <= b["x1"] + folga and \
        a["top"] >= b["top"] - folga and a["bottom"] <= b["bottom"] + folga


def _slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-") or "modelo"


def importar_pdf(caminho: Path | str, codigo: str | None = None, largura_min_cm: float = 5.0) -> Modelo:
    """Lê um PDF de moldes no layout SpeedCorel e monta a biblioteca do modelo.

    Regras do layout:
    - molde = forma com linha de contorno (o preenchimento pode ter qualquer
      cor); marcador de logo = forma escura sem contorno dentro dele, com o
      número (1-4) escrito;
    - o tamanho de cada molde é o título de tamanho mais próximo acima da coluna;
    - parte: 2 marcadores = frente, nenhum = costas, 1 = manga (a mais alta é a
      longa); frentes diferentes na mesma coluna: a de cima é gola careca, a de
      baixo gola V; mangas: a da esquerda (marcador 3) é a esquerda.
    """
    import pdfplumber

    caminho = Path(caminho)
    with pdfplumber.open(caminho) as pdf:
        pg = pdf.pages[0]
        curvas = list(pg.curves) + list(pg.rects)
        palavras = pg.extract_words(keep_blank_chars=False)

    moldes, vistos = [], set()
    for c in curvas:
        if not (c.get("stroke") and c.get("path") and len(c["path"]) > 8
                and (c["x1"] - c["x0"]) * PT_PARA_CM >= largura_min_cm):
            continue
        chave = tuple(round(c[k]) for k in ("x0", "top", "x1", "bottom"))
        if chave not in vistos:  # o mesmo contorno pode vir repetido
            vistos.add(chave)
            moldes.append(c)
    # marcadores de logo: formas escuras de alguns cm (as letras das etiquetas em curva têm ~0,5 cm)
    marcadores = [c for c in curvas if c.get("fill") and (g := _cinza(c.get("non_stroking_color"))) is not None
                  and g < 0.3 and c.get("path") and (c["x1"] - c["x0"]) * PT_PARA_CM >= 2.0]
    if not moldes:
        raise ValueError(f"{caminho.name}: nenhum molde encontrado (formas com linha de contorno)")

    topo = min(m["top"] for m in moldes)
    titulos = []
    for w in palavras:
        t = normalizar_tamanho(w["text"])
        if t == "BLX":
            t = "BLXG"
        if t in ORDEM and w["bottom"] <= topo + 1:
            titulos.append((t, (w["x0"] + w["x1"]) / 2, w["top"]))
    if not titulos:
        raise ValueError(f"{caminho.name}: nenhum título de tamanho (ex.: P, M, G, BLM, 10) acima dos moldes")
    # num PDF de um tamanho só (título grande no topo), todo molde é daquele tamanho
    def tamanho_de(m) -> str:
        cx = (m["x0"] + m["x1"]) / 2
        return min(titulos, key=lambda t: abs(t[1] - cx))[0]

    por_tamanho: dict[str, list[dict]] = {}
    for m in moldes:
        x0, top = m["x0"], m["top"]
        pontos = [((x - x0) * PT_PARA_CM, (y - top) * PT_PARA_CM) for x, y in _poligono(m)]
        logos = {}
        for n, mk in enumerate(sorted((k for k in marcadores if _dentro(k, m) and (k["x1"] - k["x0"]) < (m["x1"] - m["x0"]) * 0.6),
                                      key=lambda k: k["x0"]), start=1):
            nums = [w["text"] for w in palavras if _dentro(w, mk, 1) and w["text"] in ("1", "2", "3", "4")]
            slot = nums[0] if nums else str(n)
            logos[slot] = (round(((mk["x0"] + mk["x1"]) / 2 - x0) * PT_PARA_CM, 2),
                           round(((mk["top"] + mk["bottom"]) / 2 - top) * PT_PARA_CM, 2),
                           round((mk["x1"] - mk["x0"]) * PT_PARA_CM, 2), round((mk["bottom"] - mk["top"]) * PT_PARA_CM, 2))
        por_tamanho.setdefault(tamanho_de(m), []).append({
            "x": x0, "y": top, "parte": Parte(round((m["x1"] - x0) * PT_PARA_CM, 2),
                                              round((m["bottom"] - top) * PT_PARA_CM, 2),
                                              [(round(x, 2), round(y, 2)) for x, y in pontos], logos)})

    tamanhos = {}
    for nome, itens in sorted(por_tamanho.items(), key=lambda kv: ORDEM.get(kv[0], 99)):
        partes: dict[str, Parte] = {}
        frentes = sorted((i for i in itens if len(i["parte"].logos) >= 2), key=lambda i: i["y"])
        costas = [i for i in itens if not i["parte"].logos]
        mangas = [i for i in itens if len(i["parte"].logos) == 1]
        for nome_parte, f in zip(("frente_careca", "frente_v", "frente_3"), frentes):
            partes[nome_parte] = f["parte"]
        if costas:
            partes["costas"] = max(costas, key=lambda c: c["parte"].altura_cm)["parte"]
        if mangas:
            alta = max(m["parte"].altura_cm for m in mangas)
            for m in mangas:
                tipo = "longa" if m["parte"].altura_cm > alta * 0.75 else "curta"
                lado = "esq" if "3" in m["parte"].logos else "dir" if "4" in m["parte"].logos else None
                if lado is None:
                    lado = "esq" if not any(o is not m and o["x"] < m["x"] and abs(o["parte"].altura_cm - m["parte"].altura_cm) < 1
                                            for o in mangas) else "dir"
                partes.setdefault(f"manga_{tipo}_{lado}", m["parte"])
        tamanhos[nome] = Tamanho(nome, grade_do_tamanho(nome), partes)
    return Modelo(codigo or _slug(caminho.stem), caminho.name, tamanhos)


# ---------------------------------------------------------------- prévia

ORDEM_PARTES = ["frente_careca", "frente_v", "costas", "manga_curta_esq", "manga_curta_dir",
                "manga_longa_esq", "manga_longa_dir"]


def desenhar_previa(modelo: Modelo, destino: Path, tamanhos: list[str] | None = None, px_por_cm: float = 4) -> None:
    """Folha com os contornos e os marcadores de logo, um tamanho por linha (para conferir a importação)."""
    from PIL import Image, ImageDraw

    from .peca import _fonte

    nomes = [normalizar_tamanho(t) for t in tamanhos] if tamanhos else list(modelo.tamanhos)
    linhas = [modelo.tamanho(n) for n in nomes]
    partes = [p for p in ORDEM_PARTES if any(p in t.partes for t in linhas)] + \
             sorted({p for t in linhas for p in t.partes} - set(ORDEM_PARTES))
    larg = {p: max((t.partes[p].largura_cm for t in linhas if p in t.partes), default=0) for p in partes}
    alt = [max(v.altura_cm for v in t.partes.values()) for t in linhas]
    margem, rotulo = 4, 12
    W = round((sum(larg.values()) + margem * (len(partes) + 1) + rotulo) * px_por_cm)
    H = round((sum(alt) + margem * (len(linhas) + 2)) * px_por_cm)
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_tit, f_peq = _fonte(round(3.5 * px_por_cm)), _fonte(round(1.6 * px_por_cm))
    x = (rotulo + margem) * px_por_cm
    for p in partes:
        d.text((x + larg[p] * px_por_cm / 2, margem * px_por_cm * 0.6), p, fill="#444", font=f_peq, anchor="mm")
        x += (larg[p] + margem) * px_por_cm
    y = margem * 1.5 * px_por_cm
    for t, h in zip(linhas, alt):
        d.text((margem * px_por_cm, y + h * px_por_cm / 2), t.nome, fill="black", font=f_tit, anchor="lm")
        x = (rotulo + margem) * px_por_cm
        for p in partes:
            if p in t.partes:
                parte = t.partes[p]
                ox = x + (larg[p] - parte.largura_cm) / 2 * px_por_cm
                pts = [(ox + a * px_por_cm, y + b * px_por_cm) for a, b in parte.contorno]
                d.polygon(pts, fill="#e9e9e9", outline="#333")
                for slot, (cx, cy, w, hh) in parte.logos.items():
                    cx, cy = ox + cx * px_por_cm, y + cy * px_por_cm
                    d.ellipse((cx - w * px_por_cm / 2, cy - hh * px_por_cm / 2, cx + w * px_por_cm / 2, cy + hh * px_por_cm / 2), fill="#333")
                    d.text((cx, cy), slot, fill="white", font=f_peq, anchor="mm")
            x += (larg[p] + margem) * px_por_cm
        y += (h + margem) * px_por_cm
    img.save(destino)
