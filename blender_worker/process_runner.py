"""Run each official generation in a fresh, bounded Blender Python process."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from typing import Protocol

from .export import AttemptMetrics, GenerateError, _StageClock
from .failures import REPORT_STAGES, FailureCode
from .reports import failure_report

DEFAULT_TIMEOUT_SECONDS = 300.0


class Cancellation(Protocol):
    @property
    def is_cancelled(self) -> bool: ...


def _timeout_seconds(explicit: float | None) -> float:
    value = explicit
    if value is None:
        value = float(os.environ.get("GERADOR_3D_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    if value <= 0:
        raise ValueError("timeout_seconds deve ser positivo")
    return value


def _remove_attempt_staging(parent: Path, attempt_id: str) -> None:
    for path in parent.glob(f".generation-{attempt_id}-*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def _code_from_stderr(stderr: str) -> tuple[FailureCode, str] | None:
    """Recover the child's structured `code: detail` line, if it printed one."""
    match = re.search(r"^([\w][\w.]*): (.*)$", stderr, re.M)
    if not match:
        return None
    try:
        return FailureCode(match.group(1)), match.group(2)
    except ValueError:
        return None


def _write_runner_failure(out_dir: Path, code: FailureCode, detail: str,
                          *, attempt_id: str,
                          metrics: AttemptMetrics | None = None,
                          stage: str | None = None) -> dict:
    measured = metrics if metrics is not None else AttemptMetrics()
    report = failure_report(
        attempt_id=attempt_id,
        code=code,
        detail=detail,
        stage=stage,
        metrics={
            "stages": dict(measured.stages) if measured.stages else {"total_seconds": 0.0},
            "peak_memory_bytes": measured.peak_memory_bytes,
        },
    )
    if not out_dir.exists() or not any(out_dir.iterdir()):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def _terminate_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return process.communicate()


def run_generation_process(
    spec_path: str,
    out_dir: str,
    *,
    force: bool = False,
    timeout_seconds: float | None = None,
    attempt_id: str | None = None,
    cancellation: Cancellation | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Run one official attempt in a new process and wait until it is reaped."""
    clock = _StageClock()
    timeout = _timeout_seconds(timeout_seconds)
    destination = Path(out_dir).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_path = destination / "report.json"
    # A failed attempt never overwrites an occupied destination, so a report
    # identical to this snapshot is the previous Result of Generation — stale,
    # never the current attempt's. Only a fresh report may be trusted below.
    previous_report = report_path.read_bytes() if report_path.is_file() else None
    attempt_id = attempt_id or uuid.uuid4().hex
    progress_path = destination.parent / f".attempt-{attempt_id}-progress.jsonl"
    progress_path.unlink(missing_ok=True)
    progress_path.touch()
    progress_offset = 0
    last_stage = "input"

    def drain_progress() -> None:
        nonlocal progress_offset, last_stage
        with progress_path.open(encoding="utf-8") as stream:
            stream.seek(progress_offset)
            for line in stream:
                try:
                    stage = str(json.loads(line)["stage"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                if stage not in REPORT_STAGES:
                    continue
                if REPORT_STAGES.index(stage) <= REPORT_STAGES.index(last_stage):
                    continue
                last_stage = stage
                if progress is not None:
                    progress(stage)
            progress_offset = stream.tell()
    executable = os.environ.get("GERADOR_3D_PYTHON", sys.executable)
    command = [
        executable,
        "-m",
        "blender_worker.generation_process",
        "--spec",
        str(Path(spec_path).resolve()),
        "--out",
        str(destination),
    ]
    if force:
        command.append("--force")
    environment = os.environ.copy()
    environment["GERADOR_3D_ATTEMPT_ID"] = attempt_id
    environment["GERADOR_3D_PROGRESS_PATH"] = str(progress_path)
    package_root = str(Path(__file__).resolve().parent.parent)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (package_root, environment.get("PYTHONPATH", "")))
    )
    if progress is not None:
        progress("input")
        progress("environment")
    last_stage = "environment"
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            start_new_session=True,
        )
    except OSError as error:
        measured = clock.snapshot()
        clock.stop()
        progress_path.unlink(missing_ok=True)
        failure_report = _write_runner_failure(
            destination, FailureCode.ENVIRONMENT_UNAVAILABLE, str(error),
            attempt_id=attempt_id,
            metrics=measured,
        )
        raise GenerateError(
            failure_report["error"]["detail"], FailureCode.ENVIRONMENT_UNAVAILABLE,
            report=failure_report,
        ) from error
    deadline = time.monotonic() + timeout
    while True:
        drain_progress()
        if cancellation is not None and cancellation.is_cancelled:
            _stdout, stderr = _terminate_process(process)
            drain_progress()
            committed = None
            if report_path.is_file() and (
                previous_report is None or report_path.read_bytes() != previous_report
            ):
                try:
                    committed = json.loads(report_path.read_text())
                except (json.JSONDecodeError, OSError):
                    committed = None
            if committed is not None and committed.get("stage") == "published":
                # Atomic commit is the terminal point: once visible, success
                # wins even if cancellation was requested concurrently.
                break
            _remove_attempt_staging(destination.parent, attempt_id)
            detail = "cancelamento solicitado durante a execução"
            measured = clock.snapshot()
            clock.stop()
            progress_path.unlink(missing_ok=True)
            cancelled_report = _write_runner_failure(
                destination, FailureCode.EXECUTION_CANCELLED, detail,
                attempt_id=attempt_id, metrics=measured, stage=last_stage,
            )
            raise GenerateError(
                cancelled_report["error"]["detail"], FailureCode.EXECUTION_CANCELLED,
                report=cancelled_report,
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_process(process)
            _remove_attempt_staging(destination.parent, attempt_id)
            detail = f"processo Blender excedeu {timeout:g} segundos e foi encerrado"
            measured = clock.snapshot()
            clock.stop()
            progress_path.unlink(missing_ok=True)
            timeout_report = _write_runner_failure(
                destination, FailureCode.PROCESS_TIMEOUT, detail,
                attempt_id=attempt_id, metrics=measured,
            )
            raise GenerateError(
                timeout_report["error"]["detail"], FailureCode.PROCESS_TIMEOUT,
                report=timeout_report,
            )
        try:
            _stdout, stderr = process.communicate(timeout=min(0.05, remaining))
            drain_progress()
            break
        except subprocess.TimeoutExpired:
            continue

    report_path = destination / "report.json"
    report: dict | None = json.loads(report_path.read_text()) if report_path.is_file() else None
    fresh = report is not None and (
        previous_report is None or report_path.read_bytes() != previous_report
    )
    try:
        committed_success = bool(
            fresh and report is not None
            and report.get("ok") is True and report.get("stage") == "published"
        )
        if process.returncode != 0 and not committed_success:
            if report is None or not fresh:
                # No report from this attempt (occupied destination or a child
                # that died before reporting): recover the structured code
                # from stderr instead of trusting a stale report.
                parsed = _code_from_stderr(stderr)
                if parsed is not None:
                    code, detail = parsed
                else:
                    code = FailureCode.ENVIRONMENT_UNAVAILABLE
                    detail = (
                        stderr.strip()
                        or "processo Blender terminou com status "
                        f"{process.returncode}"
                    )
                measured = clock.snapshot()
                report = _write_runner_failure(
                    destination, code, detail, attempt_id=attempt_id, metrics=measured
                )
            try:
                code = FailureCode(report["error"]["code"])
            except (KeyError, ValueError):
                code = FailureCode.BUILD_FAILED
            raise GenerateError(str(report["error"]["detail"]), code, report=report)
        if report is None or report.get("backend") != "bpy":
            detail = (
                "processo oficial terminou sem relatório "
                "produzido pelo backend bpy"
            )
            measured = clock.snapshot()
            unavailable_report = _write_runner_failure(
                destination, FailureCode.ENVIRONMENT_UNAVAILABLE, detail,
                attempt_id=attempt_id,
                metrics=measured,
            )
            raise GenerateError(
                detail, FailureCode.ENVIRONMENT_UNAVAILABLE,
                report=unavailable_report,
            )
        return report
    finally:
        clock.stop()
        progress_path.unlink(missing_ok=True)
