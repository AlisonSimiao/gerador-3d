"""Gerador `tree` (natureza — Marco 1). Origem na base do tronco."""

from __future__ import annotations

import math
import random

from ...geometry import MeshBuilder
from ...geometry.mesh import MeshData
from ...schema import TreeSpec
from ..base import BaseGenerator, register


@register("tree")
class TreeGenerator(BaseGenerator[TreeSpec]):
    @classmethod
    def tri_budget(cls) -> int:
        return 5000

    def build(self) -> MeshData:
        s = self.spec
        rng = random.Random(s.seed)
        b = MeshBuilder()
        trunk_m = b.material("trunk", self.style.trunk(), roughness=0.95)
        leaf_m = b.material(f"leaf_{s.leaf_color}", self.style.leaf(s.leaf_color),
                            roughness=0.9)
        # Tronco (leve inclinação determinística via lean + seed)
        lean_dir = rng.uniform(0, 6.2832)
        dx = s.lean * math.cos(lean_dir)
        dy = s.lean * math.sin(lean_dir)
        b.cylinder(0, 0, 0, s.trunk_radius, s.trunk_radius * 0.6,
                   s.trunk_height, 7, trunk_m)
        top_x, top_y = dx * s.trunk_height, dy * s.trunk_height
        cz = s.trunk_height
        if s.canopy_type == "cluster":
            n = 4 + rng.randint(0, 1)
            for i in range(n):
                r = 0.7 + rng.uniform(-0.15, 0.35)
                ox = top_x + rng.uniform(-0.9, 0.9)
                oy = top_y + rng.uniform(-0.9, 0.9)
                oz = cz + 0.6 + rng.uniform(0, 1.1)
                b.octahedron(ox, oy, oz, r, mat=leaf_m)
        elif s.canopy_type == "cone":
            b.cylinder(top_x, top_y, cz, 1.3, 0.05, 2.2, 7, leaf_m)
            b.cylinder(top_x, top_y, cz + 1.4, 0.9, 0.05, 1.6, 7, leaf_m)
        else:  # sphere
            b.octahedron(top_x, top_y, cz + 1.0, 1.4, mat=leaf_m)
            b.octahedron(top_x + 0.5, top_y - 0.3, cz + 0.5, 0.8, mat=leaf_m)
        return b.mesh
