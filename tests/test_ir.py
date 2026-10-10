"""Fast suite seam: generators expose inspectable IR without publishing artifacts."""
import pytest

from blender_worker.export import inspect
from blender_worker.registry import descriptors
from blender_worker.schema import SpecError, load_spec_file

def test_registry_is_the_single_type_policy_source() -> None:
    registry = descriptors()
    assert set(registry) == {"house", "sword", "tree", "chest"}
    assert {name: item.triangle_budget for name, item in registry.items()} == {
        "house": 8000, "sword": 2000, "tree": 5000, "chest": 2000,
    }

    for descriptor in registry.values():
        assert descriptor.json_schema["title"] == descriptor.spec_class.__name__
        assert descriptor.generator is not None
        assert descriptor.validators
        assert descriptor.acceptance_matrix.is_dir()


def test_descriptor_rejects_an_incompatible_style_at_its_boundary() -> None:
    descriptor = descriptors()["house"]

    with pytest.raises(SpecError, match="incompatível.*house"):
        descriptor.require_compatible_style("photorealistic")


@pytest.mark.parametrize("asset_type", ["house", "sword", "tree", "chest"])
def test_each_descriptor_builds_and_validates_its_default_spec(asset_type: str) -> None:
    descriptor = descriptors()[asset_type]
    spec = load_spec_file(f"specs/{asset_type}_default.json")

    mesh, checks = descriptor.inspect(spec)

    assert mesh.tri_count() > 0
    assert set(checks) == {name for name, _validator in descriptor.validators}
    assert all(check["ok"] for check in checks.values())
    assert f"/{descriptor.triangle_budget} tris" in checks["tri_budget"]["detail"]

def test_house_ir_names_required_components_and_anchor() -> None:
    mesh, checks = inspect(load_spec_file("specs/house_default.json"))
    assert {"body", "roof", "door", "windows"} <= set(mesh.components)
    assert mesh.anchor == (0.0, 0.0, 0.0)
    assert all(check["ok"] for check in checks.values())
