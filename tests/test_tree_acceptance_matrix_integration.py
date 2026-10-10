"""Ticket 19 (integration): regenerate the whole tree matrix via the official path.

Compares OBJECTIVE properties only — determinism (same seed regenerates
byte-identical GLB), tri budget, validators green, 1024px preview present.
Aesthetic judgment stays human; no pixel assertions here.
"""

import struct
from pathlib import Path

import pytest

from blender_worker.export import generate_from_spec_file
from blender_worker.registry import get_descriptor

pytestmark = pytest.mark.integration

TREE_DIR = Path("acceptance/tree")


def _matrix_specs() -> list[Path]:
    return sorted(p for p in TREE_DIR.glob("*.json") if p.name != "baseline.json")


def test_matrix_regenerates_with_objective_properties_green(tmp_path: Path) -> None:
    budget = get_descriptor("tree").triangle_budget
    for spec_path in _matrix_specs():
        out = tmp_path / spec_path.stem
        report = generate_from_spec_file(str(spec_path), str(out))
        assert report["ok"] is True, f"{spec_path.name}: {report.get('error')}"
        assert report["tri_count"] <= budget, f"{spec_path.name}: orçamento estourado"
        for name, result in report["checks"].items():
            assert result["ok"] is True, f"{spec_path.name}:{name} falhou"
        png = (out / "preview.png").read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n", f"{spec_path.name}: preview inválido"
        assert struct.unpack(">II", png[16:24]) == (1024, 1024)


def test_matrix_same_seed_regenerates_identical_glb(tmp_path: Path) -> None:
    spec_path = TREE_DIR / "canonical.json"
    generate_from_spec_file(str(spec_path), str(tmp_path / "a"))
    generate_from_spec_file(str(spec_path), str(tmp_path / "b"))
    assert (tmp_path / "a" / "model.glb").read_bytes() == (
        tmp_path / "b" / "model.glb"
    ).read_bytes()
