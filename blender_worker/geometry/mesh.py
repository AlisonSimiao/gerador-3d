"""Representação de malha pura-Python (testável sem bpy)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class AnchorKind(str, Enum):
    """Semantic meaning of the origin for an Asset Type."""

    SUPPORT_SURFACE = "support_surface_center"
    GRIP_CENTER = "grip_center"


@dataclass
class MaterialDef:
    name: str
    color: tuple[float, float, float, float]
    metallic: float = 0.0
    roughness: float = 0.8


@dataclass
class MeshData:
    """Blender-independent IR with geometry, named components and an anchor."""

    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)
    face_materials: list[int] = field(default_factory=list)
    materials: list[MaterialDef] = field(default_factory=list)
    components: dict[str, tuple[int, int]] = field(default_factory=dict)
    anchor: tuple[float, float, float] = (0.0, 0.0, 0.0)
    anchor_kind: AnchorKind = AnchorKind.SUPPORT_SURFACE

    def mark_component(self, name: str, start_face: int) -> None:
        self.components[name] = (start_face, len(self.faces))

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

    def component_bounds(
        self, name: str
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Return the axis-aligned extent of one named IR component."""
        start, end = self.components[name]
        return self._face_bounds(range(start, end))

    def component_volume_bounds(
        self, name: str
    ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
        """Return extents of disconnected closed volumes in a named component."""
        start, end = self.components[name]
        remaining = set(range(start, end))
        by_vertex: dict[int, set[int]] = {}
        for face_index in remaining:
            for vertex_index in self.faces[face_index]:
                by_vertex.setdefault(vertex_index, set()).add(face_index)

        volumes: list[set[int]] = []
        while remaining:
            pending = [min(remaining)]
            volume: set[int] = set()
            while pending:
                face_index = pending.pop()
                if face_index not in remaining:
                    continue
                remaining.remove(face_index)
                volume.add(face_index)
                for vertex_index in self.faces[face_index]:
                    pending.extend(by_vertex[vertex_index] & remaining)
            volumes.append(volume)
        return [self._face_bounds(volume) for volume in volumes]

    def _face_bounds(
        self, face_indexes: Iterable[int]
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        indexes = list(face_indexes)
        vertex_indexes = {index for face in indexes for index in self.faces[face]}
        vertices = [self.vertices[index] for index in vertex_indexes]
        xs = [vertex[0] for vertex in vertices]
        ys = [vertex[1] for vertex in vertices]
        zs = [vertex[2] for vertex in vertices]
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
