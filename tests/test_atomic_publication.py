"""Ticket 12: atomic publication of the Result of Generation (ADR 0006).

Seam under test: `generate_from_spec_file` / `generate_in_process_from_spec_file`
observed via the destination directory — the only public evidence of an
attempt. What it catches: partial publishes, stale staging areas, and
artifacts from mixed specs. What it misses: stage internals (covered by
tickets 10/11/13/14 at their own seams).
"""

import json
from pathlib import Path

import pytest

from blender_worker import export as export_module
from blender_worker.export import GenerateError, generate_from_spec_file
from blender_worker.failures import FailureCode
from blender_worker.schema import load_spec_file, spec_to_dict

pytestmark = pytest.mark.integration


def test_success_publishes_a_consistent_triple_and_discards_staging(
    tmp_path: Path,
) -> None:
    out = tmp_path / "house"
    report = generate_from_spec_file("specs/house_default.json", str(out))

    # The destination holds exactly the triple — nothing more, nothing less.
    assert sorted(p.name for p in out.iterdir()) == [
        "model.glb",
        "preview.png",
        "report.json",
    ]
    assert report["artifacts"] == ["model.glb", "preview.png", "report.json"]

    # All three artifacts answer to the same Resolved Spec.
    expected_spec = spec_to_dict(load_spec_file("specs/house_default.json"))
    assert report["resolved_spec"] == expected_spec
    on_disk = json.loads((out / "report.json").read_text())
    assert on_disk["resolved_spec"] == expected_spec
    mesh, _ = export_module.inspect(load_spec_file("specs/house_default.json"))
    assert report["materials"] == [m.name for m in mesh.materials]
    gate = report["checks"]["reimport"]
    assert gate["ok"] is True
    assigned = {mesh.materials[i].name for i in set(mesh.face_materials)}
    assert set(gate["material_names"]) == assigned
    assert assigned <= set(report["materials"])
    assert gate["tri_count"] == gate["tri_count_expected"] == len(mesh.triangulated())

    # The temporary staging area is gone after a successful publish.
    assert not list(tmp_path.glob(".generation-*"))


def test_forced_reimport_rejection_publishes_only_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _reject(_path: str, _mesh: object) -> dict:
        return {"ok": False, "detail": "reimportação rejeitada: forçada pelo teste"}

    monkeypatch.setattr(export_module, "_reimport_gate", _reject)

    with pytest.raises(GenerateError) as exc:
        export_module.generate_in_process_from_spec_file(
            "specs/house_default.json", str(tmp_path / "failed")
        )
    assert exc.value.code == FailureCode.REIMPORT_FAILED.value

    failed = tmp_path / "failed"
    assert sorted(p.name for p in failed.iterdir()) == ["report.json"]
    report = json.loads((failed / "report.json").read_text())
    assert report["ok"] is False
    assert report["error"]["code"] == FailureCode.REIMPORT_FAILED.value
    assert report["artifacts"] == ["report.json"]
    assert not (failed / "model.glb").exists()
    assert not (failed / "preview.png").exists()

    # The temporary staging area is gone after a failed publish too.
    assert not list(tmp_path.glob(".generation-*"))
