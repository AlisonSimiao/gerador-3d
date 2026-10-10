"""Official Blender Preview rendering from a versioned Style profile."""

from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile
from typing import Any


PROFILE_PATH = Path(__file__).with_name("render_profile.json")


def render_official_preview(path: str) -> dict[str, Any]:
    """Render and publish the four-view Preview using Blender Eevee."""
    import bpy  # type: ignore[import-not-found]
    from mathutils import Vector  # type: ignore[import-not-found]

    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    scene.render.engine = profile["engine"]
    scene.render.resolution_x = profile["tile_size"]
    scene.render.resolution_y = profile["tile_size"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.view_settings.look = profile["color_management"]["look"]
    scene.view_settings.view_transform = profile["color_management"]["view_transform"]
    scene.view_settings.exposure = profile["color_management"]["exposure"]
    scene.view_settings.gamma = profile["color_management"]["gamma"]
    if scene.world is None:
        scene.world = bpy.data.worlds.new("preview_world")
    scene.world.color = tuple(channel / 255 for channel in profile["background"])

    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(point[index] for point in corners) for index in range(3)))
    high = Vector(tuple(max(point[index] for point in corners) for index in range(3)))
    center = (low + high) / 2
    extent = high - low
    span = max(extent.x, extent.y, extent.z, 0.001)

    camera_data = bpy.data.cameras.new("preview_camera")
    camera = bpy.data.objects.new("preview_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    for light_profile in profile["lights"]:
        data = bpy.data.lights.new(light_profile["name"], type="AREA")
        data.energy = light_profile["energy"]
        data.color = tuple(light_profile["color"])
        data.shape = "DISK"
        data.size = span * light_profile["size_factor"]
        light = bpy.data.objects.new(light_profile["name"], data)
        light.location = tuple(
            center[index] + span * light_profile["position"][index]
            for index in range(3)
        )
        scene.collection.objects.link(light)
        _point_at(light, center)

    with tempfile.TemporaryDirectory(prefix="preview-views-") as directory:
        tiles: list[Path] = []
        for view in profile["views"]:
            direction = Vector(view["direction"]).normalized()
            camera.location = center + direction * span * view["distance_factor"]
            _point_at(camera, center)
            camera.data.type = view["projection"]
            if camera.data.type == "ORTHO":
                camera.data.ortho_scale = span * profile["frame_factor"]
            else:
                camera.data.lens = profile["perspective_lens_mm"]
            tile_path = Path(directory, f"{view['name']}.png")
            scene.render.filepath = str(tile_path)
            bpy.ops.render.render(write_still=True)
            tiles.append(tile_path)
        _compose_tiles(tiles, path, profile["size"])

    return {
        "ok": True,
        "detail": f"4 vistas renderizadas com {profile['engine']}",
        "profile": profile["name"],
        "views": [view["name"] for view in profile["views"]],
        "size": profile["size"],
    }


def _point_at(obj: Any, target: Any) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _compose_tiles(paths: list[Path], output_path: str, size: int) -> None:
    import bpy  # type: ignore[import-not-found]

    tile_size = size // 2
    canvas = [0.0] * (size * size * 4)
    loaded = []
    try:
        for index, path in enumerate(paths):
            image = bpy.data.images.load(str(path), check_existing=False)
            loaded.append(image)
            pixels = list(image.pixels)
            offset_x = (index % 2) * tile_size
            offset_y = (1 - index // 2) * tile_size
            for row in range(tile_size):
                source = row * tile_size * 4
                target = ((offset_y + row) * size + offset_x) * 4
                canvas[target:target + tile_size * 4] = pixels[source:source + tile_size * 4]
        sheet = bpy.data.images.new("official_preview", width=size, height=size, alpha=False)
        loaded.append(sheet)
        sheet.pixels.foreach_set(canvas)
        sheet.filepath_raw = output_path
        sheet.file_format = "PNG"
        sheet.save()
    finally:
        for image in loaded:
            bpy.data.images.remove(image)
