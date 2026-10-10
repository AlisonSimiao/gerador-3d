"""Camada de estilo — PLANO_MVP §5.

Geradores nunca fixam cores no código: pedem tudo a este módulo.
MVP entrega um único tema: `medieval_lowpoly`. Novo estilo = novo
dicionário de paleta, sem tocar nos geradores.
"""

from __future__ import annotations

from dataclasses import dataclass

Color = tuple[float, float, float, float]


@dataclass(frozen=True)
class TimberFacadeProfile:
    color: Color
    depth: float
    beam_width: float
    beam_height: float
    vertical_offsets: tuple[float, ...]


@dataclass(frozen=True)
class StoneFacadeProfile:
    color: Color
    depth: float
    course_height: float
    course_levels: tuple[float, ...]


class Style:
    """Paleta + parâmetros de um tema visual."""

    name: str
    palette: dict[str, Color]

    def __init__(self, name: str, palette: dict[str, Color]) -> None:
        self.name = name
        self.palette = dict(palette)

    def color(self, key: str) -> Color:
        try:
            return self.palette[key]
        except KeyError:
            raise KeyError(f"cor {key!r} não existe no estilo {self.name}") from None

    # Fachada usada pelos geradores (nomes estáveis entre estilos).
    def wall_color(self, material: str) -> Color:
        return self.color(f"wall_{material}")

    def roof_color(self) -> Color:
        return self.color("roof")

    def wood(self, part: str = "default") -> Color:
        return self.color(f"wood_{part}" if f"wood_{part}" in self.palette else "wood")

    def stone_detail(self) -> Color:
        return self.color("stone_detail")

    def timber_facade(self) -> TimberFacadeProfile:
        return TimberFacadeProfile(
            color=self.wood(),
            depth=0.06,
            beam_width=0.10,
            beam_height=0.12,
            vertical_offsets=(-0.35, 0.0, 0.35),
        )

    def stone_facade(self) -> StoneFacadeProfile:
        return StoneFacadeProfile(
            color=self.stone_detail(),
            depth=0.05,
            course_height=0.05,
            course_levels=(0.25, 0.5, 0.75),
        )

    def metal(self, part: str = "steel") -> Color:
        return self.color(f"metal_{part}" if f"metal_{part}" in self.palette else "metal")

    def leaf(self, color_name: str = "green") -> Color:
        return self.color(f"leaf_{color_name}" if f"leaf_{color_name}" in self.palette else "leaf")

    def trunk(self) -> Color:
        return self.color("trunk")

    def trim(self) -> Color:
        return self.color("trim")

    def cloth(self) -> Color:
        return self.color("cloth")


MEDIEVAL_LOWPOLY: dict[str, Color] = {
    "wall_plaster": (0.87, 0.82, 0.72, 1.0),
    "wall_brick": (0.62, 0.32, 0.24, 1.0),
    "wall_wood": (0.48, 0.33, 0.20, 1.0),
    "wall_stone": (0.55, 0.55, 0.58, 1.0),
    "wall_timber": (0.72, 0.62, 0.45, 1.0),
    "stone_detail": (0.38, 0.39, 0.42, 1.0),
    "roof": (0.55, 0.22, 0.16, 1.0),
    "wood": (0.45, 0.30, 0.17, 1.0),
    "wood_dark": (0.32, 0.21, 0.12, 1.0),
    "metal": (0.70, 0.72, 0.75, 1.0),
    "metal_steel": (0.75, 0.77, 0.80, 1.0),
    "metal_iron": (0.35, 0.36, 0.40, 1.0),
    "metal_gold": (0.85, 0.65, 0.25, 1.0),
    "leaf": (0.25, 0.50, 0.22, 1.0),
    "leaf_green": (0.25, 0.50, 0.22, 1.0),
    "leaf_autumn": (0.80, 0.45, 0.15, 1.0),
    "leaf_dark_green": (0.12, 0.32, 0.18, 1.0),
    "trunk": (0.40, 0.27, 0.15, 1.0),
    "trim": (0.25, 0.18, 0.12, 1.0),
    "cloth": (0.50, 0.15, 0.15, 1.0),
    "glass": (0.60, 0.80, 0.90, 1.0),
}

_STYLES: dict[str, dict[str, Color]] = {
    "medieval_lowpoly": MEDIEVAL_LOWPOLY,
}


def available_styles() -> tuple[str, ...]:
    return tuple(_STYLES.keys())


def get_style(name: str) -> Style:
    try:
        return Style(name, _STYLES[name])
    except KeyError:
        raise ValueError(
            f"estilo {name!r} desconhecido; disponíveis: {sorted(_STYLES)}"
        ) from None
