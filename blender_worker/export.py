"""Official Blender export plus the temporary preview/report orchestration."""

from __future__ import annotations

import json
import os
import platform
import shutil
import struct
import tempfile
import time
import tracemalloc
from typing import Any

from . import generators  # noqa: F401  (registra os 4 geradores)
from .registry import get_descriptor
from .geometry.mesh import AnchorKind, MeshData
from .schema import AnySpec, load_spec_file, spec_to_dict
from .validators import check_glb
from .failures import FailureCode, stage_for_code, structured_error


class GenerateError(RuntimeError):
    """A structured pipeline failure."""
    def __init__(self, message: str, code: FailureCode = FailureCode.VALIDATION_FAILED,
                 *, stages: dict[str, float] | None = None, peak: int | None = None) -> None:
        super().__init__(message)
        self.code = code.value
        self.stages = dict(stages) if stages else {}
        self.peak = peak


class _StageClock:
    """Wall-time laps plus approximate peak memory for one attempt.

    Every report carries the resulting metrics: per-stage durations where
    the attempt got far enough to record them, always `total_seconds`, and
    the tracemalloc peak — on success and failure paths alike.
    """
    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._mark = self._start
        self._laps: dict[str, float] = {}
        self._owns_tracing = not tracemalloc.is_tracing()
        if self._owns_tracing:
            tracemalloc.start()

    def lap(self, name: str) -> float:
        now = time.perf_counter()
        elapsed = now - self._mark
        self._mark = now
        self._laps[name] = elapsed
        return elapsed

    @property
    def laps(self) -> dict[str, float]:
        return dict(self._laps)

    def snapshot(self) -> tuple[dict[str, float], int]:
        stages = dict(self._laps)
        stages["total_seconds"] = time.perf_counter() - self._start
        _, peak = tracemalloc.get_traced_memory()
        return stages, peak

    def stop(self) -> None:
        if self._owns_tracing:
            tracemalloc.stop()
            self._owns_tracing = False


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
    clock = _StageClock()
    try:
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
        clock.lap("inspect")
        failed = {k: v for k, v in checks.items() if not v["ok"]}
        if failed:
            shutil.rmtree(stage)
            stages, peak = clock.snapshot()
            raise GenerateError(f"validação falhou: {list(failed)}",
                                stages={k: v for k, v in stages.items() if k != "total_seconds"},
                                peak=peak)
        try:
            import bpy  # type: ignore[import-not-found]
            from .bpy_build import mesh_to_bpy
            bpy.ops.wm.read_factory_settings(use_empty=True); mesh_to_bpy(mesh, spec.type)
            clock.lap("build")
            glb_path = os.path.join(stage, "model.glb")
            # Explicit internal→glTF conversion: mesh_to_bpy rotated the IR
            # into Blender space; export_yup=True + metric units emit +Y up / meters.
            _export_glb(glb_path)
            clock.lap("export")
            checks["reimport"] = _reimport_gate(glb_path, mesh)
            clock.lap("reimport")
            if not checks["reimport"]["ok"]: raise GenerateError(checks["reimport"]["detail"], FailureCode.REIMPORT_FAILED)
            from .preview import render_official_preview
            checks["preview"] = render_official_preview(os.path.join(stage, "preview.png"))
            clock.lap("render")
            stages, peak = clock.snapshot()
            report = _report(spec, mesh, checks, ok=True, renderer="bpy", stages=stages, peak=peak)
            _write_report(stage, report)
            backup = destination + ".previous"
            if os.path.exists(backup): shutil.rmtree(backup)
            if os.path.exists(destination): os.replace(destination, backup)
            os.replace(stage, destination)
            if os.path.exists(backup): shutil.rmtree(backup)
            return report
        except Exception as error:
            shutil.rmtree(stage, ignore_errors=True)
            if isinstance(error, GenerateError):
                if not error.stages:
                    error.stages = clock.laps
                if error.peak is None:
                    error.peak = clock.snapshot()[1]
                raise
            stages, peak = clock.snapshot()
            raise GenerateError(str(error), FailureCode.BUILD_FAILED,
                                stages={k: v for k, v in stages.items() if k != "total_seconds"},
                                peak=peak) from error
    finally:
        clock.stop()


def _renderer() -> str:
    return "bpy" if bpy_available() else "fallback"


# glTF coordinate contract (ADR 0007): right-handed, +Y up, +Z front,
# meters, Anchor at the origin. `mesh_to_bpy` already rotated the IR into
# Blender space; `export_yup=True` + metric units finish the conversion.
GLTF_COORDINATE_SYSTEM = {"handedness": "right", "up": "+Y", "front": "+Z", "unit": "meter"}


def _identity_4x4(matrix: Any, tolerance: float = 1e-6) -> bool:
    rows = [list(row) for row in matrix]
    return all(
        abs(value - (1.0 if row == col else 0.0)) < tolerance
        for row, line in enumerate(rows)
        for col, value in enumerate(line)
    )


def _export_glb(path: str) -> None:
    """Official scene→GLB step (Blender glTF exporter, +Y up, meters)."""
    import bpy  # type: ignore[import-not-found]

    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True)


#: Slack (meters) for the IR→glTF→Blender roundtrip: the exporter writes
#: float32, so coordinates that went through Blender gain ~1e-7 relative
#: noise. A wrong unit (cm/mm) would shift extents by 10–1000x, far above this.
REIMPORT_TOLERANCE_M = 1e-3
#: A zero-area reimported polygon is degenerate when below this (m²); the
#: smallest real faces the generators emit are ~1e-4 m².
REIMPORT_MIN_FACE_AREA = 1e-7
#: Plausible Asset extents in meters (units proof, mirrors check_transform).
REIMPORT_MIN_EXTENT_M = 0.05
REIMPORT_MAX_EXTENT_M = 60.0


def _expected_reimport_bounds(mesh: MeshData) -> tuple[tuple[float, float, float],
                                                      tuple[float, float, float]]:
    """IR bounds mapped into reimported Blender space.

    `mesh_to_bpy` emits (-x, -y, z) and the glTF export/import roundtrip
    preserves Blender space, so the origin stays fixed while X/Y flip.
    """
    (x0, y0, z0), (x1, y1, z1) = mesh.bounds()
    return ((-x1, -y1, z0), (-x0, -y0, z1))


def _anchor_holds(bounds_min: tuple[float, float, float],
                  bounds_max: tuple[float, float, float],
                  kind: AnchorKind, tolerance: float = REIMPORT_TOLERANCE_M) -> bool:
    """Anchor semantics checked against reimported world bounds (meters)."""
    if kind is AnchorKind.SUPPORT_SURFACE:
        return (abs(bounds_min[2]) <= tolerance
                and bounds_min[0] <= tolerance <= bounds_max[0]
                and bounds_min[1] <= tolerance <= bounds_max[1])
    if kind is AnchorKind.GRIP_CENTER:
        return all(lo - tolerance <= 0.0 <= hi + tolerance
                   for lo, hi in zip(bounds_min, bounds_max))
    return False


def _reimport_gate(path: str, mesh: MeshData) -> dict:
    """Prove the delivered Asset by reimporting it with Blender (ADR 0006).

    Runs inside the attempt, before any publication: topology (no degenerate
    faces, no orphan verts, tri count preserved), assigned materials (every
    expected material present and used by ≥1 face), Anchor at the origin,
    identity transforms, metric units with matching extents, and overall
    integrity of the roundtrip.
    """
    import bpy  # type: ignore[import-not-found]

    expected_names = sorted({mesh.materials[i].name for i in set(mesh.face_materials)})
    # Actual tris handed to Blender. (MeshData.tri_count overcounts quads and
    # stays as-is: budgets and the report contract depend on it.)
    expected_tris = len(mesh.triangulated())
    exp_min, exp_max = _expected_reimport_bounds(mesh)
    expected_extent = max(hi - lo for lo, hi in zip(exp_min, exp_max))

    def _reject(detail: str, **fields: Any) -> dict:
        result = {"ok": False, "detail": f"reimportação rejeitada: {detail}",
                  "mesh_count": 0, "root_nodes": 0,
                  "root_transform_identity": False,
                  "coordinate_system": dict(GLTF_COORDINATE_SYSTEM),
                  "topology_ok": False, "tri_count": 0,
                  "tri_count_expected": expected_tris,
                  "materials_ok": False, "material_names": [],
                  "anchor_ok": False, "anchor_kind": mesh.anchor_kind.value,
                  "transforms_ok": False,
                  "units_ok": False, "units": {"system": None, "scale_length": None},
                  "integrity_ok": False}
        result.update(fields)
        return result

    smoke = check_glb(path)
    if not smoke["ok"]:
        return _reject(f"GLB inválido ({smoke['detail']})")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        result = bpy.ops.import_scene.gltf(filepath=path)
    except (OSError, RuntimeError) as error:
        return _reject(f"o importador glTF falhou ({error})")
    if "FINISHED" not in result:
        return _reject("o importador glTF não concluiu a reimportação")
    bpy.context.view_layer.update()
    objects = list(bpy.context.scene.objects)
    roots = [obj for obj in objects if obj.parent is None]
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if len(meshes) != 1 or len(roots) != 1:
        return _reject(f"esperado 1 mesh/1 nó raiz, obtido {len(meshes)}/{len(roots)}",
                       mesh_count=len(meshes), root_nodes=len(roots))
    obj = meshes[0]
    data = obj.data
    identity = _identity_4x4(obj.matrix_world)
    transforms_ok = bool(identity) and all(_identity_4x4(o.matrix_world) for o in objects)

    polygons = list(data.polygons)
    degenerate = [p.index for p in polygons
                  if len(p.loop_indices) < 3 or p.area < REIMPORT_MIN_FACE_AREA]
    used: set[int] = set()
    for poly in polygons:
        used.update(poly.vertices)
    orphan = len(used) != len(data.vertices)
    # The glTF importer rebuilds quads from triangle pairs, so polygon count
    # is not the tri count: count loop triangles (what the exporter wrote).
    data.calc_loop_triangles()
    tri_count = len(data.loop_triangles)
    topology_ok = not degenerate and not orphan and tri_count == expected_tris

    names = [m.name if m is not None else "" for m in data.materials]
    slots_used = {p.material_index for p in polygons}
    materials_ok = (set(names) == set(expected_names) and len(names) == len(expected_names)
                    and all(p.material_index < len(names) for p in polygons)
                    and set(range(len(names))) <= slots_used)

    world = [obj.matrix_world @ v.co for v in data.vertices]
    wmin = (min(c.x for c in world), min(c.y for c in world), min(c.z for c in world))
    wmax = (max(c.x for c in world), max(c.y for c in world), max(c.z for c in world))
    anchor_ok = _anchor_holds(wmin, wmax, mesh.anchor_kind)
    bounds_ok = all(abs(a - b) <= REIMPORT_TOLERANCE_M
                    for a, b in zip(wmin + wmax, exp_min + exp_max))

    units = bpy.context.scene.unit_settings
    extent = max(hi - lo for lo, hi in zip(wmin, wmax))
    units_ok = (units.system == "METRIC" and units.scale_length == 1.0
                and REIMPORT_MIN_EXTENT_M <= extent <= REIMPORT_MAX_EXTENT_M
                and abs(extent - expected_extent)
                <= REIMPORT_TOLERANCE_M + 1e-3 * expected_extent)

    integrity_ok = bool(topology_ok and materials_ok and anchor_ok and bounds_ok
                        and transforms_ok and units_ok)
    ok = bool(identity and materials_ok and integrity_ok)
    if ok:
        detail = (f"{len(meshes)} mesh, 1 nó raiz, materiais preservados, "
                  "topologia/âncora/unidades íntegras")
    else:
        reasons = []
        if not topology_ok:
            if degenerate:
                reasons.append(f"{len(degenerate)} face(s) degenerada(s)")
            if orphan:
                reasons.append("vértices órfãos")
            if tri_count != expected_tris:
                reasons.append(f"{tri_count} tris reimportados ≠ {expected_tris} esperados")
        if not materials_ok:
            reasons.append(f"materiais {names} ≠ {expected_names} ou slots sem faces")
        if not anchor_ok:
            reasons.append(f"Âncora {mesh.anchor_kind.value} fora da origem")
        if not bounds_ok:
            reasons.append("limites reimportados divergem da IR")
        if not transforms_ok:
            reasons.append("transformações não-identidade")
        if not units_ok:
            reasons.append("unidades/extensão fora do contrato métrico")
        detail = f"reimportação rejeitada: {'; '.join(reasons) or 'GLB não conformante'}"
    return {"ok": ok, "detail": detail,
            "mesh_count": len(meshes), "root_nodes": len(roots),
            "root_transform_identity": bool(identity),
            "coordinate_system": dict(GLTF_COORDINATE_SYSTEM),
            "topology_ok": bool(topology_ok), "tri_count": tri_count,
            "tri_count_expected": expected_tris,
            "materials_ok": bool(materials_ok), "material_names": names,
            "anchor_ok": bool(anchor_ok), "anchor_kind": mesh.anchor_kind.value,
            "transforms_ok": bool(transforms_ok),
            "units_ok": bool(units_ok),
            "units": {"system": str(units.system), "scale_length": float(units.scale_length)},
            "integrity_ok": bool(integrity_ok)}


def _report(spec: AnySpec, mesh: MeshData, checks: dict, ok: bool, renderer: str,
            stages: dict[str, float] | None = None, peak: int = 0) -> dict:
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
        "error": None, "metrics": {"stages": dict(stages) if stages else {"total_seconds": 0.0},
                                   "peak_memory_bytes": peak},
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
    clock = _StageClock()
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
                stages, peak = clock.snapshot()
                if isinstance(error, GenerateError) and error.stages:
                    partial = dict(error.stages)
                    partial.pop("total_seconds", None)
                    partial.update(stages)
                    stages = partial
                report = {"schema_version": 1, "status": "failure", "ok": False,
                          "stage": stage_for_code(code),
                          "backend": "bpy" if bpy_available() else None,
                          "environment": {"worker": "0.1.0", "blender": _blender_version(),
                                          "process_id": os.getpid(),
                                          "python": platform.python_version(), "render_profile": "medieval_lowpoly-v1"},
                          "resolved_spec": None, "checks": {}, "artifacts": ["report.json"],
                          "error": structured_error(code, str(error)),
                          "metrics": {"stages": stages, "peak_memory_bytes": peak}}
                _write_report(out_dir, report)
            except OSError:
                pass
        raise
    finally:
        clock.stop()


def generate_from_spec_file(
    spec_path: str, out_dir: str, *, force: bool = False, timeout_seconds: float | None = None
) -> dict:
    """Run one official generation in a fresh process."""
    from .process_runner import run_generation_process

    return run_generation_process(
        spec_path, out_dir, force=force, timeout_seconds=timeout_seconds
    )
