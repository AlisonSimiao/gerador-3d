"""Validadores — PLANO_MVP §6. Falha bloqueia a geração (exit ≠ 0 + motivo no report)."""

from __future__ import annotations

import struct
from typing import Any

from ..geometry.mesh import AnchorKind, MeshData

def _ok(ok: bool, detail: str = "") -> dict[str, Any]:
    return {"ok": ok, "detail": detail}


def check_mesh_valid(mesh: MeshData, _spec_type: str = "") -> dict[str, Any]:
    """Validate named, closed component volumes in the Blender-independent IR."""
    if not mesh.faces:
        return _ok(False, "malha sem faces")
    if not mesh.components:
        return _ok(False, "malha sem componentes nomeados")
    # Degeneradas: índices duplicados ou área ~0
    for i, face in enumerate(mesh.faces):
        if len(set(face)) != len(face):
            return _ok(False, f"face {i} com vértices duplicados")
        if len(face) < 3:
            return _ok(False, f"face {i} com menos de 3 vértices")
    for i, face in enumerate(mesh.faces):
        pts = [mesh.vertices[j] for j in face]
        # área via fan a partir do vértice 0
        ax = 0.0
        ay = 0.0
        az = 0.0
        for k in range(1, len(pts) - 1):
            ux = pts[k][0] - pts[0][0]
            uy = pts[k][1] - pts[0][1]
            uz = pts[k][2] - pts[0][2]
            vx = pts[k + 1][0] - pts[0][0]
            vy = pts[k + 1][1] - pts[0][1]
            vz = pts[k + 1][2] - pts[0][2]
            ax += uy * vz - uz * vy
            ay += uz * vx - ux * vz
            az += ux * vy - uy * vx
        area2 = (ax * ax + ay * ay + az * az) ** 0.5
        if area2 < 1e-12:
            return _ok(False, f"face {i} degenerada (área ~0)")
    covered: list[int] = []
    closed: list[str] = []
    for name, (start, end) in mesh.components.items():
        if not name or start < 0 or end > len(mesh.faces) or start >= end:
            return _ok(False, f"componente {name!r} possui intervalo de faces inválido")
        covered.extend(range(start, end))
        directed_edges: dict[tuple[int, int], int] = {}
        for face in mesh.faces[start:end]:
            for index, vertex in enumerate(face):
                edge = (vertex, face[(index + 1) % len(face)])
                directed_edges[edge] = directed_edges.get(edge, 0) + 1
        bad_edges = [
            edge for edge, count in directed_edges.items()
            if count != 1 or directed_edges.get((edge[1], edge[0])) != 1
        ]
        if bad_edges:
            return _ok(False, f"componente {name!r} não é um volume fechado e orientado")
        closed.append(name)
    if sorted(covered) != list(range(len(mesh.faces))):
        return _ok(False, "faces devem pertencer exatamente a um componente nomeado")
    return {
        "ok": True,
        "detail": f"{len(mesh.faces)} faces, {len(mesh.vertices)} verts, componentes fechados",
        "components_closed": sorted(closed),
    }


def check_tri_budget(mesh: MeshData, spec_type: str) -> dict[str, Any]:
    from ..registry import get_descriptor
    budget = get_descriptor(spec_type).triangle_budget
    n = mesh.tri_count()
    if n > budget:
        return _ok(False, f"{n} tris excede orçamento de {budget} para {spec_type}")
    return _ok(True, f"{n}/{budget} tris")


def check_materials(mesh: MeshData, _spec_type: str = "") -> dict[str, Any]:
    if not mesh.materials:
        return _ok(False, "nenhum material atribuído")
    if len(mesh.face_materials) != len(mesh.faces):
        return _ok(False, "cada face deve possuir exatamente uma atribuição de material")
    for i, m in enumerate(mesh.face_materials):
        if m < 0 or m >= len(mesh.materials):
            return _ok(False, f"face {i} com material inválido ({m})")
    return _ok(True, f"{len(mesh.materials)} materiais, todas as faces cobertas")


def check_transform(mesh: MeshData, _spec_type: str = "") -> dict[str, Any]:
    """Validate positioning from the IR's semantic Anchor, independent of Type dispatch."""
    if not mesh.vertices:
        return _ok(False, "malha vazia")
    (x0, y0, z0), (x1, y1, z1) = mesh.bounds()
    if mesh.anchor != (0.0, 0.0, 0.0):
        return _ok(False, f"Âncora fora da origem: {mesh.anchor}")
    if mesh.anchor_kind is AnchorKind.SUPPORT_SURFACE:
        if abs(z0 - mesh.anchor[2]) > 1e-6 or not (x0 <= 0 <= x1 and y0 <= 0 <= y1):
            return _ok(False, "centro da superfície de apoio não coincide com a Âncora")
    elif mesh.anchor_kind is AnchorKind.GRIP_CENTER:
        grip = mesh.components.get("grip")
        if grip is None:
            return _ok(False, "componente 'grip' ausente para Âncora de empunhadura")
        vertex_indices = {
            vertex for face in mesh.faces[grip[0]:grip[1]] for vertex in face
        }
        coordinates = [mesh.vertices[index] for index in vertex_indices]
        grip_center = tuple(
            (min(point[axis] for point in coordinates) + max(point[axis] for point in coordinates)) / 2
            for axis in range(3)
        )
        if any(abs(grip_center[axis] - mesh.anchor[axis]) > 1e-6 for axis in range(3)):
            return _ok(False, "centro da empunhadura não coincide com a Âncora")
    else:
        return _ok(False, f"semântica de Âncora desconhecida: {mesh.anchor_kind!r}")
    size = max(x1 - x0, y1 - y0, z1 - z0)
    if not (0.05 <= size <= 60.0):
        return _ok(False, f"escala implausível ({size:.2f} m)")
    return {
        "ok": True,
        "detail": f"Âncora {mesh.anchor_kind.value} OK, extensão {size:.2f} m",
        "kind": mesh.anchor_kind.value,
    }


def check_glb(path: str) -> dict[str, Any]:
    """Smoke test: GLB válido com chunk JSON parseável contendo malhas."""
    import json as _json

    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return _ok(False, f"GLB ausente: {e}")
    if len(data) < 20 or data[:4] != b"glTF":
        return _ok(False, "magic glTF ausente")
    (version, _length) = struct.unpack("<II", data[4:12])
    if version != 2:
        return _ok(False, f"versão glTF {version} ≠ 2")
    json_len, json_type = struct.unpack("<II", data[12:20])
    if json_type != 0x4E4F534A:  # "JSON"
        return _ok(False, "chunk JSON ausente")
    try:
        doc = _json.loads(data[20:20 + json_len].decode("utf-8"))
    except Exception as e:
        return _ok(False, f"JSON do GLB inválido: {e}")
    if not doc.get("meshes"):
        return _ok(False, "GLB sem meshes")
    return _ok(True, f"{len(doc['meshes'])} mesh(es), {len(data)} bytes")


def validate_before_export(mesh: MeshData, spec_type: str) -> dict[str, dict[str, Any]]:
    from ..registry import get_descriptor

    return get_descriptor(spec_type).validate(mesh)
