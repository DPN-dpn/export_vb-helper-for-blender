import bpy
from bpy.types import Panel
import os


class PREP_PANEL(Panel):
    bl_label = "엵툵 사전작업"
    bl_idname = "PREP_PT_panel"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "엵툵 사전작업"

    def draw(self, context):
        pass


def register():
    bpy.utils.register_class(PREP_PANEL)


def unregister():
    bpy.utils.unregister_class(PREP_PANEL)
