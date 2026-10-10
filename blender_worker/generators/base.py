"""Contrato dos geradores: spec -> MeshData (+ objetos bpy quando disponível)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ..geometry.mesh import MeshData
from ..schema import BaseSpec
from ..style import Style

S = TypeVar("S", bound=BaseSpec)

def register(spec_type: str):  # type: ignore[no-untyped-def]
    """Compatibility decorator; the contractual registry owns discovery."""
    def deco(cls: type["BaseGenerator[Any]"]) -> type["BaseGenerator[Any]"]:
        return cls

    return deco


def get_generator(spec_type: str) -> type["BaseGenerator[Any]"]:
    from ..registry import get_descriptor
    return get_descriptor(spec_type).generator


class BaseGenerator(ABC, Generic[S]):
    spec: S
    style: Style

    def __init__(self, spec: S, style: Style) -> None:
        self.spec = spec
        self.style = style

    @abstractmethod
    def build(self) -> MeshData:
        """Constrói a malha (origem na base-centro, metros, rotação zerada)."""

    def build_bpy_objects(self, mesh: MeshData) -> list[Any]:
        """Converte MeshData em objetos bpy quando bpy está disponível.

        Retorna [] se bpy não estiver instalado (fallback puro-Python).
        """
        try:
            import bpy  # type: ignore[import-not-found]
        except ImportError:
            return []
        from ..bpy_build import mesh_to_bpy

        obj = mesh_to_bpy(mesh, self.spec.type)
        return [obj]
