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

TRANSFERENCIAS = ("calandra", "prensa")
Transferencia = Literal["calandra", "prensa"]


@dataclass(frozen=True)
class Produto:
    codigo: str
    nome: str
    largura_cm: float = 0
    altura_cm: float = 0
    margem_cm: float = 1.0
    lados: int = 1
    espelhar: bool = False
    transferencia: Transferencia = "calandra"  # equipamento padrão da transferência
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

    def validar_impressao(self, produto: Produto, transferencia: str | None = None) -> None:
        """Sem emenda de painéis: a peça tem que caber na largura do rolo/calandra
        e, se for para a prensa, na mesa da prensa (em qualquer orientação)."""
        w, h = produto.largura_total_cm, produto.altura_total_cm
        largura = self.config.largura_rolo_cm
        if min(w, h) > largura:
            raise ValueError(f"{produto.nome}: peça de {w:g}x{h:g} cm não cabe na largura de impressão de {largura:g} cm")
        transferencia = transferencia or produto.transferencia
        if transferencia not in TRANSFERENCIAS:
            raise ValueError(f"transferência '{transferencia}' inválida (use calandra ou prensa)")
        if transferencia == "prensa":
            pl, pc = self.config.prensa_largura_cm, self.config.prensa_comprimento_cm
            cabe = (w <= pl and h <= pc) or (h <= pl and w <= pc)
            if not cabe:
                raise ValueError(f"{produto.nome}: peça de {w:g}x{h:g} cm não cabe na prensa de {pl:g}x{pc:g} cm")

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
    return Catalogo(config=config, produtos=produtos, pasta_molduras=pasta_molduras, os=ConfigOS(**os_),
                    avisos=dados.get("avisos", {}))
