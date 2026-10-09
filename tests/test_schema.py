"""Seam 1: validação de spec JSON (contrato por tipo, PLANO_MVP §3)."""

import json

import pytest

from blender_worker.schema import SpecError, load_spec


def test_house_default_spec_loads() -> None:
    with open("specs/house_default.json") as f:
        data = json.load(f)
    spec = load_spec(data)
    assert spec.type == "house"


def test_all_example_specs_load() -> None:
    for name in ("house_default", "sword_default", "tree_default", "chest_default"):
        with open(f"specs/{name}.json") as f:
            spec = load_spec(json.load(f))
        assert spec.type in ("house", "sword", "tree", "chest")


def test_unknown_type_rejected() -> None:
    with pytest.raises(SpecError):
        load_spec({"type": "dragon", "seed": 1})


def test_unknown_field_rejected() -> None:
    # Regra do plano: campos desconhecidos são rejeitados.
    with pytest.raises(SpecError):
        load_spec({"type": "house", "seed": 1, "width": 6.0, "depth": 5.0,
                   "floors": 1, "roof_type": "gable", "chimney": True,
                   "windows": 4, "wall_material": "plaster",
                   "style": "medieval_lowpoly", "torre_extra": 1})


def test_out_of_range_rejected() -> None:
    with pytest.raises(SpecError):
        load_spec({"type": "sword", "seed": 1, "blade_length": 99.0,
                   "blade_width": 0.08, "guard_type": "straight",
                   "grip_length": 0.15, "pommel": "round",
                   "style": "medieval_lowpoly"})


def test_seed_required_and_deterministic() -> None:
    with pytest.raises(SpecError):
        load_spec({"type": "tree", "trunk_height": 2.5, "trunk_radius": 0.25,
                   "canopy_type": "cluster", "leaf_color": "green",
                   "lean": 0.05, "style": "medieval_lowpoly"})
