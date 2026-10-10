"""Ticket 19: tree v1 acceptance matrix — objective properties (fast level, no bpy).

Seams under test:
- Spec files on disk (acceptance/tree/*.json) parsed by the public
  schema.load_spec contract — catches invalid/out-of-bounds matrix entries.
- Registry descriptor inspect (pure-Python IR path) — catches
  non-determinism, budget overruns, validator regressions.
- baseline.json metadata contract — catches missing approver/version fields.

Aesthetic judgment stays human; this suite never asserts pixel equality.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from blender_worker import registry, schema

TREE_DIR = Path("acceptance/tree")
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
    return sorted(p for p in TREE_DIR.glob("*.json") if p.name != "baseline.json")


def _tree(**changes: Any):
    return registry.get_descriptor("tree").inspect(
        schema.load_spec({"spec_version": 1, "type": "tree", "seed": 13, **changes})
    )[0]


def test_tree_v1_contract_matches_adr0009() -> None:
    spec = schema.load_spec(
        {"spec_version": 1, "type": "tree", "seed": 13}
    )
    assert type(spec) is schema.TreeSpec
    assert (spec.trunk_height, spec.trunk_radius) == (3.0, 0.25)
    assert (spec.canopy_form, spec.foliage_palette) == ("clustered", "green")
    assert spec.lean_degrees == 5.0

    # Old `lean` fraction field is rejected; lean is degrees, not a fraction.
    with pytest.raises(schema.SpecError):
        schema.load_spec(
            {"spec_version": 1, "type": "tree", "seed": 13, "lean": 0.1,
             "trunk_height": 3.0, "trunk_radius": 0.25,
             "canopy_form": "clustered", "foliage_palette": "green",
             "lean_degrees": 5.0, "style": "medieval_lowpoly"}
        )

    for bad in (
        {"lean_degrees": -0.1},
        {"lean_degrees": 20.1},
        {"trunk_height": 1.4},
        {"trunk_height": 8.1},
        {"trunk_radius": 0.11},
        {"trunk_radius": 0.61},
        {"canopy_form": "pine"},
        {"foliage_palette": "pine"},
    ):
        with pytest.raises(schema.SpecError):
            schema.load_spec({"spec_version": 1, "type": "tree", "seed": 13, **bad})


def test_tree_canopy_form_and_foliage_palette_are_independent() -> None:
    descriptor = registry.get_descriptor("tree")

    # Same form, two palettes: same structure, different leaf color.
    green = _tree(canopy_form="clustered", foliage_palette="green")
    autumn = _tree(canopy_form="clustered", foliage_palette="autumn")
    assert green.components == autumn.components
    assert [m.name for m in green.materials] == ["trunk", "leaf_green"]
    assert [m.name for m in autumn.materials] == ["trunk", "leaf_autumn"]
    assert green.materials[1].color == (0.25, 0.50, 0.22, 1.0)
    assert autumn.materials[1].color == (0.80, 0.45, 0.15, 1.0)

    # Same palette, two forms: same leaf color, different structure.
    round_green = _tree(canopy_form="round", foliage_palette="green")
    conical_green = _tree(canopy_form="conical", foliage_palette="green")
    assert round_green.materials[1].color == green.materials[1].color
    assert conical_green.materials[1].color == green.materials[1].color
    canopy_faces = {
        form: _tree(canopy_form=form).components["canopy"][1]
        - _tree(canopy_form=form).components["canopy"][0]
        for form in ("clustered", "round", "conical")
    }
    assert len(set(canopy_faces.values())) >= 2, "canopy forms must differ observably"

    for form in ("clustered", "round", "conical"):
        mesh, checks = descriptor.inspect(
            schema.load_spec(
                {"spec_version": 1, "type": "tree", "seed": 13,
                 "canopy_form": form, "foliage_palette": "dark_green"}
            )
        )
        assert all(check["ok"] for check in checks.values())
        assert mesh.materials[1].name == "leaf_dark_green"


def test_tree_lean_degrees_applies_to_trunk_and_canopy() -> None:
    upright = _tree(lean_degrees=0.0)
    leaning = _tree(lean_degrees=20.0)

    # Upright: trunk base at origin, canopy centered above it.
    trunk_lower, _trunk_upper = upright.component_bounds("trunk")
    assert trunk_lower[0] == pytest.approx(0.0, abs=0.3)
    assert trunk_lower[1] == pytest.approx(0.0, abs=0.3)

    # Leaning: trunk top and canopy both shift off-axis in the same direction.
    trunk_bounds = leaning.component_bounds("trunk")
    canopy_bounds = leaning.component_bounds("canopy")
    trunk_shift = (
        (trunk_bounds[0][0] + trunk_bounds[1][0]) / 2,
        (trunk_bounds[0][1] + trunk_bounds[1][1]) / 2,
    )
    canopy_center = (
        (canopy_bounds[0][0] + canopy_bounds[1][0]) / 2,
        (canopy_bounds[0][1] + canopy_bounds[1][1]) / 2,
    )
    assert abs(trunk_shift[0]) + abs(trunk_shift[1]) > 0.1
    assert (canopy_center[0] * trunk_shift[0] >= 0) and (
        canopy_center[1] * trunk_shift[1] >= 0
    ), "canopy must follow the lean direction, not oppose it"
    assert abs(canopy_center[0]) + abs(canopy_center[1]) >= abs(
        trunk_shift[0]
    ) + abs(trunk_shift[1])


def test_tree_anchor_is_support_surface_center_at_origin() -> None:
    from blender_worker.geometry import AnchorKind

    descriptor = registry.get_descriptor("tree")
    for form in ("clustered", "round", "conical"):
        mesh, checks = descriptor.inspect(
            schema.load_spec(
                {"spec_version": 1, "type": "tree", "seed": 13, "canopy_form": form}
            )
        )
        assert mesh.anchor == (0.0, 0.0, 0.0)
        assert mesh.anchor_kind is AnchorKind.SUPPORT_SURFACE
        assert checks["anchor"]["ok"] is True


def test_tree_same_seed_rebuilds_equivalent_geometry_and_materials() -> None:
    descriptor = registry.get_descriptor("tree")
    spec = schema.load_spec(
        {"spec_version": 1, "type": "tree", "seed": 13,
         "canopy_form": "clustered", "foliage_palette": "autumn"}
    )

    first, first_checks = descriptor.inspect(spec)
    second, second_checks = descriptor.inspect(spec)

    assert first.vertices == second.vertices
    assert first.faces == second.faces
    assert first.face_materials == second.face_materials
    assert [(m.name, m.color) for m in first.materials] == [
        (m.name, m.color) for m in second.materials
    ]
    assert first.components == second.components
    assert all(check["ok"] for check in first_checks.values())
    assert all(check["ok"] for check in second_checks.values())


def test_tree_distinct_seeds_vary_observably_but_stay_recognizable() -> None:
    descriptor = registry.get_descriptor("tree")

    def tree(seed: int):
        return descriptor.inspect(
            schema.load_spec({"spec_version": 1, "type": "tree", "seed": seed})
        )[0]

    first = tree(13)
    second = tree(14)

    assert first.vertices != second.vertices

    for mesh in (first, second):
        assert set(mesh.components) == {"trunk", "canopy"}
        assert [m.name for m in mesh.materials] == ["trunk", "leaf_green"]
        assert mesh.tri_count() == first.tri_count()


def test_matrix_covers_canonical_options_limits_seeds_and_risk_combos() -> None:
    specs = _matrix_specs()
    assert len(specs) >= 6, f"matriz pequena demais: {[p.name for p in specs]}"

    loaded = {p.stem: schema.load_spec(json.loads(p.read_text())) for p in specs}
    assert all(type(s) is schema.TreeSpec for s in loaded.values())

    forms = {s.canopy_form for s in loaded.values()}
    palettes = {s.foliage_palette for s in loaded.values()}
    assert forms == {"clustered", "round", "conical"}, f"formas sem cobertura: {forms}"
    assert palettes == {"green", "autumn", "dark_green"}, (
        f"paletas sem cobertura: {palettes}"
    )

    # Independence: one form appears with two palettes.
    by_form: dict[str, set[str]] = {}
    for s in loaded.values():
        by_form.setdefault(s.canopy_form, set()).add(s.foliage_palette)
    assert any(len(v) >= 2 for v in by_form.values()), "forma × paleta sem prova de independência"

    bounds = registry.get_descriptor("tree").numeric_bounds
    heights = [s.trunk_height for s in loaded.values()]
    radii = [s.trunk_radius for s in loaded.values()]
    leans = [s.lean_degrees for s in loaded.values()]
    assert min(heights) <= bounds["trunk_height"][0] + 0.01
    assert max(heights) >= bounds["trunk_height"][1] - 0.01
    assert min(radii) <= bounds["trunk_radius"][0] + 0.01
    assert max(radii) >= bounds["trunk_radius"][1] - 0.01
    assert min(leans) <= bounds["lean_degrees"][0] + 0.01
    assert max(leans) >= bounds["lean_degrees"][1] - 0.01

    seeds = [s.seed for s in loaded.values()]
    assert len(set(seeds)) == len(seeds), "seeds devem variar entre specs"


def test_matrix_specs_are_deterministic_within_budget_and_validators_green() -> None:
    descriptor = registry.get_descriptor("tree")
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


def test_baseline_metadata_is_ready_for_human_not_approved() -> None:
    baseline = json.loads((TREE_DIR / "baseline.json").read_text())
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
