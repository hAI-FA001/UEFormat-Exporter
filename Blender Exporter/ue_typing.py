from bpy.types import Context, Scene

from .op.settings import UMESettings


class UFormatScene(Scene):
    ume_settings: UMESettings

class UFormatContext(Context):
    scene: UFormatScene