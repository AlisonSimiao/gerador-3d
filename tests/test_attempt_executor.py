"""Marco 2: public GenerationAttemptExecutor seam."""

import json
import math
import os
from dataclasses import fields
from pathlib import Path
import threading
import time

import pytest

from blender_worker.attempts import (
    AttemptId,
    CancellationToken,
    CancelledAttempt,
    ExistingResultPolicy,
    FailedAttempt,
    GenerationAttempt,
    GenerationAttemptExecutor,
    InMemoryProgressObserver,
    JsonLinesProgressObserver,
    PublishedResult,
    new_attempt_id,
)
from blender_worker.export import GenerateError, generate_from_spec_file
from blender_worker.failures import REPORT_STAGES
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
    marker = tmp_path / "launched"
    executable = tmp_path / "marker-python"
    executable.write_text(f"#!/bin/sh\ntouch {marker}\n")
    executable.chmod(0o755)
    attempt = GenerationAttempt(
        attempt_id=AttemptId("attempt-invalid-1"),
        spec={"spec_version": 1, "type": "house", "seed": 42, "unknown": secret},
        destination=tmp_path / "result",
    )

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GERADOR_3D_PYTHON", str(executable))
        outcome = GenerationAttemptExecutor().execute(attempt)

    assert isinstance(outcome, FailedAttempt)
    assert outcome.attempt_id == AttemptId("attempt-invalid-1")
    assert outcome.report["error"]["code"] == "input.invalid"
    assert outcome.report["attempt_id"] == "attempt-invalid-1"
    assert outcome.report["input_hash"].startswith("sha256:")
    assert secret not in str(outcome.report)
    assert sorted(path.name for path in (tmp_path / "result").iterdir()) == ["report.json"]
    assert not marker.exists()


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


def test_invalid_execution_options_are_rejected_before_any_process_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "launched"
    executable = tmp_path / "marker-python"
    executable.write_text(f"#!/bin/sh\ntouch {marker}\n")
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))
    monkeypatch.setenv("GERADOR_3D_TIMEOUT_SECONDS", "not-a-number")

    with pytest.raises(ValueError, match="finito e positivo"):
        GenerationAttemptExecutor().execute(GenerationAttempt(
            AttemptId("attempt-bad-default-timeout"), _valid_house(), tmp_path / "result",
        ))

    assert not marker.exists()
    assert not (tmp_path / "result").exists()


def test_previous_entry_point_delegates_without_generation_logic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The transitional wrapper only translates the typed outcome it receives."""
    seen: list[GenerationAttempt] = []
    outcome = PublishedResult(
        AttemptId("attempt-wrapper"), tmp_path / "result", "sha256:wrapper",
        {"ok": True, "stage": "published", "tri_count": 12},
    )

    def fake_execute(_self: object, attempt: GenerationAttempt) -> PublishedResult:
        seen.append(attempt)
        return outcome

    monkeypatch.setattr(GenerationAttemptExecutor, "execute", fake_execute)

    report = generate_from_spec_file(
        "specs/house_default.json", str(tmp_path / "result"), timeout_seconds=12.5,
    )

    assert report == outcome.report
    assert len(seen) == 1
    assert seen[0].timeout_seconds == 12.5
    assert seen[0].existing_result is ExistingResultPolicy.REJECT
    assert seen[0].destination == tmp_path / "result"
    assert seen[0].spec == _valid_house()


def test_previous_entry_point_makes_replacement_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[GenerationAttempt] = []

    def fake_execute(_self: object, attempt: GenerationAttempt) -> PublishedResult:
        seen.append(attempt)
        return PublishedResult(attempt.attempt_id, attempt.destination, "sha256:x", {"ok": True})

    monkeypatch.setattr(GenerationAttemptExecutor, "execute", fake_execute)

    generate_from_spec_file("specs/house_default.json", str(tmp_path / "result"), force=True)

    assert seen[0].existing_result is ExistingResultPolicy.REPLACE


def test_previous_entry_point_raises_the_typed_failure_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_execute(_self: object, attempt: GenerationAttempt) -> FailedAttempt:
        return FailedAttempt(attempt.attempt_id, {
            "ok": False, "error": {"code": "reimport.failed", "detail": "malformed"},
        })

    monkeypatch.setattr(GenerationAttemptExecutor, "execute", fake_execute)

    with pytest.raises(GenerateError) as raised:
        generate_from_spec_file("specs/house_default.json", str(tmp_path / "result"))

    assert raised.value.code == "reimport.failed"


def test_previous_entry_point_never_reports_cancellation_as_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cancelled attempt is not a result: the legacy contract raises."""

    def fake_execute(_self: object, attempt: GenerationAttempt) -> CancelledAttempt:
        return CancelledAttempt(attempt.attempt_id, {
            "ok": False, "error": {"code": "execution.cancelled", "detail": "cancelado"},
        })

    monkeypatch.setattr(GenerationAttemptExecutor, "execute", fake_execute)

    with pytest.raises(GenerateError) as raised:
        generate_from_spec_file("specs/house_default.json", str(tmp_path / "result"))

    assert raised.value.code == "execution.cancelled"


def test_attempt_input_carries_only_the_documented_execution_data(
    tmp_path: Path,
) -> None:
    assert {field.name for field in fields(GenerationAttempt)} == {
        "attempt_id", "spec", "destination", "existing_result",
        "timeout_seconds", "cancellation",
    }
    attempt = GenerationAttempt(
        AttemptId("attempt-fields"), _valid_house(), tmp_path / "result",
    )
    # No pipeline stage, queue or infrastructure handle is caller-supplied.
    assert attempt.existing_result is ExistingResultPolicy.REJECT
    assert attempt.timeout_seconds is None
    assert attempt.cancellation is None


def test_executor_exposes_one_public_execution_operation() -> None:
    public_operations = sorted(
        name for name in dir(GenerationAttemptExecutor)
        if not name.startswith("_") and callable(getattr(GenerationAttemptExecutor, name))
    )

    assert public_operations == ["execute"]


def _occupy(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in {
        "model.glb": b"existing-asset",
        "preview.png": b"existing-preview",
        "report.json": b'{"existing": true}',
    }.items():
        (destination / name).write_bytes(content)


def _assert_untouched(destination: Path) -> None:
    assert sorted(path.name for path in destination.iterdir()) == [
        "model.glb", "preview.png", "report.json",
    ]
    assert (destination / "model.glb").read_bytes() == b"existing-asset"
    assert (destination / "preview.png").read_bytes() == b"existing-preview"
    assert (destination / "report.json").read_bytes() == b'{"existing": true}'


def _publishing_executable(tmp_path: Path, body: str) -> Path:
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
        "publish_report() {\n"
        "  printf '{\"ok\":true,\"stage\":\"published\",\"backend\":\"bpy\","
        "\"attempt_id\":\"%s\",\"generation_fingerprint\":\"sha256:replaced\","
        "\"resolved_spec\":{\"spec_version\":1,\"type\":\"house\",\"seed\":42},"
        "\"artifacts\":[\"model.glb\",\"preview.png\",\"report.json\"]}'"
        " \"$GERADOR_3D_ATTEMPT_ID\"\n"
        "}\n" + body
    )
    executable.chmod(0o755)
    return executable


def _reject_when_occupied() -> str:
    return (
        'if [ -n "$(ls -A "$out" 2>/dev/null)" ] && [ "$forced" != "yes" ]; then\n'
        "  printf 'publication.failed: destino ocupado: %s\\n' \"$out\" >&2\n"
        "  exit 1\n"
        "fi\n"
    )


def test_occupied_destination_is_rejected_by_default_with_the_publication_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "result"
    _occupy(destination)
    # A controlled child standing in for the official pipeline's occupied
    # destination policy: it refuses to overwrite without an explicit request.
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(_publishing_executable(
        tmp_path,
        _reject_when_occupied()
        + 'mkdir -p "$out"\n'
        + "printf 'glb' > \"$out/model.glb\"\n"
        + "printf 'png' > \"$out/preview.png\"\n"
        + 'publish_report > "$out/report.json"\n',
    )))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-reject-occupied"), _valid_house(), destination,
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "publication.failed"
    assert outcome.report["stage"] == "publication"
    _assert_untouched(destination)


def test_explicit_replacement_replaces_the_whole_result_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "result"
    _occupy(destination)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(_publishing_executable(
        tmp_path,
        _reject_when_occupied()
        + 'rm -f "$out/model.glb" "$out/preview.png" "$out/report.json"\n'
        + 'mkdir -p "$out"\n'
        + "printf 'new-glb' > \"$out/model.glb\"\n"
        + "printf 'new-png' > \"$out/preview.png\"\n"
        + 'publish_report > "$out/report.json"\n',
    )))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-replace-occupied"), _valid_house(), destination,
        existing_result=ExistingResultPolicy.REPLACE,
    ))

    assert isinstance(outcome, PublishedResult)
    assert outcome.fingerprint == "sha256:replaced"
    assert outcome.report["attempt_id"] == "attempt-replace-occupied"
    assert sorted(path.name for path in destination.iterdir()) == [
        "model.glb", "preview.png", "report.json",
    ]
    assert (destination / "model.glb").read_bytes() == b"new-glb"
    assert (destination / "preview.png").read_bytes() == b"new-png"
    assert json.loads((destination / "report.json").read_text())["stage"] == "published"
    assert not list(tmp_path.glob(".generation-*"))
    assert not list(tmp_path.glob(".attempt-*"))


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


def test_timeout_report_keeps_the_furthest_observed_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "rendering-python"
    executable.write_text(
        "#!/bin/sh\n"
        "printf '{\"stage\":\"render\"}\\n' > \"$GERADOR_3D_PROGRESS_PATH\"\n"
        "sleep 30\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-timeout-stage"), _valid_house(), tmp_path / "result",
        timeout_seconds=0.1,
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "environment.timeout"
    assert outcome.report["stage"] == "render"


def test_timeout_discards_assets_written_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "partial-python"
    executable.write_text(
        "#!/bin/sh\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--out\" ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        "mkdir -p \"$out\"\n"
        "printf partial > \"$out/model.glb\"\n"
        "sleep 30\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-timeout-partial"), _valid_house(), tmp_path / "result",
        timeout_seconds=0.1,
    ))

    assert isinstance(outcome, FailedAttempt)
    assert sorted(path.name for path in (tmp_path / "result").iterdir()) == [
        "report.json",
    ]


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


def test_cancellation_in_the_prelaunch_window_never_starts_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CancelAtRunnerBoundary:
        def __init__(self) -> None:
            self.checks = 0

        @property
        def is_cancelled(self) -> bool:
            self.checks += 1
            return self.checks >= 3

    marker = tmp_path / "launched"
    executable = tmp_path / "marker-python"
    executable.write_text(f"#!/bin/sh\ntouch {marker}\n")
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))
    cancellation = CancelAtRunnerBoundary()

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-cancelled-prelaunch"), _valid_house(),
        tmp_path / "result", cancellation=cancellation,  # type: ignore[arg-type]
    ))

    assert isinstance(outcome, CancelledAttempt)
    assert outcome.report["stage"] == "input"
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


def test_cancellation_reports_the_furthest_documented_stage_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "reached-reimport"
    executable = tmp_path / "staged-python"
    executable.write_text(
        "#!/bin/sh\n"
        "printf '{\"stage\":\"environment\"}\\n' > \"$GERADOR_3D_PROGRESS_PATH\"\n"
        "printf '{\"stage\":\"reimport\"}\\n' >> \"$GERADOR_3D_PROGRESS_PATH\"\n"
        f"touch {marker}\n"
        "sleep 30\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))
    cancellation = CancellationToken()

    def cancel_once_reached() -> None:
        while not marker.exists():
            time.sleep(0.01)
        for _ in range(3):
            cancellation.cancel()

    requester = threading.Thread(target=cancel_once_reached)
    requester.start()
    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-stage-reached"), _valid_house(), tmp_path / "result",
        timeout_seconds=10, cancellation=cancellation,
    ))
    requester.join()

    assert isinstance(outcome, CancelledAttempt)
    assert outcome.report["stage"] == "reimport"
    assert outcome.report["stage"] in REPORT_STAGES


def test_repeated_cancellation_requests_stay_idempotent(tmp_path: Path) -> None:
    cancellation = CancellationToken()

    def request() -> None:
        for _ in range(20):
            cancellation.cancel()

    requesters = [threading.Thread(target=request) for _ in range(4)]
    for requester in requesters:
        requester.start()
    for requester in requesters:
        requester.join()
    destination = tmp_path / "result"

    first = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-idempotent"), _valid_house(), destination,
        cancellation=cancellation,
    ))
    second = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-idempotent"), _valid_house(), destination,
        cancellation=cancellation,
    ))

    assert isinstance(first, CancelledAttempt)
    assert isinstance(second, CancelledAttempt)
    assert first.report["error"] == second.report["error"]
    assert sorted(path.name for path in destination.iterdir()) == ["report.json"]


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


def test_abnormal_child_report_keeps_the_furthest_observed_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "crashing-python"
    executable.write_text(
        "#!/bin/sh\n"
        "printf '{\"stage\":\"reimport\"}\\n' > \"$GERADOR_3D_PROGRESS_PATH\"\n"
        "exit 7\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId("attempt-crash-stage"), _valid_house(), tmp_path / "result",
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["stage"] == "reimport"


def test_interrupted_forced_replacement_restores_the_previous_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_id = "attempt-force-interrupted"
    token = attempt_storage_token(attempt_id)
    destination = tmp_path / "result"
    destination.mkdir()
    previous = {
        "model.glb": b"previous-glb",
        "preview.png": b"previous-png",
        "report.json": b'{"previous":true}',
    }
    for name, content in previous.items():
        (destination / name).write_bytes(content)
    executable = tmp_path / "interruptible-publisher"
    executable.write_text(
        "#!/bin/sh\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--out\" ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        f'mv "$out" "$out.previous-{token}"\n'
        f'mkdir -p "$(dirname "$out")/.generation-{token}-orphan"\n'
        "sleep 30\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("GERADOR_3D_PYTHON", str(executable))

    outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
        AttemptId(attempt_id), _valid_house(), destination,
        existing_result=ExistingResultPolicy.REPLACE, timeout_seconds=0.1,
    ))

    assert isinstance(outcome, FailedAttempt)
    assert outcome.report["error"]["code"] == "environment.timeout"
    assert {name: (destination / name).read_bytes() for name in previous} == previous
    assert not list(tmp_path.glob("result.previous-*"))
    assert not list(tmp_path.glob(".generation-*"))


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
