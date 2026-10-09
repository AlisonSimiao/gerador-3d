"""CLI — PLANO_MVP §7: generate --spec X --out Y."""

from __future__ import annotations

import argparse
import sys

from .export import GenerateError, generate_from_spec_file
from .schema import SpecError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="blender-worker", description="Gerador 3D low-poly (Marco 1)")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="gera model.glb + preview.png + report.json")
    g.add_argument("--spec", required=True, help="spec JSON de entrada")
    g.add_argument("--out", required=True, help="diretório de saída")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "generate":
        try:
            report = generate_from_spec_file(args.spec, args.out)
        except (SpecError, GenerateError) as e:
            print(f"erro: {e}", file=sys.stderr)
            return 1
        print(f"ok: {report['tri_count']} tris -> {args.out}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
