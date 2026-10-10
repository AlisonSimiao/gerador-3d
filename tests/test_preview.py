"""Ticket 10 seams: versioned Style render profile + fallback publishes nothing.

Fast level (no bpy): the profile is a repository-versioned contract and the
auxiliary fallback path must never publish ``preview.png``.
"""

import json
from pathlib import Path

import pytest

from blender_worker.export import GenerateError, generate
from blender_worker.schema import load_spec_file


def test_render_profile_is_versioned_for_the_style() -> None:
    profile = json.loads(
        (Path(__file__).parents[1] / "blender_worker" / "render_profile.json").read_text(
            encoding="utf-8"
        )
    )

    assert profile["schema_version"] == 1
    assert profile["name"] == "medieval_lowpoly-v1"
    assert profile["engine"] == "BLENDER_EEVEE"
    assert profile["size"] == 1024
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
