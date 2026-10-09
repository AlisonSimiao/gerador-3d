"""Seam 2: pipeline generate — CLI --spec --out gera model.glb + preview + report."""

import json
from pathlib import Path

import pytest

from blender_worker.export import GenerateError, generate_from_spec_file
from blender_worker.validators import TRI_BUDGETS

SPECS = ["house_default", "sword_default", "tree_default", "chest_default"]


@pytest.mark.parametrize("name", SPECS)
def test_generate_produces_artifacts(tmp_path: Path, name: str) -> None:
    out = tmp_path / name
    report = generate_from_spec_file(f"specs/{name}.json", str(out))
    assert report["ok"] is True
    assert (out / "model.glb").exists()
    assert (out / "preview.png").exists()
    assert (out / "report.json").exists()
    assert report["tri_count"] > 0
    assert report["tri_count"] <= TRI_BUDGETS[report["spec"]["type"]]
    for check, result in report["checks"].items():
        assert result["ok"] is True, f"{name}:{check} falhou: {result.get('detail')}"


def test_generate_is_deterministic(tmp_path: Path) -> None:
    r1 = generate_from_spec_file("specs/tree_default.json", str(tmp_path / "a"))
    r2 = generate_from_spec_file("specs/tree_default.json", str(tmp_path / "b"))
    assert r1["tri_count"] == r2["tri_count"]
    glb_a = (tmp_path / "a" / "model.glb").read_bytes()
    glb_b = (tmp_path / "b" / "model.glb").read_bytes()
    assert glb_a == glb_b


def test_invalid_spec_blocks_generation(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"type": "chest", "seed": 1, "width": -5,
                               "height": 0.6, "depth": 0.6, "lid_type": "arched",
                               "bands": 2, "lock": True, "style": "medieval_lowpoly"}))
    with pytest.raises((GenerateError, Exception)):
        generate_from_spec_file(str(bad), str(tmp_path / "out"))
