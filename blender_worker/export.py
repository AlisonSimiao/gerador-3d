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
import platform
import shutil
import struct
import tempfile
import time
import tracemalloc
import zlib

from . import generators  # noqa: F401  (registra os 4 geradores)
from .registry import get_descriptor
from .geometry.mesh import MeshData
from .schema import AnySpec, load_spec_file, spec_to_dict
from .validators import check_glb
from .failures import FailureCode, structured_error


class GenerateError(RuntimeError):
    """A structured pipeline failure."""
    def __init__(self, message: str, code: FailureCode = FailureCode.VALIDATION_FAILED) -> None:
        super().__init__(message)
        self.code = code.value


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

SIZE = 1024
BG = (38, 40, 46)


def _render_preview(mesh: MeshData, path: str, size: int = SIZE) -> None:
    """Render the versioned four-view contact sheet used by the official profile."""
    tile = size // 2
    views = [_render_view(mesh, tile, angle) for angle in (30.0, 0.0, 90.0, 180.0)]
    board = [[BG for _ in range(size)] for _ in range(size)]
    for index, view in enumerate(views):
        ox, oy = (index % 2) * tile, (index // 2) * tile
        for y, row in enumerate(view): board[oy + y][ox:ox + tile] = row
    _write_png(board, size, path)


def _render_view(mesh: MeshData, size: int, angle_degrees: float) -> list:
    (x0, y0, z0), (x1, y1, z1) = mesh.bounds()
    span = max(x1 - x0, y1 - y0, z1 - z0, 1e-6)
    scale = (size * 0.72) / span
    cx, cy, czm = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    ang = math.radians(angle_degrees)

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
    return buf


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


def inspect(spec: AnySpec) -> tuple[MeshData, dict]:
    """Build and validate the IR without publishing an official result."""
    descriptor = get_descriptor(spec.type)
    return descriptor.inspect(spec)


def generate(spec: AnySpec, out_dir: str, *, force: bool = False) -> dict:
    """Produce an atomic official Result of Generation using Blender."""
    started = time.perf_counter(); tracemalloc.start()
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise GenerateError("plataforma oficial requer Linux x86_64", FailureCode.ENVIRONMENT_UNAVAILABLE)
    if not bpy_available():
        raise GenerateError("bpy 5.2.2 indisponível; use inspect() para a IR", FailureCode.ENVIRONMENT_UNAVAILABLE)
    destination = os.path.abspath(out_dir); parent = os.path.dirname(destination)
    os.makedirs(parent, exist_ok=True)
    if os.path.exists(destination) and os.listdir(destination) and not force:
        raise GenerateError("destino já contém um Resultado de Geração", FailureCode.PUBLICATION_FAILED)
    attempt_id = os.environ.get("GERADOR_3D_ATTEMPT_ID", "local")
    stage = tempfile.mkdtemp(prefix=f".generation-{attempt_id}-", dir=parent)
    mesh, checks = inspect(spec)
    failed = {k: v for k, v in checks.items() if not v["ok"]}
    if failed:
        shutil.rmtree(stage); raise GenerateError(f"validação falhou: {list(failed)}")
    try:
        import bpy  # type: ignore[import-not-found]
        from .bpy_build import mesh_to_bpy
        bpy.ops.wm.read_factory_settings(use_empty=True); mesh_to_bpy(mesh, spec.type)
        glb_path = os.path.join(stage, "model.glb")
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", export_yup=True)
        checks["reimport"] = _reimport_gate(glb_path, len(set(mesh.face_materials)))
        if not checks["reimport"]["ok"]: raise GenerateError(checks["reimport"]["detail"], FailureCode.REIMPORT_FAILED)
        _render_preview(mesh, os.path.join(stage, "preview.png"))
        _, peak = tracemalloc.get_traced_memory()
        report = _report(spec, mesh, checks, ok=True, renderer="bpy", duration=time.perf_counter()-started, peak=peak)
        _write_report(stage, report)
        backup = destination + ".previous"
        if os.path.exists(backup): shutil.rmtree(backup)
        if os.path.exists(destination): os.replace(destination, backup)
        os.replace(stage, destination)
        if os.path.exists(backup): shutil.rmtree(backup)
        return report
    except Exception as error:
        shutil.rmtree(stage, ignore_errors=True)
        if isinstance(error, GenerateError): raise
        raise GenerateError(str(error), FailureCode.BUILD_FAILED) from error
    finally:
        tracemalloc.stop()


def _renderer() -> str:
    return "bpy" if bpy_available() else "fallback"


def _reimport_gate(path: str, material_count: int) -> dict:
    import bpy  # type: ignore[import-not-found]
    smoke = check_glb(path)
    if not smoke["ok"]: return smoke
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.gltf(filepath=path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    ok = "FINISHED" in result and len(meshes) == 1 and len(meshes[0].data.materials) == material_count
    return {"ok": ok, "detail": f"{len(meshes)} mesh, materiais preservados" if ok else "GLB reimportado não conformante"}


def _report(spec: AnySpec, mesh: MeshData, checks: dict, ok: bool, renderer: str,
            duration: float = 0.0, peak: int = 0) -> dict:
    return {
        "schema_version": 1, "status": "success" if ok else "failure", "ok": ok,
        "stage": "published" if ok else "validation", "backend": renderer, "renderer": renderer,
        "environment": {"worker": "0.1.0", "blender": _blender_version(), "python": platform.python_version(),
                        "process_id": os.getpid(),
                        "render_profile": "medieval_lowpoly-v1"},
        "resolved_spec": spec_to_dict(spec), "spec": spec_to_dict(spec),
        "tri_count": mesh.tri_count(),
        "verts": len(mesh.vertices),
        "faces": len(mesh.faces),
        "materials": [m.name for m in mesh.materials],
        "checks": checks,
        "artifacts": ["model.glb", "preview.png", "report.json"] if ok else ["report.json"],
        "error": None, "metrics": {"stages": {"total_seconds": duration}, "peak_memory_bytes": peak},
    }


def _blender_version() -> str | None:
    try:
        import bpy  # type: ignore[import-not-found]
        return bpy.app.version_string
    except ImportError: return None


def _write_report(out_dir: str, report: dict) -> None:
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_in_process_from_spec_file(spec_path: str, out_dir: str, *, force: bool = False) -> dict:
    try:
        return generate(load_spec_file(spec_path), out_dir, force=force)
    except Exception as error:
        # Never damage an existing result. For every other attempt, leave only
        # the machine-readable report if its destination can be created.
        occupied = os.path.isdir(out_dir) and bool(os.listdir(out_dir))
        if not occupied:
            try:
                os.makedirs(out_dir, exist_ok=True)
                code = FailureCode.INPUT_INVALID if error.__class__.__name__ == "SpecError" else FailureCode(
                    getattr(error, "code", FailureCode.BUILD_FAILED.value)
                )
                report = {"schema_version": 1, "status": "failure", "ok": False, "stage": "input",
                          "backend": "bpy" if bpy_available() else None,
                          "environment": {"worker": "0.1.0", "blender": _blender_version(),
                                          "process_id": os.getpid(),
                                          "python": platform.python_version(), "render_profile": "medieval_lowpoly-v1"},
                          "resolved_spec": None, "checks": {}, "artifacts": ["report.json"],
                          "error": structured_error(code, str(error)),
                          "metrics": {"stages": {}, "peak_memory_bytes": 0}}
                _write_report(out_dir, report)
            except OSError:
                pass
        raise


def generate_from_spec_file(
    spec_path: str, out_dir: str, *, force: bool = False, timeout_seconds: float | None = None
) -> dict:
    """Run one official generation in a fresh process."""
    from .process_runner import run_generation_process

    return run_generation_process(
        spec_path, out_dir, force=force, timeout_seconds=timeout_seconds
    )
