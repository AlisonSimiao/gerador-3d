"""Official process-runner seam: every generation executes in a clean child."""

import json
import os
from pathlib import Path

import pytest

from blender_worker.export import GenerateError
from blender_worker.main import build_parser, main
from blender_worker.process_runner import DEFAULT_TIMEOUT_SECONDS, run_generation_process


def test_generate_cli_accepts_a_configurable_timeout() -> None:
    args = build_parser().parse_args(
        ["generate", "--spec", "spec.json", "--out", "result", "--timeout-seconds", "12.5"]
    )

    assert args.timeout_seconds == 12.5


def test_process_runner_has_a_finite_default_timeout() -> None:
    assert DEFAULT_TIMEOUT_SECONDS > 0


def test_missing_bpy_is_a_structured_environment_failure_without_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "result"
    monkeypatch.setenv("GERADOR_3D_PYTHON", "/usr/bin/python3")

    with pytest.raises(GenerateError) as raised:
        run_generation_process("specs/house_default.json", str(out), timeout_seconds=10)

    assert raised.value.code == "environment.unavailable"
    report = json.loads((out / "report.json").read_text())
    assert report["backend"] is None
    assert report["environment"]["python"]
    assert report["environment"]["blender"] is None
    assert report["error"]["code"] == "environment.unavailable"
    assert not (out / "model.glb").exists()
    assert not (out / "preview.png").exists()


def test_cli_returns_nonzero_and_prints_the_same_structured_code_without_bpy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "result"
    monkeypatch.setenv("GERADOR_3D_PYTHON", "/usr/bin/python3")

    exit_code = main([
        "generate", "--spec", "specs/tree_default.json", "--out", str(out),
        "--timeout-seconds", "10",
    ])

    assert exit_code != 0
    assert "environment.unavailable" in capsys.readouterr().err
    report = json.loads((out / "report.json").read_text())
    assert report["error"]["code"] == "environment.unavailable"


def test_timeout_kills_and_reaps_the_child_and_discards_temporary_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = tmp_path / "child.pid"
    executable = tmp_path / "slow-python"
    executable.write_text(f"#!/bin/sh\necho $$ > {pid_file}\nsleep 30\n")
    executable.chmod(0o755)
    out = tmp_path / "result"
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    with pytest.raises(GenerateError) as raised:
        run_generation_process("specs/house_default.json", str(out), timeout_seconds=0.05)

    assert raised.value.code == "environment.timeout"
    child_pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)
    report = json.loads((out / "report.json").read_text())
    assert report["error"]["code"] == "environment.timeout"
    assert not (out / "model.glb").exists()
    assert not (out / "preview.png").exists()
    assert not list(tmp_path.glob(".generation-*"))
