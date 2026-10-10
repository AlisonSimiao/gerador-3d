"""Helpers de geometria: prism, taper, cyl, merge — operam sobre MeshData."""

from __future__ import annotations

import math

from .mesh import AnchorKind, MaterialDef, MeshData


class MeshBuilder:
    """Acumula primitivas low-poly na representação intermediária pública."""

    def __init__(self) -> None:
        self.mesh = MeshData()

    def material(self, name: str, color: tuple[float, float, float, float],
                 metallic: float = 0.0, roughness: float = 0.8) -> int:
        return self.mesh.add_material(MaterialDef(name, color, metallic, roughness))

    def box(self, cx: float, cy: float, z0: float, sx: float, sy: float, sz: float,
            mat: int) -> None:
        """Caixa com base em z0 e centro (cx, cy)."""
        x0, x1 = cx - sx / 2, cx + sx / 2
        y0, y1 = cy - sy / 2, cy + sy / 2
        z1 = z0 + sz
        v = self.mesh.vertices
        base = len(v)
        v.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
                  (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            self.mesh.add_face(tuple(b + base for b in f), mat)

    def tapered_box(self, cx: float, cy: float, z0: float,
                    sx0: float, sy0: float, sx1: float, sy1: float, sz: float,
                    mat: int) -> None:
        """Tronco de pirâmide (ex.: lâmina que afunila)."""
        x0a, x1a = cx - sx0 / 2, cx + sx0 / 2
        y0a, y1a = cy - sy0 / 2, cy + sy0 / 2
        x0b, x1b = cx - sx1 / 2, cx + sx1 / 2
        y0b, y1b = cy - sy1 / 2, cy + sy1 / 2
        z1 = z0 + sz
        v = self.mesh.vertices
        base = len(v)
        v.extend([(x0a, y0a, z0), (x1a, y0a, z0), (x1a, y1a, z0), (x0a, y1a, z0),
                  (x0b, y0b, z1), (x1b, y0b, z1), (x1b, y1b, z1), (x0b, y1b, z1)])
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
                  (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            self.mesh.add_face(tuple(b + base for b in f), mat)

    def pyramid_tip(self, cx: float, cy: float, z0: float,
                    sx: float, sy: float, h: float, mat: int) -> None:
        """Ponta de pirâmide (ex.: ponta da espada, telhado)."""
        x0, x1 = cx - sx / 2, cx + sx / 2
        y0, y1 = cy - sy / 2, cy + sy / 2
        z1 = z0 + h
        v = self.mesh.vertices
        base = len(v)
        v.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (cx, cy, z1)])
        self.mesh.add_face((base + 3, base + 2, base + 1, base), mat)
        for i in range(4):
            self.mesh.add_face((base + i, base + (i + 1) % 4, base + 4), mat)

    def gable_roof(self, cx: float, cy: float, z0: float,
                   sx: float, sy: float, h: float, overhang: float, mat: int) -> None:
        """Telhado de duas águas com cumeeira ao longo de X."""
        x0, x1 = cx - sx / 2 - overhang, cx + sx / 2 + overhang
        y0, y1 = cy - sy / 2 - overhang, cy + sy / 2 + overhang
        zr = z0 + h
        v = self.mesh.vertices
        base = len(v)
        v.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, cy, zr), (x1, cy, zr)])
        m = self.mesh.add_face
        b = base
        m((b, b + 1, b + 5, b + 4), mat)  # água sul
        m((b + 2, b + 3, b + 4, b + 5), mat)  # água norte
        m((b, b + 4, b + 3), mat)  # frontão oeste
        m((b + 1, b + 2, b + 5), mat)  # frontão leste
        m((b, b + 3, b + 2, b + 1), mat)  # fechamento inferior

    def cylinder(self, cx: float, cy: float, z0: float, r0: float, r1: float,
                 h: float, segments: int, mat: int, cap_top: bool = True) -> None:
        """Cilindro/cone low-poly."""
        v = self.mesh.vertices
        base = len(v)
        z1 = z0 + h
        for i in range(segments):
            a = 2 * math.pi * i / segments
            v.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0))
        for i in range(segments):
            a = 2 * math.pi * i / segments
            v.append((cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1))
        for i in range(segments):
            j = (i + 1) % segments
            self.mesh.add_face((base + i, base + j, base + segments + j,
                                base + segments + i), mat)
        # base sempre tampada (malha fechada); topo opcional
        cb = len(v)
        v.append((cx, cy, z0))
        for i in range(segments):
            j = (i + 1) % segments
            self.mesh.add_face((cb, base + j, base + i), mat)
        if cap_top:
            ct = len(v)
            v.append((cx, cy, z1))
            for i in range(segments):
                j = (i + 1) % segments
                self.mesh.add_face((ct, base + segments + i, base + segments + j), mat)

    def octahedron(self, cx: float, cy: float, cz: float, r: float,
                   sy: float = 1.0, mat: int = 0) -> None:
        """Octaedro low-poly (8 tris) — folhagem/rochas/pomo."""
        v = self.mesh.vertices
        base = len(v)
        v.extend([(cx - r, cy, cz), (cx, cy - r * sy, cz), (cx + r, cy, cz),
                  (cx, cy + r * sy, cz), (cx, cy, cz + r), (cx, cy, cz - r)])
        b = base
        for f in ((b, b + 1, b + 4), (b + 1, b + 2, b + 4), (b + 2, b + 3, b + 4),
                  (b + 3, b, b + 4), (b + 1, b, b + 5), (b + 2, b + 1, b + 5),
                  (b + 3, b + 2, b + 5), (b, b + 3, b + 5)):
            self.mesh.add_face(f, mat)
