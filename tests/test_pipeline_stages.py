"""Ticket 17: integration level covers each pipeline stage separately.

End-to-end `generate()` is pinned by test_pipeline.py; the reimport gate's
rejection paths by test_reimport_gate.py (ticket 11). Here each official
stage — construction, rendering, export, reimport — is exercised at its own
seam on the official environment (Python 3.13 + bpy 5.2.2), so a stage
regression points at the stage, not at the whole pipeline.
"""

import json
import struct
from pathlib import Path

import pytest

from blender_worker import export as export_module
from blender_worker.bpy_build import mesh_to_bpy
from blender_worker.export import _export_glb, _reimport_gate, inspect
from blender_worker.preview import render_official_preview
from blender_worker.schema import load_spec_file

pytestmark = pytest.mark.integration

SPEC = "specs/house_default.json"


def _fresh_build() -> tuple[object, object]:
    """Inspect the default house spec and construct it in a fresh scene."""
    import bpy  # type: ignore[import-not-found]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh, _ = inspect(load_spec_file(SPEC))
    return mesh, mesh_to_bpy(mesh, "house")


def _glb_document(path: Path) -> dict:
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    json_length, json_type = struct.unpack("<II", data[12:20])
    assert json_type == 0x4E4F534A
    return json.loads(data[20:20 + json_length])


def test_stage_construction_builds_one_linked_mesh_with_assigned_materials() -> None:
    import bpy  # type: ignore[import-not-found]

    mesh, obj = _fresh_build()

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    assert meshes == [obj]
    assert obj.parent is None
    assert len(obj.data.polygons) > 0
    expected = sorted({mesh.materials[i].name for i in set(mesh.face_materials)})
    slots = [m.name for m in obj.data.materials]
    # Construction assigns every face a valid slot covering each used material
    # (unused palette entries ride along; the exporter prunes them).
    assert sorted({slots[i] for i in {p.material_index for p in obj.data.polygons}}) == expected
    assert all(p.material_index < len(slots) for p in obj.data.polygons)


def test_stage_render_produces_the_versioned_four_view_board(tmp_path: Path) -> None:
    _fresh_build()
    out = tmp_path / "preview.png"

    check = render_official_preview(str(out))

    assert check == {
        "ok": True,
        "detail": "4 vistas renderizadas com BLENDER_EEVEE",
        "profile": "medieval_lowpoly-v1",
        "views": ["perspective", "front", "side", "rear"],
        "size": 1024,
    }
    png = out.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (1024, 1024)


def test_stage_export_writes_a_blender_glb_with_a_single_root(tmp_path: Path) -> None:
    _fresh_build()
    glb = tmp_path / "model.glb"

    _export_glb(str(glb))

    document = _glb_document(glb)
    assert "Blender" in document["asset"]["generator"]
    assert document["scenes"][document["scene"]]["nodes"] == [0]
    assert len(document["nodes"]) == 1
    assert document["nodes"][0]["mesh"] == 0
    assert len(document["meshes"]) == 1


def test_stage_reimport_proves_the_staged_export_before_publication(
    tmp_path: Path,
) -> None:
    mesh, _ = _fresh_build()
    glb = tmp_path / "model.glb"
    _export_glb(str(glb))

    gate = _reimport_gate(str(glb), mesh)

    assert gate["ok"] is True
    assert gate["mesh_count"] == 1
    assert gate["root_nodes"] == 1
    assert gate["root_transform_identity"] is True
    assert gate["topology_ok"] is True
    assert gate["tri_count"] == gate["tri_count_expected"] == len(mesh.triangulated())
    assert gate["materials_ok"] is True
    assert gate["anchor_ok"] is True
    assert gate["transforms_ok"] is True
    assert gate["units_ok"] is True
    assert gate["integrity_ok"] is True
    assert gate["coordinate_system"] == {
        "handedness": "right",
        "up": "+Y",
        "front": "+Z",
        "unit": "meter",
    }
    assert export_module.GLTF_COORDINATE_SYSTEM["up"] == "+Y"
