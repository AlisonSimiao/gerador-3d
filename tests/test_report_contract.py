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

from blender_worker import export, reports
from blender_worker.export import generate_in_process_from_spec_file
from blender_worker.failures import REPORT_STAGES, FailureCode, stage_for_code
from blender_worker.process_runner import run_generation_process
from blender_worker.schema import load_spec, load_spec_file, spec_to_dict

#: Stable top-level fields every report carries (ADR 0007 + ticket 13).
REQUIRED_TOP_LEVEL = frozenset({
    "schema_version",
    "attempt_id",
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
    for key in ("worker", "blender", "python", "render_profile", "build_commit"):
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
        assert report["generation_fingerprint"].startswith("sha256:")
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
    assert report["input_hash"].startswith("sha256:")
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


def _resolved_house(seed: int = 7) -> dict:
    return spec_to_dict(load_spec({"spec_version": 1, "type": "house", "seed": seed}))


def test_fingerprint_derives_from_resolved_spec_and_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A pinned environment yields a known-good fingerprint, so an accidental
    # change to the derivation inputs is caught rather than silently accepted.
    monkeypatch.setattr(reports, "WORKER_VERSION", "worker-fixture")
    monkeypatch.setattr(reports, "RENDER_PROFILE", "profile-fixture")
    resolved = {"spec_version": 1, "type": "house", "seed": 7}

    assert reports.generation_fingerprint(
        resolved, blender_version="4.2.0-fixture",
    ) == "sha256:dbdcdf477a288743de1d57e7472582aea741d43605a068442bdd2ce5f6feb801"

    baseline = reports.generation_fingerprint(resolved, blender_version="4.2.0")
    # Each relevant version participates in the fingerprint.
    assert reports.generation_fingerprint(
        resolved, blender_version="4.3.0",
    ) != baseline
    monkeypatch.setattr(reports, "WORKER_VERSION", "other-worker")
    assert reports.generation_fingerprint(
        resolved, blender_version="4.2.0",
    ) != baseline


def test_fingerprint_ignores_key_order_and_equivalent_resolved_specs() -> None:
    # Two raw representations that resolve to one Resolved Spec must agree, so
    # equivalence is a property of the Resolved Spec, not of key ordering.
    minimal_raw = {"spec_version": 1, "type": "house", "seed": 42}
    expanded_raw = json.loads(Path("specs/house_default.json").read_text())
    resolved = spec_to_dict(load_spec(minimal_raw))
    assert spec_to_dict(load_spec(expanded_raw)) == resolved

    fingerprint = reports.generation_fingerprint(resolved, blender_version="4.2.0")
    assert reports.generation_fingerprint(
        dict(reversed(list(resolved.items()))), blender_version="4.2.0",
    ) == fingerprint


def test_fingerprint_is_independent_of_attempt_identity_and_not_seed_alone(
    tmp_path: Path,
) -> None:
    resolved = _resolved_house(seed=42)

    def fingerprint_for_attempt(attempt_id: str) -> str:
        report = reports.success_report(
            attempt_id=attempt_id,
            resolved_spec=resolved,
            checks={},
            blender="4.2.0",
            metrics={"stages": {"total_seconds": 0.0}, "peak_memory_bytes": 0},
            tri_count=1, verts=1, faces=1, materials=[],
        )
        return str(report["generation_fingerprint"])

    assert fingerprint_for_attempt("attempt-one") == fingerprint_for_attempt("attempt-two")
    # The Seed is an input to the fingerprint, never the identity itself.
    assert fingerprint_for_attempt("attempt-one") != (
        reports.generation_fingerprint(_resolved_house(seed=43), blender_version="4.2.0")
    )


def test_success_report_records_attempt_identity_and_fingerprint() -> None:
    report = reports.success_report(
        attempt_id="attempt-identity",
        resolved_spec=_resolved_house(seed=42),
        checks={},
        blender="4.2.0",
        metrics={"stages": {"total_seconds": 0.0}, "peak_memory_bytes": 0},
        tri_count=1, verts=1, faces=1, materials=[],
    )

    assert_report_contract(report)
    assert report["attempt_id"] == "attempt-identity"
    assert report["generation_fingerprint"] == reports.generation_fingerprint(
        report["resolved_spec"], blender_version="4.2.0",
    )


def test_invalid_input_report_records_only_attempt_identity_and_safe_hash() -> None:
    secret = "conteúdo-arbitrário-rejeitado"
    report = reports.failure_report(
        attempt_id="attempt-invalid-identity",
        code=FailureCode.INPUT_INVALID,
        detail="campo desconhecido",
        input_value={"type": "house", "unknown": secret},
    )

    assert_report_contract(report)
    assert report["attempt_id"] == "attempt-invalid-identity"
    assert report["input_hash"] == reports.safe_input_hash(
        {"type": "house", "unknown": secret},
    )
    # No fingerprint is claimed for input that never resolved.
    assert "generation_fingerprint" not in report
    assert report["resolved_spec"] is None
    assert secret not in json.dumps(report, ensure_ascii=False)


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
