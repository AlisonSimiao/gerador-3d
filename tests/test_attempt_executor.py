"""Marco 2: public GenerationAttemptExecutor seam."""

import json
import math
import os
from pathlib import Path
import threading
import time

import pytest

from blender_worker.attempts import (
    AttemptId,
    CancellationToken,
    CancelledAttempt,
    FailedAttempt,
    GenerationAttempt,
    GenerationAttemptExecutor,
    InMemoryProgressObserver,
    JsonLinesProgressObserver,
    PublishedResult,
    new_attempt_id,
)
from blender_worker.reports import attempt_storage_token, environment


@pytest.mark.parametrize("timeout", [math.nan, math.inf, -math.inf, 0.0, -1.0])
def test_timeout_must_be_finite_and_positive(tmp_path: Path, timeout: float) -> None:
    with pytest.raises(ValueError, match="finito e positivo"):
        GenerationAttempt(
            AttemptId("attempt-bad-timeout"), _valid_house(), tmp_path / "result",
            timeout_seconds=timeout,
        )


@pytest.mark.parametrize("blank", ["", "   "])
def test_attempt_identity_must_be_opaque_and_non_empty(blank: str) -> None:
    with pytest.raises(ValueError, match="não pode ser vazio"):
        AttemptId(blank)


def test_generated_attempt_identities_are_distinct() -> None:
    identities = {new_attempt_id() for _ in range(100)}

    assert len(identities) == 100
    # The identity is opaque: it carries no Spec, Seed or fingerprint content.
    assert all(identity.value for identity in identities)


def test_invalid_input_returns_a_correlated_safe_failure(tmp_path: Path) -> None:
    secret = "não copiar este valor arbitrário"
    attempt = GenerationAttempt(
        attempt_id=AttemptId("attempt-invalid-1"),
        spec={"spec_version": 1, "type": "house", "seed": 42, "unknown": secret},
        destination=tmp_path / "result",
    )

    outcome = GenerationAttemptExecutor().execute(attempt)

    assert isinstance(outcome, FailedAttempt)
    assert outcome.attempt_id == AttemptId("attempt-invalid-1")
    assert outcome.report["error"]["code"] == "input.invalid"
    assert outcome.report["attempt_id"] == "attempt-invalid-1"
    assert outcome.report["input_hash"].startswith("sha256:")
    assert secret not in str(outcome.report)
    assert sorted(path.name for path in (tmp_path / "result").iterdir()) == ["report.json"]


def test_invalid_input_progress_is_optional_and_observational(tmp_path: Path) -> None:
    observer = InMemoryProgressObserver()

    outcome = GenerationAttemptExecutor(observer=observer).execute(GenerationAttempt(
        AttemptId("attempt-progress-invalid"), {"not-json"}, tmp_path / "result",
    ))

    assert isinstance(outcome, FailedAttempt)
    assert [(event.sequence, event.stage) for event in observer.events] == [(1, "input")]


def test_progress_observer_failure_does_not_change_the_outcome(tmp_path: Path) -> None:
    class BrokenObserver:
        def observe(self, _event: object) -> None:
            raise RuntimeError("telemetria indisponível")

    outcome = GenerationAttemptExecutor(observer=BrokenObserver()).execute(GenerationAttempt(
        AttemptId("attempt-broken-observer"), {"not-json"}, tmp_path / "result",
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "input.invalid"


def test_slow_progress_observer_does_not_block_the_outcome(tmp_path: Path) -> None:
    class SlowObserver:
        def observe(self, _event: object) -> None:
            time.sleep(1)

    started = time.monotonic()
    outcome = GenerationAttemptExecutor(observer=SlowObserver()).execute(GenerationAttempt(
        AttemptId("attempt-slow-observer"), {"not-json"}, tmp_path / "result",
    ))

    assert isinstance(outcome, FailedAttempt)
    assert time.monotonic() - started < 0.5


def test_json_lines_progress_adapter_is_local_and_structured(tmp_path: Path) -> None:
    path = tmp_path / "progress.jsonl"
    outcome = GenerationAttemptExecutor(
        observer=JsonLinesProgressObserver(path),
    ).execute(GenerationAttempt(
        AttemptId("attempt-jsonl"), {"not-json"}, tmp_path / "result",
    ))

    assert isinstance(outcome, FailedAttempt)
    assert json.loads(path.read_text()) == {
        "attempt_id": "attempt-jsonl", "sequence": 1, "stage": "input",
    }


def _valid_house() -> dict[str, object]:
    return json.loads(Path("specs/house_default.json").read_text())


def _slow_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "slow-python"
    executable.write_text("#!/bin/sh\nsleep 30\n")
    executable.chmod(0o755)
    return executable


def test_environment_failure_is_a_typed_correlated_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GERADOR_3D_PYTHON", "/usr/bin/python3")
    attempt = GenerationAttempt(
        AttemptId("tenant/attempt no bpy"), _valid_house(), tmp_path / "result",
        timeout_seconds=10,
    )

    outcome = GenerationAttemptExecutor().execute(attempt)

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["attempt_id"] == "tenant/attempt no bpy"
    assert outcome.report["error"]["code"] == "environment.unavailable"


def test_occupied_destination_is_preserved_by_the_executor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "result"
    destination.mkdir()
    original = b'{"ok":true,"sentinel":"keep"}'
    (destination / "report.json").write_bytes(original)
    monkeypatch.setenv("GERADOR_3D_PYTHON", "/usr/bin/python3")

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-occupied"), _valid_house(), destination,
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "environment.unavailable"
    assert (destination / "report.json").read_bytes() == original


def test_timeout_is_distinct_and_cleans_the_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(_slow_executable(tmp_path)))
    attempt = GenerationAttempt(
        AttemptId("attempt-timeout"), _valid_house(), tmp_path / "result",
        timeout_seconds=0.05,
    )

    outcome = GenerationAttemptExecutor().execute(attempt)

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "environment.timeout"
    assert outcome.report["attempt_id"] == "attempt-timeout"
    assert sorted(path.name for path in (tmp_path / "result").iterdir()) == ["report.json"]
    assert not list(tmp_path.glob(".generation-*"))
    assert not list(tmp_path.glob(".attempt-*.json"))


def test_cancellation_before_start_never_launches_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "launched"
    executable = tmp_path / "marker-python"
    executable.write_text(f"#!/bin/sh\ntouch {marker}\nsleep 30\n")
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))
    cancellation = CancellationToken()
    cancellation.cancel()

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-cancelled-before"), _valid_house(), tmp_path / "result",
        cancellation=cancellation,
    ))

    assert isinstance(outcome, CancelledAttempt)
    assert outcome.report["error"]["code"] == "execution.cancelled"
    assert outcome.report["error"]["taxonomy_version"] == 2
    assert not marker.exists()


def test_cancellation_during_execution_reaps_the_process_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid_file = tmp_path / "child.pid"
    executable = tmp_path / "slow-python"
    executable.write_text(f"#!/bin/sh\necho $$ > {pid_file}\nsleep 30\n")
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))
    cancellation = CancellationToken()
    timer = threading.Timer(0.1, cancellation.cancel)
    timer.start()
    try:
        outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
            AttemptId("attempt-cancelled-running"), _valid_house(), tmp_path / "result",
            timeout_seconds=10, cancellation=cancellation,
        ))
    finally:
        timer.cancel()

    assert isinstance(outcome, CancelledAttempt)
    assert outcome.report["error"]["code"] == "execution.cancelled"
    child_pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)
    assert not list(tmp_path.glob(".generation-*"))
    assert not list(tmp_path.glob(".attempt-*.json"))


def test_atomic_publication_wins_a_concurrent_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "publishing-python"
    executable.write_text(
        "#!/bin/sh\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--out\" ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        "mkdir -p \"$out\"\n"
        "printf 'glb' > \"$out/model.glb\"\n"
        "printf 'png' > \"$out/preview.png\"\n"
        "printf '%s' '{\"ok\":true,\"stage\":\"published\",\"backend\":\"bpy\","
        "\"attempt_id\":\"attempt-commit-wins\","
        "\"generation_fingerprint\":\"sha256:committed\","
        "\"resolved_spec\":{\"spec_version\":1,\"type\":\"house\",\"seed\":42},"
        "\"artifacts\":[\"model.glb\",\"preview.png\",\"report.json\"]}'"
        " > \"$out/report.json\"\n"
        "sleep 30\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))
    destination = tmp_path / "result"
    cancellation = CancellationToken()

    def cancel_after_commit() -> None:
        while not (destination / "report.json").exists():
            time.sleep(0.01)
        cancellation.cancel()

    requester = threading.Thread(target=cancel_after_commit)
    requester.start()
    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-commit-wins"), _valid_house(), destination,
        timeout_seconds=10, cancellation=cancellation,
    ))
    requester.join()

    assert isinstance(outcome, PublishedResult)
    assert outcome.fingerprint == "sha256:committed"
    assert json.loads((destination / "report.json").read_text())["stage"] == "published"


def test_incomplete_published_report_is_not_a_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "incomplete-python"
    executable.write_text(
        "#!/bin/sh\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--out\" ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        "mkdir -p \"$out\"\n"
        "printf '%s' '{\"ok\":true,\"stage\":\"published\",\"backend\":\"bpy\"}'"
        " > \"$out/report.json\"\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-incomplete"), _valid_house(), tmp_path / "result",
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "environment.unavailable"
    assert sorted(path.name for path in (tmp_path / "result").iterdir()) == ["report.json"]


def test_abnormal_child_cleanup_removes_only_its_staging_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_id = "tenant/abnormal attempt"
    token = attempt_storage_token(attempt_id)
    executable = tmp_path / "abnormal-python"
    executable.write_text(
        "#!/bin/sh\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--out\" ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        f'mkdir -p "$(dirname "$out")/.generation-{token}-orphan"\n'
        "exit 7\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId(attempt_id), _valid_house(), tmp_path / "result",
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "environment.unavailable"
    assert not list(tmp_path.glob(".generation-*"))
    assert not list(tmp_path.glob(".attempt-*"))


def test_environment_records_configured_build_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GERADOR_3D_BUILD_COMMIT", "abc123")

    assert environment(blender=None)["build_commit"] == "abc123"


@pytest.mark.integration
def test_distinct_attempts_share_the_fingerprint_of_the_same_generation(
    tmp_path: Path,
) -> None:
    spec = json.loads(Path("specs/house_default.json").read_text())
    observer = InMemoryProgressObserver()
    executor = GenerationAttemptExecutor(observer=observer)

    first = executor.execute(GenerationAttempt(
        AttemptId("attempt-one"), spec, tmp_path / "one",
    ))
    second = executor.execute(GenerationAttempt(
        AttemptId("attempt-two"),
        {"spec_version": 1, "type": "house", "seed": 42},
        tmp_path / "two",
    ))

    assert isinstance(first, PublishedResult)
    assert isinstance(second, PublishedResult)
    assert first.attempt_id != second.attempt_id
    assert first.fingerprint.startswith("sha256:")
    assert first.fingerprint == second.fingerprint
    assert first.report["attempt_id"] == "attempt-one"
    assert second.report["attempt_id"] == "attempt-two"
    assert first.report["generation_fingerprint"] == first.fingerprint
    first_events = [
        event for event in observer.events
        if event.attempt_id == AttemptId("attempt-one")
    ]
    assert [event.stage for event in first_events] == [
        "input", "environment", "validation", "build", "export", "reimport",
        "render", "publication", "published",
    ]
    assert [event.sequence for event in first_events] == list(range(1, 10))
