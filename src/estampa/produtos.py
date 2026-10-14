"""Catálogo de produtos e parâmetros gerais de produção."""

from __future__ import annotations

import tomllib
from typing import Literal
from dataclasses import dataclass, field, replace
from pathlib import Path

def _catalogo_padrao() -> Path:
    """produtos.toml da pasta atual ou, se não houver, o da raiz do projeto."""
    local = Path("produtos.toml")
    return local if local.exists() else Path(__file__).resolve().parents[2] / "produtos.toml"


CATALOGO_PADRAO = _catalogo_padrao()

TRANSFERENCIAS = ("auto", "prensa", "calandra")
Transferencia = Literal["auto", "prensa", "calandra"]


@dataclass(frozen=True)
class Produto:
    codigo: str
    nome: str
    largura_cm: float = 0
    altura_cm: float = 0
    margem_cm: float = 1.0
    lados: int = 1
    espelhar: bool = False
    transferencia: Transferencia = "auto"  # auto = prensa se couber, senão calandra
    sob_medida: bool = False      # medidas vêm de cada pedido
    dpi: int | None = None        # sobrepõe o DPI geral (peças grandes)
    largura_max_cm: float | None = None
    altura_max_cm: float | None = None

    def com_medidas(self, largura_cm: float, altura_cm: float) -> Produto:
        """Produto sob medida com as dimensões de um pedido específico."""
        if not self.sob_medida:
            raise ValueError(f"{self.nome} tem medida fixa ({self.largura_cm:g}x{self.altura_cm:g} cm)")
        if largura_cm <= 0 or altura_cm <= 0:
            raise ValueError(f"{self.nome}: medidas inválidas {largura_cm:g}x{altura_cm:g}")
        for valor, limite, eixo in ((largura_cm, self.largura_max_cm, "largura"),
                                    (altura_cm, self.altura_max_cm, "altura")):
            if limite and valor > limite:
                raise ValueError(f"{self.nome}: {eixo} {valor:g} cm acima do máximo de {limite:g} cm")
        return replace(
            self,
            codigo=f"{self.codigo}-{largura_cm:g}x{altura_cm:g}",
            nome=f"{self.nome} {largura_cm:g}x{altura_cm:g}",
            largura_cm=largura_cm,
            altura_cm=altura_cm,
            sob_medida=False,
        )

    @property
    def largura_total_cm(self) -> float:
        return self.largura_cm + 2 * self.margem_cm

    @property
    def altura_total_cm(self) -> float:
        return self.altura_cm + 2 * self.margem_cm


@dataclass(frozen=True)
class Config:
    dpi: int = 150
    largura_rolo_cm: float = 180
    espaco_entre_pecas_cm: float = 0.5
    comprimento_max_cm: float = 300
    borda_mm: float = 1.0
    enquadrar_rosto: bool = True
    prensa_largura_cm: float = 120
    prensa_comprimento_cm: float = 200
    separar_por_transferencia: bool = False  # subpastas calandra/ e prensa/ na saída


@dataclass(frozen=True)
class ConfigOS:
    pasta: Path = Path("ordens")
    prefixo: str = "OS"


@dataclass(frozen=True)
class Catalogo:
    config: Config
    produtos: dict[str, Produto]
    pasta_molduras: Path = Path("molduras")
    os: ConfigOS = ConfigOS()
    avisos: dict = field(default_factory=dict)
    pastas_rip: dict[str, tuple[Path, ...]] = field(default_factory=dict)

    def cabe_na_prensa(self, produto: Produto) -> bool:
        w, h = produto.largura_total_cm, produto.altura_total_cm
        pl, pc = self.config.prensa_largura_cm, self.config.prensa_comprimento_cm
        return (w <= pl and h <= pc) or (h <= pl and w <= pc)

    def resolver_transferencia(self, produto: Produto, pedida: str | None = None) -> str:
        """Equipamento da transferência ("prensa" ou "calandra"), validando o tamanho.

        Sem emenda de painéis: a peça tem que caber na largura do rolo/calandra.
        `auto` (padrão) usa a prensa quando a peça cabe na mesa e a calandra
        quando não cabe; rolo a rolo é escolhido explicitamente como calandra.
        """
        w, h = produto.largura_total_cm, produto.altura_total_cm
        largura = self.config.largura_rolo_cm
        if min(w, h) > largura:
            raise ValueError(f"{produto.nome}: peça de {w:g}x{h:g} cm não cabe na largura de impressão de {largura:g} cm")
        escolha = (pedida or produto.transferencia or "auto").strip().lower()
        if escolha not in TRANSFERENCIAS:
            raise ValueError(f"transferência '{escolha}' inválida (use auto, prensa ou calandra)")
        if escolha == "auto":
            return "prensa" if self.cabe_na_prensa(produto) else "calandra"
        if escolha == "prensa" and not self.cabe_na_prensa(produto):
            pl, pc = self.config.prensa_largura_cm, self.config.prensa_comprimento_cm
            raise ValueError(f"{produto.nome}: peça de {w:g}x{h:g} cm não cabe na prensa de {pl:g}x{pc:g} cm")
        return escolha

    def validar_impressao(self, produto: Produto, transferencia: str | None = None) -> None:
        self.resolver_transferencia(produto, transferencia)

    def produto(self, codigo: str) -> Produto:
        try:
            return self.produtos[codigo]
        except KeyError:
            disponiveis = ", ".join(sorted(self.produtos))
            raise KeyError(f"produto '{codigo}' não cadastrado (disponíveis: {disponiveis})") from None


def carregar_catalogo(caminho: Path | str = CATALOGO_PADRAO) -> Catalogo:
    with open(caminho, "rb") as f:
        dados = tomllib.load(f)
    geral = dict(dados.get("geral", {}))
    pasta_molduras = Path(caminho).resolve().parent / geral.pop("pasta_molduras", "molduras")
    config = Config(**geral)
    produtos = {
        codigo: Produto(codigo=codigo, **campos)
        for codigo, campos in dados.get("produtos", {}).items()
    }
    os_ = dict(dados.get("os", {}))
    os_["pasta"] = Path(caminho).resolve().parent / os_.get("pasta", "ordens")
    pastas_rip = {}
    for equipamento, pastas in dados.get("rip", {}).items():
        if equipamento not in TRANSFERENCIAS or equipamento == "auto":
            raise ValueError(f"[rip] {equipamento}: use prensa ou calandra")
        lista = [pastas] if isinstance(pastas, str) else list(pastas)
        pastas_rip[equipamento] = tuple(Path(p) for p in lista if p)
    return Catalogo(config=config, produtos=produtos, pasta_molduras=pasta_molduras, os=ConfigOS(**os_),
                    avisos=dados.get("avisos", {}), pastas_rip=pastas_rip)
