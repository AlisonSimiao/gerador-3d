"""Seam 2: pipeline generate — CLI --spec --out gera model.glb + preview + report."""

import json
from pathlib import Path
import struct

import pytest

from blender_worker.export import GenerateError, generate_from_spec_file
from blender_worker.registry import get_descriptor

SPECS = ["house_default", "sword_default", "tree_default", "chest_default"]
pytestmark = pytest.mark.integration


def _glb_document(path: Path) -> dict:
    data = path.read_bytes()
    json_length, json_type = struct.unpack("<II", data[12:20])
    assert json_type == 0x4E4F534A
    return json.loads(data[20:20 + json_length])


@pytest.mark.parametrize("name", SPECS)
def test_generate_produces_artifacts(tmp_path: Path, name: str) -> None:
    out = tmp_path / name
    report = generate_from_spec_file(f"specs/{name}.json", str(out))
    assert report["ok"] is True
    assert (out / "model.glb").exists()
    assert (out / "preview.png").exists()
    assert (out / "report.json").exists()
    assert report["tri_count"] > 0
    assert report["backend"] == "bpy"
    assert report["environment"]["blender"]
    assert report["environment"]["python"]
    assert report["environment"]["process_id"]
    assert report["tri_count"] <= get_descriptor(report["spec"]["type"]).triangle_budget
    for check, result in report["checks"].items():
        assert result["ok"] is True, f"{name}:{check} falhou: {result.get('detail')}"


def test_official_preview_uses_versioned_eevee_four_view_profile(tmp_path: Path) -> None:
    out = tmp_path / "house-preview"

    report = generate_from_spec_file("specs/house_default.json", str(out))

    png = (out / "preview.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (1024, 1024)
    assert report["checks"]["preview"] == {
        "ok": True,
        "detail": "4 vistas renderizadas com BLENDER_EEVEE",
        "profile": "medieval_lowpoly-v1",
        "views": ["perspective", "front", "side", "rear"],
        "size": 1024,
    }


def test_generate_is_deterministic(tmp_path: Path) -> None:
    r1 = generate_from_spec_file("specs/tree_default.json", str(tmp_path / "a"))
    r2 = generate_from_spec_file("specs/tree_default.json", str(tmp_path / "b"))
    assert r1["tri_count"] == r2["tri_count"]
    assert r1["environment"]["process_id"] != r2["environment"]["process_id"]
    glb_a = (tmp_path / "a" / "model.glb").read_bytes()
    glb_b = (tmp_path / "b" / "model.glb").read_bytes()
    assert glb_a == glb_b


def test_invalid_spec_blocks_generation(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"spec_version": 1, "type": "chest", "seed": 1, "width": -5.0,
                               "height": 0.6, "depth": 0.6, "lid_form": "arched",
                               "band_count": 2, "has_lock": True, "style": "medieval_lowpoly"}))
    with pytest.raises((GenerateError, Exception)):
        generate_from_spec_file(str(bad), str(tmp_path / "out"))


def test_report_records_the_fully_resolved_spec(tmp_path: Path) -> None:
    source = tmp_path / "minimal-house.json"
    source.write_text(json.dumps({"spec_version": 1, "type": "house", "seed": 42}))

    report = generate_from_spec_file(str(source), str(tmp_path / "out"))

    assert report["resolved_spec"] == {
        "spec_version": 1,
        "type": "house",
        "seed": 42,
        "width": 6.0,
        "depth": 5.0,
        "floors": 1,
        "roof_form": "gable",
        "wall_finish": "plaster",
        "window_count": 4,
        "has_chimney": True,
        "style": "medieval_lowpoly",
    }


def test_official_glb_has_blender_provenance_and_the_coordinate_contract(tmp_path: Path) -> None:
    out = tmp_path / "house"
    report = generate_from_spec_file("specs/house_default.json", str(out))

    document = _glb_document(out / "model.glb")

    assert "Blender" in document["asset"]["generator"]
    assert document["scenes"][document["scene"]]["nodes"] == [0]
    assert len(document["nodes"]) == 1
    root = document["nodes"][0]
    assert root["mesh"] == 0
    assert not ({"translation", "rotation", "scale"} & root.keys())
    assert len(document["meshes"]) == 1

    primitives = document["meshes"][0]["primitives"]
    material_names = {
        document["materials"][primitive["material"]]["name"] for primitive in primitives
    }
    assert material_names == {"wall_plaster", "roof", "wood_dark", "glass"}

    position_bounds = [
        document["accessors"][primitive["attributes"]["POSITION"]] for primitive in primitives
    ]
    assert min(bounds["min"][1] for bounds in position_bounds) == pytest.approx(0.0)
    assert max(bounds["max"][1] for bounds in position_bounds) < 10.0
    door = next(
        primitive for primitive in primitives
        if document["materials"][primitive["material"]]["name"] == "wood_dark"
    )
    door_bounds = document["accessors"][door["attributes"]["POSITION"]]
    assert door_bounds["min"][2] > 0.0, "a fachada frontal deve apontar para +Z"
    assert report["checks"]["reimport"]["coordinate_system"] == {
        "handedness": "right",
        "up": "+Y",
        "front": "+Z",
        "unit": "meter",
    }
    assert report["checks"]["reimport"]["root_nodes"] == 1
    assert report["checks"]["reimport"]["mesh_count"] == 1
    assert report["checks"]["reimport"]["root_transform_identity"] is True


def test_canonical_house_passes_the_official_pipeline_within_budget(tmp_path: Path) -> None:
    report = generate_from_spec_file(
        "acceptance/house/canonical.json", str(tmp_path / "canonical-house")
    )

    assert report["status"] == "success"
    assert report["resolved_spec"]["type"] == "house"
    assert report["tri_count"] <= get_descriptor("house").triangle_budget
    assert all(check["ok"] for check in report["checks"].values())
