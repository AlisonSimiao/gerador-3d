"""Private child entry point for one isolated official generation attempt."""

from __future__ import annotations

import argparse
import sys

from .export import GenerateError, generate_in_process_from_spec_file
from .failures import FailureCode
from .schema import SpecError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="blender-worker-generation-process")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        generate_in_process_from_spec_file(args.spec, args.out, force=args.force)
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
