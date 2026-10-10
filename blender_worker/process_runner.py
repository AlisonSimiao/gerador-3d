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
import uuid

from .export import AttemptMetrics, GenerateError, _StageClock
from .failures import FailureCode, stage_for_code, structured_error

DEFAULT_TIMEOUT_SECONDS = 300.0


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
                            metrics: AttemptMetrics | None = None) -> dict:
    measured = metrics if metrics is not None else AttemptMetrics()
    report = {
        "schema_version": 1,
        "status": "failure",
        "ok": False,
        "stage": stage_for_code(code),
        "backend": None,
        "environment": {"worker": "0.1.0", "blender": None, "python": None,
                        "process_id": os.getpid(),
                        "render_profile": "medieval_lowpoly-v1"},
        "resolved_spec": None,
        "checks": {},
        "artifacts": ["report.json"],
        "error": structured_error(code, detail),
        "metrics": {"stages": dict(measured.stages)
                    if measured.stages else {"total_seconds": 0.0},
                    "peak_memory_bytes": measured.peak_memory_bytes},
    }
    if not out_dir.exists() or not any(out_dir.iterdir()):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def run_generation_process(
    spec_path: str,
    out_dir: str,
    *,
    force: bool = False,
    timeout_seconds: float | None = None,
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
    attempt_id = uuid.uuid4().hex
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
    package_root = str(Path(__file__).resolve().parent.parent)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (package_root, environment.get("PYTHONPATH", "")))
    )
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
        failure_report = _write_runner_failure(
            destination, FailureCode.ENVIRONMENT_UNAVAILABLE, str(error),
            metrics=measured,
        )
        raise GenerateError(
            failure_report["error"]["detail"], FailureCode.ENVIRONMENT_UNAVAILABLE
        ) from error
    try:
        _stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        _remove_attempt_staging(destination.parent, attempt_id)
        detail = f"processo Blender excedeu {timeout:g} segundos e foi encerrado"
        measured = clock.snapshot()
        clock.stop()
        failure_report = _write_runner_failure(
            destination, FailureCode.PROCESS_TIMEOUT, detail,
            metrics=measured,
        )
        raise GenerateError(
            failure_report["error"]["detail"], FailureCode.PROCESS_TIMEOUT
        ) from error

    report_path = destination / "report.json"
    report: dict | None = json.loads(report_path.read_text()) if report_path.is_file() else None
    fresh = report is not None and (
        previous_report is None or report_path.read_bytes() != previous_report
    )
    try:
        if process.returncode != 0:
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
                    destination, code, detail, metrics=measured
                )
            try:
                code = FailureCode(report["error"]["code"])
            except (KeyError, ValueError):
                code = FailureCode.BUILD_FAILED
            raise GenerateError(str(report["error"]["detail"]), code)
        if report is None or report.get("backend") != "bpy":
            detail = (
                "processo oficial terminou sem relatório "
                "produzido pelo backend bpy"
            )
            measured = clock.snapshot()
            _write_runner_failure(
                destination, FailureCode.ENVIRONMENT_UNAVAILABLE, detail,
                metrics=measured,
            )
            raise GenerateError(detail, FailureCode.ENVIRONMENT_UNAVAILABLE)
        return report
    finally:
        clock.stop()
