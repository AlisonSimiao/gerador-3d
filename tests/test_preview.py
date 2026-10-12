"""Ticket 10 seams: versioned Style render profile + fallback publishes nothing.

Fast level (no bpy): the profile is a repository-versioned contract and the
auxiliary fallback path must never publish ``preview.png``.
"""

import json
from pathlib import Path

import pytest

from blender_worker import preview as preview_module
from blender_worker.bpy_build import mesh_to_bpy
from blender_worker.export import GenerateError, generate
from blender_worker.geometry import MeshBuilder
from blender_worker.preview import render_official_preview
from blender_worker.schema import load_spec_file


def test_render_profile_is_versioned_for_the_style() -> None:
    profile = json.loads(
        (Path(__file__).parents[1] / "blender_worker" / "render_profile.json").read_text(
            encoding="utf-8"
        )
    )

    assert profile["schema_version"] == 1
    assert profile["name"] == "medieval_lowpoly-v2"
    assert profile["engine"] == "BLENDER_EEVEE"
    assert profile["size"] == 1024
    assert profile["reference_span"] == 4.0
    assert [view["name"] for view in profile["views"]] == [
        "perspective",
        "front",
        "side",
        "rear",
    ]
    assert profile["background"] == [38, 40, 46]
    assert profile["color_management"]["view_transform"] == "Standard"


def test_fallback_never_publishes_preview_png(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("blender_worker.export.bpy_available", lambda: False)
    out = tmp_path / "result"

    with pytest.raises(GenerateError) as raised:
        generate(load_spec_file("specs/house_default.json"), str(out))

    assert raised.value.code == "environment.unavailable"
    assert not (out / "preview.png").exists()
    assert not (out / "model.glb").exists()


@pytest.mark.integration
def test_official_preview_brightness_is_stable_across_asset_scales(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The normalized board must not over/under-expose assets by their size."""
    import bpy  # type: ignore[import-not-found]

    profile = json.loads(preview_module.PROFILE_PATH.read_text(encoding="utf-8"))
    profile["size"] = 128
    profile["tile_size"] = 64
    profile["views"] = [profile["views"][1]]
    profile_path = tmp_path / "render_profile.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    monkeypatch.setattr(preview_module, "PROFILE_PATH", profile_path)

    def render_center_luminance(span: float) -> float:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        builder = MeshBuilder()
        material = builder.material("matte", (0.45, 0.30, 0.17, 1.0), roughness=0.85)
        builder.box(0, 0, 0, span, span, span, material)
        mesh_to_bpy(builder.mesh, f"cube_{span}")
        path = tmp_path / f"preview-{span}.png"
        render_official_preview(str(path))

        image = bpy.data.images.load(str(path), check_existing=False)
        try:
            pixels = list(image.pixels)
            samples: list[float] = []
            for center_x, center_y in ((32, 96),):
                for y in range(center_y - 4, center_y + 4):
                    for x in range(center_x - 4, center_x + 4):
                        offset = (y * 128 + x) * 4
                        red, green, blue = pixels[offset:offset + 3]
                        samples.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)
            return sum(samples) / len(samples)
        finally:
            bpy.data.images.remove(image)

    small = render_center_luminance(0.6)
    large = render_center_luminance(8.0)

    assert abs(small - large) <= 0.08, (small, large)
    assert 0.20 <= small <= 0.65, (small, large)
    assert 0.20 <= large <= 0.65, (small, large)
