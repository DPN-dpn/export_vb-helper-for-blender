import bpy
from bpy.types import Panel


class EXPORT_VB_PREPANEL(Panel):
    bl_label = "엵툵 사전작업"
    bl_idname = "Export_vb_PREP_PT_panel"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "엵툵 사전작업"

    def draw(self, context):
        layout = self.layout
        layout.label(text="엵툵 사전작업 패널")
        layout.operator("exportvb.dummy", icon="PLAY")


def register():
    bpy.utils.register_class(EXPORT_VB_PREPANEL)


def unregister():
    bpy.utils.unregister_class(EXPORT_VB_PREPANEL)
