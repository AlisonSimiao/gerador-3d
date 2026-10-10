"""Ticket 14: versioned failure taxonomy — one covered failure path per class.

Seams (pre-agreed, the same ones tickets 10/13 use):
- `export.generate_in_process_from_spec_file` + `report.json` for every class
  except `environment.timeout` (which needs a real child process);
- `process_runner.run_generation_process` with the `GERADOR_3D_PYTHON` seam
  for `environment.timeout` (same fake-executable pattern as
  `test_process_runner.py`);
- `main([...])` for the CLI/report code-parity check.

Every test pins the same contract: the raised `GenerateError.code`, the
report's `error.code`, and the CLI's stderr share exactly one taxonomy code,
while the human message is derived from that code (`MESSAGES`), never free
text, and the report stage follows `stage_for_code`.
"""

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from blender_worker import export
from blender_worker.export import GenerateError, generate_in_process_from_spec_file
from blender_worker.failures import MESSAGES, FailureCode, stage_for_code
from blender_worker.main import main
from blender_worker.process_runner import run_generation_process
from blender_worker.schema import load_spec_file
from tests.test_report_contract import assert_report_contract


def assert_taxonomy_failure(report: dict, raised_code: str, code: FailureCode) -> None:
    """One code everywhere; the human message derives from that code."""
    assert raised_code == code.value
    assert report["error"]["code"] == code.value
    assert report["error"]["taxonomy_version"] == 1
    assert report["error"]["message"] == MESSAGES[code]
    assert report["error"]["detail"]
    assert report["stage"] == stage_for_code(code)
    assert_report_contract(report)


def _read_report(out: Path) -> dict:
    return json.loads((out / "report.json").read_text())


@pytest.fixture
def fake_bpy(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Enough of the Blender API for `generate()` to reach each stage seam."""
    bpy = types.ModuleType("bpy")
    bpy.app = types.SimpleNamespace(version_string="5.2.2-fake")  # type: ignore[attr-defined]
    bpy.ops = types.SimpleNamespace(  # type: ignore[attr-defined]
        wm=types.SimpleNamespace(read_factory_settings=lambda **_: None),
        export_scene=types.SimpleNamespace(gltf=lambda **_: None),
        import_scene=types.SimpleNamespace(gltf=lambda **_: {"FINISHED"}),
    )
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    monkeypatch.setattr("blender_worker.export.bpy_available", lambda: True)
    return bpy


def _bad_spec(tmp_path: Path) -> str:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"spec_version": 1, "type": "chest", "seed": 1, "width": -5.0,
                               "height": 0.6, "depth": 0.6, "lid_form": "arched",
                               "band_count": 2, "has_lock": True, "style": "medieval_lowpoly"}))
    return str(bad)


def test_input_failure_maps_to_exactly_one_code(tmp_path: Path) -> None:
    out = tmp_path / "out"

    with pytest.raises(Exception) as raised:
        generate_in_process_from_spec_file(_bad_spec(tmp_path), str(out))

    assert_taxonomy_failure(_read_report(out), getattr(raised.value, "code", "input.invalid"),
                            FailureCode.INPUT_INVALID)


def test_environment_unavailable_maps_to_exactly_one_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("blender_worker.export.bpy_available", lambda: False)
    out = tmp_path / "out"

    with pytest.raises(GenerateError) as raised:
        generate_in_process_from_spec_file("specs/house_default.json", str(out))

    assert_taxonomy_failure(_read_report(out), raised.value.code,
                            FailureCode.ENVIRONMENT_UNAVAILABLE)


def test_environment_timeout_maps_to_exactly_one_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "slow-python"
    executable.write_text("#!/bin/sh\nsleep 30\n")
    executable.chmod(0o755)
    out = tmp_path / "result"
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    with pytest.raises(GenerateError) as raised:
        run_generation_process("specs/house_default.json", str(out), timeout_seconds=0.05)

    assert_taxonomy_failure(_read_report(out), raised.value.code,
                            FailureCode.PROCESS_TIMEOUT)


def test_build_failure_maps_to_exactly_one_code(
    tmp_path: Path, fake_bpy: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(_mesh: Any, _name: str) -> Any:
        raise RuntimeError("solda da IR estourou")

    monkeypatch.setattr("blender_worker.bpy_build.mesh_to_bpy", _boom)
    out = tmp_path / "out"

    with pytest.raises(GenerateError) as raised:
        generate_in_process_from_spec_file("specs/house_default.json", str(out))

    assert_taxonomy_failure(_read_report(out), raised.value.code,
                            FailureCode.BUILD_FAILED)


def test_validation_failure_maps_to_exactly_one_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("blender_worker.export.bpy_available", lambda: True)
    mesh, _ = export.inspect(load_spec_file("specs/house_default.json"))
    monkeypatch.setattr(
        export, "inspect", lambda _spec: (mesh, {"mesh_valid": {"ok": False, "detail": "forced"}})
    )
    out = tmp_path / "out"

    with pytest.raises(GenerateError) as raised:
        generate_in_process_from_spec_file("specs/house_default.json", str(out))

    assert_taxonomy_failure(_read_report(out), raised.value.code,
                            FailureCode.VALIDATION_FAILED)


def test_render_failure_maps_to_exactly_one_code(
    tmp_path: Path, fake_bpy: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("blender_worker.bpy_build.mesh_to_bpy", lambda _mesh, _name: None)
    monkeypatch.setattr(
        export, "_reimport_gate",
        lambda _path, _count: {"ok": True, "detail": "forced"},
    )

    def _boom(_path: str) -> dict:
        raise RuntimeError("Eevee estourou")

    import blender_worker.preview as preview

    monkeypatch.setattr(preview, "render_official_preview", _boom)
    out = tmp_path / "out"

    with pytest.raises(GenerateError) as raised:
        generate_in_process_from_spec_file("specs/house_default.json", str(out))

    assert_taxonomy_failure(_read_report(out), raised.value.code,
                            FailureCode.RENDER_FAILED)


def test_export_failure_maps_to_exactly_one_code(
    tmp_path: Path, fake_bpy: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("blender_worker.bpy_build.mesh_to_bpy", lambda _mesh, _name: None)

    def _boom(**_: Any) -> None:
        raise RuntimeError("disco estourou")

    fake_bpy.ops.export_scene.gltf = _boom  # type: ignore[attr-defined]
    out = tmp_path / "out"

    with pytest.raises(GenerateError) as raised:
        generate_in_process_from_spec_file("specs/house_default.json", str(out))

    assert_taxonomy_failure(_read_report(out), raised.value.code,
                            FailureCode.EXPORT_FAILED)


def test_reimport_failure_maps_to_exactly_one_code(
    tmp_path: Path, fake_bpy: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("blender_worker.bpy_build.mesh_to_bpy", lambda _mesh, _name: None)
    monkeypatch.setattr(
        export, "_reimport_gate",
        lambda _path, _count: {"ok": False, "detail": "forced gate rejection"},
    )
    out = tmp_path / "out"

    with pytest.raises(GenerateError) as raised:
        generate_in_process_from_spec_file("specs/house_default.json", str(out))

    assert_taxonomy_failure(_read_report(out), raised.value.code,
                            FailureCode.REIMPORT_FAILED)


def test_publication_failure_maps_to_exactly_one_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("blender_worker.export.bpy_available", lambda: True)
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.json").write_text("{}")

    with pytest.raises(GenerateError) as raised:
        generate_in_process_from_spec_file("specs/house_default.json", str(out))

    # An occupied destination is never damaged: only the previous report stays.
    assert raised.value.code == FailureCode.PUBLICATION_FAILED.value
    assert (out / "report.json").read_text() == "{}"
    assert not (out / "model.glb").exists()


def test_cli_and_report_surface_the_same_code_with_a_derived_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"

    exit_code = main(["generate", "--spec", _bad_spec(tmp_path), "--out", str(out)])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert FailureCode.INPUT_INVALID.value in captured.err
    assert MESSAGES[FailureCode.INPUT_INVALID] in captured.err
    assert _read_report(out)["error"]["code"] == FailureCode.INPUT_INVALID.value
