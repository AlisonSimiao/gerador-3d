"""Ticket 20: Baú Fechado v1 — contrato, envelope externo, Seed (rápido, sem bpy).

Costuras sob teste:
- schema.load_spec para chest (faixas/defaults do ADR 0009, campos antigos
  rejeitados) — pega divergência de contrato.
- Descritor chest via inspect (IR puro-Python) — envelope externo, Âncora no
  centro da superfície de apoio, variação por Seed, orçamento de 2000 tris.
"""

import pytest

from blender_worker.registry import get_descriptor
from blender_worker.schema import SpecError, load_spec, spec_to_dict


def _chest(**changes):
    base = {"spec_version": 1, "type": "chest", "seed": 3}
    base.update(changes)
    return load_spec(base)


def test_chest_defaults_match_adr_0009() -> None:
    resolved = spec_to_dict(_chest())

    assert resolved == {
        "spec_version": 1,
        "type": "chest",
        "seed": 3,
        "width": 1.0,
        "height": 0.6,
        "depth": 0.6,
        "lid_form": "arched",
        "band_count": 2,
        "has_lock": True,
        "style": "medieval_lowpoly",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seed", -1),
        ("seed", 4_294_967_296),
        ("width", 0.59),
        ("width", 1.81),
        ("height", 0.39),
        ("height", 1.11),
        ("depth", 0.39),
        ("depth", 1.01),
        ("band_count", -1),
        ("band_count", 5),
    ],
)
def test_chest_rejects_values_outside_v1_ranges(field: str, value: int | float) -> None:
    with pytest.raises(SpecError, match=f"{field}=.*fora do intervalo"):
        _chest(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seed", 0),
        ("seed", 4_294_967_295),
        ("width", 0.6),
        ("width", 1.8),
        ("height", 0.4),
        ("height", 1.1),
        ("depth", 0.4),
        ("depth", 1.0),
        ("band_count", 0),
        ("band_count", 4),
    ],
)
def test_chest_accepts_v1_range_boundaries(field: str, value: int | float) -> None:
    assert _chest(**{field: value}).type == "chest"


@pytest.mark.parametrize(
    ("old_field", "old_value"),
    [
        ("lid_type", "arched"),
        ("lock", True),
        ("straps", 2),
        ("handle_count", 1),
    ],
)
def test_chest_rejects_fields_from_the_pre_v1_contract(
    old_field: str, old_value: object
) -> None:
    data = {"spec_version": 1, "type": "chest", "seed": 3, old_field: old_value}
    with pytest.raises(SpecError, match="campos desconhecidos"):
        load_spec(data)


def test_chest_rejects_values_outside_the_v1_vocabulary() -> None:
    with pytest.raises(SpecError, match="lid_form.*tipo JSON inválido"):
        _chest(lid_form="domed")


def test_chest_external_envelope_matches_declared_dimensions() -> None:
    """Envelope externo = width/height/depth declarados, tampa e cintas incluídas."""
    descriptor = get_descriptor("chest")
    cases = [
        {},
        {"lid_form": "flat", "band_count": 0, "has_lock": False},
        {"lid_form": "arched", "band_count": 4, "has_lock": True},
        {"width": 0.6, "height": 0.4, "depth": 0.4, "lid_form": "flat"},
        {"width": 1.8, "height": 1.1, "depth": 1.0, "lid_form": "arched"},
    ]
    for changes in cases:
        spec = _chest(**changes)
        mesh, checks = descriptor.inspect(spec)
        (lo, hi) = (mesh.bounds()[0], mesh.bounds()[1])
        w, h, d = spec.width, spec.height, spec.depth
        assert lo[0] == pytest.approx(-w / 2, abs=1e-6), changes
        assert hi[0] == pytest.approx(w / 2, abs=1e-6), changes
        assert lo[1] == pytest.approx(-d / 2, abs=1e-6), changes
        assert hi[1] == pytest.approx(d / 2, abs=1e-6), changes
        assert lo[2] == pytest.approx(0.0, abs=1e-6), changes
        assert hi[2] == pytest.approx(h, abs=1e-6), changes
        # Tampa, cintas e fecho são visuais: nada ultrapassa o envelope.
        for name in mesh.components:
            (clo, chi) = mesh.component_bounds(name)
            for axis in range(3):
                assert clo[axis] >= lo[axis] - 1e-6, (changes, name)
                assert chi[axis] <= hi[axis] + 1e-6, (changes, name)
        assert all(check["ok"] for check in checks.values()), changes


def test_chest_anchor_is_the_support_surface_center_at_origin() -> None:
    descriptor = get_descriptor("chest")
    for changes in [{}, {"lid_form": "flat", "band_count": 0, "has_lock": False}]:
        mesh, checks = descriptor.inspect(_chest(**changes))
        assert mesh.anchor == (0.0, 0.0, 0.0)
        assert mesh.anchor_kind.value == "support_surface_center"
        assert checks["anchor"]["ok"] is True


def test_chest_same_seed_rebuilds_equivalent_geometry_and_materials() -> None:
    descriptor = get_descriptor("chest")
    spec = _chest(seed=7, lid_form="arched", band_count=4)

    first, first_checks = descriptor.inspect(spec)
    second, second_checks = descriptor.inspect(spec)

    assert first.vertices == second.vertices
    assert first.faces == second.faces
    assert first.face_materials == second.face_materials
    assert [(m.name, m.color) for m in first.materials] == [
        (m.name, m.color) for m in second.materials
    ]
    assert first.components == second.components
    assert all(check["ok"] for check in first_checks.values())
    assert all(check["ok"] for check in second_checks.values())


def test_chest_distinct_seeds_vary_observably_but_stay_recognizable() -> None:
    """Seeds distintas: mesmo Baú reconhecível, variação observável (ADR 0008)."""
    descriptor = get_descriptor("chest")

    first, first_checks = descriptor.inspect(_chest(seed=7))
    second, second_checks = descriptor.inspect(_chest(seed=8))

    assert first.vertices != second.vertices

    for mesh in (first, second):
        (lo, hi) = (mesh.bounds()[0], mesh.bounds()[1])
        assert lo[0] == pytest.approx(-0.5, abs=1e-6)
        assert hi[0] == pytest.approx(0.5, abs=1e-6)
        assert lo[2] == pytest.approx(0.0, abs=1e-6)
        assert hi[2] == pytest.approx(0.6, abs=1e-6)
        assert set(mesh.components) == {"body", "lid", "bands", "lock"}
        assert [m.name for m in mesh.materials] == [
            "wood",
            "wood_dark",
            "band_iron",
            "lock_gold",
        ]
        assert mesh.tri_count() == first.tri_count()
    assert all(check["ok"] for check in first_checks.values())
    assert all(check["ok"] for check in second_checks.values())


def test_chest_distinct_seeds_vary_observably_at_chest_scale() -> None:
    """Duas seeds movem vértices em escala visual (>3cm no baú default).

    A variação vive nos detalhes secundários (largura/posição das
    cintas, tamanho/posição da fechadura): mesma topologia e mesmo
    envelope, geometria visivelmente distinta.
    """
    descriptor = get_descriptor("chest")

    first, _ = descriptor.inspect(_chest(seed=7))
    second, _ = descriptor.inspect(_chest(seed=8))

    assert len(first.vertices) == len(second.vertices)
    displacement = max(
        max(abs(a - b) for a, b in zip(first.vertices[i], second.vertices[i]))
        for i in range(len(first.vertices))
    )
    assert displacement > 0.03


def test_chest_seed_never_contradicts_dimensions_options_or_materials() -> None:
    descriptor = get_descriptor("chest")
    for seed in range(20):
        mesh, checks = descriptor.inspect(_chest(seed=seed))
        (lo, hi) = (mesh.bounds()[0], mesh.bounds()[1])
        assert tuple(lo) + tuple(hi) == pytest.approx(
            (-0.5, -0.3, 0.0, 0.5, 0.3, 0.6), abs=1e-6
        )
        assert set(mesh.components) == {"body", "lid", "bands", "lock"}
        assert mesh.tri_count() <= descriptor.triangle_budget
        assert all(check["ok"] for check in checks.values())
