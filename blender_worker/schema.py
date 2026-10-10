"""Versioned, strict input contracts for Marco 1 asset specs."""
from __future__ import annotations

import json
import math
from dataclasses import MISSING, dataclass, fields, is_dataclass
from typing import Any, ClassVar, Literal, Union, get_args, get_origin, get_type_hints


class SpecError(ValueError):
    """The input is not a supported, valid Spec."""


def _range(name: str, value: int | float, lo: float, hi: float) -> None:
    if not math.isfinite(float(value)) or not lo <= value <= hi:
        raise SpecError(f"{name}={value!r} fora do intervalo [{lo}, {hi}]")


class BaseSpec:
    SPEC_VERSION: ClassVar[int] = 1
    spec_version: int
    type: str
    seed: int
    style: str

    def _common(self) -> None:
        if self.spec_version != self.SPEC_VERSION:
            raise SpecError(f"spec_version={self.spec_version!r} não suportada; esperado 1")
        if self.style != "medieval_lowpoly":
            raise SpecError("style incompatível; esperado 'medieval_lowpoly'")


@dataclass(frozen=True)
class HouseSpec(BaseSpec):
    spec_version: Literal[1]
    type: Literal["house"]
    seed: int
    width: float = 6.0
    depth: float = 5.0
    floors: int = 1
    roof_form: Literal["gable", "hip"] = "gable"
    wall_finish: Literal["plaster", "timber", "stone"] = "plaster"
    window_count: int = 4
    has_chimney: bool = True
    style: Literal["medieval_lowpoly"] = "medieval_lowpoly"

    def __post_init__(self) -> None:
        self._common()
        if self.window_count > int((self.width + self.depth) * 1.6):
            raise SpecError("window_count não cabe nas fachadas declaradas")


@dataclass(frozen=True)
class SwordSpec(BaseSpec):
    spec_version: Literal[1]
    type: Literal["sword"]
    seed: int
    blade_length: float = 0.9
    blade_width: float = 0.07
    guard_form: Literal["straight", "curved", "none"] = "straight"
    grip_length: float = 0.14
    pommel_form: Literal["round", "faceted", "none"] = "round"
    style: Literal["medieval_lowpoly"] = "medieval_lowpoly"

    def __post_init__(self) -> None:
        self._common()


@dataclass(frozen=True)
class TreeSpec(BaseSpec):
    spec_version: Literal[1]
    type: Literal["tree"]
    seed: int
    trunk_height: float = 3.0
    trunk_radius: float = 0.25
    canopy_form: Literal["clustered", "round", "conical"] = "clustered"
    foliage_palette: Literal["green", "autumn", "dark_green"] = "green"
    lean_degrees: float = 5.0
    style: Literal["medieval_lowpoly"] = "medieval_lowpoly"

    def __post_init__(self) -> None:
        self._common()


@dataclass(frozen=True)
class ChestSpec(BaseSpec):
    spec_version: Literal[1]
    type: Literal["chest"]
    seed: int
    width: float = 1.0
    height: float = 0.6
    depth: float = 0.6
    lid_form: Literal["arched", "flat"] = "arched"
    band_count: int = 2
    has_lock: bool = True
    style: Literal["medieval_lowpoly"] = "medieval_lowpoly"

    def __post_init__(self) -> None:
        self._common()


AnySpec = Union[HouseSpec, SwordSpec, TreeSpec, ChestSpec]


def _matches(value: Any, annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is Literal:
        return value in get_args(annotation) and type(value) in {type(v) for v in get_args(annotation)}
    if annotation is float: return type(value) is float
    if annotation is int: return type(value) is int
    if annotation is bool: return type(value) is bool
    if annotation is str: return type(value) is str
    return isinstance(value, annotation)


def load_spec(data: dict[str, Any]) -> AnySpec:
    if not isinstance(data, dict): raise SpecError("spec deve ser um objeto JSON")
    spec_type = data.get("type")
    from .registry import descriptors
    registry = descriptors()
    descriptor = registry.get(spec_type) if type(spec_type) is str else None
    if descriptor is None: raise SpecError(f"type={spec_type!r} desconhecido; esperado um de {sorted(registry)}")
    cls = descriptor.spec_class
    known = {field.name for field in fields(cls)}
    unknown = set(data) - known
    if unknown: raise SpecError(f"campos desconhecidos para {cls.__name__}: {sorted(unknown)}")
    missing = [field.name for field in fields(cls) if field.default is MISSING and field.name not in data]
    if missing: raise SpecError(f"campo obrigatório ausente: {missing[0]}")
    hints = get_type_hints(cls)
    for name, value in data.items():
        if not _matches(value, hints[name]): raise SpecError(f"{name} possui tipo JSON inválido")
        if type(value) is float and not math.isfinite(value): raise SpecError(f"{name} deve ser finito")
        if name in descriptor.numeric_bounds:
            _range(name, value, *descriptor.numeric_bounds[name])
    return cls(**data)  # type: ignore[return-value]


def load_spec_file(path: str) -> AnySpec:
    with open(path, encoding="utf-8") as file: return load_spec(json.load(file))


def spec_to_dict(spec: AnySpec) -> dict[str, Any]:
    assert is_dataclass(spec)
    return {field.name: getattr(spec, field.name) for field in fields(spec)}


def json_schema_for(spec_type: str) -> dict[str, Any]:
    from .registry import get_descriptor

    descriptor = get_descriptor(spec_type)
    cls = descriptor.spec_class
    hints = get_type_hints(cls)
    properties: dict[str, Any] = {}
    required = []
    for field in fields(cls):
        annotation = hints[field.name]
        values = get_args(annotation)
        prop: dict[str, Any]
        if get_origin(annotation) is Literal:
            prop = {"type": _json_type(type(values[0]))}
            if len(values) == 1:
                prop["const"] = values[0]
            else:
                prop["enum"] = list(values)
        else:
            prop = {"type": _json_type(annotation)}
        properties[field.name] = prop
        if field.name in descriptor.numeric_bounds:
            prop["minimum"], prop["maximum"] = descriptor.numeric_bounds[field.name]
        if field.default is MISSING:
            required.append(field.name)
        else:
            prop["default"] = field.default
    return {
        "title": cls.__name__,
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def versioned_json_schema(spec_version: int) -> dict[str, Any]:
    """Return the complete public input contract for one supported Spec version."""
    if type(spec_version) is not int or spec_version != BaseSpec.SPEC_VERSION:
        raise SpecError(f"spec_version={spec_version!r} não suportada; esperado 1")

    from .registry import descriptors

    registered = descriptors()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://gerador-3d.local/schemas/spec-v{spec_version}.schema.json",
        "title": f"Gerador 3D Spec v{spec_version}",
        "oneOf": [{"$ref": f"#/$defs/{name}"} for name in registered],
        "$defs": {name: json_schema_for(name) for name in registered},
    }


def _json_type(annotation: Any) -> str:
    return {str: "string", int: "integer", float: "number", bool: "boolean"}[annotation]
