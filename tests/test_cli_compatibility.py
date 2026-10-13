"""Marco 2 ticket 04: CLI compatibility through the public command seam.

Scripts depend on the command shape, the exit code, the structured code on
stderr and the published artifact triple. These tests observe only those, never
free-form prose and never the executor's internal stages.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from blender_worker.attempts import (
    AttemptId,
    CancelledAttempt,
    GenerationAttempt,
    GenerationAttemptExecutor,
)
from blender_worker.main import main


def _publishing_child(tmp_path: Path, *, reject_when_occupied: bool) -> Path:
    """A controlled child standing in for the official pipeline's publication."""
    executable = tmp_path / "controlled-python"
    executable.write_text(
        "#!/bin/sh\n"
        "out=\n"
        "forced=no\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--out\" ]; then shift; out=$1; fi\n"
        "  if [ \"$1\" = \"--force\" ]; then forced=yes; fi\n"
        "  shift\n"
        "done\n"
        + (
            'if [ -n "$(ls -A "$out" 2>/dev/null)" ] && [ "$forced" != "yes" ]; then\n'
            "  printf 'publication.failed: destino ocupado\\n' >&2\n"
            "  exit 1\n"
            "fi\n"
            if reject_when_occupied
            else ""
        )
        + "rm -f \"$out/model.glb\" \"$out/preview.png\" \"$out/report.json\"\n"
        'mkdir -p "$out"\n'
        "printf 'glb' > \"$out/model.glb\"\n"
        "printf 'png' > \"$out/preview.png\"\n"
        'printf \'{"ok":true,"stage":"published","backend":"bpy","tri_count":7,'
        '"attempt_id":"%s","generation_fingerprint":"sha256:cli",'
        '"resolved_spec":{"spec_version":1,"type":"house","seed":42},'
        '"artifacts":["model.glb","preview.png","report.json"]}\''
        ' "$GERADOR_3D_ATTEMPT_ID" > "$out/report.json"\n'
    )
    executable.chmod(0o755)
    return executable


def _stderr_code(stderr: str) -> str:
    """The structured code a shell script matches on: the token before ': '."""
    return stderr.strip().splitlines()[-1].split(":")[0]


def test_cancelled_attempt_is_not_reported_as_an_ordinary_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Shell automation must be able to tell an interruption from a failure."""

    def fake_execute(_self: object, attempt: GenerationAttempt) -> CancelledAttempt:
        return CancelledAttempt(attempt.attempt_id, {
            "ok": False,
            "error": {"code": "execution.cancelled", "message": "x", "detail": "y"},
        })

    monkeypatch.setattr(GenerationAttemptExecutor, "execute", fake_execute)

    exit_code = main(["generate", "--spec", "specs/house_default.json", "--out", "out"])

    assert exit_code != 0
    assert _stderr_code(capsys.readouterr().err) == "execution.cancelled"
    assert exit_code != 1


def test_successful_command_publishes_the_indivisible_artifact_triple(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    destination = tmp_path / "result"
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(_publishing_child(
        tmp_path, reject_when_occupied=False,
    )))

    exit_code = main([
        "generate", "--spec", "specs/house_default.json", "--out", str(destination),
    ])

    assert exit_code == 0
    assert capsys.readouterr().err == ""
    assert sorted(path.name for path in destination.iterdir()) == [
        "model.glb", "preview.png", "report.json",
    ]
    assert json.loads((destination / "report.json").read_text())["stage"] == "published"
    assert not list(tmp_path.glob(".generation-*"))


def test_occupied_destination_without_force_is_untouched_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    destination = tmp_path / "result"
    destination.mkdir()
    (destination / "model.glb").write_bytes(b"existing-asset")
    (destination / "preview.png").write_bytes(b"existing-preview")
    (destination / "report.json").write_bytes(b'{"previous": true}')
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(_publishing_child(
        tmp_path, reject_when_occupied=True,
    )))

    exit_code = main([
        "generate", "--spec", "specs/house_default.json", "--out", str(destination),
    ])

    assert exit_code == 1
    assert _stderr_code(capsys.readouterr().err) == "publication.failed"
    assert (destination / "model.glb").read_bytes() == b"existing-asset"
    assert (destination / "preview.png").read_bytes() == b"existing-preview"
    assert (destination / "report.json").read_bytes() == b'{"previous": true}'


def test_force_replaces_the_result_through_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    destination = tmp_path / "result"
    destination.mkdir()
    (destination / "model.glb").write_bytes(b"existing-asset")
    (destination / "preview.png").write_bytes(b"existing-preview")
    (destination / "report.json").write_bytes(b'{"previous": true}')
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(_publishing_child(
        tmp_path, reject_when_occupied=True,
    )))

    exit_code = main([
        "generate", "--spec", "specs/house_default.json", "--out", str(destination),
        "--force",
    ])

    assert exit_code == 0
    assert capsys.readouterr().err == ""
    # No artifact of the previous Result of Generation survives the replacement.
    assert sorted(path.name for path in destination.iterdir()) == [
        "model.glb", "preview.png", "report.json",
    ]
    assert (destination / "model.glb").read_bytes() == b"glb"
    assert json.loads((destination / "report.json").read_text())["stage"] == "published"


def test_explicit_timeout_is_enforced_by_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    slow = tmp_path / "slow-python"
    slow.write_text("#!/bin/sh\nsleep 30\n")
    slow.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(slow))
    destination = tmp_path / "result"

    exit_code = main([
        "generate", "--spec", "specs/house_default.json", "--out", str(destination),
        "--timeout-seconds", "0.5",
    ])

    assert exit_code == 1
    assert _stderr_code(capsys.readouterr().err) == "environment.timeout"
    assert not (destination / "model.glb").exists()
    assert not (destination / "preview.png").exists()


def test_configured_operational_default_timeout_applies_without_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    slow = tmp_path / "slow-python"
    slow.write_text("#!/bin/sh\nsleep 30\n")
    slow.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(slow))
    monkeypatch.setenv("GERADOR_3D_TIMEOUT_SECONDS", "0.5")

    exit_code = main([
        "generate", "--spec", "specs/house_default.json", "--out", str(tmp_path / "result"),
    ])

    assert exit_code == 1
    assert _stderr_code(capsys.readouterr().err) == "environment.timeout"


def test_command_forwards_its_arguments_as_one_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The command is a thin caller: it maps argv onto a Tentativa and nothing else."""
    seen: list[GenerationAttempt] = []

    def fake_execute(_self: object, attempt: GenerationAttempt) -> object:
        seen.append(attempt)
        raise AssertionError("no outcome construction is needed for this assertion")

    monkeypatch.setattr(GenerationAttemptExecutor, "execute", fake_execute)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "spec.json").write_text('{"spec_version": 1, "type": "house", "seed": 7}')

    with pytest.raises(AssertionError):
        main([
            "generate", "--spec", "spec.json", "--out", "out", "--force",
            "--timeout-seconds", "12.5",
        ])

    assert len(seen) == 1
    attempt = seen[0]
    assert attempt.spec == {"spec_version": 1, "type": "house", "seed": 7}
    assert attempt.destination == Path("out")
    assert attempt.existing_result.value == "replace"
    assert attempt.timeout_seconds == 12.5
    assert isinstance(attempt.attempt_id, AttemptId)


def test_missing_required_arguments_are_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as usage:
        main(["generate", "--spec", "specs/house_default.json"])

    assert usage.value.code == 2