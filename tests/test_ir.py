"""Fast suite seam: generators expose inspectable IR without publishing artifacts."""
import pytest

from blender_worker.export import inspect
from blender_worker.geometry.mesh import MeshData
from blender_worker.registry import descriptors
from blender_worker.schema import SpecError, load_spec, load_spec_file


def _component_bounds(
    mesh: MeshData, component: str
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    start, end = mesh.components[component]
    vertex_indexes = {index for face in mesh.faces[start:end] for index in face}
    vertices = [mesh.vertices[index] for index in vertex_indexes]
    return (
        (
            min(vertex[0] for vertex in vertices),
            min(vertex[1] for vertex in vertices),
            min(vertex[2] for vertex in vertices),
        ),
        (
            max(vertex[0] for vertex in vertices),
            max(vertex[1] for vertex in vertices),
            max(vertex[2] for vertex in vertices),
        ),
    )


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


def test_house_chimney_presence_is_explicit_in_the_ir() -> None:
    descriptor = descriptors()["house"]

    with_chimney, _ = descriptor.inspect(
        load_spec({"spec_version": 1, "type": "house", "seed": 42})
    )
    without_chimney, _ = descriptor.inspect(
        load_spec(
            {"spec_version": 1, "type": "house", "seed": 42, "has_chimney": False}
        )
    )

    assert "chimney" in with_chimney.components
    assert "chimney" not in without_chimney.components


def test_every_house_v1_parameter_has_a_recognizable_ir_effect() -> None:
    descriptor = descriptors()["house"]

    def house(**changes):
        return descriptor.inspect(
            load_spec({"spec_version": 1, "type": "house", "seed": 42, **changes})
        )[0]

    wider = house(width=7.0)
    deeper = house(depth=6.0)
    taller = house(floors=2)
    gable = house(roof_form="gable")
    hip = house(roof_form="hip")
    more_windows = house(window_count=8)
    plaster = house(wall_finish="plaster")
    stone = house(wall_finish="stone")

    assert _component_bounds(wider, "body") == ((-3.5, -2.5, 0), (3.5, 2.5, 2.6))
    assert _component_bounds(deeper, "body") == ((-3.0, -3.0, 0), (3.0, 3.0, 2.6))
    assert _component_bounds(taller, "body")[1][2] == 5.2
    assert gable.components["roof"][1] - gable.components["roof"][0] == 4
    assert hip.components["roof"][1] - hip.components["roof"][0] == 12
    assert more_windows.components["windows"][1] - more_windows.components["windows"][0] == 48
    assert plaster.materials[0].name == "wall_plaster"
    assert stone.materials[0].name == "wall_stone"
    assert "door" in plaster.components
