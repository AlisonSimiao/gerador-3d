"""Private child entry point for one isolated official generation attempt."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .export import GenerateError, generate_in_process_from_spec_file
from .failures import FailureCode
from .schema import SpecError


def _progress_writer():
    path = os.environ.get("GERADOR_3D_PROGRESS_PATH")
    attempt_id = os.environ.get("GERADOR_3D_ATTEMPT_ID", "local")
    sequence = 0

    def emit(stage: str) -> None:
        nonlocal sequence
        if path is None:
            return
        sequence += 1
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "attempt_id": attempt_id,
                "sequence": sequence,
                "stage": stage,
            }) + "\n")
            stream.flush()

    return emit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="blender-worker-generation-process")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        generate_in_process_from_spec_file(
            args.spec, args.out, force=args.force, progress=_progress_writer(),
        )
    except (SpecError, GenerateError) as error:
        # Structured stderr so the parent CLI can report the exact failure
        # code even when no fresh report exists (e.g. an occupied destination
        # the attempt must leave untouched).
        code = error.code if isinstance(error, GenerateError) else FailureCode.INPUT_INVALID.value
        print(f"{code}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
