"""CLI — PLANO_MVP §7: generate --spec X --out Y."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .attempts import (
    CancelledAttempt,
    ExistingResultPolicy,
    FailedAttempt,
    GenerationAttempt,
    GenerationAttemptExecutor,
    new_attempt_id,
    read_untrusted_spec_file,
)
from .failures import MESSAGES, FailureCode


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="blender-worker", description="Gerador 3D low-poly (Marco 1)")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="gera model.glb + preview.png + report.json")
    g.add_argument("--spec", required=True, help="spec JSON de entrada")
    g.add_argument("--out", required=True, help="diretório de saída")
    g.add_argument("--force", action="store_true", help="substitui um Resultado de Geração existente")
    g.add_argument(
        "--timeout-seconds", type=float, default=None,
        help="limite da Tentativa; usa GERADOR_3D_TIMEOUT_SECONDS ou o default do worker",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "generate":
        try:
            outcome = GenerationAttemptExecutor().execute(GenerationAttempt(
                attempt_id=new_attempt_id(),
                spec=read_untrusted_spec_file(args.spec),
                destination=Path(args.out),
                existing_result=(
                    ExistingResultPolicy.REPLACE
                    if args.force else ExistingResultPolicy.REJECT
                ),
                timeout_seconds=args.timeout_seconds,
            ))
        except ValueError as input_error:
            print(f"input.invalid: {input_error}", file=sys.stderr)
            return 1
        if isinstance(outcome, (FailedAttempt, CancelledAttempt)):
            terminal_error = outcome.report["error"]
            code = str(terminal_error["code"])
            try:
                message = MESSAGES[FailureCode(code)]
            except ValueError:
                message = str(terminal_error["message"])
            print(f"{code}: {message}", file=sys.stderr)
            return 1
        report = outcome.report
        print(f"ok: {report['tri_count']} tris -> {args.out}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
