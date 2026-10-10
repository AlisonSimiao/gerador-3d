"""Gerador `sword` (armas — Marco 1). Eixo Z para cima, origem na base do pomo."""

from __future__ import annotations

from ...geometry import MeshBuilder
from ...geometry.mesh import MeshData
from ...materials import metal_material
from ...schema import SwordSpec
from ..base import BaseGenerator, register


@register("sword")
class SwordGenerator(BaseGenerator[SwordSpec]):
    @classmethod
    def tri_budget(cls) -> int:
        return 2000

    def build(self) -> MeshData:
        s = self.spec
        b = MeshBuilder()
        steel = b.mesh.add_material(metal_material(self.style, "steel", "blade_steel"))
        iron = b.mesh.add_material(metal_material(self.style, "iron", "guard_iron"))
        gold = b.mesh.add_material(metal_material(self.style, "gold", "pommel_gold"))
        grip_m = b.material("grip", self.style.wood("dark"), roughness=0.9)

        # Anchor is the grip centre, therefore the grip spans around z=0.
        grip_start = -s.grip_length / 2
        start = len(b.mesh.faces)
        # Pomo
        if s.pommel_form == "round":
            b.octahedron(0, 0, grip_start - 0.05, 0.05, mat=gold)
        elif s.pommel_form == "faceted":
            b.box(0, 0, grip_start - 0.03, 0.07, 0.07, 0.03, gold)
        b.mesh.mark_component("pommel", start)
        # Empunhadura
        start = len(b.mesh.faces); b.cylinder(0, 0, grip_start, 0.025, 0.025, s.grip_length, 6, grip_m)
        b.mesh.mark_component("grip", start); z = s.grip_length / 2
        # Guarda
        start = len(b.mesh.faces)
        if s.guard_form == "straight":
            b.box(0, 0, z, 0.26, 0.05, 0.04, iron)
            z += 0.04
        elif s.guard_form == "curved":
            b.box(0, 0, z, 0.24, 0.05, 0.03, iron)
            b.box(-0.12, 0, z + 0.03, 0.04, 0.04, 0.05, iron)
            b.box(0.12, 0, z + 0.03, 0.04, 0.04, 0.05, iron)
            z += 0.03
        b.mesh.mark_component("guard", start)
        # Lâmina (afunila até a ponta)
        start = len(b.mesh.faces); bw = s.blade_width
        b.tapered_box(0, 0, z, bw, bw * 0.35, bw * 0.15, bw * 0.1,
                      s.blade_length * 0.9, steel)
        b.pyramid_tip(0, 0, z + s.blade_length * 0.9, bw * 0.15, bw * 0.1,
                      s.blade_length * 0.1, steel)
        b.mesh.mark_component("blade", start)
        return b.mesh
