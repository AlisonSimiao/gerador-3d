"""Fast suite seam: generators expose inspectable IR without publishing artifacts."""
from blender_worker.export import inspect
from blender_worker.registry import descriptors
from blender_worker.schema import load_spec_file

def test_registry_is_the_single_type_policy_source() -> None:
    registry = descriptors()
    assert set(registry) == {"house", "sword", "tree", "chest"}
    assert {name: item.triangle_budget for name, item in registry.items()} == {
        "house": 8000, "sword": 2000, "tree": 5000, "chest": 2000,
    }

def test_house_ir_names_required_components_and_anchor() -> None:
    mesh, checks = inspect(load_spec_file("specs/house_default.json"))
    assert {"body", "roof", "door", "windows"} <= set(mesh.components)
    assert mesh.anchor == (0.0, 0.0, 0.0)
    assert all(check["ok"] for check in checks.values())
