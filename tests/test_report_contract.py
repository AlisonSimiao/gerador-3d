"""Ticket 13: versioned validation report contract.

Every generation attempt produces a machine-readable report whose stable
field set (ADR 0007) lets the future SaaS backend consume it without
parsing free text. This file pins that contract at the report-builder
seams: `export._report`, `generate_in_process_from_spec_file`, and the
process-runner reports, observed via their dicts and `report.json`.
"""

import json
from pathlib import Path

import pytest

from blender_worker import export
from blender_worker.export import generate_in_process_from_spec_file
from blender_worker.failures import REPORT_STAGES, FailureCode, stage_for_code
from blender_worker.process_runner import run_generation_process
from blender_worker.schema import load_spec_file

#: Stable top-level fields every report carries (ADR 0007 + ticket 13).
REQUIRED_TOP_LEVEL = frozenset({
    "schema_version",
    "status",
    "stage",
    "backend",
    "environment",
    "resolved_spec",
    "checks",
    "artifacts",
    "error",
    "metrics",
})


def assert_report_contract(report: dict) -> None:
    """The full stable field set holds for success AND failure reports."""
    assert REQUIRED_TOP_LEVEL <= set(report), (
        f"missing stable fields: {REQUIRED_TOP_LEVEL - set(report)}"
    )
    assert report["schema_version"] == 1
    assert report["ok"] in (True, False)
    assert report["status"] == ("success" if report["ok"] else "failure")
    assert report["stage"] in REPORT_STAGES, f"undocumented stage: {report['stage']!r}"
    assert report["backend"] in ("bpy", None)
    environment = report["environment"]
    for key in ("worker", "blender", "python", "render_profile"):
        assert key in environment, f"environment missing {key!r}"
    assert isinstance(report["checks"], dict)
    assert isinstance(report["artifacts"], list) and report["artifacts"]
    metrics = report["metrics"]
    assert isinstance(metrics["stages"], dict)
    assert isinstance(metrics["stages"]["total_seconds"], float)
    assert metrics["stages"]["total_seconds"] >= 0.0
    assert isinstance(metrics["peak_memory_bytes"], int)
    assert metrics["peak_memory_bytes"] >= 0
    if report["ok"]:
        assert report["error"] is None
        assert report["resolved_spec"] is not None
    else:
        assert "report.json" in report["artifacts"]
        error = report["error"]
        assert error["taxonomy_version"] == 1
        assert error["code"] in {code.value for code in FailureCode}
        assert error["message"] and error["detail"]


def test_success_report_pins_the_stable_field_set() -> None:
    spec = load_spec_file("specs/house_default.json")
    mesh, checks = export.inspect(spec)

    report = export._report(
        spec,
        mesh,
        checks,
        ok=True,
        renderer="bpy",
        metrics=export.AttemptMetrics(
            {"inspect": 0.01, "build": 0.02, "total_seconds": 0.05}, 12345
        ),
    )

    assert_report_contract(report)
    assert report["stage"] == "published"
    assert report["backend"] == "bpy"
    assert report["resolved_spec"]["type"] == "house"
    # Per-stage durations and the measured peak travel verbatim.
    assert report["metrics"]["stages"] == {"inspect": 0.01, "build": 0.02, "total_seconds": 0.05}
    assert report["metrics"]["peak_memory_bytes"] == 12345
    assert set(("model.glb", "preview.png", "report.json")) <= set(report["artifacts"])


def test_input_failure_report_carries_measured_metrics(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"spec_version": 1, "type": "chest", "seed": 1, "width": -5.0,
                               "height": 0.6, "depth": 0.6, "lid_form": "arched",
                               "band_count": 2, "has_lock": True, "style": "medieval_lowpoly"}))

    with pytest.raises(Exception):
        generate_in_process_from_spec_file(str(bad), str(tmp_path / "out"))

    report = json.loads((tmp_path / "out" / "report.json").read_text())
    assert_report_contract(report)
    assert report["status"] == "failure"
    assert report["stage"] == "input"
    assert report["error"]["code"] == "input.invalid"
    # A failure attempt still measures its own duration and peak (never 0/{}).
    assert "total_seconds" in report["metrics"]["stages"]
    assert report["metrics"]["peak_memory_bytes"] > 0


def test_validation_failure_report_keeps_the_stages_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("bpy")
    spec = load_spec_file("specs/house_default.json")
    mesh, _ = export.inspect(spec)
    monkeypatch.setattr(
        export, "inspect", lambda _spec: (mesh, {"mesh_valid": {"ok": False, "detail": "forced"}})
    )

    with pytest.raises(Exception):
        generate_in_process_from_spec_file("specs/house_default.json", str(tmp_path / "out"))

    report = json.loads((tmp_path / "out" / "report.json").read_text())
    assert_report_contract(report)
    assert report["stage"] == "validation"
    assert report["error"]["code"] == "validation.failed"
    assert "inspect" in report["metrics"]["stages"]
    assert "total_seconds" in report["metrics"]["stages"]


def test_runner_failure_report_carries_measured_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "result"
    monkeypatch.setenv("GERADOR_3D_PYTHON", "/usr/bin/python3")

    with pytest.raises(Exception):
        run_generation_process("specs/house_default.json", str(out), timeout_seconds=10)

    report = json.loads((out / "report.json").read_text())
    assert_report_contract(report)
    assert report["stage"] == "environment"
    assert report["error"]["code"] == "environment.unavailable"
    assert "total_seconds" in report["metrics"]["stages"]
    assert report["metrics"]["peak_memory_bytes"] > 0


def test_stage_values_come_from_the_documented_stable_set() -> None:
    assert "published" in REPORT_STAGES
    assert "input" in REPORT_STAGES
    assert "environment" in REPORT_STAGES
    # Every failure code maps to a documented stage; success keeps "published".
    stages = {stage_for_code(code) for code in FailureCode}
    assert stages <= set(REPORT_STAGES)
    assert "published" not in stages
    assert stage_for_code(FailureCode.INPUT_INVALID) == "input"
    assert stage_for_code(FailureCode.PROCESS_TIMEOUT) == "environment"
    assert stage_for_code(FailureCode.VALIDATION_FAILED) == "validation"
    assert stage_for_code(FailureCode.REIMPORT_FAILED) == "reimport"
