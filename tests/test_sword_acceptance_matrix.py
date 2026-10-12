"""Ticket 18: sword acceptance matrix — objective properties (fast level, no bpy).

Seams under test:
- Spec files on disk (acceptance/sword/*.json) parsed by the public
  schema.load_spec contract — catches invalid/out-of-bounds matrix entries.
- Registry descriptor inspect (pure-Python IR path) — catches
  non-determinism, budget overruns, validator regressions.
- baseline.json metadata contract — catches missing approver/version fields.

Aesthetic judgment stays human; this suite never asserts pixel equality.
"""

import json
from pathlib import Path

from blender_worker import registry, schema

SWORD_DIR = Path("acceptance/sword")
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
    return sorted(p for p in SWORD_DIR.glob("*.json") if p.name != "baseline.json")


def test_matrix_covers_canonical_options_limits_seeds_and_risk_combos() -> None:
    specs = _matrix_specs()
    assert len(specs) >= 6, f"matriz pequena demais: {[p.name for p in specs]}"

    loaded = {p.stem: schema.load_spec(json.loads(p.read_text())) for p in specs}
    assert all(type(s) is schema.SwordSpec for s in loaded.values())

    guards = {s.guard_form for s in loaded.values()}
    pommels = {s.pommel_form for s in loaded.values()}
    assert guards == {"straight", "curved", "none"}, f"guard_form sem cobertura: {guards}"
    assert pommels == {"round", "faceted", "none"}, f"pommel_form sem cobertura: {pommels}"

    assert any(
        s.guard_form == "none" and s.pommel_form == "none" for s in loaded.values()
    ), "combo de risco guarda+pomo ausentes sem cobertura"

    bounds = registry.get_descriptor("sword").numeric_bounds
    blades = [s.blade_length for s in loaded.values()]
    widths = [s.blade_width for s in loaded.values()]
    grips = [s.grip_length for s in loaded.values()]
    assert min(blades) <= bounds["blade_length"][0] + 1e-9
    assert max(blades) >= bounds["blade_length"][1] - 1e-9
    assert min(widths) <= bounds["blade_width"][0] + 1e-9
    assert max(widths) >= bounds["blade_width"][1] - 1e-9
    assert min(grips) <= bounds["grip_length"][0] + 1e-9
    assert max(grips) >= bounds["grip_length"][1] - 1e-9

    seeds = [s.seed for s in loaded.values()]
    assert len(set(seeds)) == len(seeds), "seeds devem variar entre specs"


def test_matrix_specs_are_deterministic_within_budget_and_validators_green() -> None:
    descriptor = registry.get_descriptor("sword")
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
    baseline = json.loads((SWORD_DIR / "baseline.json").read_text())
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
