"""Criação de materiais a partir da paleta do estilo."""

from __future__ import annotations

from ..geometry.mesh import MaterialDef
from ..style import Style


def metal_material(style: Style, kind: str, name: str) -> MaterialDef:
    color = style.metal(kind)
    metallic = 0.9 if kind in ("steel", "iron", "gold") else 0.6
    return MaterialDef(name, color, metallic=metallic, roughness=0.35)


def matte_material(style: Style, key: str, name: str) -> MaterialDef:
    return MaterialDef(name, style.color(key), metallic=0.0, roughness=0.85)
