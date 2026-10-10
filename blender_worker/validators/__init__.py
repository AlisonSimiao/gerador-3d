"""Validadores — PLANO_MVP §6. Falha bloqueia a geração (exit ≠ 0 + motivo no report)."""

from __future__ import annotations

import struct
from typing import Any

from ..geometry.mesh import MeshData

def _ok(ok: bool, detail: str = "") -> dict[str, Any]:
    return {"ok": ok, "detail": detail}


def check_mesh_valid(mesh: MeshData) -> dict[str, Any]:
    """Sem faces degeneradas nem geometria não-manifold (checagem de arestas)."""
    if not mesh.faces:
        return _ok(False, "malha sem faces")
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
    # Não-manifold: aresta compartilhada por >2 faces (borda com 1 é OK)
    edge_count: dict[tuple[int, int], int] = {}
    for face in mesh.faces:
        n = len(face)
        for k in range(n):
            e = (min(face[k], face[(k + 1) % n]), max(face[k], face[(k + 1) % n]))
            edge_count[e] = edge_count.get(e, 0) + 1
    bad = [e for e, c in edge_count.items() if c > 2]
    if bad:
        return _ok(False, f"{len(bad)} arestas não-manifold (ex.: {bad[0]})")
    return _ok(True, f"{len(mesh.faces)} faces, {len(mesh.vertices)} verts, manifold")


def check_tri_budget(mesh: MeshData, spec_type: str) -> dict[str, Any]:
    from ..registry import get_descriptor
    budget = get_descriptor(spec_type).triangle_budget
    n = mesh.tri_count()
    if n > budget:
        return _ok(False, f"{n} tris excede orçamento de {budget} para {spec_type}")
    return _ok(True, f"{n}/{budget} tris")


def check_materials(mesh: MeshData) -> dict[str, Any]:
    if not mesh.materials:
        return _ok(False, "nenhum material atribuído")
    for i, m in enumerate(mesh.face_materials):
        if m < 0 or m >= len(mesh.materials):
            return _ok(False, f"face {i} com material inválido ({m})")
    return _ok(True, f"{len(mesh.materials)} materiais, todas as faces cobertas")


def check_transform(mesh: MeshData, spec_type: str) -> dict[str, Any]:
    """Validate the Type-specific Anchor at the origin and scale in metres."""
    if not mesh.vertices:
        return _ok(False, "malha vazia")
    (x0, y0, z0), (x1, y1, z1) = mesh.bounds()
    if mesh.anchor != (0.0, 0.0, 0.0):
        return _ok(False, f"Âncora fora da origem: {mesh.anchor}")
    if spec_type == "sword":
        if not z0 <= 0 <= z1:
            return _ok(False, "centro da empunhadura não coincide com a origem")
    elif abs(z0) > 1e-6:
        return _ok(False, f"superfície de apoio fora da origem (zmin={z0:.4f})")
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # Copas assimétricas (ex.: árvore) deslocam o centro; tolerar até 15% da extensão.
    tol_x = max(0.05, 0.15 * (x1 - x0))
    tol_y = max(0.05, 0.15 * (y1 - y0))
    if abs(cx) > tol_x or abs(cy) > tol_y:
        return _ok(False, f"centro XY fora da origem ({cx:.4f}, {cy:.4f})")
    size = max(x1 - x0, y1 - y0, z1 - z0)
    if not (0.05 <= size <= 60.0):
        return _ok(False, f"escala implausível ({size:.2f} m)")
    return _ok(True, f"Âncora OK, extensão {size:.2f} m")


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
    return {
        "mesh_valid": check_mesh_valid(mesh),
        "tri_budget": check_tri_budget(mesh, spec_type),
        "materials": check_materials(mesh),
        "anchor": check_transform(mesh, spec_type),
    }
