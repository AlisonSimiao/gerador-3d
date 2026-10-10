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
        _range("seed", self.seed, 0, 4_294_967_295)
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
        _range("width", self.width, 3, 12); _range("depth", self.depth, 3, 10)
        _range("floors", self.floors, 1, 3); _range("window_count", self.window_count, 0, 16)
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
        self._common(); _range("blade_length", self.blade_length, 0.6, 1.1)
        _range("blade_width", self.blade_width, 0.04, 0.10); _range("grip_length", self.grip_length, 0.10, 0.18)


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
        self._common(); _range("trunk_height", self.trunk_height, 1.5, 8)
        _range("trunk_radius", self.trunk_radius, 0.12, 0.60); _range("lean_degrees", self.lean_degrees, 0, 20)


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
        self._common(); _range("width", self.width, 0.6, 1.8); _range("height", self.height, 0.4, 1.1)
        _range("depth", self.depth, 0.4, 1.0); _range("band_count", self.band_count, 0, 4)


AnySpec = Union[HouseSpec, SwordSpec, TreeSpec, ChestSpec]
SPEC_CLASSES: dict[str, type[Any]] = {"house": HouseSpec, "sword": SwordSpec, "tree": TreeSpec, "chest": ChestSpec}


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
    cls = SPEC_CLASSES.get(spec_type) if type(spec_type) is str else None
    if cls is None: raise SpecError(f"type={spec_type!r} desconhecido; esperado um de {sorted(SPEC_CLASSES)}")
    known = {field.name for field in fields(cls)}
    unknown = set(data) - known
    if unknown: raise SpecError(f"campos desconhecidos para {cls.__name__}: {sorted(unknown)}")
    missing = [field.name for field in fields(cls) if field.default is MISSING and field.name not in data]
    if missing: raise SpecError(f"campo obrigatório ausente: {missing[0]}")
    hints = get_type_hints(cls)
    for name, value in data.items():
        if not _matches(value, hints[name]): raise SpecError(f"{name} possui tipo JSON inválido")
        if type(value) is float and not math.isfinite(value): raise SpecError(f"{name} deve ser finito")
    return cls(**data)  # type: ignore[return-value]


def load_spec_file(path: str) -> AnySpec:
    with open(path, encoding="utf-8") as file: return load_spec(json.load(file))


def spec_to_dict(spec: AnySpec) -> dict[str, Any]:
    assert is_dataclass(spec)
    return {field.name: getattr(spec, field.name) for field in fields(spec)}


def json_schema_for(spec_type: str) -> dict[str, Any]:
    cls = SPEC_CLASSES[spec_type]; hints = get_type_hints(cls); properties: dict[str, Any] = {}; required = []
    for field in fields(cls):
        annotation = hints[field.name]; values = get_args(annotation)
        prop = ({"enum": list(values), "type": _json_type(type(values[0]))} if get_origin(annotation) is Literal
                else {"type": _json_type(annotation)})
        properties[field.name] = prop
        if field.default is MISSING: required.append(field.name)
        else: prop["default"] = field.default
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": cls.__name__, "type": "object",
            "additionalProperties": False, "properties": properties, "required": required}


def _json_type(annotation: Any) -> str:
    return {str: "string", int: "integer", float: "number", bool: "boolean"}[annotation]
