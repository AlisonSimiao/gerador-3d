"""Versioned construction of terminal validation reports."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .failures import FailureCode, stage_for_code, structured_error

WORKER_VERSION = "0.1.0"
RENDER_PROFILE = "medieval_lowpoly-v2"


def attempt_storage_token(attempt_id: str) -> str:
    """Derive a filesystem-safe token without changing the opaque identity."""
    return hashlib.sha256(attempt_id.encode()).hexdigest()[:32]


def attempt_backup_path(destination: Path, attempt_id: str) -> Path:
    """Name the recoverable backup owned by one replacement attempt."""
    token = attempt_storage_token(attempt_id)
    return destination.with_name(f"{destination.name}.previous-{token}")


def safe_input_hash(value: object) -> str:
    """Correlate rejected JSON without copying its contents into a report."""
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()
    except (TypeError, ValueError):
        encoded = repr(type(value).__name__).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def generation_fingerprint(
    resolved_spec: Mapping[str, object], *, blender_version: str,
) -> str:
    logical_environment = {
        "resolved_spec": dict(resolved_spec),
        "worker": WORKER_VERSION,
        "blender": blender_version,
        "style_profile": RENDER_PROFILE,
    }
    encoded = json.dumps(
        logical_environment, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def environment(*, blender: str | None) -> dict[str, Any]:
    return {
        "worker": WORKER_VERSION,
        "blender": blender,
        "python": platform.python_version(),
        "process_id": os.getpid(),
        "render_profile": RENDER_PROFILE,
        "build_commit": (
            os.environ.get("GERADOR_3D_BUILD_COMMIT")
            or os.environ.get("GITHUB_SHA")
        ),
    }


def publish_failure_report(destination: Path, report: Mapping[str, Any]) -> bool:
    """Publish only a report without replacing an occupied destination."""
    if destination.exists() and any(destination.iterdir()):
        return False
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(dict(report), indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return True


def failure_report(
    *,
    attempt_id: str,
    code: FailureCode,
    detail: str,
    input_value: object | None = None,
    stage: str | None = None,
    backend: str | None = None,
    blender: str | None = None,
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    measured = dict(metrics or {})
    stages = dict(measured.get("stages", {}))
    stages.setdefault("total_seconds", 0.0)
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "failure",
        "ok": False,
        "stage": stage or stage_for_code(code),
        "backend": backend,
        "environment": environment(blender=blender),
        "attempt_id": attempt_id,
        "resolved_spec": None,
        "checks": {},
        "artifacts": ["report.json"],
        "error": structured_error(code, detail),
        "metrics": {
            "stages": stages,
            "peak_memory_bytes": int(measured.get("peak_memory_bytes", 0)),
        },
    }
    if input_value is not None:
        report["input_hash"] = safe_input_hash(input_value)
    return report


def success_report(
    *,
    attempt_id: str,
    resolved_spec: Mapping[str, object],
    checks: Mapping[str, object],
    blender: str,
    metrics: Mapping[str, Any],
    tri_count: int,
    verts: int,
    faces: int,
    materials: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "success",
        "ok": True,
        "stage": "published",
        "backend": "bpy",
        "renderer": "bpy",
        "attempt_id": attempt_id,
        "generation_fingerprint": generation_fingerprint(
            resolved_spec, blender_version=blender,
        ),
        "environment": environment(blender=blender),
        "resolved_spec": dict(resolved_spec),
        # Compatibility field retained while consumers migrate to resolved_spec.
        "spec": dict(resolved_spec),
        "tri_count": tri_count,
        "verts": verts,
        "faces": faces,
        "materials": list(materials),
        "checks": dict(checks),
        "artifacts": ["model.glb", "preview.png", "report.json"],
        "error": None,
        "metrics": dict(metrics),
    }


def measured_failure_report(
    *, attempt_id: str, code: FailureCode, detail: str, input_value: object,
) -> dict[str, Any]:
    started = time.perf_counter()
    report = failure_report(
        attempt_id=attempt_id, code=code, detail=detail, input_value=input_value,
    )
    report["metrics"]["stages"]["total_seconds"] = time.perf_counter() - started
    return report
