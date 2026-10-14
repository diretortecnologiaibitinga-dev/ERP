"""Catálogo de produtos e parâmetros gerais de produção."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
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
    largura_cm: float = 0
    altura_cm: float = 0
    margem_cm: float = 1.0
    lados: int = 1
    espelhar: bool = False
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
