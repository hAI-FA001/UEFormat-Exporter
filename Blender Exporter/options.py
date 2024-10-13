from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .op.settings import UMESettings

@dataclass(slots=True)
class UEFormatOptions:
    scale_factor: float = 1.0

    @classmethod
    def from_settings(cls, settings: UMESettings) -> UEFormatOptions:
        field_names = {field.name for field in fields(cls)}
        return cls(**{k: v for k, v in settings.get_props().items() if k in field_names})

@dataclass(slots=True)
class UEModelOptions(UEFormatOptions):
    # bone_length: float = 4.0
    # reorient_bones: bool = False
    export_collision: bool = True
    export_sockets: bool = True
    export_morph_targets: bool = True
    export_lods: bool = True
    export_virtual_bones: bool = True
    export_selected_only: bool = False
