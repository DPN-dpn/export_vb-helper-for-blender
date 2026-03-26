import bpy
from bpy.types import Panel
from ..core.preferences import addon_module_name


class PREP_ADDON(Panel):
    bl_label = "연결"
    bl_idname = "PREP_PT_addon"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "엵툵 사전작업"

    def draw(self, context):
        layout = self.layout
        prefs = bpy.context.preferences.addons[addon_module_name()].preferences

        layout.prop(prefs, "evbh_export_vb")
        if prefs.evbh_export_vb:
            layout.prop(prefs, "evbh_export_vb_use")


def register():
    bpy.utils.register_class(PREP_ADDON)


def unregister():
    bpy.utils.unregister_class(PREP_ADDON)
