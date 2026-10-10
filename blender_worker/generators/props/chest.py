"""Gerador `chest` (objetos/móveis — Marco 1). Âncora no centro do apoio."""

from __future__ import annotations

import math
import random

from ...geometry import MeshBuilder
from ...geometry.mesh import MeshData
from ...materials import metal_material
from ...schema import ChestSpec
from ..base import BaseGenerator, register


@register("chest")
class ChestGenerator(BaseGenerator[ChestSpec]):
    def build(self) -> MeshData:
        s = self.spec
        rng = random.Random(s.seed)
        b = MeshBuilder()
        wood = b.material("wood", self.style.wood(), roughness=0.85)
        wood_dark = b.material("wood_dark", self.style.wood("dark"), roughness=0.85)
        iron = b.mesh.add_material(metal_material(self.style, "iron", "band_iron"))
        gold = b.mesh.add_material(metal_material(self.style, "gold", "lock_gold"))

        body_h = s.height * 0.65
        start = len(b.mesh.faces)
        b.box(0, 0, 0, s.width, s.depth, body_h, wood)
        b.mesh.mark_component("body", start)
        # Tampa
        start = len(b.mesh.faces)
        if s.lid_form == "flat":
            b.box(0, 0, body_h, s.width, s.depth, s.height * 0.35, wood_dark)
        else:
            lid_h = s.height * 0.35
            self._arch_lid(b, s.width, s.depth, body_h, lid_h, wood_dark)
        b.mesh.mark_component("lid", start)
        # Cintas metálicas (largura e posição variam por seed, sem sair
        # do envelope: meio-perfil da cinta mais larga cabe em width/2).
        start = len(b.mesh.faces)
        for i in range(s.band_count):
            t = (i + 1) / (s.band_count + 1) - 0.5 if s.band_count else 0.0
            band_w = 0.05 + rng.uniform(0, 0.05)
            band_x = t * s.width * 0.8 + rng.uniform(-0.02, 0.02) * s.width
            b.box(band_x, 0, 0, band_w, s.depth, s.height, iron)
        if len(b.mesh.faces) > start:
            b.mesh.mark_component("bands", start)
        # Fechadura (tamanho e posição variam por seed; face frontal
        # alinhada a depth/2 para nunca ultrapassar o envelope).
        start = len(b.mesh.faces)
        if s.has_lock:
            lock_w = 0.12 + rng.uniform(0, 0.06)
            lock_h = 0.16 + rng.uniform(0, 0.06)
            lock_d = 0.05 + rng.uniform(0, 0.03)
            lock_x = rng.uniform(-0.03, 0.03)
            lock_z = body_h - 0.05 + rng.uniform(-0.02, 0.02)
            b.box(lock_x, s.depth / 2 - lock_d / 2, lock_z - lock_h / 2,
                  lock_w, lock_d, lock_h, gold)
        if len(b.mesh.faces) > start:
            b.mesh.mark_component("lock", start)
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
        centers = []
        for ring, x in ((ring0, -w / 2), (ring1, w / 2)):
            c = len(mesh.vertices)
            mesh.vertices.append((x, 0, z0))
            centers.append(c)
            for i in range(segs):
                if x < 0:
                    mesh.add_face((c, ring[i + 1], ring[i]), mat)
                else:
                    mesh.add_face((c, ring[i], ring[i + 1]), mat)
        mesh.add_face((ring0[0], ring1[0], centers[1], centers[0]), mat)
        mesh.add_face((centers[0], centers[1], ring1[-1], ring0[-1]), mat)
