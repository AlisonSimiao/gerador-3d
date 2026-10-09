"""Gerador `chest` (objetos/móveis — Marco 1). Origem na base-centro."""

from __future__ import annotations

import math

from ...geometry import MeshBuilder
from ...geometry.mesh import MeshData
from ...materials import metal_material
from ...schema import ChestSpec
from ..base import BaseGenerator, register


@register("chest")
class ChestGenerator(BaseGenerator[ChestSpec]):
    @classmethod
    def tri_budget(cls) -> int:
        return 2000

    def build(self) -> MeshData:
        s = self.spec
        b = MeshBuilder()
        wood = b.material("wood", self.style.wood(), roughness=0.85)
        wood_dark = b.material("wood_dark", self.style.wood("dark"), roughness=0.85)
        iron = b.mesh.add_material(metal_material(self.style, "iron", "band_iron"))
        gold = b.mesh.add_material(metal_material(self.style, "gold", "lock_gold"))

        body_h = s.height * 0.65
        b.box(0, 0, 0, s.width, s.depth, body_h, wood)
        # Tampa
        if s.lid_type == "flat":
            b.box(0, 0, body_h, s.width, s.depth, s.height * 0.35, wood_dark)
        else:
            lid_h = s.height * 0.35
            self._arch_lid(b, s.width, s.depth, body_h, lid_h, wood_dark)
        # Cintas metálicas
        for i in range(s.bands):
            t = (i + 1) / (s.bands + 1) - 0.5 if s.bands else 0.0
            b.box(t * s.width * 0.8, 0, 0, 0.07, s.depth + 0.04, s.height, iron)
        # Fechadura
        if s.lock:
            b.box(0, s.depth / 2, body_h - 0.05, 0.14, 0.06, 0.18, gold)
        return b.mesh

    def _arch_lid(self, b: MeshBuilder, w: float, d: float, z0: float,
                  h: float, mat: int) -> None:
        """Meio-cilindro horizontal ao longo de X (6 segmentos)."""
        segs = 6
        mesh = b.mesh
        r = d / 2
        # anéis em x = -w/2 e +w/2, meio-círculo de 0..pi
        ring0, ring1 = [], []
        for i in range(segs + 1):
            a = math.pi * i / segs
            y = -r * math.cos(a)
            z = z0 + h * math.sin(a)
            ring0.append(len(mesh.vertices))
            mesh.vertices.append((-w / 2, y, z))
            ring1.append(len(mesh.vertices))
            mesh.vertices.append((w / 2, y, z))
        for i in range(segs):
            mesh.add_face((ring0[i], ring0[i + 1], ring1[i + 1], ring1[i]), mat)
        # tampas laterais (fan)
        for ring, x in ((ring0, -w / 2), (ring1, w / 2)):
            c = len(mesh.vertices)
            mesh.vertices.append((x, 0, z0))
            for i in range(segs):
                if x < 0:
                    mesh.add_face((c, ring[i + 1], ring[i]), mat)
                else:
                    mesh.add_face((c, ring[i], ring[i + 1]), mat)
