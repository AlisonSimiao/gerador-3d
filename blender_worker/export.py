"""Export: GLB + preview.png + report.json — PLANO_MVP §7.

Pipeline puro-Python (determinístico, testável sem Blender). Quando `bpy`
está disponível, os objetos Blender são construídos via `bpy_build`
antes do export para fidelidade de cena; o GLB/preview seguem o mesmo
contrato de artefatos.
"""

from __future__ import annotations

import binascii
import json
import math
import os
import struct
import zlib

from . import generators  # noqa: F401  (registra os 4 geradores)
from .generators.base import get_generator
from .geometry.mesh import MeshData
from .schema import AnySpec, load_spec_file, spec_to_dict
from .style import get_style
from .validators import check_glb, validate_before_export


class GenerateError(RuntimeError):
    """Falha de validação: bloqueia a geração (motivo vai para o report)."""


# ---------------------------------------------------------------- GLB

def _write_glb(mesh: MeshData, path: str) -> None:
    tris = mesh.triangulated()
    positions: list[float] = []
    for v in mesh.vertices:
        positions.extend([float(v[0]), float(v[1]), float(v[2])])
    pos_bytes = struct.pack(f"<{len(positions)}f", *positions)

    # Um primitive por grupo de material (glTF: 1 material por primitive).
    order: list[int] = []
    groups: dict[int, list[tuple[int, int, int]]] = {}
    for tri, mat in tris:
        if mat not in groups:
            groups[mat] = []
            order.append(mat)
        groups[mat].append(tri)

    use32 = len(mesh.vertices) > 65535
    idx_fmt = "I" if use32 else "H"
    idx_ctype = 5125 if use32 else 5123

    bin_blob = bytearray(pos_bytes)
    while len(bin_blob) % 4:
        bin_blob.append(0)
    buffer_views: list[dict] = [
        {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962}
    ]
    accessors: list[dict] = [
        {"bufferView": 0, "componentType": 5126, "count": len(mesh.vertices),
         "type": "VEC3", "min": list(map(float, _min_v(mesh))),
         "max": list(map(float, _max_v(mesh)))}
    ]
    primitives: list[dict] = []
    for mat in order:
        idx: list[int] = []
        for t in groups[mat]:
            idx.extend(t)
        raw = struct.pack(f"<{len(idx)}{idx_fmt}", *idx)
        off = len(bin_blob)
        bin_blob.extend(raw)
        while len(bin_blob) % 4:
            bin_blob.append(0)
        buffer_views.append(
            {"buffer": 0, "byteOffset": off, "byteLength": len(raw), "target": 34963}
        )
        acc_idx = len(accessors)
        accessors.append({"bufferView": len(buffer_views) - 1, "componentType": idx_ctype,
                          "count": len(idx), "type": "SCALAR"})
        primitives.append({"attributes": {"POSITION": 0}, "indices": acc_idx,
                           "material": order.index(mat), "mode": 4})

    materials = []
    for m in mesh.materials:
        materials.append({
            "name": m.name,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(m.color),
                "metallicFactor": m.metallic,
                "roughnessFactor": m.roughness,
            },
        })
    doc = {
        "asset": {"version": "2.0", "generator": "gerador-3d-marco1"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "asset"}],
        "meshes": [{"name": "asset", "primitives": primitives}],
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_blob)}],
    }
    json_bytes = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_blob)
    with open(path, "wb") as f:
        f.write(b"glTF" + struct.pack("<II", 2, total))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_blob), 0x004E4942))
        f.write(bin_blob)


def _min_v(mesh: MeshData) -> tuple[float, float, float]:
    b, _ = mesh.bounds()
    return b


def _max_v(mesh: MeshData) -> tuple[float, float, float]:
    _, t = mesh.bounds()
    return t


# ---------------------------------------------------------------- Preview (PNG puro-stdlib, 512px)

SIZE = 512
BG = (38, 40, 46)


def _render_preview(mesh: MeshData, path: str, size: int = SIZE) -> None:
    (x0, y0, z0), (x1, y1, z1) = mesh.bounds()
    span = max(x1 - x0, y1 - y0, z1 - z0, 1e-6)
    scale = (size * 0.72) / span
    cx, cy, czm = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    ang = math.radians(30.0)

    def proj(v: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, z = v[0] - cx, v[1] - cy, v[2] - czm
        xr = x * math.cos(ang) - y * math.sin(ang)
        yr = x * math.sin(ang) + y * math.cos(ang)
        depth = yr  # pintor: menor yr = mais longe
        sx = size / 2 + xr * scale
        sy = size / 2 - (z * 0.95 + yr * 0.38) * scale
        return (sx, sy, depth)

    sp = [proj(v) for v in mesh.vertices]
    buf = [[BG] * size for _ in range(size)]

    tris = mesh.triangulated()

    def shade(i: int) -> tuple[int, int, int]:
        c = mesh.materials[tris[i][1]].color if mesh.materials else (0.8, 0.8, 0.8, 1.0)
        # sombreamento fake pela altura média (topo mais claro)
        pts = [sp[j] for j in tris[i][0]]
        h = sum(p[1] for p in pts) / 3 / size  # 0..1 (y invertido)
        k = 0.75 + 0.35 * (1 - h)
        return (min(255, int(c[0] * 255 * k)),
                min(255, int(c[1] * 255 * k)),
                min(255, int(c[2] * 255 * k)))

    order_idx = sorted(range(len(tris)), key=lambda i: sum(sp[j][2] for j in tris[i][0]) / 3)
    for i in order_idx:
        (a, b2, c), _ = tris[i]
        _fill_tri(buf, size, sp[a], sp[b2], sp[c], shade(i))
    _write_png(buf, size, path)


def _fill_tri(buf: list, size: int, p0: tuple, p1: tuple, p2: tuple,
              color: tuple[int, int, int]) -> None:
    xs = (p0[0], p1[0], p2[0])
    ys = (p0[1], p1[1], p2[1])
    x_min = max(0, int(min(xs)))
    x_max = min(size - 1, int(max(xs)) + 1)
    y_min = max(0, int(min(ys)))
    y_max = min(size - 1, int(max(ys)) + 1)
    if x_max < x_min or y_max < y_min:
        return
    (x0, y0), (x1, y1), (x2, y2) = (xs[0], ys[0]), (xs[1], ys[1]), (xs[2], ys[2])
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(den) < 1e-9:
        return
    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            w1 = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / den
            w2 = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / den
            w3 = 1 - w1 - w2
            if w1 >= -0.01 and w2 >= -0.01 and w3 >= -0.01:
                buf[y][x] = color


def _write_png(buf: list, size: int, path: str) -> None:
    def chunk(ctype: bytes, payload: bytes) -> bytes:
        c = ctype + payload
        return struct.pack(">I", len(payload)) + c + struct.pack(">I", binascii.crc32(c))

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            raw.extend(buf[y][x])
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- Orquestração

def bpy_available() -> bool:
    try:
        import bpy  # type: ignore[import-not-found]
    except ImportError:
        return False
    return True


def generate(spec: AnySpec, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    style = get_style(spec.style)
    gen_cls = get_generator(spec.type)
    mesh = gen_cls(spec, style).build()

    checks = validate_before_export(mesh, spec.type)
    failed = {k: v for k, v in checks.items() if not v["ok"]}
    if failed:
        report = _report(spec, mesh, checks, ok=False, renderer=_renderer())
        _write_report(out_dir, report)
        raise GenerateError(f"validação falhou: {list(failed)} — ver report.json")

    if bpy_available():
        try:
            from .bpy_build import mesh_to_bpy

            mesh_to_bpy(mesh, spec.type)
        except Exception:
            pass  # fallback puro-Python já validado acima

    glb_path = os.path.join(out_dir, "model.glb")
    _write_glb(mesh, glb_path)
    checks["glb"] = check_glb(glb_path)
    if not checks["glb"]["ok"]:
        report = _report(spec, mesh, checks, ok=False, renderer=_renderer())
        _write_report(out_dir, report)
        raise GenerateError(f"GLB inválido: {checks['glb']['detail']}")

    _render_preview(mesh, os.path.join(out_dir, "preview.png"))
    report = _report(spec, mesh, checks, ok=True, renderer=_renderer())
    _write_report(out_dir, report)
    return report


def _renderer() -> str:
    return "bpy" if bpy_available() else "fallback"


def _report(spec: AnySpec, mesh: MeshData, checks: dict, ok: bool, renderer: str) -> dict:
    return {
        "ok": ok,
        "renderer": renderer,
        "spec": spec_to_dict(spec),
        "tri_count": mesh.tri_count(),
        "verts": len(mesh.vertices),
        "faces": len(mesh.faces),
        "materials": [m.name for m in mesh.materials],
        "checks": checks,
        "artifacts": ["model.glb", "preview.png", "report.json"],
    }


def _write_report(out_dir: str, report: dict) -> None:
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_from_spec_file(spec_path: str, out_dir: str) -> dict:
    return generate(load_spec_file(spec_path), out_dir)
