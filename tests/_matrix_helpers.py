"""Shared helper for the four acceptance-matrix integration suites.

Compares OBJECTIVE properties only — determinism (same seed regenerates
byte-identical GLB), tri budget, validators green, 1024px preview present.
Aesthetic judgment stays human; no pixel assertions here.

Importing this module never requires `bpy`: generation runs in the
official child process via `generate_from_spec_file`.
"""

from __future__ import annotations

import struct
from pathlib import Path

from blender_worker.export import generate_from_spec_file
from blender_worker.registry import get_descriptor


def matrix_specs(asset_dir: Path) -> list[Path]:
    """Return every matrix spec, excluding the human-owned baseline."""
    return sorted(
        p for p in asset_dir.glob("*.json") if p.name != "baseline.json"
    )


def assert_matrix_regenerates(
    asset_type: str, asset_dir: Path, tmp_path: Path
) -> None:
    """Regenerate the whole matrix via the official path, all green."""
    budget = get_descriptor(asset_type).triangle_budget
    for spec_path in matrix_specs(asset_dir):
        out = tmp_path / spec_path.stem
        report = generate_from_spec_file(str(spec_path), str(out))
        assert report["ok"] is True, f"{spec_path.name}: {report.get('error')}"
        budget_msg = f"{spec_path.name}: orçamento estourado"
        assert report["tri_count"] <= budget, budget_msg
        for name, result in report["checks"].items():
            assert result["ok"] is True, f"{spec_path.name}:{name} falhou"
        png = (out / "preview.png").read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n", (
            f"{spec_path.name}: preview inválido"
        )
        assert struct.unpack(">II", png[16:24]) == (1024, 1024)


def assert_same_seed_regenerates_identical_glb(
    asset_dir: Path, tmp_path: Path
) -> None:
    """The canonical spec regenerates a byte-identical GLB."""
    spec_path = asset_dir / "canonical.json"
    generate_from_spec_file(str(spec_path), str(tmp_path / "a"))
    generate_from_spec_file(str(spec_path), str(tmp_path / "b"))
    assert (tmp_path / "a" / "model.glb").read_bytes() == (
        tmp_path / "b" / "model.glb"
    ).read_bytes()
