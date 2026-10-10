"""Seam 1: validação de spec JSON (contrato por tipo, PLANO_MVP §3)."""

import json

import pytest

from blender_worker.schema import SpecError, json_schema_for, load_spec


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
        load_spec({"spec_version": 1, "type": "dragon", "seed": 1})


def test_unknown_field_rejected() -> None:
    # Regra do plano: campos desconhecidos são rejeitados.
    with pytest.raises(SpecError):
        load_spec({"spec_version": 1, "type": "house", "seed": 1, "width": 6.0, "depth": 5.0,
                   "floors": 1, "roof_form": "gable", "has_chimney": True,
                   "window_count": 4, "wall_finish": "plaster",
                   "style": "medieval_lowpoly", "torre_extra": 1})


def test_out_of_range_rejected() -> None:
    with pytest.raises(SpecError):
        load_spec({"spec_version": 1, "type": "sword", "seed": 1, "blade_length": 99.0,
                   "blade_width": 0.08, "guard_form": "straight",
                   "grip_length": 0.15, "pommel_form": "round",
                   "style": "medieval_lowpoly"})


def test_incompatible_style_is_rejected_by_the_type_descriptor() -> None:
    data = json.loads(open("specs/house_default.json").read())
    data["style"] = "photorealistic"

    with pytest.raises(SpecError, match="incompatível com house"):
        load_spec(data)


def test_seed_required_and_deterministic() -> None:
    with pytest.raises(SpecError):
        load_spec({"spec_version": 1, "type": "tree", "trunk_height": 2.5, "trunk_radius": 0.25,
                   "canopy_form": "clustered", "foliage_palette": "green",
                   "lean_degrees": 5.0, "style": "medieval_lowpoly"})


@pytest.mark.parametrize("field,value", [("seed", 1.0), ("width", 6), ("has_chimney", 1)])
def test_contract_does_not_coerce_json_types(field: str, value: object) -> None:
    data = json.loads(open("specs/house_default.json").read())
    data[field] = value
    with pytest.raises(SpecError): load_spec(data)


def test_spec_version_is_required_and_supported() -> None:
    data = json.loads(open("specs/house_default.json").read()); del data["spec_version"]
    with pytest.raises(SpecError): load_spec(data)
    data["spec_version"] = 2
    with pytest.raises(SpecError): load_spec(data)


def test_generated_schema_has_the_same_fields_as_model() -> None:
    for name in ("house", "sword", "tree", "chest"):
        schema = json_schema_for(name)
        example = json.loads(open(f"specs/{name}_default.json").read())
        assert set(example) == set(schema["properties"])
        assert schema["additionalProperties"] is False
