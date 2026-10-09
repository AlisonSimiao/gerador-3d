"""Representação de malha pura-Python (testável sem bpy)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MaterialDef:
    name: str
    color: tuple[float, float, float, float]
    metallic: float = 0.0
    roughness: float = 0.8


@dataclass
class MeshData:
    """Malha com faces de 3 ou 4 vértices e um material por face."""

    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)
    face_materials: list[int] = field(default_factory=list)
    materials: list[MaterialDef] = field(default_factory=list)

    def add_material(self, mat: MaterialDef) -> int:
        for i, m in enumerate(self.materials):
            if m.name == mat.name:
                return i
        self.materials.append(mat)
        return len(self.materials) - 1

    def add_face(self, verts: tuple[int, ...], mat: int) -> None:
        self.faces.append(verts)
        self.face_materials.append(mat)

    def tri_count(self) -> int:
        n = 0
        for f in self.faces:
            n += 1 if len(f) == 3 else 2 * (len(f) - 2) if len(f) > 3 else 0
        return n

    def bounds(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))

    def triangulated(self) -> list[tuple[tuple[int, int, int], int]]:
        """Retorna [(tri, mat), ...] com quads/n-gons convertidos em fan."""
        out: list[tuple[tuple[int, int, int], int]] = []
        for face, mat in zip(self.faces, self.face_materials):
            if len(face) == 3:
                out.append(((face[0], face[1], face[2]), mat))
            elif len(face) > 3:
                for i in range(1, len(face) - 1):
                    out.append(((face[0], face[i], face[i + 1]), mat))
        return out
