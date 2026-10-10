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
    def build(self) -> MeshData:
        s = self.spec
        rng = random.Random(s.seed)
        b = MeshBuilder()
        trunk_m = b.material("trunk", self.style.trunk(), roughness=0.95)
        leaf_m = b.material(f"leaf_{s.foliage_palette}", self.style.leaf(s.foliage_palette),
                            roughness=0.9)
        # Tronco (leve inclinação determinística via lean + seed)
        lean_dir = rng.uniform(0, 6.2832)
        lean = math.tan(math.radians(s.lean_degrees))
        dx = lean * math.cos(lean_dir)
        dy = lean * math.sin(lean_dir)
        start = len(b.mesh.faces)
        first_vertex = len(b.mesh.vertices)
        b.cylinder(0, 0, 0, s.trunk_radius, s.trunk_radius * 0.6,
                   s.trunk_height, 7, trunk_m)
        # Apply the requested lean to every trunk vertex proportionally to height.
        for index in range(first_vertex, len(b.mesh.vertices)):
            x, y, z = b.mesh.vertices[index]
            b.mesh.vertices[index] = (x + dx * z, y + dy * z, z)
        b.mesh.mark_component("trunk", start)
        top_x, top_y = dx * s.trunk_height, dy * s.trunk_height
        cz = s.trunk_height
        start = len(b.mesh.faces)
        if s.canopy_form == "clustered":
            n = 4 + rng.randint(0, 1)
            for i in range(n):
                r = 0.7 + rng.uniform(-0.15, 0.35)
                ox = top_x + rng.uniform(-0.9, 0.9)
                oy = top_y + rng.uniform(-0.9, 0.9)
                oz = cz + 0.6 + rng.uniform(0, 1.1)
                b.octahedron(ox, oy, oz, r, mat=leaf_m)
        elif s.canopy_form == "conical":
            b.cylinder(top_x, top_y, cz, 1.3, 0.05, 2.2, 7, leaf_m)
            b.cylinder(top_x, top_y, cz + 1.4, 0.9, 0.05, 1.6, 7, leaf_m)
        else:  # round
            b.octahedron(top_x, top_y, cz + 1.0, 1.4, mat=leaf_m)
            b.octahedron(top_x + 0.5, top_y - 0.3, cz + 0.5, 0.8, mat=leaf_m)
        b.mesh.mark_component("canopy", start)
        return b.mesh
