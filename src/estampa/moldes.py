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


NOMES_PADRAO = {
    "adulto": ["PP", "P", "M", "G", "GG", "XG", "EXG", "EXGG"],
    "infantil": ["2", "4", "6", "8", "10", "12", "14", "16"],
    "feminino": ["BLPP", "BLP", "BLM", "BLG", "BLGG", "BLXG", "BLXGG"],
}
PALAVRAS_GRADE = {"INFANTIL": "infantil", "KIDS": "infantil", "MULHER": "feminino", "FEMININO": "feminino",
                  "FEMININA": "feminino", "BABY": "feminino", "HOMEM": "adulto", "MASCULINO": "adulto",
                  "UNISSEX": "adulto", "ADULTO": "adulto"}


def _nomes_ancorados(grade: str, escritos: list[str | None]) -> list[str]:
    """Nomes por ordem; se alguma peça traz o tamanho escrito (ex.: "FEM. P"), alinha a lista por ele."""
    n = len(escritos)
    for lista in (NOMES_PADRAO[grade], NOMES_PADRAO["adulto"], NOMES_PADRAO["feminino"], NOMES_PADRAO["infantil"]):
        for i, e in enumerate(escritos):
            if e and e in lista:
                inicio = lista.index(e) - i
                if inicio >= 0 and inicio + n <= len(lista) and all(
                        x is None or x == lista[inicio + k] for k, x in enumerate(escritos)):
                    return lista[inicio:inicio + n]
    return nomes_padrao(grade, n)


def nomes_padrao(grade: str, n: int) -> list[str]:
    """Nomes por ordem de tamanho (menor → maior) quando o PDF não traz o texto dos tamanhos."""
    lista = NOMES_PADRAO[grade]
    if grade == "infantil":
        return lista[-n:] if n <= len(lista) else [f"T{i}" for i in range(1, n + 1)]
    if grade == "feminino" and n <= 4:
        return ["BLP", "BLM", "BLG", "BLGG"][:n]
    return lista[:n] if n <= len(lista) else lista + [f"T{i}" for i in range(len(lista) + 1, n + 1)]


def _retangulo(c: dict) -> bool:
    """Retângulo alinhado (molduras, faixas): todos os pontos nos cantos da caixa."""
    pts = [p for cmd, *ps in c["path"] for p in ps]
    tol = 0.5
    return all((abs(x - c["x0"]) < tol or abs(x - c["x1"]) < tol) and
               (abs(y - c["top"]) < tol or abs(y - c["bottom"]) < tol) for x, y in pts)


def _ler_pdf(caminho: Path, largura_min_cm: float):
    import pdfplumber

    with pdfplumber.open(caminho) as pdf:
        pg = pdf.pages[0]
        curvas = list(pg.curves) + list(pg.rects)
        palavras = pg.extract_words(keep_blank_chars=False)

    # peça = forma (com contorno ou só preenchida) de alguns cm que não seja retângulo
    candidatos, vistos = [], set()
    for c in curvas:
        if not ((c.get("stroke") or c.get("fill")) and c.get("path") and len(c["path"]) >= 4
                and (c["x1"] - c["x0"]) * PT_PARA_CM >= largura_min_cm) or _retangulo(c):
            continue
        chave = tuple(round(c[k]) for k in ("x0", "top", "x1", "bottom"))
        if chave not in vistos:  # preenchimento e contorno da mesma peça vêm separados
            vistos.add(chave)
            candidatos.append(c)
    # o que está dentro de outra peça é decoração (marcador, faixa de punho, etiqueta em
    # curva, linha de costura): fica só a peça de fora
    area = lambda c: (c["x1"] - c["x0"]) * (c["bottom"] - c["top"])
    moldes = [b for b in candidatos if not any(
        a is not b and _dentro(b, a, 0.5 / PT_PARA_CM) and area(b) < area(a) for a in candidatos)]
    marcadores = [c for c in curvas if c.get("fill") and _tipo_marcador(c.get("non_stroking_color"))
                  and c.get("path") and 2.0 <= (c["x1"] - c["x0"]) * PT_PARA_CM <= 25]
    return moldes, marcadores, palavras


def _tipo_marcador(cor) -> str | None:
    """Cinza-escuro = logos 1-4; azul-marinho = perna direita do short; vermelho = perna esquerda."""
    if not isinstance(cor, (list, tuple)) or len(cor) < 3:
        return "logo" if isinstance(cor, (int, float)) and cor < 0.3 else None
    r, g, b = cor[:3]
    if max(r, g, b) - min(r, g, b) < 0.06 and (r + g + b) / 3 < 0.3:
        return "logo"
    if b > 0.3 and r < 0.15 and g < 0.15:
        return "direita"
    if r > 0.7 and g < 0.4 and b < 0.4:
        return "esquerda"
    return None


def _peca(m, marcadores, palavras) -> dict:
    x0, top = m["x0"], m["top"]
    pontos = [((x - x0) * PT_PARA_CM, (y - top) * PT_PARA_CM) for x, y in _poligono(m)]
    logos = {}
    dentro = sorted((k for k in marcadores if _dentro(k, m) and (k["x1"] - k["x0"]) < (m["x1"] - m["x0"]) * 0.6),
                    key=lambda k: k["x0"])
    contagem = {"logo": 0, "direita": 0, "esquerda": 0}
    for mk in dentro:
        tipo = _tipo_marcador(mk.get("non_stroking_color"))
        contagem[tipo] += 1
        if tipo == "logo":
            nums = [w["text"] for w in palavras if _dentro(w, mk, 1) and w["text"] in ("1", "2", "3", "4")]
            slot = nums[0] if nums else str(contagem["logo"])
        else:  # short: D1, D2 (perna direita) / E1, E2 (perna esquerda), da esquerda para a direita
            slot = f"{tipo[0].upper()}{contagem[tipo]}"
        logos[slot] = (round(((mk["x0"] + mk["x1"]) / 2 - x0) * PT_PARA_CM, 2),
                       round(((mk["top"] + mk["bottom"]) / 2 - top) * PT_PARA_CM, 2),
                       round((mk["x1"] - mk["x0"]) * PT_PARA_CM, 2), round((mk["bottom"] - mk["top"]) * PT_PARA_CM, 2))
    parte = Parte(round((m["x1"] - x0) * PT_PARA_CM, 2), round((m["bottom"] - top) * PT_PARA_CM, 2),
                  [(round(x, 2), round(y, 2)) for x, y in pontos], logos)
    return {"x": x0, "y": top, "parte": parte}


def _classificar(itens: list[dict], raglan: bool = False) -> dict[str, Parte]:
    """Nomeia as partes de um tamanho.

    2 marcadores = frente (a de cima gola careca, a de baixo gola V; só uma = "frente");
    nenhum = costas, ou gola se for uma faixa (bem mais larga que alta);
    1 marcador = manga (3 = esquerda, 4 = direita): alturas bem diferentes = longa
    e curta; parecidas = curta e curta com barra (a de baixo); raglan = manga_raglan.
    """
    partes: dict[str, Parte] = {}
    numericos = lambda i: [k for k in i["parte"].logos if k.isdigit()]
    perna = lambda i: "dir" if any(k.startswith("D") for k in i["parte"].logos) else (
        "esq" if any(k.startswith("E") for k in i["parte"].logos) else None)
    shorts = [i for i in itens if perna(i)]
    for lado in ("dir", "esq"):
        pecas = sorted((i for i in shorts if perna(i) == lado), key=lambda i: i["x"])
        sufixos = [""] if len(pecas) == 1 else [f"_{c}" for c in "abcdef"]
        for suf, i in zip(sufixos, pecas):
            partes[f"short_{lado}{suf}"] = i["parte"]
    itens = [i for i in itens if not perna(i)]
    # faixas estreitas sem logo (faixa lateral do short, vivo da regata)
    estreitas = [i for i in itens if not i["parte"].logos and i["parte"].largura_cm < 0.3 * i["parte"].altura_cm]
    centro = lambda i: i["x"] + i["parte"].largura_cm / PT_PARA_CM / 2
    vivos = 0
    for i in sorted(estreitas, key=lambda i: i["x"]):
        if shorts and min(s["x"] for s in shorts) <= centro(i) <= max(centro(s) * 2 - s["x"] for s in shorts):
            perto = min(shorts, key=lambda s: abs(centro(s) - centro(i)))
            nome = f"short_faixa_{perna(perto)}"
            n = 2
            while nome in partes:
                nome, n = f"short_faixa_{perna(perto)}_{n}", n + 1
            partes[nome] = i["parte"]
        else:
            vivos += 1
            partes[f"vivo_{vivos}"] = i["parte"]
    itens = [i for i in itens if i not in estreitas]
    frentes = sorted((i for i in itens if len(numericos(i)) >= 2), key=lambda i: i["y"])
    if len(frentes) == 1:
        partes["frente"] = frentes[0]["parte"]
    else:
        for nome, f in zip(("frente_careca", "frente_v", "frente_3"), frentes):
            partes[nome] = f["parte"]
    sem_logo = [i for i in itens if not i["parte"].logos]
    golas = [i for i in sem_logo if i["parte"].largura_cm > 2.5 * i["parte"].altura_cm]
    costas = [i for i in sem_logo if i not in golas]
    if golas:
        partes["gola"] = max(golas, key=lambda g: g["parte"].largura_cm)["parte"]
    if costas:
        partes["costas"] = max(costas, key=lambda c: c["parte"].altura_cm)["parte"]
    mangas = [i for i in itens if len(numericos(i)) == 1]
    if not mangas:
        return partes
    # linhas de mangas (pares esquerda/direita na mesma altura da página)
    linhas: list[list[dict]] = []
    for m in sorted(mangas, key=lambda m: m["y"]):
        if linhas and abs(m["y"] - linhas[-1][0]["y"]) * PT_PARA_CM < 3:
            linhas[-1].append(m)
        else:
            linhas.append([m])
    if raglan:
        tipos = ["raglan"] + [f"raglan_{i}" for i in range(2, len(linhas) + 1)]
    elif len(linhas) == 1:
        tipos = ["curta"]
    else:
        alturas = [max(m["parte"].altura_cm for m in l) for l in linhas]
        if min(alturas) < 0.75 * max(alturas):
            tipos = ["longa" if a == max(alturas) else "curta" for a in alturas]
        else:
            tipos = ["curta", "curta_barra"] + [f"curta_{i}" for i in range(3, len(linhas) + 1)]
    for tipo, linha in zip(tipos, linhas):
        for m in linha:
            lado = "esq" if "3" in m["parte"].logos else "dir" if "4" in m["parte"].logos else (
                "esq" if m is min(linha, key=lambda o: o["x"]) else "dir")
            partes.setdefault(f"manga_{tipo}_{lado}", m["parte"])
    return partes


def importar_pdf_modelos(caminho: Path | str, codigo: str | None = None,
                         tamanhos: dict[str, list[str]] | None = None, largura_min_cm: float = 2.5) -> list[Modelo]:
    """Lê um PDF de moldes (layouts SpeedCorel) e devolve um ou mais modelos.

    Layout em colunas: título do tamanho acima de cada coluna (ex.: casual
    tradicionais) → um modelo. Layout em linhas: cada linha tem um nome à
    esquerda (POLO HOMEM, RAGLAN INFANTIL...) e as colunas não têm título
    (o tamanho está desenhado em curvas) → um modelo por linha, com os
    tamanhos nomeados por ordem de tamanho da peça. `tamanhos` troca esses
    nomes: {"polo-homem": ["P", "M", ...]} (do menor para o maior).
    """
    caminho = Path(caminho)
    moldes, marcadores, palavras = _ler_pdf(caminho, largura_min_cm)
    if not moldes:
        raise ValueError(f"{caminho.name}: nenhum molde encontrado (formas com linha de contorno)")
    base = codigo or _slug(caminho.stem)
    raglan = "raglan" in (base + caminho.stem).lower()

    topo = min(m["top"] for m in moldes)
    titulos = []
    for w in palavras:
        t = normalizar_tamanho(w["text"])
        t = "BLXG" if t == "BLX" else t
        if t in ORDEM and w["bottom"] <= topo + 1:
            titulos.append((t, (w["x0"] + w["x1"]) / 2))
    if titulos:
        limite = max(w["bottom"] for w in palavras if normalizar_tamanho(w["text"]) in ORDEM and w["bottom"] <= topo + 1)
        por_tamanho: dict[str, list[dict]] = {}
        for m in moldes:
            if m["top"] < limite:  # gola/legenda desenhada acima dos títulos
                continue
            cx = (m["x0"] + m["x1"]) / 2
            nome = min(titulos, key=lambda t: abs(t[1] - cx))[0]
            por_tamanho.setdefault(nome, []).append(_peca(m, marcadores, palavras))
        tams = {n: Tamanho(n, grade_do_tamanho(n), _classificar(it, raglan))
                for n, it in sorted(por_tamanho.items(), key=lambda kv: ORDEM.get(kv[0], 99))}
        return [Modelo(base, caminho.name, tams)]

    # ---- tamanho escrito à esquerda de cada linha (ex.: basquete)
    esquerda = min(m["x0"] for m in moldes)
    laterais = [(normalizar_tamanho(w["text"]), (w["top"] + w["bottom"]) / 2) for w in palavras
                if normalizar_tamanho(w["text"]) in ORDEM and w["x1"] <= esquerda + 1
                and (w["bottom"] - w["top"]) * PT_PARA_CM > 3]
    if len(laterais) >= 2:
        primeira = min(t[1] for t in laterais) - 50 / PT_PARA_CM
        comuns = [_peca(m, marcadores, palavras) for m in moldes if m["bottom"] < primeira]
        por_tamanho = {}
        for m in moldes:
            if m["bottom"] < primeira:
                continue
            meio = (m["top"] + m["bottom"]) / 2
            nome = min(laterais, key=lambda t: abs(t[1] - meio))[0]
            por_tamanho.setdefault(nome, []).append(_peca(m, marcadores, palavras))
        tams = {}
        for n, it in sorted(por_tamanho.items(), key=lambda kv: ORDEM.get(kv[0], 99)):
            partes = _classificar(it, raglan)
            for c in comuns:  # ex.: uma gola só, desenhada no topo, para todos os tamanhos
                partes.setdefault("gola" if c["parte"].largura_cm > 2.5 * c["parte"].altura_cm else "comum", c["parte"])
            tams[n] = Tamanho(n, grade_do_tamanho(n), partes)
        return [Modelo(base, caminho.name, tams)]

    # ---- layout em linhas/colunas sem títulos de tamanho
    linhas_txt: dict[int, list[dict]] = {}
    for w in palavras:
        linhas_txt.setdefault(round(w["top"] * PT_PARA_CM / 2), []).append(w)
    rotulos = []
    for linha in linhas_txt.values():
        trechos: list[list[dict]] = []
        for w in sorted(linha, key=lambda w: w["x0"]):  # "Feminino ... Masculino" na mesma linha = 2 rótulos
            if trechos and w["x0"] - trechos[-1][-1]["x1"] < 15 / PT_PARA_CM:
                trechos[-1].append(w)
            else:
                trechos.append([w])
        for ws in trechos:
            texto = " ".join(w["text"] for w in ws if w["text"].isalpha()).upper()
            if any(p in texto.split() for p in PALAVRAS_GRADE):
                rotulos.append((texto, (min(w["top"] for w in ws) + max(w["bottom"] for w in ws)) / 2,
                                (min(w["x0"] for w in ws) + max(w["x1"] for w in ws)) / 2, max(w["bottom"] for w in ws)))

    if rotulos and all(r[3] <= topo + 1 for r in rotulos):
        # nomes dos grupos acima das peças (ex.: shorts Feminino | Masculino): grupos lado a lado
        grupos: dict[str, list[dict]] = {}
        for m in moldes:
            cx = (m["x0"] + m["x1"]) / 2
            grupos.setdefault(min(rotulos, key=lambda r: abs(r[2] - cx))[0], []).append(m)
        faixas = [(r, g) for r, g in grupos.items()]
    else:
        blocos: list[list[dict]] = []
        for m in sorted(moldes, key=lambda m: m["top"]):
            if blocos and m["top"] <= max(o["bottom"] for o in blocos[-1]) + 15 / PT_PARA_CM:
                blocos[-1].append(m)
            else:
                blocos.append([m])
        faixas = []
        for bloco in blocos:
            meio = (min(m["top"] for m in bloco) + max(m["bottom"] for m in bloco)) / 2
            faixas.append((min(rotulos, key=lambda r: abs(r[1] - meio))[0] if rotulos else "", bloco))

    modelos = []
    for rotulo, faixa in faixas:
        grade = next((PALAVRAS_GRADE[p] for p in rotulo.split() if p in PALAVRAS_GRADE), "adulto")
        cod = _slug(rotulo) if rotulo else base
        if rotulo and not cod.startswith(base.split("-")[0]):
            cod = f"{base}-{cod}"
        celulas = []
        for cel in _celulas(faixa, marcadores):
            partes = _classificar([_peca(m, marcadores, palavras) for m in cel], raglan)
            escrito = next((normalizar_tamanho(w["text"]) for w in palavras for m in cel
                            if _dentro(w, m) and normalizar_tamanho(w["text"]) in ORDEM), None)
            if partes:
                celulas.append((max(v.largura_cm * v.altura_cm for v in partes.values()), partes, escrito))
        celulas.sort(key=lambda c: c[0])
        partes_col = [c[1] for c in celulas]
        nomes = (tamanhos or {}).get(cod) or _nomes_ancorados(grade, [c[2] for c in celulas])
        if len(nomes) != len(partes_col):
            raise ValueError(f"{cod}: {len(partes_col)} tamanhos no PDF, mas {len(nomes)} nomes informados")
        tams = {normalizar_tamanho(n): Tamanho(normalizar_tamanho(n), grade, p) for n, p in zip(nomes, partes_col)}
        modelos.append(Modelo(cod, caminho.name, tams))
    return modelos


def _agrupar(moldes: list[dict], eixo: str, folga_cm: float) -> list[list[dict]]:
    ini, fim = ("x0", "x1") if eixo == "x" else ("top", "bottom")
    grupos: list[list[dict]] = []
    for m in sorted(moldes, key=lambda m: m[ini]):
        if grupos and m[ini] <= max(o[fim] for o in grupos[-1]) + folga_cm / PT_PARA_CM:
            grupos[-1].append(m)
        else:
            grupos.append([m])
    return grupos


def _celulas(moldes: list[dict], marcadores: list[dict]) -> list[list[dict]]:
    """Separa as peças de cada tamanho: em colunas (polo, raglan) ou em linhas (shorts).
    Fica o arranjo em que nenhum tamanho tem duas frentes ou duas pernas iguais."""
    def tipo(m):
        tipos = [_tipo_marcador(k.get("non_stroking_color")) for k in marcadores
                 if _dentro(k, m) and (k["x1"] - k["x0"]) < (m["x1"] - m["x0"]) * 0.6]
        if tipos.count("logo") >= 2:
            return "frente"
        return next((t for t in tipos if t in ("direita", "esquerda")), None)

    def valido(celulas):
        for cel in celulas:
            ts = [t for t in map(tipo, cel) if t]
            if len(ts) != len(set(ts)):
                return False
        return True

    opcoes = [_agrupar(moldes, "x", 4), _agrupar(moldes, "y", 2)]
    boas = [o for o in opcoes if valido(o)] or opcoes[:1]
    return max(boas, key=len)


def importar_pdf(caminho: Path | str, codigo: str | None = None, largura_min_cm: float = 5.0) -> Modelo:
    """Atalho para PDFs com um modelo só (layout em colunas, como o casual tradicionais)."""
    modelos = importar_pdf_modelos(caminho, codigo, largura_min_cm=largura_min_cm)
    if len(modelos) != 1:
        raise ValueError(f"{Path(caminho).name} tem {len(modelos)} modelos ({', '.join(m.codigo for m in modelos)}); "
                         "use importar_pdf_modelos")
    return modelos[0]


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
