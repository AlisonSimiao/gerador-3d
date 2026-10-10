"""Fast suite seam: generators expose inspectable IR without publishing artifacts."""
import builtins
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from blender_worker.export import inspect
from blender_worker.geometry import AnchorKind
from blender_worker.registry import descriptors
from blender_worker.schema import SpecError, load_spec, load_spec_file


EXPECTED_COMPONENTS = {
    "house": {"body", "roof", "chimney", "door", "windows"},
    "sword": {"pommel", "grip", "guard", "blade"},
    "tree": {"trunk", "canopy"},
    "chest": {"body", "lid", "bands", "lock"},
}
EXPECTED_ANCHORS = {
    "house": AnchorKind.SUPPORT_SURFACE,
    "sword": AnchorKind.GRIP_CENTER,
    "tree": AnchorKind.SUPPORT_SURFACE,
    "chest": AnchorKind.SUPPORT_SURFACE,
}

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


@pytest.mark.parametrize("asset_type", ["house", "sword", "tree", "chest"])
def test_ir_names_every_nonempty_component_and_assigns_every_face(asset_type: str) -> None:
    descriptor = descriptors()[asset_type]

    mesh, _checks = descriptor.inspect(load_spec_file(f"specs/{asset_type}_default.json"))

    assert set(mesh.components) == EXPECTED_COMPONENTS[asset_type]
    covered_faces: list[int] = []
    for start, end in mesh.components.values():
        assert end > start
        covered_faces.extend(range(start, end))
    assert sorted(covered_faces) == list(range(len(mesh.faces)))
    assert len(mesh.face_materials) == len(mesh.faces)
    assert all(0 <= material < len(mesh.materials) for material in mesh.face_materials)


@pytest.mark.parametrize("asset_type", ["house", "sword", "tree", "chest"])
def test_descriptor_validates_that_each_named_component_is_closed(asset_type: str) -> None:
    descriptor = descriptors()[asset_type]

    _mesh, checks = descriptor.inspect(load_spec_file(f"specs/{asset_type}_default.json"))

    assert checks["mesh_valid"]["ok"] is True
    assert checks["mesh_valid"]["components_closed"] == sorted(EXPECTED_COMPONENTS[asset_type])


@pytest.mark.parametrize("asset_type", ["house", "sword", "tree", "chest"])
def test_ir_exposes_and_validates_the_type_specific_anchor(asset_type: str) -> None:
    descriptor = descriptors()[asset_type]

    mesh, checks = descriptor.inspect(load_spec_file(f"specs/{asset_type}_default.json"))

    assert mesh.anchor == (0.0, 0.0, 0.0)
    assert mesh.anchor_kind is EXPECTED_ANCHORS[asset_type]
    assert checks["anchor"]["ok"] is True
    assert checks["anchor"]["kind"] == EXPECTED_ANCHORS[asset_type].value


@pytest.mark.parametrize(
    "asset_type,changes",
    [
        ("house", {"window_count": 0, "has_chimney": False}),
        ("sword", {"guard_form": "none", "pommel_form": "none"}),
        ("chest", {"band_count": 0, "has_lock": False}),
    ],
)
def test_optional_absent_volumes_do_not_create_empty_components(
    asset_type: str, changes: dict[str, Any]
) -> None:
    descriptor = descriptors()[asset_type]
    spec = replace(cast(Any, load_spec_file(f"specs/{asset_type}_default.json")), **changes)

    mesh, checks = descriptor.inspect(spec)

    assert all(end > start for start, end in mesh.components.values())
    assert all(check["ok"] for check in checks.values())


def test_inspection_neither_imports_bpy_nor_publishes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_import = builtins.__import__

    def reject_bpy(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "bpy":
            raise AssertionError("a inspeção da IR não pode importar bpy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_bpy)
    monkeypatch.chdir(tmp_path)
    descriptor = descriptors()["tree"]

    mesh, checks = descriptor.inspect(load_spec_file(str(Path(__file__).parents[1] / "specs/tree_default.json")))

    assert mesh.faces
    assert all(check["ok"] for check in checks.values())
    assert list(tmp_path.iterdir()) == []


def test_descriptor_validation_rejects_incomplete_material_assignments() -> None:
    descriptor = descriptors()["tree"]
    mesh, _checks = descriptor.inspect(load_spec_file("specs/tree_default.json"))
    mesh.face_materials.pop()

    checks = descriptor.validate(mesh)

    assert checks["materials"]["ok"] is False
    assert "cada face" in checks["materials"]["detail"]

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


def test_house_distributes_the_exact_window_total_deterministically() -> None:
    descriptor = descriptors()["house"]
    spec = load_spec(
        {"spec_version": 1, "type": "house", "seed": 42, "window_count": 10}
    )

    first, _ = descriptor.inspect(spec)
    second, _ = descriptor.inspect(spec)
    first_windows = first.component_volume_bounds("windows")
    second_windows = second.component_volume_bounds("windows")

    assert first_windows == second_windows
    assert len(first_windows) == 10
    centers = [
        tuple((lower[axis] + upper[axis]) / 2 for axis in range(3))
        for lower, upper in first_windows
    ]
    assert sum(center[1] == 2.5 for center in centers) == 3
    assert sum(center[1] == -2.5 for center in centers) == 3
    assert sum(center[0] == 3.0 for center in centers) == 2
    assert sum(center[0] == -3.0 for center in centers) == 2


def test_house_body_dimensions_exclude_the_roof_overhang() -> None:
    descriptor = descriptors()["house"]
    mesh, _ = descriptor.inspect(load_spec_file("specs/house_default.json"))

    assert mesh.component_bounds("body") == ((-3.0, -2.5, 0), (3.0, 2.5, 2.6))
    roof_lower, roof_upper = mesh.component_bounds("roof")
    assert roof_lower[0] < -3.0
    assert roof_lower[1] < -2.5
    assert roof_upper[0] > 3.0
    assert roof_upper[1] > 2.5


def test_house_door_is_one_visual_volume_for_every_supported_variant() -> None:
    descriptor = descriptors()["house"]
    variants: list[dict[str, Any]] = [
        {},
        {"roof_form": "hip", "wall_finish": "stone", "has_chimney": False},
        {"window_count": 0, "floors": 3, "depth": 4.5},
    ]

    for changes in variants:
        mesh, checks = descriptor.inspect(
            load_spec({"spec_version": 1, "type": "house", "seed": 42, **changes})
        )
        assert len(mesh.component_volume_bounds("door")) == 1
        assert all(check["ok"] for check in checks.values())


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

    assert wider.component_bounds("body") == ((-3.5, -2.5, 0), (3.5, 2.5, 2.6))
    assert deeper.component_bounds("body") == ((-3.0, -3.0, 0), (3.0, 3.0, 2.6))
    assert taller.component_bounds("body")[1][2] == 5.2
    assert gable.components["roof"][1] - gable.components["roof"][0] == 5
    assert hip.components["roof"][1] - hip.components["roof"][0] == 12
    assert more_windows.components["windows"][1] - more_windows.components["windows"][0] == 48
    assert plaster.materials[0].name == "wall_plaster"
    assert stone.materials[0].name == "wall_stone"
    assert "door" in plaster.components


def test_stone_facade_details_use_stone_instead_of_wood() -> None:
    descriptor = descriptors()["house"]
    stone, checks = descriptor.inspect(
        load_spec(
            {"spec_version": 1, "type": "house", "seed": 42, "wall_finish": "stone"}
        )
    )

    start, end = stone.components["facade_details"]
    detail_materials = {
        stone.materials[stone.face_materials[index]].name for index in range(start, end)
    }
    assert detail_materials == {"stone_detail"}
    assert all(check["ok"] for check in checks.values())


HOUSE_COVERAGE_MATRIX: list[dict[str, Any]] = [
    {"roof_form": "gable", "wall_finish": "plaster"},
    {"roof_form": "gable", "wall_finish": "timber"},
    {"roof_form": "gable", "wall_finish": "stone"},
    {"roof_form": "hip", "wall_finish": "plaster"},
    {"roof_form": "hip", "wall_finish": "timber"},
    {"roof_form": "hip", "wall_finish": "stone"},
]


@pytest.mark.parametrize("changes", HOUSE_COVERAGE_MATRIX)
def test_house_roof_form_by_wall_finish_matrix_is_green_within_budget(
    changes: dict[str, Any],
) -> None:
    """Matriz de cobertura 06: cada combinação roof_form × wall_finish gera verde."""
    descriptor = descriptors()["house"]
    mesh, checks = descriptor.inspect(
        load_spec(
            {
                "spec_version": 1,
                "type": "house",
                "seed": 42,
                "width": 6.0,
                "depth": 5.0,
                "floors": 2,
                "window_count": 8,
                "has_chimney": True,
                **changes,
            }
        )
    )

    assert all(check["ok"] for check in checks.values())
    assert mesh.tri_count() <= descriptor.triangle_budget

    roof_faces = mesh.components["roof"][1] - mesh.components["roof"][0]
    if changes["roof_form"] == "gable":
        assert roof_faces == 5
    else:
        assert roof_faces == 12

    assert mesh.materials[0].name == f"wall_{changes['wall_finish']}"
    assert mesh.materials[0].color == {
        "plaster": (0.87, 0.82, 0.72, 1.0),
        "timber": (0.72, 0.62, 0.45, 1.0),
        "stone": (0.55, 0.55, 0.58, 1.0),
    }[changes["wall_finish"]]
    if changes["wall_finish"] == "plaster":
        assert "facade_details" not in mesh.components
    elif changes["wall_finish"] == "timber":
        start, end = mesh.components["facade_details"]
        detail_materials = {
            mesh.materials[mesh.face_materials[index]].name
            for index in range(start, end)
        }
        assert detail_materials == {"wood"}
        assert mesh.materials[mesh.face_materials[start]].color == (
            0.45, 0.30, 0.17, 1.0,
        )
        beam_widths = {
            round(upper[0] - lower[0], 6)
            for lower, upper in mesh.component_volume_bounds("facade_details")
        }
        assert 0.10 in beam_widths
    else:
        start, end = mesh.components["facade_details"]
        detail_materials = {
            mesh.materials[mesh.face_materials[index]].name
            for index in range(start, end)
        }
        assert detail_materials == {"stone_detail"}
        assert mesh.materials[mesh.face_materials[start]].color == (
            0.38, 0.39, 0.42, 1.0,
        )
        course_heights = {
            round(upper[2] - lower[2], 6)
            for lower, upper in mesh.component_volume_bounds("facade_details")
        }
        assert 0.05 in course_heights


def test_house_facade_details_follow_the_style_not_the_generator() -> None:
    """Nenhuma cor de fachada fixada no Gerador: tudo vem do Estilo (ADR 0004)."""
    from blender_worker.generators.base import get_generator
    from blender_worker.style import MEDIEVAL_LOWPOLY, Style

    palette = dict(MEDIEVAL_LOWPOLY)
    palette["stone_detail"] = (0.01, 0.02, 0.03, 1.0)
    palette["wood"] = (0.04, 0.05, 0.06, 1.0)
    custom = Style("medieval_lowpoly", palette)
    generator_cls = get_generator("house")

    for finish, expected in (("stone", (0.01, 0.02, 0.03, 1.0)), ("timber", (0.04, 0.05, 0.06, 1.0))):
        spec = load_spec(
            {"spec_version": 1, "type": "house", "seed": 42, "wall_finish": finish}
        )
        mesh = generator_cls(spec, custom).build()
        start, end = mesh.components["facade_details"]
        colors = {
            mesh.materials[mesh.face_materials[index]].color
            for index in range(start, end)
        }
        assert colors == {expected}
