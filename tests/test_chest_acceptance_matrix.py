"""Ticket 20: matriz de aceitação do Baú Fechado — propriedades objetivas (rápido).

Espelha o padrão do ticket 16 (casa): specs em disco validadas pelo contrato
público, IR determinística dentro do orçamento com validadores verdes, e
baseline.json como metadados prontos-para-humano (nenhuma aprovação automática).
Julgamento estético continua humano; sem asserções de pixel aqui.
"""

import json
from pathlib import Path

from blender_worker import registry, schema

CHEST_DIR = Path("acceptance/chest")
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
    return sorted(p for p in CHEST_DIR.glob("*.json") if p.name != "baseline.json")


def test_matrix_covers_lid_forms_band_lock_combos_limits_and_seeds() -> None:
    specs = _matrix_specs()
    assert len(specs) >= 6, f"matriz pequena demais: {[p.name for p in specs]}"

    loaded = {p.stem: schema.load_spec(json.loads(p.read_text())) for p in specs}
    assert all(type(s) is schema.ChestSpec for s in loaded.values())

    assert {s.lid_form for s in loaded.values()} == {"arched", "flat"}

    bands = {s.band_count for s in loaded.values()}
    assert 0 in bands and 4 in bands, "extremos de band_count sem cobertura"

    locks = {s.has_lock for s in loaded.values()}
    assert locks == {True, False}, "has_lock sem as duas opções"

    bounds = registry.get_descriptor("chest").numeric_bounds
    widths = [s.width for s in loaded.values()]
    heights = [s.height for s in loaded.values()]
    depths = [s.depth for s in loaded.values()]
    assert min(widths) <= bounds["width"][0] + 0.01
    assert max(widths) >= bounds["width"][1] - 0.01
    assert min(heights) <= bounds["height"][0] + 0.01
    assert max(heights) >= bounds["height"][1] - 0.01
    assert min(depths) <= bounds["depth"][0] + 0.01
    assert max(depths) >= bounds["depth"][1] - 0.01

    seeds = [s.seed for s in loaded.values()]
    assert len(set(seeds)) == len(seeds), "seeds devem variar entre specs"


def test_matrix_specs_are_deterministic_within_budget_and_validators_green() -> None:
    descriptor = registry.get_descriptor("chest")
    for path in _matrix_specs():
        spec = schema.load_spec(json.loads(path.read_text()))
        mesh_a, checks_a = descriptor.inspect(spec)
        mesh_b, _ = descriptor.inspect(spec)
        assert mesh_a.vertices == mesh_b.vertices, f"{path.name}: mesma seed divergiu"
        assert [m.name for m in mesh_a.materials] == [m.name for m in mesh_b.materials]
        assert mesh_a.tri_count() <= descriptor.triangle_budget, (
            f"{path.name}: {mesh_a.tri_count()} tris acima do orçamento"
        )
        assert checks_a, f"{path.name}: sem validadores"
        for name, result in checks_a.items():
            assert result["ok"] is True, f"{path.name}:{name} falhou: {result.get('detail')}"


def test_baseline_metadata_is_ready_for_human_not_approved() -> None:
    baseline = json.loads((CHEST_DIR / "baseline.json").read_text())
    assert BASELINE_REQUIRED <= set(baseline), "metadados de baseline incompletos"
    assert baseline["status"] == "ready-for-human"
    assert baseline["approver"] is None
    assert baseline["approved_at"] is None

    stems = {p.stem for p in _matrix_specs()}
    assert set(baseline["specs"]) == stems, "baseline deve listar cada spec da matriz"
    for stem, entry in baseline["specs"].items():
        assert entry["status"] == "ready-for-human", f"{stem}: só humano aprova"
        assert entry["approver"] is None, f"{stem}: aprovador deve ser nulo até revisão"
        assert entry["spec"] == f"{stem}.json"
