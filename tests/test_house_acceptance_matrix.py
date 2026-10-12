"""Ticket 16: house acceptance matrix — objective properties (fast level, no bpy).

Seams under test:
- Spec files on disk (acceptance/house/*.json) parsed by the public
  schema.load_spec contract — catches invalid/out-of-bounds matrix entries.
- Registry descriptor inspect (pure-Python IR path) — catches
  non-determinism, budget overruns, validator regressions.
- baseline.json metadata contract — catches missing approver/version fields.

Aesthetic judgment stays human; this suite never asserts pixel equality.
"""

import json
from pathlib import Path

from blender_worker import registry, schema

HOUSE_DIR = Path("acceptance/house")
BASELINE_REQUIRED = {
    "status",
    "approver",
    "approved_at",
    "spec_version",
    "worker_version",
    "blender_version",
    "render_profile",
    "specs",
}


def _matrix_specs() -> list[Path]:
    return sorted(p for p in HOUSE_DIR.glob("*.json") if p.name != "baseline.json")


def test_matrix_covers_canonical_options_limits_seeds_and_risk_combos() -> None:
    specs = _matrix_specs()
    assert len(specs) >= 6, f"matriz pequena demais: {[p.name for p in specs]}"

    loaded = {p.stem: schema.load_spec(json.loads(p.read_text())) for p in specs}
    assert all(type(s) is schema.HouseSpec for s in loaded.values())

    combos = {(s.roof_form, s.wall_finish) for s in loaded.values()}
    for roof in ("gable", "hip"):
        for finish in ("plaster", "timber", "stone"):
            assert (roof, finish) in combos, f"combo {roof}x{finish} sem cobertura"

    floors = {s.floors for s in loaded.values()}
    assert 1 in floors and 3 in floors, "extremos de pavimentos sem cobertura"

    seeds = [s.seed for s in loaded.values()]
    assert len(set(seeds)) == len(seeds), "seeds devem variar entre specs"

    widths = [s.width for s in loaded.values()]
    depths = [s.depth for s in loaded.values()]
    bounds = registry.get_descriptor("house").numeric_bounds
    assert min(widths) <= bounds["width"][0] + 0.01, "limite inferior de width sem cobertura"
    assert max(widths) >= bounds["width"][1] - 0.01, "limite superior de width sem cobertura"
    assert min(depths) <= bounds["depth"][0] + 0.01, "limite inferior de depth sem cobertura"
    assert max(depths) >= bounds["depth"][1] - 0.01, "limite superior de depth sem cobertura"


def test_matrix_specs_are_deterministic_within_budget_and_validators_green() -> None:
    descriptor = registry.get_descriptor("house")
    for path in _matrix_specs():
        spec = schema.load_spec(json.loads(path.read_text()))
        mesh_a, checks_a = descriptor.inspect(spec)
        mesh_b, _ = descriptor.inspect(spec)
        assert mesh_a.tri_count() == mesh_b.tri_count(), f"{path.name}: mesma seed divergiu"
        assert [m.name for m in mesh_a.materials] == [m.name for m in mesh_b.materials]
        assert mesh_a.tri_count() <= descriptor.triangle_budget, (
            f"{path.name}: {mesh_a.tri_count()} tris acima do orçamento"
        )
        assert checks_a, f"{path.name}: sem validadores"
        for name, result in checks_a.items():
            assert result["ok"] is True, f"{path.name}:{name} falhou: {result.get('detail')}"


def test_baseline_metadata_records_human_approval() -> None:
    baseline = json.loads((HOUSE_DIR / "baseline.json").read_text())
    assert BASELINE_REQUIRED <= set(baseline), "metadados de baseline incompletos"
    assert baseline["status"] == "approved"
    assert baseline["approver"] == "user"
    assert baseline["approved_at"] == "2026-10-12"

    stems = {p.stem for p in _matrix_specs()}
    assert set(baseline["specs"]) == stems, "baseline deve listar cada spec da matriz"
    for stem, entry in baseline["specs"].items():
        assert entry["status"] == "approved", f"{stem}: aprovação humana não registrada"
        assert entry["approver"] == "user", f"{stem}: aprovador incorreto"
        assert entry["approved_at"] == "2026-10-12", f"{stem}: data de aprovação incorreta"
        assert entry["spec"] == f"{stem}.json"
