"""Single contractual registry for every Marco 1 Asset Type."""
from __future__ import annotations
from dataclasses import dataclass
from .schema import ChestSpec, HouseSpec, SwordSpec, TreeSpec, json_schema_for

@dataclass(frozen=True)
class AssetTypeDescriptor:
    spec_class: type
    generator: type
    compatible_styles: frozenset[str]
    validators: tuple[str, ...]
    triangle_budget: int
    acceptance_matrix: str
    numeric_bounds: dict[str, tuple[float, float]]

    @property
    def json_schema(self) -> dict:
        asset_type = {HouseSpec: "house", SwordSpec: "sword", TreeSpec: "tree", ChestSpec: "chest"}[self.spec_class]
        return json_schema_for(asset_type)

def descriptors() -> dict[str, AssetTypeDescriptor]:
    from .generators.buildings.house import HouseGenerator
    from .generators.nature.tree import TreeGenerator
    from .generators.props.chest import ChestGenerator
    from .generators.weapons.sword import SwordGenerator
    common = ("mesh_valid", "triangle_budget", "materials", "anchor"); style = frozenset({"medieval_lowpoly"})
    return {
        "house": AssetTypeDescriptor(HouseSpec, HouseGenerator, style, common, 8000, "house",
            {"seed": (0, 4_294_967_295), "width": (3, 12), "depth": (3, 10), "floors": (1, 3), "window_count": (0, 16)}),
        "sword": AssetTypeDescriptor(SwordSpec, SwordGenerator, style, common, 2000, "sword",
            {"seed": (0, 4_294_967_295), "blade_length": (.6, 1.1), "blade_width": (.04, .10), "grip_length": (.10, .18)}),
        "tree": AssetTypeDescriptor(TreeSpec, TreeGenerator, style, common, 5000, "tree",
            {"seed": (0, 4_294_967_295), "trunk_height": (1.5, 8), "trunk_radius": (.12, .60), "lean_degrees": (0, 20)}),
        "chest": AssetTypeDescriptor(ChestSpec, ChestGenerator, style, common, 2000, "chest",
            {"seed": (0, 4_294_967_295), "width": (.6, 1.8), "height": (.4, 1.1), "depth": (.4, 1), "band_count": (0, 4)}),
    }

def get_descriptor(asset_type: str) -> AssetTypeDescriptor:
    try: return descriptors()[asset_type]
    except KeyError: raise KeyError(f"Tipo de Asset {asset_type!r} não registrado") from None
