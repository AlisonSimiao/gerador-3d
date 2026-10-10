"""Ticket 18: sword v1 contract, grip-center anchor and seed behavior (fast, no bpy).

Seams under test:
- schema.load_spec contract — catches drift from the ADR 0009 sword v1
  vocabulary (fields, ranges, defaults) and silently accepted old fields.
- Registry descriptor inspect (pure-Python IR path) — catches anchor
  regressions, seed-ignored builds, and non-reproducible generations.
"""

from dataclasses import replace
from typing import Any, cast

import pytest

from blender_worker.geometry import AnchorKind
from blender_worker.registry import get_descriptor
from blender_worker.schema import SpecError, load_spec, load_spec_file


def _sword(**overrides: Any):
    base = {
        "spec_version": 1,
        "type": "sword",
        "seed": 7,
    }
    base.update(overrides)
    return load_spec(base)


def test_sword_v1_contract_has_exact_fields_ranges_and_defaults() -> None:
    spec = load_spec_file("specs/sword_default.json")

    assert spec.blade_length == 0.9
    assert spec.blade_width == 0.07
    assert spec.guard_form == "straight"
    assert spec.grip_length == 0.14
    assert spec.pommel_form == "round"

    bounds = get_descriptor("sword").numeric_bounds
    assert bounds["blade_length"] == (0.6, 1.1)
    assert bounds["blade_width"] == (0.04, 0.10)
    assert bounds["grip_length"] == (0.10, 0.18)


@pytest.mark.parametrize(
    "field,value",
    [
        ("blade_length", 0.59),
        ("blade_length", 1.11),
        ("blade_width", 0.039),
        ("blade_width", 0.101),
        ("grip_length", 0.099),
        ("grip_length", 0.181),
        ("guard_form", "cross"),
        ("pommel_form", "spiked"),
    ],
)
def test_sword_v1_rejects_out_of_contract_values(field: str, value: Any) -> None:
    data = {
        "spec_version": 1, "type": "sword", "seed": 7,
        "blade_length": 0.9, "blade_width": 0.07, "guard_form": "straight",
        "grip_length": 0.14, "pommel_form": "round",
        "style": "medieval_lowpoly",
    }
    data[field] = value
    with pytest.raises(SpecError):
        load_spec(data)


@pytest.mark.parametrize("old_field", ["blade_thickness", "fuller_depth", "edge_sharpness", "crossguard_width"])
def test_sword_v1_rejects_old_or_unknown_fields(old_field: str) -> None:
    data = {
        "spec_version": 1, "type": "sword", "seed": 7,
        "blade_length": 0.9, "blade_width": 0.07, "guard_form": "straight",
        "grip_length": 0.14, "pommel_form": "round",
        "style": "medieval_lowpoly", old_field: 0.01,
    }
    with pytest.raises(SpecError):
        load_spec(data)


def test_sword_anchor_is_the_grip_center_at_the_origin() -> None:
    descriptor = get_descriptor("sword")
    mesh, checks = descriptor.inspect(load_spec_file("specs/sword_default.json"))

    assert mesh.anchor == (0.0, 0.0, 0.0)
    assert mesh.anchor_kind is AnchorKind.GRIP_CENTER
    assert checks["anchor"]["ok"] is True
    assert checks["anchor"]["kind"] == "grip_center"

    # The grip spans symmetrically around the origin: its bbox centre IS the anchor.
    (x0, y0, z0), (x1, y1, z1) = mesh.component_bounds("grip")
    assert (x0 + x1) / 2 == pytest.approx(0.0)
    assert (y0 + y1) / 2 == pytest.approx(0.0)
    assert (z0 + z1) / 2 == pytest.approx(0.0)


@pytest.mark.parametrize(
    "changes", [{"guard_form": "curved"}, {"guard_form": "none"}, {"pommel_form": "none"}]
)
def test_sword_anchor_holds_for_every_guard_pommel_option(changes: dict[str, Any]) -> None:
    descriptor = get_descriptor("sword")
    spec = replace(cast(Any, load_spec_file("specs/sword_default.json")), **changes)

    mesh, checks = descriptor.inspect(spec)

    assert mesh.anchor == (0.0, 0.0, 0.0)
    assert checks["anchor"]["ok"] is True


def test_sword_same_seed_rebuilds_equivalent_geometry_and_materials() -> None:
    """Same Spec + same Seed + same environment → equivalent IR (ADR 0004)."""
    descriptor = get_descriptor("sword")
    spec = _sword(seed=7, guard_form="curved", pommel_form="faceted")

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


def test_sword_distinct_seeds_vary_observably_but_stay_recognizable() -> None:
    """Two distinct Seeds: recognizably the same sword, observable variation."""
    descriptor = get_descriptor("sword")

    def sword(seed: int):
        return descriptor.inspect(_sword(seed=seed))[0]

    first = sword(7)
    second = sword(8)

    # Observable variation: secondary geometry (blade thickness jitter) differs.
    assert first.vertices != second.vertices
    assert first.component_bounds("blade") != second.component_bounds("blade")

    # Recognizably the same sword: structure, options, dimensions, materials.
    for mesh in (first, second):
        assert set(mesh.components) == {"pommel", "grip", "guard", "blade"}
        assert [m.name for m in mesh.materials] == [
            "blade_steel", "guard_iron", "pommel_gold", "grip",
        ]
        assert mesh.component_bounds("grip") == first.component_bounds("grip")
        assert mesh.tri_count() == first.tri_count()


@pytest.mark.parametrize(
    "changes",
    [
        {"guard_form": "curved", "pommel_form": "faceted"},
        {"guard_form": "none", "pommel_form": "none"},
    ],
)
def test_sword_seed_never_contradicts_spec_intent(changes: dict[str, Any]) -> None:
    """The Seed never overrides dimensions, options or material family."""
    descriptor = get_descriptor("sword")
    spec_changes = dict(changes)

    for seed in range(20):
        mesh, checks = descriptor.inspect(_sword(seed=seed, **spec_changes))

        assert all(check["ok"] for check in checks.values())
        assert mesh.tri_count() <= descriptor.triangle_budget
        (x0, y0, z0), (x1, y1, z1) = mesh.component_bounds("grip")
        assert z1 - z0 == pytest.approx(0.14)
        if changes.get("guard_form") == "none":
            assert "guard" not in mesh.components
        if changes.get("pommel_form") == "none":
            assert "pommel" not in mesh.components
        assert [m.name for m in mesh.materials] == [
            "blade_steel", "guard_iron", "pommel_gold", "grip",
        ]
