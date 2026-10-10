"""Private child entry point for one isolated official generation attempt."""

from __future__ import annotations

import argparse

from .export import GenerateError, generate_in_process_from_spec_file
from .schema import SpecError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="blender-worker-generation-process")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        generate_in_process_from_spec_file(args.spec, args.out, force=args.force)
    except (SpecError, GenerateError):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
