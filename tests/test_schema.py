"""Seam 1: validação de spec JSON (contrato por tipo, PLANO_MVP §3)."""

import json
from importlib.resources import files

import pytest

from blender_worker.schema import (
    SpecError,
    json_schema_for,
    load_spec,
    spec_to_dict,
    versioned_json_schema,
)


def test_house_default_spec_loads() -> None:
    with open("specs/house_default.json") as f:
        data = json.load(f)
    spec = load_spec(data)
    assert spec.type == "house"


def test_house_depth_must_remain_proportional_to_its_floors() -> None:
    data = json.loads(open("specs/house_default.json").read())
    data.update({"depth": 3.0, "floors": 3})

    with pytest.raises(SpecError, match="depth.*pavimentos"):
        load_spec(data)


def test_house_window_count_must_fit_its_facades() -> None:
    data = json.loads(open("specs/house_default.json").read())
    data.update({"width": 3.0, "depth": 3.0, "window_count": 10})

    with pytest.raises(SpecError, match="window_count.*fachadas"):
        load_spec(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seed", -1),
        ("seed", 4_294_967_296),
        ("width", 2.99),
        ("width", 12.01),
        ("depth", 2.99),
        ("depth", 10.01),
        ("floors", 0),
        ("floors", 4),
        ("window_count", -1),
        ("window_count", 17),
    ],
)
def test_house_rejects_values_outside_v1_ranges(field: str, value: int | float) -> None:
    data = json.loads(open("specs/house_default.json").read())
    data[field] = value

    with pytest.raises(SpecError, match=f"{field}=.*fora do intervalo"):
        load_spec(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seed", 0),
        ("seed", 4_294_967_295),
        ("width", 3.0),
        ("width", 12.0),
        ("depth", 3.0),
        ("depth", 10.0),
        ("floors", 1),
        ("floors", 3),
        ("window_count", 0),
        ("window_count", 16),
    ],
)
def test_house_accepts_v1_range_boundaries(field: str, value: int | float) -> None:
    data = json.loads(open("specs/house_default.json").read())
    data[field] = value

    assert load_spec(data).type == "house"


def test_house_public_schema_exposes_the_depth_floor_relation() -> None:
    assert json_schema_for("house")["allOf"] == [
        {
            "if": {"properties": {"floors": {"const": 3}}, "required": ["floors"]},
            "then": {"properties": {"depth": {"minimum": 4.5}}},
        }
    ]


@pytest.mark.parametrize(
    ("old_field", "old_value"),
    [
        ("roof_type", "gable"),
        ("wall_material", "plaster"),
        ("windows", 4),
        ("chimney", True),
    ],
)
def test_house_rejects_fields_from_the_pre_v1_contract(
    old_field: str, old_value: object
) -> None:
    data = json.loads(open("specs/house_default.json").read())
    data[old_field] = old_value

    with pytest.raises(SpecError, match="campos desconhecidos"):
        load_spec(data)


@pytest.mark.parametrize(
    ("field", "old_value"),
    [("roof_form", "shed"), ("wall_finish", "brick")],
)
def test_house_rejects_values_outside_the_v1_vocabulary(
    field: str, old_value: str
) -> None:
    data = json.loads(open("specs/house_default.json").read())
    data[field] = old_value

    with pytest.raises(SpecError, match=f"{field}.*tipo JSON inválido"):
        load_spec(data)


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


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_contract_rejects_non_finite_numbers(value: float) -> None:
    data = json.loads(open("specs/house_default.json").read())
    data["width"] = value

    with pytest.raises(SpecError):
        load_spec(data)


def test_spec_version_is_required_and_supported() -> None:
    data = json.loads(open("specs/house_default.json").read()); del data["spec_version"]
    with pytest.raises(SpecError): load_spec(data)
    data["spec_version"] = 2
    with pytest.raises(SpecError): load_spec(data)


def test_distributed_v1_schema_equals_runtime_contract() -> None:
    schema_path = files("blender_worker").joinpath("schemas/spec-v1.schema.json")
    distributed = json.loads(schema_path.read_text(encoding="utf-8"))

    assert distributed == versioned_json_schema(1)


def test_generated_schema_carries_types_enums_defaults_and_limits() -> None:
    for name in ("house", "sword", "tree", "chest"):
        schema = json_schema_for(name)
        example = json.loads(open(f"specs/{name}_default.json").read())
        assert set(example) == set(schema["properties"])
        assert schema["additionalProperties"] is False

    house = json_schema_for("house")
    assert house["properties"]["spec_version"] == {"const": 1, "type": "integer"}
    assert house["properties"]["type"] == {"const": "house", "type": "string"}
    assert house["properties"]["roof_form"] == {
        "default": "gable",
        "enum": ["gable", "hip"],
        "type": "string",
    }
    assert house["properties"]["width"] == {
        "default": 6.0,
        "maximum": 12,
        "minimum": 3,
        "type": "number",
    }
    assert house["required"] == ["spec_version", "type", "seed"]


def test_defaults_are_explicit_in_resolved_spec() -> None:
    resolved = load_spec({"spec_version": 1, "type": "house", "seed": 42})

    assert spec_to_dict(resolved) == {
        "spec_version": 1,
        "type": "house",
        "seed": 42,
        "width": 6.0,
        "depth": 5.0,
        "floors": 1,
        "roof_form": "gable",
        "wall_finish": "plaster",
        "window_count": 4,
        "has_chimney": True,
        "style": "medieval_lowpoly",
    }
