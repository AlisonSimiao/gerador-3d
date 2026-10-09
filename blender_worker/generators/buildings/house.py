"""Gerador `house` (construções — Marco 1)."""

from __future__ import annotations

import random

from ...geometry import MeshBuilder
from ...geometry.mesh import MeshData
from ...schema import HouseSpec
from ..base import BaseGenerator, register


@register("house")
class HouseGenerator(BaseGenerator[HouseSpec]):
    """Casa low-poly: corpo + telhado + chaminé + janelas + porta."""

    @classmethod
    def tri_budget(cls) -> int:
        return 8000

    def build(self) -> MeshData:
        s = self.spec
        st = self.style
        rng = random.Random(s.seed)
        b = MeshBuilder()
        wall = b.material(f"wall_{s.wall_material}", st.wall_color(s.wall_material))
        roof = b.material("roof", st.roof_color(), roughness=0.9)
        wood = b.material("wood", st.wood(), roughness=0.85)
        wood_dark = b.material("wood_dark", st.wood("dark"), roughness=0.85)
        glass = b.material("glass", st.color("glass"), roughness=0.2)

        wall_h = 2.6 * s.floors
        # Corpo
        b.box(0, 0, 0, s.width, s.depth, wall_h, wall)
        # Telhado
        roof_h = min(s.width, s.depth) * 0.35
        if s.roof_type == "gable":
            b.gable_roof(0, 0, wall_h, s.width, s.depth, roof_h, 0.3, roof)
        elif s.roof_type == "hip":
            b.tapered_box(0, 0, wall_h, s.width + 0.6, s.depth + 0.6,
                          s.width * 0.25, s.depth * 0.25, roof_h, roof)
            b.box(0, 0, wall_h + roof_h, s.width * 0.25, s.depth * 0.25, 0.08, roof)
        else:  # flat
            b.box(0, 0, wall_h, s.width + 0.4, s.depth + 0.4, 0.18, roof)
        # Chaminé
        if s.chimney:
            chx = s.width * 0.28 * (1 if rng.random() < 0.5 else -1)
            b.box(chx, 0, wall_h + roof_h * 0.4, 0.5, 0.5, 1.4, wall)
        # Porta (face sul, centrada)
        b.box(0, s.depth / 2, 0, 1.0, 0.12, 2.0, wood_dark)
        # Janelas distribuídas nas 4 fachadas
        per_face = [s.windows // 4 + (1 if i < s.windows % 4 else 0) for i in range(4)]
        for i, n in enumerate(per_face):
            for k in range(n):
                t = (k + 1) / (n + 1) - 0.5
                zy = 1.0 + wall_h / 2 * 0.4
                if i == 0:  # sul
                    b.box(t * (s.width - 1.6), s.depth / 2, zy, 0.7, 0.1, 0.7, glass)
                elif i == 1:  # norte
                    b.box(t * (s.width - 1.6), -s.depth / 2, zy, 0.7, 0.1, 0.7, glass)
                elif i == 2:  # leste
                    b.box(s.width / 2, t * (s.depth - 1.6), zy, 0.1, 0.7, 0.7, glass)
                else:  # oeste
                    b.box(-s.width / 2, t * (s.depth - 1.6), zy, 0.1, 0.7, 0.7, glass)
        # Vigas de madeira (detalhe do estilo)
        b.box(0, 0, wall_h - 0.15, s.width + 0.15, s.depth + 0.15, 0.15, wood)
        return b.mesh
