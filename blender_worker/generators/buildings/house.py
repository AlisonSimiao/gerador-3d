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

    def build(self) -> MeshData:
        s = self.spec
        st = self.style
        rng = random.Random(s.seed)
        b = MeshBuilder()
        wall = b.material(f"wall_{s.wall_finish}", st.wall_color(s.wall_finish))
        roof = b.material("roof", st.roof_color(), roughness=0.9)
        wood = b.material("wood", st.wood(), roughness=0.85)
        wood_dark = b.material("wood_dark", st.wood("dark"), roughness=0.85)
        glass = b.material("glass", st.color("glass"), roughness=0.2)

        wall_h = 2.6 * s.floors
        # Corpo
        start = len(b.mesh.faces); b.box(0, 0, 0, s.width, s.depth, wall_h, wall); b.mesh.mark_component("body", start)
        # Telhado
        roof_h = min(s.width, s.depth) * (0.33 + rng.uniform(-0.02, 0.02))
        start = len(b.mesh.faces)
        if s.roof_form == "gable":
            b.gable_roof(0, 0, wall_h, s.width, s.depth, roof_h, 0.25 + rng.uniform(0, 0.1), roof)
        elif s.roof_form == "hip":
            b.tapered_box(0, 0, wall_h, s.width + 0.6, s.depth + 0.6,
                          s.width * 0.25, s.depth * 0.25, roof_h, roof)
            b.box(0, 0, wall_h + roof_h, s.width * 0.25, s.depth * 0.25, 0.08, roof)
        b.mesh.mark_component("roof", start)
        # Chaminé
        if s.has_chimney:
            start = len(b.mesh.faces)
            chx = s.width * 0.28 * (1 if rng.random() < 0.5 else -1)
            b.box(chx, 0, wall_h + roof_h * 0.4, 0.5, 0.5, 1.4, wall)
            b.mesh.mark_component("chimney", start)
        # Porta (face sul, centrada)
        start = len(b.mesh.faces); b.box(0, s.depth / 2, 0, 1.0, 0.12, 2.0, wood_dark); b.mesh.mark_component("door", start)
        # Janelas distribuídas nas 4 fachadas
        start = len(b.mesh.faces)
        per_face = [s.window_count // 4 + (1 if i < s.window_count % 4 else 0) for i in range(4)]
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
        if len(b.mesh.faces) > start:
            b.mesh.mark_component("windows", start)
        # The finish changes facade structure, while all colors remain in Style.
        start = len(b.mesh.faces)
        if s.wall_finish == "timber":
            b.box(0, s.depth / 2 + 0.03, 0, s.width, 0.06, 0.12, wood)
            for x in (-s.width * .35, 0, s.width * .35): b.box(x, s.depth / 2 + .03, 0, .10, .06, wall_h, wood)
        elif s.wall_finish == "stone":
            for z in (wall_h * .25, wall_h * .5, wall_h * .75): b.box(0, s.depth / 2 + .03, z, s.width, .05, .05, wood)
        if len(b.mesh.faces) > start:
            b.mesh.mark_component("facade_details", start)
        return b.mesh
