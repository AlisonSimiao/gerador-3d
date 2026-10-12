"""Deep module for one complete Generation Attempt."""

from __future__ import annotations

import json
import math
import queue
import tempfile
import threading
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from .failures import FailureCode
from .reports import (
    attempt_storage_token,
    measured_failure_report,
    publish_failure_report,
)


@dataclass(frozen=True)
class AttemptId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("attempt_id não pode ser vazio")


class ExistingResultPolicy(StrEnum):
    REJECT = "reject"
    REPLACE = "replace"


class CancellationToken:
    """Thread-safe, idempotent cancellation request for one attempt."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class GenerationAttempt:
    attempt_id: AttemptId
    spec: object
    destination: Path
    existing_result: ExistingResultPolicy = ExistingResultPolicy.REJECT
    timeout_seconds: float | None = None
    cancellation: CancellationToken | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds is not None and (
            not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds deve ser finito e positivo")


@dataclass(frozen=True)
class PublishedResult:
    attempt_id: AttemptId
    destination: Path
    fingerprint: str
    report: dict[str, Any]


@dataclass(frozen=True)
class FailedAttempt:
    attempt_id: AttemptId
    report: dict[str, Any]


@dataclass(frozen=True)
class CancelledAttempt:
    attempt_id: AttemptId
    report: dict[str, Any]


AttemptOutcome = PublishedResult | FailedAttempt | CancelledAttempt


@dataclass(frozen=True)
class AttemptProgress:
    attempt_id: AttemptId
    sequence: int
    stage: str


class ProgressObserver(Protocol):
    def observe(self, event: AttemptProgress) -> None: ...


class InMemoryProgressObserver:
    def __init__(self) -> None:
        self.events: list[AttemptProgress] = []
        self._lock = threading.Lock()

    def observe(self, event: AttemptProgress) -> None:
        with self._lock:
            self.events.append(event)


class JsonLinesProgressObserver:
    """Local structured progress adapter; remote transports stay out of scope."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    def observe(self, event: AttemptProgress) -> None:
        line = json.dumps({
            "attempt_id": event.attempt_id.value,
            "sequence": event.sequence,
            "stage": event.stage,
        }, ensure_ascii=False)
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")


class _ProgressDispatcher:
    def __init__(self, attempt_id: AttemptId, observer: ProgressObserver | None) -> None:
        self._attempt_id = attempt_id
        self._observer = observer
        self._sequence = 0
        self._queue: queue.Queue[AttemptProgress | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        if observer is not None:
            self._thread = threading.Thread(target=self._deliver, daemon=True)
            self._thread.start()

    def emit(self, stage: str) -> None:
        if self._observer is None:
            return
        self._sequence += 1
        self._queue.put(AttemptProgress(self._attempt_id, self._sequence, stage))

    def _deliver(self) -> None:
        while True:
            event = self._queue.get()
            if event is None:
                return
            try:
                assert self._observer is not None
                self._observer.observe(event)
            except Exception:
                # Progress is observational and cannot change the outcome.
                continue

    def close(self) -> None:
        if self._thread is None:
            return
        self._queue.put(None)
        self._thread.join(timeout=0.25)


def read_untrusted_spec_file(path: str | Path) -> object:
    """Read CLI input while keeping syntax and I/O failures inside the attempt."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return {"input_error": str(error)}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


class GenerationAttemptExecutor:
    """Execute one attempt without exposing the pipeline's internal stages."""

    def __init__(self, observer: ProgressObserver | None = None) -> None:
        self._observer = observer

    def execute(self, attempt: GenerationAttempt) -> AttemptOutcome:
        progress = _ProgressDispatcher(attempt.attempt_id, self._observer)
        try:
            return self._execute(attempt, progress)
        finally:
            progress.close()

    def _execute(
        self, attempt: GenerationAttempt, progress: _ProgressDispatcher,
    ) -> AttemptOutcome:
        if attempt.cancellation is not None and attempt.cancellation.is_cancelled:
            progress.emit("input")
            report = measured_failure_report(
                attempt_id=attempt.attempt_id.value,
                code=FailureCode.EXECUTION_CANCELLED,
                detail="cancelamento solicitado antes do início",
                input_value=attempt.spec,
            )
            publish_failure_report(attempt.destination, report)
            return CancelledAttempt(attempt.attempt_id, report)
        try:
            serialized_spec = json.dumps(attempt.spec, ensure_ascii=False)
        except (TypeError, ValueError) as error:
            progress.emit("input")
            report = measured_failure_report(
                attempt_id=attempt.attempt_id.value,
                code=FailureCode.INPUT_INVALID,
                detail=str(error),
                input_value=attempt.spec,
            )
            publish_failure_report(attempt.destination, report)
            return FailedAttempt(attempt.attempt_id, report)

        # The existing process runner remains the single official execution
        # implementation while this new interface is introduced beside it.
        from .export import GenerateError
        from .process_runner import run_generation_process

        attempt.destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json",
            prefix=f".attempt-{attempt_storage_token(attempt.attempt_id.value)}-",
            dir=attempt.destination.parent, delete=False,
        ) as source:
            source.write(serialized_spec)
            source_path = Path(source.name)
        try:
            try:
                report = run_generation_process(
                    str(source_path), str(attempt.destination),
                    force=attempt.existing_result is ExistingResultPolicy.REPLACE,
                    timeout_seconds=attempt.timeout_seconds,
                    attempt_id=attempt.attempt_id.value,
                    cancellation=attempt.cancellation,
                    progress=progress.emit,
                )
            except GenerateError as error:
                report_path = attempt.destination / "report.json"
                if error.report is not None:
                    report = error.report
                elif report_path.is_file():
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                else:
                    report = measured_failure_report(
                        attempt_id=attempt.attempt_id.value,
                        code=FailureCode(error.code),
                        detail=str(error),
                        input_value=attempt.spec,
                    )
                if error.code == FailureCode.EXECUTION_CANCELLED.value:
                    return CancelledAttempt(attempt.attempt_id, report)
                return FailedAttempt(attempt.attempt_id, report)
        finally:
            source_path.unlink(missing_ok=True)

        fingerprint = str(report.get("generation_fingerprint", ""))
        return PublishedResult(
            attempt.attempt_id, attempt.destination, fingerprint, report,
        )


def new_attempt_id() -> AttemptId:
    return AttemptId(uuid.uuid4().hex)
