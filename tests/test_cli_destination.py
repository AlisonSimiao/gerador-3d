"""Ticket 15: CLI occupied destination, --force, per-stage metrics, platform gate.

All tests run WITHOUT Blender: `export.generate` is observed directly with
the environment gate stubbed where the real gate would need bpy, and the CLI
path is exercised with an unavailable-Blender interpreter like
`test_process_runner.py` does.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from blender_worker import export, preview
from blender_worker.export import GenerateError, generate
from blender_worker.main import main
from blender_worker.schema import load_spec_file

SPEC = "specs/house_default.json"

#: Sentinel contents of a pre-existing Result of Generation.
EXISTING = {
    "model.glb": b"existing-asset",
    "preview.png": b"existing-preview",
    "report.json": b'{"existing": true}',
}


def _occupy(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name, content in EXISTING.items():
        (dest / name).write_bytes(content)


def _assert_existing_untouched(dest: Path) -> None:
    for name, content in EXISTING.items():
        assert (dest / name).read_bytes() == content


def _stub_bpy_pipeline(monkeypatch: pytest.MonkeyPatch, stage_dir_files: dict | None = None) -> None:
    """Fake the Blender-only steps so `generate` runs its real orchestration."""
    monkeypatch.setattr(export, "bpy_available", lambda: True)
    fake_bpy = types.SimpleNamespace(
        ops=types.SimpleNamespace(wm=types.SimpleNamespace(read_factory_settings=lambda **_: None)),
        app=types.SimpleNamespace(version_string="5.2.2-fake"),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setattr("blender_worker.bpy_build.mesh_to_bpy", lambda _mesh, _type: None)

    def fake_export(path: str) -> None:
        Path(path).write_bytes(b"fake-glb")

    def fake_reimport(path: str, _mesh: object) -> dict:
        assert Path(path).is_file()
        return {"ok": True, "detail": "fake reimport gate"}

    def fake_render(path: str) -> dict:
        Path(path).write_bytes(b"fake-preview")
        return {"ok": True, "detail": "fake render"}

    monkeypatch.setattr(export, "_export_glb", fake_export)
    monkeypatch.setattr(export, "_reimport_gate", fake_reimport)
    monkeypatch.setattr(preview, "render_official_preview", fake_render)


def test_occupied_destination_without_force_fails_with_publication_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "result"
    _occupy(dest)
    # Real Linux x86_64 platform gate holds here; only the bpy gate is stubbed
    # so the attempt reaches the occupied-destination check without Blender.
    monkeypatch.setattr(export, "bpy_available", lambda: True)

    with pytest.raises(GenerateError) as raised:
        generate(load_spec_file(SPEC), str(dest))

    assert raised.value.code == "publication.failed"
    _assert_existing_untouched(dest)
    assert not list(tmp_path.glob(".generation-*"))
    assert not Path(str(dest) + ".previous").exists()


def test_force_replaces_safely_and_stays_atomic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "result"
    _occupy(dest)
    _stub_bpy_pipeline(monkeypatch)

    report = generate(load_spec_file(SPEC), str(dest), force=True)

    assert report["ok"] is True
    assert report["stage"] == "published"
    assert (dest / "model.glb").read_bytes() == b"fake-glb"
    assert (dest / "preview.png").read_bytes() == b"fake-preview"
    written = json.loads((dest / "report.json").read_text())
    assert written["ok"] is True
    # Atomic publication leaves no backup or staging behind.
    assert not Path(str(dest) + ".previous").exists()
    assert not list(tmp_path.glob(".generation-*"))
    assert not list(tmp_path.glob("result.previous*"))


def test_success_report_carries_per_stage_durations_and_peak_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_bpy_pipeline(monkeypatch)

    report = generate(load_spec_file(SPEC), str(tmp_path / "fresh"))

    stages = report["metrics"]["stages"]
    for stage in ("inspect", "build", "export", "reimport", "render", "total_seconds"):
        assert isinstance(stages[stage], float), f"missing per-stage duration: {stage}"
        assert stages[stage] >= 0.0
    assert isinstance(report["metrics"]["peak_memory_bytes"], int)
    assert report["metrics"]["peak_memory_bytes"] > 0


def test_unsupported_platform_fails_early_with_environment_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export.platform, "system", lambda: "Darwin")

    with pytest.raises(GenerateError) as raised:
        generate(load_spec_file(SPEC), str(tmp_path / "result"))

    assert raised.value.code == "environment.unavailable"
    assert not (tmp_path / "result").exists()


def test_unsupported_architecture_fails_early_with_environment_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export.platform, "machine", lambda: "aarch64")

    with pytest.raises(GenerateError) as raised:
        generate(load_spec_file(SPEC), str(tmp_path / "result"))

    assert raised.value.code == "environment.unavailable"


def test_cli_without_blender_never_destroys_an_existing_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "result"
    _occupy(dest)
    monkeypatch.setenv("GERADOR_3D_PYTHON", "/usr/bin/python3")

    exit_code = main(["generate", "--spec", SPEC, "--out", str(dest), "--timeout-seconds", "10"])

    assert exit_code != 0
    # The child's structured code survives even though no fresh report exists.
    assert "environment.unavailable" in capsys.readouterr().err
    _assert_existing_untouched(dest)
    assert not list(tmp_path.glob(".generation-*"))
