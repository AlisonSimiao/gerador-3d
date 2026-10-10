"""Single contractual registry for every Marco 1 Asset Type."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .geometry.mesh import MeshData
from .schema import BaseSpec, ChestSpec, HouseSpec, SpecError, SwordSpec, TreeSpec, json_schema_for

ValidationResult = dict[str, Any]
Validator = Callable[[MeshData, str], ValidationResult]


@dataclass(frozen=True)
class AssetTypeDescriptor:
    asset_type: str
    spec_class: type[Any]
    generator: type
    compatible_styles: frozenset[str]
    validators: tuple[tuple[str, Validator], ...]
    triangle_budget: int
    acceptance_matrix: Path
    numeric_bounds: Mapping[str, tuple[float, float]]

    @property
    def json_schema(self) -> dict[str, Any]:
        return json_schema_for(self.asset_type)

    def require_compatible_style(self, style: str) -> None:
        """Enforce style policy at the Asset Type descriptor boundary."""
        if style not in self.compatible_styles:
            expected = ", ".join(sorted(self.compatible_styles))
            raise SpecError(
                f"style={style!r} incompatível com {self.asset_type}; esperado um de [{expected}]"
            )

    def validate(self, mesh: MeshData) -> dict[str, ValidationResult]:
        """Run exactly the validators contracted for this Asset Type."""
        return {name: validator(mesh, self.asset_type) for name, validator in self.validators}

    def inspect(self, spec: BaseSpec) -> tuple[MeshData, dict[str, ValidationResult]]:
        """Build and validate this Type's IR through its complete contract."""
        if not isinstance(spec, self.spec_class):
            raise SpecError(
                f"Spec {type(spec).__name__} incompatível com descritor {self.asset_type}"
            )
        self.require_compatible_style(spec.style)
        from .style import get_style

        mesh = self.generator(spec, get_style(spec.style)).build()
        return mesh, self.validate(mesh)


_REGISTRY: Mapping[str, AssetTypeDescriptor] | None = None


def descriptors() -> Mapping[str, AssetTypeDescriptor]:
    """Return the immutable, process-wide registry of Asset Type contracts."""
    global _REGISTRY
    if _REGISTRY is None:
        from .generators.buildings.house import HouseGenerator
        from .generators.nature.tree import TreeGenerator
        from .generators.props.chest import ChestGenerator
        from .generators.weapons.sword import SwordGenerator
        from .validators import check_materials, check_mesh_valid, check_transform, check_tri_budget

        root = Path(__file__).resolve().parent.parent
        validators = (
            ("mesh_valid", check_mesh_valid),
            ("tri_budget", check_tri_budget),
            ("materials", check_materials),
            ("anchor", check_transform),
        )
        style = frozenset({"medieval_lowpoly"})
        registry = {
            "house": AssetTypeDescriptor(
                "house", HouseSpec, HouseGenerator, style, validators, 8000,
                root / "acceptance" / "house",
                {"seed": (0, 4_294_967_295), "width": (3, 12), "depth": (3, 10),
                 "floors": (1, 3), "window_count": (0, 16)},
            ),
            "sword": AssetTypeDescriptor(
                "sword", SwordSpec, SwordGenerator, style, validators, 2000,
                root / "acceptance" / "sword",
                {"seed": (0, 4_294_967_295), "blade_length": (.6, 1.1),
                 "blade_width": (.04, .10), "grip_length": (.10, .18)},
            ),
            "tree": AssetTypeDescriptor(
                "tree", TreeSpec, TreeGenerator, style, validators, 5000,
                root / "acceptance" / "tree",
                {"seed": (0, 4_294_967_295), "trunk_height": (1.5, 8),
                 "trunk_radius": (.12, .60), "lean_degrees": (0, 20)},
            ),
            "chest": AssetTypeDescriptor(
                "chest", ChestSpec, ChestGenerator, style, validators, 2000,
                root / "acceptance" / "chest",
                {"seed": (0, 4_294_967_295), "width": (.6, 1.8), "height": (.4, 1.1),
                 "depth": (.4, 1), "band_count": (0, 4)},
            ),
        }
        _REGISTRY = MappingProxyType(registry)
    return _REGISTRY


def get_descriptor(asset_type: str) -> AssetTypeDescriptor:
    try:
        return descriptors()[asset_type]
    except KeyError:
        raise KeyError(f"Tipo de Asset {asset_type!r} não registrado") from None
