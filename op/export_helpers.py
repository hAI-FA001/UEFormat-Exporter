from pathlib import Path
from typing import Generic, TypeVar

from bpy.props import CollectionProperty, StringProperty
from bpy.types import Operator, OperatorFileListElement
from bpy_extras.io_utils import ExportHelper

from .panels import UEFORMAT_PT_Panel
from ..ue_typing import UFormatContext
from ..options import UEFormatOptions, UEModelOptions

T = TypeVar("T", bound=UEFormatOptions)

class UFExportBase(Operator, ExportHelper, Generic[T]):
    bl_context = "scene"
    files: CollectionProperty(
        type=OperatorFileListElement,
        options={"HIDDEN", "SKIP_SAVE"}
    ) # type: ignore[reportInvalidTypeForm]
    directory: StringProperty(subtype="DIR_PATH") # type: ignore[reportInvalidTypeForm]

    options_class: type[T]

    def execute(self, context: UFormatContext) -> set[str]:
        options = self.options_class.from_settings(context.scene.ume_settings)

        directory = Path(self.directory)
        for file in self.files:
            file: OperatorFileListElement
        
        return {"FINISHED"}


class UFExportUEModel(UFExportBase):
    bl_idname = "uf.export_uemodel"
    bl_label = "Export Model"

    filename_ext = ".uemodel"
    filter_glob: StringProperty(default="*.uemodel", options={"HIDDEN"}, maxlen=255) # type: ignore[reportInvalidTypeForm]

    options_class = UEModelOptions

    def draw(self, context: UFormatContext) -> None:
        UEFORMAT_PT_Panel.draw_general_options(self, context.scene.ume_settings)
        UEFORMAT_PT_Panel.draw_model_options(
            self,
            context.scene.ume_settings,
            export_menu=True
        )

