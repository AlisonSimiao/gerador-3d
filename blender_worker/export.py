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
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from . import generators  # noqa: F401  (registra os 4 geradores)
from .registry import get_descriptor
from .geometry.mesh import AnchorKind, MeshData
from .schema import AnySpec, load_spec_file, spec_to_dict
from .validators import check_glb
from .failures import FailureCode
from .reports import (
    attempt_storage_token,
    failure_report,
    publish_failure_report,
    success_report,
)


@dataclass
class AttemptMetrics:
    """Per-stage durations plus the tracemalloc peak for one attempt."""

    stages: dict[str, float] = field(default_factory=dict)
    peak_memory_bytes: int = 0

    def without_total(self) -> dict[str, float]:
        """Partial laps without the running total (failure paths)."""
        return {
            key: value
            for key, value in self.stages.items()
            if key != "total_seconds"
        }


class GenerateError(RuntimeError):
    """A structured pipeline failure."""
    def __init__(self, message: str,
                 code: FailureCode = FailureCode.VALIDATION_FAILED,
                 *, metrics: AttemptMetrics | None = None,
                 report: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code.value
        self.metrics = metrics if metrics is not None else AttemptMetrics()
        self.report = report


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

    def snapshot(self) -> AttemptMetrics:
        stages = dict(self._laps)
        stages["total_seconds"] = time.perf_counter() - self._start
        _, peak = tracemalloc.get_traced_memory()
        return AttemptMetrics(stages, peak)

    def stop(self) -> None:
        if self._owns_tracing:
            tracemalloc.stop()
            self._owns_tracing = False


T = TypeVar("T")


def _run_stage(name: str, code: FailureCode, fn: Callable[[], T],
               clock: _StageClock, *, record_lap: bool = True) -> T:
    """Run one pipeline stage, mapping unexpected errors to its code.

    A `GenerateError` raised inside already carries its own code and
    passes through untouched; anything else becomes `code`. Successful
    stages record a lap, except the publication swap, whose timing is
    not part of the staged metrics contract (`record_lap=False`).
    """
    try:
        result = fn()
    except GenerateError:
        raise
    except Exception as error:
        raise GenerateError(str(error), code) from error
    if record_lap:
        clock.lap(name)
    return result


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


def _ensure_official_platform() -> None:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise GenerateError(
            "plataforma oficial requer Linux x86_64",
            FailureCode.ENVIRONMENT_UNAVAILABLE,
        )
    if not bpy_available():
        raise GenerateError(
            "bpy 5.2.2 indisponível; use inspect() para a IR",
            FailureCode.ENVIRONMENT_UNAVAILABLE,
        )


def _build_scene(mesh: MeshData, spec_type: str) -> None:
    import bpy  # type: ignore[import-not-found]
    from .bpy_build import mesh_to_bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh_to_bpy(mesh, spec_type)


def _publish(stage: str, destination: str) -> None:
    backup = destination + ".previous"
    if os.path.exists(backup):
        shutil.rmtree(backup)
    if os.path.exists(destination):
        os.replace(destination, backup)
    os.replace(stage, destination)
    if os.path.exists(backup):
        shutil.rmtree(backup)


def generate(
    spec: AnySpec, out_dir: str, *, force: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Produce an atomic official Result of Generation using Blender."""
    clock = _StageClock()
    try:
        if progress is not None:
            progress("environment")
        _ensure_official_platform()
        destination = os.path.abspath(out_dir)
        parent = os.path.dirname(destination)
        os.makedirs(parent, exist_ok=True)
        if os.path.exists(destination) and os.listdir(destination) and not force:
            raise GenerateError(
                "destino já contém um Resultado de Geração",
                FailureCode.PUBLICATION_FAILED,
            )
        attempt_id = os.environ.get("GERADOR_3D_ATTEMPT_ID", "local")
        stage = tempfile.mkdtemp(
            prefix=f".generation-{attempt_storage_token(attempt_id)}-", dir=parent
        )
        if progress is not None:
            progress("validation")
        mesh, checks = inspect(spec)
        clock.lap("inspect")
        failed = {k: v for k, v in checks.items() if not v["ok"]}
        if failed:
            shutil.rmtree(stage)
            metrics = clock.snapshot()
            raise GenerateError(
                f"validação falhou: {list(failed)}",
                FailureCode.VALIDATION_FAILED,
                metrics=AttemptMetrics(
                    metrics.without_total(), metrics.peak_memory_bytes
                ),
            )
        try:
            if progress is not None:
                progress("build")
            _run_stage(
                "build", FailureCode.BUILD_FAILED,
                lambda: _build_scene(mesh, spec.type), clock,
            )
            glb_path = os.path.join(stage, "model.glb")
            # Explicit internal→glTF conversion: mesh_to_bpy rotated the
            # IR into Blender space; export_yup=True + metric units emit
            # +Y up / meters.
            if progress is not None:
                progress("export")
            _run_stage(
                "export", FailureCode.EXPORT_FAILED,
                lambda: _export_glb(glb_path), clock,
            )
            if progress is not None:
                progress("reimport")
            checks["reimport"] = _run_stage(
                "reimport", FailureCode.REIMPORT_FAILED,
                lambda: _reimport_gate(glb_path, mesh), clock,
            )
            if not checks["reimport"]["ok"]:
                raise GenerateError(
                    checks["reimport"]["detail"],
                    FailureCode.REIMPORT_FAILED,
                )
            from .preview import render_official_preview
            if progress is not None:
                progress("render")
            checks["preview"] = _run_stage(
                "render", FailureCode.RENDER_FAILED,
                lambda: render_official_preview(
                    os.path.join(stage, "preview.png")
                ),
                clock,
            )
            report = _report(
                spec, mesh, checks, ok=True, renderer="bpy",
                metrics=clock.snapshot(),
            )
            _write_report(stage, report)
            if progress is not None:
                progress("publication")
            _run_stage(
                "publication", FailureCode.PUBLICATION_FAILED,
                lambda: _publish(stage, destination), clock,
                record_lap=False,
            )
            if progress is not None:
                progress("published")
            return report
        except Exception as error:
            shutil.rmtree(stage, ignore_errors=True)
            if isinstance(error, GenerateError):
                if not error.metrics.stages:
                    error.metrics.stages = clock.laps
                if not error.metrics.peak_memory_bytes:
                    error.metrics.peak_memory_bytes = (
                        clock.snapshot().peak_memory_bytes
                    )
                raise
            metrics = clock.snapshot()
            raise GenerateError(
                str(error), FailureCode.BUILD_FAILED,
                metrics=AttemptMetrics(
                    metrics.without_total(), metrics.peak_memory_bytes
                ),
            ) from error
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


def _reject_reimport(expected_tris: int, anchor_kind: str,
                     detail: str, **fields: Any) -> dict:
    result = {"ok": False, "detail": f"reimportação rejeitada: {detail}",
              "mesh_count": 0, "root_nodes": 0,
              "root_transform_identity": False,
              "coordinate_system": dict(GLTF_COORDINATE_SYSTEM),
              "topology_ok": False, "tri_count": 0,
              "tri_count_expected": expected_tris,
              "materials_ok": False, "material_names": [],
              "anchor_ok": False, "anchor_kind": anchor_kind,
              "transforms_ok": False,
              "units_ok": False, "units": {"system": None, "scale_length": None},
              "integrity_ok": False}
    result.update(fields)
    return result


def _reimport_topology(data: Any, expected_tris: int) -> dict[str, Any]:
    """No degenerate faces, no orphan verts, tri count preserved."""
    polygons = list(data.polygons)
    degenerate = [p.index for p in polygons
                  if len(p.loop_indices) < 3 or p.area < REIMPORT_MIN_FACE_AREA]
    used: set[int] = set()
    for poly in polygons:
        used.update(poly.vertices)
    orphan = len(used) != len(data.vertices)
    # The glTF importer rebuilds quads from triangle pairs, so polygon
    # count is not the tri count: count loop triangles instead (what the
    # exporter wrote).
    data.calc_loop_triangles()
    tri_count = len(data.loop_triangles)
    return {
        "topology_ok": not degenerate and not orphan
        and tri_count == expected_tris,
        "tri_count": tri_count,
        "degenerate_count": len(degenerate),
        "orphan": orphan,
    }


def _reimport_materials(data: Any, expected_names: list[str]) -> dict[str, Any]:
    """Every expected material present and used by ≥1 face."""
    polygons = list(data.polygons)
    names = [m.name if m is not None else "" for m in data.materials]
    slots_used = {p.material_index for p in polygons}
    materials_ok = (
        set(names) == set(expected_names)
        and len(names) == len(expected_names)
        and all(p.material_index < len(names) for p in polygons)
        and set(range(len(names))) <= slots_used
    )
    return {"materials_ok": materials_ok, "material_names": names}


def _reimport_placement(objects: list[Any], obj: Any, data: Any, mesh: MeshData,
                        units: Any,
                        exp_min: tuple[float, float, float],
                        exp_max: tuple[float, float, float],
                        expected_extent: float) -> dict[str, Any]:
    """Anchor at the origin, identity transforms, metric units extents."""
    identity = _identity_4x4(obj.matrix_world)
    transforms_ok = bool(identity) and all(
        _identity_4x4(o.matrix_world) for o in objects
    )
    world = [obj.matrix_world @ v.co for v in data.vertices]
    wmin = (
        min(c.x for c in world),
        min(c.y for c in world),
        min(c.z for c in world),
    )
    wmax = (
        max(c.x for c in world),
        max(c.y for c in world),
        max(c.z for c in world),
    )
    anchor_ok = _anchor_holds(wmin, wmax, mesh.anchor_kind)
    bounds_ok = all(
        abs(a - b) <= REIMPORT_TOLERANCE_M
        for a, b in zip(wmin + wmax, exp_min + exp_max)
    )
    extent = max(hi - lo for lo, hi in zip(wmin, wmax))
    units_ok = (
        units.system == "METRIC" and units.scale_length == 1.0
        and REIMPORT_MIN_EXTENT_M <= extent <= REIMPORT_MAX_EXTENT_M
        and abs(extent - expected_extent)
        <= REIMPORT_TOLERANCE_M + 1e-3 * expected_extent
    )
    return {
        "root_transform_identity": bool(identity),
        "transforms_ok": bool(transforms_ok),
        "anchor_ok": bool(anchor_ok),
        "bounds_ok": bool(bounds_ok),
        "units_ok": bool(units_ok),
        "units": {
            "system": str(units.system),
            "scale_length": float(units.scale_length),
        },
    }
def _reimport_integrity(topology: dict[str, Any], materials: dict[str, Any],
                        placement: dict[str, Any], mesh: MeshData,
                        expected_names: list[str],
                        expected_tris: int) -> dict[str, Any]:
    """Combine the per-concern checks into the roundtrip verdict."""
    integrity_ok = bool(
        topology["topology_ok"] and materials["materials_ok"]
        and placement["anchor_ok"] and placement["bounds_ok"]
        and placement["transforms_ok"] and placement["units_ok"]
    )
    ok = bool(
        placement["root_transform_identity"]
        and materials["materials_ok"]
        and integrity_ok
    )
    if ok:
        detail = (
            "1 mesh, 1 nó raiz, materiais preservados, "
            "topologia/âncora/unidades íntegras"
        )
    else:
        reasons = []
        if not topology["topology_ok"]:
            if topology["degenerate_count"]:
                reasons.append(
                    f"{topology['degenerate_count']} face(s) degenerada(s)"
                )
            if topology["orphan"]:
                reasons.append("vértices órfãos")
            if topology["tri_count"] != expected_tris:
                reasons.append(
                    f"{topology['tri_count']} tris reimportados ≠ "
                    f"{expected_tris} esperados"
                )
        if not materials["materials_ok"]:
            reasons.append(
                f"materiais {materials['material_names']} ≠ "
                f"{expected_names} ou slots sem faces"
            )
        if not placement["anchor_ok"]:
            reasons.append(
                f"Âncora {mesh.anchor_kind.value} fora da origem"
            )
        if not placement["bounds_ok"]:
            reasons.append("limites reimportados divergem da IR")
        if not placement["transforms_ok"]:
            reasons.append("transformações não-identidade")
        if not placement["units_ok"]:
            reasons.append("unidades/extensão fora do contrato métrico")
        joined = "; ".join(reasons) or "GLB não conformante"
        detail = f"reimportação rejeitada: {joined}"
    return {"ok": ok, "detail": detail, "integrity_ok": integrity_ok}


def _reimport_gate(path: str, mesh: MeshData) -> dict:
    """Prove the delivered Asset by reimporting it with Blender (ADR 0006).

    Runs inside the attempt, before any publication. Each concern has
    its own check above (topology / materials / anchor+transforms+units
    / integrity); this gate only loads the scene and coordinates them.
    """
    import bpy  # type: ignore[import-not-found]

    expected_names = sorted(
        {mesh.materials[i].name for i in set(mesh.face_materials)}
    )
    # Actual tris handed to Blender. (MeshData.tri_count overcounts quads
    # and stays as-is: budgets and the report contract depend on it.)
    expected_tris = len(mesh.triangulated())
    exp_min, exp_max = _expected_reimport_bounds(mesh)
    expected_extent = max(hi - lo for lo, hi in zip(exp_min, exp_max))
    anchor_kind = mesh.anchor_kind.value

    smoke = check_glb(path)
    if not smoke["ok"]:
        return _reject_reimport(
            expected_tris, anchor_kind, f"GLB inválido ({smoke['detail']})"
        )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        result = bpy.ops.import_scene.gltf(filepath=path)
    except (OSError, RuntimeError) as error:
        return _reject_reimport(
            expected_tris, anchor_kind, f"o importador glTF falhou ({error})"
        )
    if "FINISHED" not in result:
        return _reject_reimport(
            expected_tris, anchor_kind,
            "o importador glTF não concluiu a reimportação",
        )
    bpy.context.view_layer.update()
    objects = list(bpy.context.scene.objects)
    roots = [obj for obj in objects if obj.parent is None]
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if len(meshes) != 1 or len(roots) != 1:
        return _reject_reimport(
            expected_tris, anchor_kind,
            f"esperado 1 mesh/1 nó raiz, obtido {len(meshes)}/{len(roots)}",
            mesh_count=len(meshes), root_nodes=len(roots),
        )
    obj = meshes[0]
    data = obj.data
    units = bpy.context.scene.unit_settings
    topology = _reimport_topology(data, expected_tris)
    materials = _reimport_materials(data, expected_names)
    placement = _reimport_placement(
        objects, obj, data, mesh, units, exp_min, exp_max, expected_extent
    )
    integrity = _reimport_integrity(
        topology, materials, placement, mesh, expected_names, expected_tris
    )
    return {"ok": integrity["ok"], "detail": integrity["detail"],
            "mesh_count": len(meshes), "root_nodes": len(roots),
            "root_transform_identity": placement["root_transform_identity"],
            "coordinate_system": dict(GLTF_COORDINATE_SYSTEM),
            "topology_ok": bool(topology["topology_ok"]),
            "tri_count": topology["tri_count"],
            "tri_count_expected": expected_tris,
            "materials_ok": bool(materials["materials_ok"]),
            "material_names": materials["material_names"],
            "anchor_ok": bool(placement["anchor_ok"]),
            "anchor_kind": anchor_kind,
            "transforms_ok": bool(placement["transforms_ok"]),
            "units_ok": bool(placement["units_ok"]),
            "units": placement["units"],
            "integrity_ok": bool(integrity["integrity_ok"])}


def _report(spec: AnySpec, mesh: MeshData, checks: dict, ok: bool, renderer: str,
            metrics: AttemptMetrics | None = None) -> dict:
    measured = metrics if metrics is not None else AttemptMetrics()
    resolved_spec = spec_to_dict(spec)
    blender_version = _blender_version() or "unavailable"
    return success_report(
        attempt_id=os.environ.get("GERADOR_3D_ATTEMPT_ID", "local"),
        resolved_spec=resolved_spec,
        checks=checks,
        blender=blender_version,
        tri_count=mesh.tri_count(),
        verts=len(mesh.vertices),
        faces=len(mesh.faces),
        materials=[material.name for material in mesh.materials],
        metrics={
            "stages": dict(measured.stages)
            if measured.stages else {"total_seconds": 0.0},
            "peak_memory_bytes": measured.peak_memory_bytes,
        },
    )


def _blender_version() -> str | None:
    try:
        import bpy  # type: ignore[import-not-found]
        return bpy.app.version_string
    except ImportError: return None


def _write_report(out_dir: str, report: dict) -> None:
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_in_process_from_spec_file(
    spec_path: str, out_dir: str, *, force: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict:
    clock = _StageClock()
    try:
        if progress is not None:
            progress("input")
        return generate(
            load_spec_file(spec_path), out_dir, force=force, progress=progress,
        )
    except Exception as error:
        # Never damage an existing result. For every other attempt, leave only
        # the machine-readable report if its destination can be created.
        occupied = os.path.isdir(out_dir) and bool(os.listdir(out_dir))
        if not occupied:
            try:
                os.makedirs(out_dir, exist_ok=True)
                code = _code_for_in_process_error(error)
                measured = clock.snapshot()
                if isinstance(error, GenerateError) and error.metrics.stages:
                    partial = error.metrics.without_total()
                    partial.update(measured.stages)
                    measured = AttemptMetrics(
                        partial, measured.peak_memory_bytes
                    )
                input_value: object | None = None
                if code is FailureCode.INPUT_INVALID:
                    try:
                        with open(spec_path, encoding="utf-8") as source:
                            raw = source.read()
                        try:
                            input_value = json.loads(raw)
                        except json.JSONDecodeError:
                            input_value = raw
                    except OSError:
                        input_value = {"unreadable": True}
                report = failure_report(
                    attempt_id=os.environ.get("GERADOR_3D_ATTEMPT_ID", "local"),
                    code=code,
                    detail=str(error),
                    input_value=input_value,
                    backend="bpy" if bpy_available() else None,
                    blender=_blender_version(),
                    metrics={
                        "stages": measured.stages,
                        "peak_memory_bytes": measured.peak_memory_bytes,
                    },
                )
                publish_failure_report(Path(out_dir), report)
            except OSError:
                pass
        raise
    finally:
        clock.stop()


def _code_for_in_process_error(error: Exception) -> FailureCode:
    if error.__class__.__name__ == "SpecError":
        return FailureCode.INPUT_INVALID
    return FailureCode(getattr(
        error, "code", FailureCode.BUILD_FAILED.value
    ))


def generate_from_spec_file(
    spec_path: str, out_dir: str, *, force: bool = False, timeout_seconds: float | None = None
) -> dict:
    """Compatibility wrapper around the GenerationAttemptExecutor seam."""
    from pathlib import Path

    from .attempts import (
        ExistingResultPolicy,
        FailedAttempt,
        GenerationAttempt,
        GenerationAttemptExecutor,
        new_attempt_id,
        read_untrusted_spec_file,
    )

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        attempt_id=new_attempt_id(),
        spec=read_untrusted_spec_file(spec_path),
        destination=Path(out_dir),
        existing_result=(ExistingResultPolicy.REPLACE if force else ExistingResultPolicy.REJECT),
        timeout_seconds=timeout_seconds,
    ))
    if isinstance(outcome, FailedAttempt):
        error = outcome.report["error"]
        raise GenerateError(str(error["detail"]), FailureCode(str(error["code"])))
    return outcome.report
