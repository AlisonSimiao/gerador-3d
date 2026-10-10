"""Gate de reimportação (ADR 0006): prova via Blender + caminho de falha."""

import json
from pathlib import Path

import pytest

from blender_worker import export as export_module
from blender_worker.export import GenerateError, generate_from_spec_file, inspect as inspect_ir
from blender_worker.failures import FailureCode
from blender_worker.generation_process import main as process_main
from blender_worker.schema import load_spec_file

pytestmark = pytest.mark.integration


def test_gate_proves_topology_materials_anchor_transforms_units_and_integrity(
    tmp_path: Path,
) -> None:
    out = tmp_path / "house"
    report = generate_from_spec_file("specs/house_default.json", str(out))

    gate = report["checks"]["reimport"]
    assert gate["ok"] is True
    # Ticket 09 (contrato de coordenadas) continua verde.
    assert gate["mesh_count"] == 1
    assert gate["root_nodes"] == 1
    assert gate["root_transform_identity"] is True
    # Ticket 11: o gate comprova cada dimensão do Asset entregue.
    assert gate["topology_ok"] is True
    mesh, _ = inspect_ir(load_spec_file("specs/house_default.json"))
    assert gate["tri_count"] == gate["tri_count_expected"] == len(mesh.triangulated())
    assert gate["materials_ok"] is True
    assigned = {mesh.materials[i].name for i in set(mesh.face_materials)}
    assert set(gate["material_names"]) == assigned
    assert gate["anchor_ok"] is True
    assert gate["transforms_ok"] is True
    assert gate["units_ok"] is True
    assert gate["integrity_ok"] is True


def test_gate_rejects_corrupt_or_truncated_glb(tmp_path: Path) -> None:
    mesh, _ = inspect_ir(load_spec_file("specs/house_default.json"))

    garbage = tmp_path / "garbage.glb"
    garbage.write_bytes(b"not a glb at all" * 64)
    assert export_module._reimport_gate(str(garbage), mesh)["ok"] is False

    out = tmp_path / "house"
    generate_from_spec_file("specs/house_default.json", str(out))
    data = (out / "model.glb").read_bytes()
    cut = tmp_path / "cut.glb"
    cut.write_bytes(data[: len(data) // 2])
    assert export_module._reimport_gate(str(cut), mesh)["ok"] is False


def test_corrupt_export_fails_attempt_with_structured_reimport_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        export_module, "_export_glb", lambda path: Path(path).write_bytes(b"GLB corrompido")
    )
    spec = load_spec_file("specs/house_default.json")

    with pytest.raises(GenerateError) as exc:
        export_module.generate(spec, str(tmp_path / "attempt"))
    assert exc.value.code == FailureCode.REIMPORT_FAILED.value

    failed = tmp_path / "failed"
    with pytest.raises(GenerateError):
        export_module.generate_in_process_from_spec_file(
            "specs/house_default.json", str(failed)
        )
    report = json.loads((failed / "report.json").read_text())
    assert report["ok"] is False
    assert report["error"]["code"] == FailureCode.REIMPORT_FAILED.value
    assert report["stage"] == "reimport"
    assert report["artifacts"] == ["report.json"]
    assert sorted(p.name for p in failed.iterdir()) == ["report.json"]
    assert not (failed / "model.glb").exists()

    assert (
        process_main(["--spec", "specs/house_default.json", "--out", str(tmp_path / "failed2")])
        == 1
    )
