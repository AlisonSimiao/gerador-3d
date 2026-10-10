"""Gate de reimportação: auxiliares puros (sem bpy)."""

from blender_worker.export import _anchor_holds, _expected_reimport_bounds
from blender_worker.geometry.mesh import AnchorKind, MeshData


def _mesh_with(vertices: list[tuple[float, float, float]]) -> MeshData:
    return MeshData(vertices=list(vertices))


def test_expected_reimport_bounds_negates_x_and_y() -> None:
    mesh = _mesh_with([(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)])

    assert _expected_reimport_bounds(mesh) == ((-4.0, -5.0, 3.0), (-1.0, -2.0, 6.0))


def test_anchor_holds_support_surface_at_origin() -> None:
    assert _anchor_holds((-1.0, -2.0, 0.0), (3.0, 4.0, 5.0), AnchorKind.SUPPORT_SURFACE) is True
    # Âncora flutuando acima da origem: rejeita.
    assert _anchor_holds((-1.0, -2.0, 0.5), (3.0, 4.0, 5.0), AnchorKind.SUPPORT_SURFACE) is False
    # Origem fora da projeção XZ da base: rejeita.
    assert _anchor_holds((1.0, 2.0, 0.0), (3.0, 4.0, 5.0), AnchorKind.SUPPORT_SURFACE) is False


def test_anchor_holds_grip_center_contains_origin() -> None:
    assert _anchor_holds((-0.13, -0.03, -0.12), (0.13, 0.03, 1.0), AnchorKind.GRIP_CENTER) is True
    assert _anchor_holds((0.5, 0.5, 0.5), (1.0, 1.0, 1.0), AnchorKind.GRIP_CENTER) is False
