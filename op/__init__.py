import bpy
from bpy.props import PointerProperty
from bpy.types import Context, Menu, Scene

from .export_helpers import UFExportUEModel
from .panels import UEEXPORT_PT_Panel
from .settings import UMESettings

operators = [UEEXPORT_PT_Panel, UFExportUEModel, UMESettings]


def draw_export_menu(self: Menu, context: Context) -> None:
    self.layout.operator(UFExportUEModel.bl_idname, text="Unreal Model (.uemodel)")

def register() -> None:
    for operator in operators:
        bpy.utils.register_class(operator)
    
    Scene.ume_settings = PointerProperty(type=UMESettings)
    bpy.types.TOPBAR_MT_file_export.append(draw_export_menu)

def unregister() -> None:
    for operator in operators:
        bpy.utils.unregister_class(operator)
    
    del Scene.ume_settings
    bpy.types.TOPBAR_MT_file_export.remove(draw_export_menu)

