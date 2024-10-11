from typing import Any

from bpy.props import BoolProperty, FloatProperty
from bpy.types import PropertyGroup


class UMESettings(PropertyGroup):
    scale_factor: FloatProperty(name="Scale", default=0.01, min=0.01) # type: ignore[reportInvalidTypeForm]
    bone_length: FloatProperty(name="Bone Length", default=4.0, min=0.1) # type: ignore[reportInvalidTypeForm]
    reorient_bones: BoolProperty(name="Reorient Bones", default=False) # type: ignore[reportInvalidTypeForm]
    export_lods: BoolProperty(name="Export Levels of Detail", default=False) # type: ignore[reportInvalidTypeForm]
    export_collision: BoolProperty(name="Export Collision", default=False) # type: ignore[reportInvalidTypeForm]
    export_morph_targets: BoolProperty(name="Export Morph Targets", default=True) # type: ignore[reportInvalidTypeForm]
    export_sockets: BoolProperty(name="Export Sockets", default=True) # type: ignore[reportInvalidTypeForm]
    export_virtual_bones: BoolProperty(name="Export Virtual Bones", default=False) # type: ignore[reportInvalidTypeForm]
    rotation_only: BoolProperty(name="Rotation Only", default=False) # type: ignore[reportInvalidTypeForm]

    def get_props(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self.__annotations__}
