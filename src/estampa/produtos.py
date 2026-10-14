"""Catálogo de produtos e parâmetros gerais de produção."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

def _catalogo_padrao() -> Path:
    """produtos.toml da pasta atual ou, se não houver, o da raiz do projeto."""
    local = Path("produtos.toml")
    return local if local.exists() else Path(__file__).resolve().parents[2] / "produtos.toml"


CATALOGO_PADRAO = _catalogo_padrao()


@dataclass(frozen=True)
class Produto:
    codigo: str
    nome: str
    largura_cm: float
    altura_cm: float
    margem_cm: float = 1.0
    lados: int = 1
    espelhar: bool = False

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


@dataclass(frozen=True)
class Catalogo:
    config: Config
    produtos: dict[str, Produto]

    def produto(self, codigo: str) -> Produto:
        try:
            return self.produtos[codigo]
        except KeyError:
            disponiveis = ", ".join(sorted(self.produtos))
            raise KeyError(f"produto '{codigo}' não cadastrado (disponíveis: {disponiveis})") from None


def carregar_catalogo(caminho: Path | str = CATALOGO_PADRAO) -> Catalogo:
    with open(caminho, "rb") as f:
        dados = tomllib.load(f)
    config = Config(**dados.get("geral", {}))
    produtos = {
        codigo: Produto(codigo=codigo, **campos)
        for codigo, campos in dados.get("produtos", {}).items()
    }
    return Catalogo(config=config, produtos=produtos)
