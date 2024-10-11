import bpy
from bpy.props import PointerProperty
from bpy.types import Context, Menu, Scene

from .export_helpers import UFExportUEModel
from .panels import UEFORMAT_PT_Panel
from .settings import UFSettings

operators = [UEFORMAT_PT_Panel, UFExportUEModel, UFSettings]


def draw_export_menu(self: Menu, context: Context) -> None:
    self.layout.operator(UFExportUEModel.bl_idname, text="Unreal Model (.uemodel)")

def register() -> None:
    for operator in operators:
        bpy.utils.register_class(operator)
    
    Scene.uf_settings = PointerProperty(type=UFSettings)
    bpy.types.TOPBAR_MT_file_export.append(draw_export_menu)

def unregister() -> None:
    for operator in operators:
        bpy.utils.unregister_class(operator)
    
    del Scene.uf_settings
    bpy.types.TOPBAR_MT_file_export.remove(draw_export_menu)

