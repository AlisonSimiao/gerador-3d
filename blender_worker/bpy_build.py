"""Ponte MeshData -> bpy (usada só quando bpy está instalado).

Mantida fina e tolerante a diferenças 4.x/5.x: usa apenas
`from_pydata`, Principled BSDF com sockets padrão e assigns de material.
"""

from __future__ import annotations

from typing import Any

from .geometry.mesh import MeshData


def mesh_to_bpy(mesh: MeshData, name: str) -> Any:
    import bpy  # type: ignore[import-not-found]

    tris = mesh.triangulated()
    faces = [t for t, _ in tris]
    me = bpy.data.meshes.new(f"{name}_mesh")
    me.from_pydata([tuple(v) for v in mesh.vertices], [], [tuple(f) for f in faces])
    me.update()
    obj = bpy.data.objects.new(name, me)
    scene = bpy.context.scene
    scene.collection.objects.link(obj)

    mats = []
    for m in mesh.materials:
        ma = bpy.data.materials.new(m.name)
        ma.use_nodes = True
        bsdf = None
        for n in ma.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                bsdf = n
                break
        if bsdf is not None:
            for sock_name, val in (("Base Color", (*m.color,)),
                                   ("Metallic", m.metallic),
                                   ("Roughness", m.roughness)):
                sock = bsdf.inputs.get(sock_name)
                if sock is not None:
                    try:
                        sock.default_value = val
                    except Exception:
                        pass
        mats.append(ma)
        obj.data.materials.append(ma)
    # um material por face
    for poly, (_, mat_idx) in zip(obj.data.polygons, tris):
        poly.material_index = min(mat_idx, max(0, len(mats) - 1))
    return obj
