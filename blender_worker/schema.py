"""Contrato de spec (JSON por tipo) — PLANO_MVP §3.

Regras: campos desconhecidos são rejeitados; aleatoriedade somente via
`seed` determinística (reprodutibilidade).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Literal, Union


class SpecError(ValueError):
    """Spec inválida: tipo desconhecido, campo desconhecido ou valor fora do domínio."""


HouseRoof = Literal["gable", "hip", "flat"]
WallMaterial = Literal["plaster", "brick", "wood", "stone"]
GuardType = Literal["straight", "curved", "none"]
PommelType = Literal["round", "flat", "skull", "none"]
CanopyType = Literal["cluster", "cone", "sphere"]
LeafColor = Literal["green", "autumn", "pine"]
LidType = Literal["arched", "flat"]


def _check_range(name: str, value: float, lo: float, hi: float) -> None:
    if not (lo <= value <= hi):
        raise SpecError(f"{name}={value} fora do intervalo [{lo}, {hi}]")


def _check_choice(name: str, value: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        raise SpecError(f"{name}={value!r} inválido; esperado um de {choices}")


class BaseSpec:
    type: str
    seed: int
    style: str


def _reject_unknown(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    assert is_dataclass(cls)
    known = {f.name for f in fields(cls)}
    unknown = set(data.keys()) - known
    if unknown:
        raise SpecError(f"campos desconhecidos para {cls.__name__}: {sorted(unknown)}")
    return {k: v for k, v in data.items() if k in known}


@dataclass(frozen=True)
class HouseSpec(BaseSpec):
    type: Literal["house"]
    seed: int
    width: float = 6.0
    depth: float = 5.0
    floors: int = 1
    roof_type: HouseRoof = "gable"
    chimney: bool = True
    windows: int = 4
    wall_material: WallMaterial = "plaster"
    style: str = "medieval_lowpoly"

    def __post_init__(self) -> None:
        _check_range("width", self.width, 0.5, 50.0)
        _check_range("depth", self.depth, 0.5, 50.0)
        _check_range("floors", float(self.floors), 1, 5)
        _check_range("windows", float(self.windows), 0, 32)
        _check_choice("roof_type", self.roof_type, ("gable", "hip", "flat"))
        _check_choice("wall_material", self.wall_material, ("plaster", "brick", "wood", "stone"))


@dataclass(frozen=True)
class SwordSpec(BaseSpec):
    type: Literal["sword"]
    seed: int
    blade_length: float = 0.9
    blade_width: float = 0.08
    guard_type: GuardType = "straight"
    grip_length: float = 0.15
    pommel: PommelType = "round"
    style: str = "medieval_lowpoly"

    def __post_init__(self) -> None:
        _check_range("blade_length", self.blade_length, 0.2, 2.5)
        _check_range("blade_width", self.blade_width, 0.02, 0.3)
        _check_range("grip_length", self.grip_length, 0.05, 0.5)
        _check_choice("guard_type", self.guard_type, ("straight", "curved", "none"))
        _check_choice("pommel", self.pommel, ("round", "flat", "skull", "none"))


@dataclass(frozen=True)
class TreeSpec(BaseSpec):
    type: Literal["tree"]
    seed: int
    trunk_height: float = 2.5
    trunk_radius: float = 0.25
    canopy_type: CanopyType = "cluster"
    leaf_color: LeafColor = "green"
    lean: float = 0.05
    style: str = "medieval_lowpoly"

    def __post_init__(self) -> None:
        _check_range("trunk_height", self.trunk_height, 0.5, 15.0)
        _check_range("trunk_radius", self.trunk_radius, 0.05, 1.5)
        _check_range("lean", self.lean, 0.0, 0.5)
        _check_choice("canopy_type", self.canopy_type, ("cluster", "cone", "sphere"))
        _check_choice("leaf_color", self.leaf_color, ("green", "autumn", "pine"))


@dataclass(frozen=True)
class ChestSpec(BaseSpec):
    type: Literal["chest"]
    seed: int
    width: float = 1.0
    height: float = 0.6
    depth: float = 0.6
    lid_type: LidType = "arched"
    bands: int = 2
    lock: bool = True
    style: str = "medieval_lowpoly"

    def __post_init__(self) -> None:
        _check_range("width", self.width, 0.2, 3.0)
        _check_range("height", self.height, 0.2, 2.0)
        _check_range("depth", self.depth, 0.2, 2.0)
        _check_range("bands", float(self.bands), 0, 6)
        _check_choice("lid_type", self.lid_type, ("arched", "flat"))


AnySpec = Union[HouseSpec, SwordSpec, TreeSpec, ChestSpec]

_SPEC_CLASSES: dict[str, type] = {
    "house": HouseSpec,
    "sword": SwordSpec,
    "tree": TreeSpec,
    "chest": ChestSpec,
}


def load_spec(data: dict[str, Any]) -> AnySpec:
    """Valida um dict e retorna a spec tipada. Rejeita tipo/campos desconhecidos."""
    if not isinstance(data, dict):
        raise SpecError("spec deve ser um objeto JSON")
    spec_type = data.get("type")
    if spec_type not in _SPEC_CLASSES:
        raise SpecError(f"type={spec_type!r} desconhecido; esperado um de {sorted(_SPEC_CLASSES)}")
    if "seed" not in data:
        raise SpecError("campo obrigatório ausente: seed")
    seed = data["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise SpecError(f"seed={seed!r} inválida; esperado int >= 0")
    cls = _SPEC_CLASSES[spec_type]
    kwargs = _reject_unknown(cls, data)
    try:
        return cls(**kwargs)  # type: ignore[arg-type]
    except TypeError as e:
        raise SpecError(str(e)) from e


def load_spec_file(path: str) -> AnySpec:
    with open(path, encoding="utf-8") as f:
        return load_spec(json.load(f))


def spec_to_dict(spec: AnySpec) -> dict[str, Any]:
    assert is_dataclass(spec)
    return {f.name: getattr(spec, f.name) for f in fields(spec)}  # type: ignore[arg-type]
