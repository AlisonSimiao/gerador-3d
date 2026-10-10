"""Export: GLB + preview.png + report.json — PLANO_MVP §7.

Pipeline puro-Python (determinístico, testável sem Blender). Quando `bpy`
está disponível, os objetos Blender são construídos via `bpy_build`
antes do export para fidelidade de cena; o GLB/preview seguem o mesmo
contrato de artefatos.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import struct
import tempfile
import time
import tracemalloc

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
        from .preview import render_official_preview
        checks["preview"] = render_official_preview(os.path.join(stage, "preview.png"))
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
