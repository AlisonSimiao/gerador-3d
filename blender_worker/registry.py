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
        "house": AssetTypeDescriptor(HouseSpec, HouseGenerator, style, common, 8000, "house"),
        "sword": AssetTypeDescriptor(SwordSpec, SwordGenerator, style, common, 2000, "sword"),
        "tree": AssetTypeDescriptor(TreeSpec, TreeGenerator, style, common, 5000, "tree"),
        "chest": AssetTypeDescriptor(ChestSpec, ChestGenerator, style, common, 2000, "chest"),
    }

def get_descriptor(asset_type: str) -> AssetTypeDescriptor:
    try: return descriptors()[asset_type]
    except KeyError: raise KeyError(f"Tipo de Asset {asset_type!r} não registrado") from None
