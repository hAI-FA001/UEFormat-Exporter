from typing import cast

from bpy.types import Context, Operator, Panel

from ..ue_typing import UFormatContext, UFSettings


class UEFORMAT_PT_Panel(Panel):
    bl_category = "UE Format"
    bl_label = "UE Format"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context: Context | UFormatContext) -> None:
        assert hasattr(context.scene, "ume_settings")

        context = cast(UFormatContext, context)
        ume_settings = context.scene.ume_settings

        self.draw_general_options(self, ume_settings)
        self.draw_model_options(self, ume_settings)
    
    @staticmethod
    def draw_general_options(obj: Panel | Operator, settings: UFSettings) -> None:
        box = obj.layout.box()
        box.label(text="General", icon="SETTINGS")
        box.row().prop(settings, "scale_factor")
    
    @staticmethod
    def draw_model_options(
        obj: Panel | Operator,
        settings: UFSettings,
        *,
        export_menu: bool = False
    ) -> None:
        box = obj.layout.box()
        box.label(text="Model", icon="OUTLINER_OB_MESH")
        box.row().prop(settings, "export_lods")
        box.row().prop(settings, "export_collision")
        box.row().prop(settings, "export_morph_targets")
        # box.row().prop(settings, "export_sockets")
        box.row().prop(settings, "export_virtual_bones")
        # box.row().prop(settings, "reorient_bones")
        box.row().prop(settings, "bone_length")

        if not export_menu:
            box.row().operator("uf.export_uemodel", icon="MESH_DATA")

