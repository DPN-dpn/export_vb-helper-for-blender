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
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.label(text="에셋/모드 불러오기")
        row = col.row(align=True)
        row.label(
            text=(
                "에셋: "
                + (
                    os.path.basename(os.path.dirname(scene.evbh_asset_path))
                    if scene.evbh_asset_path
                    else "선택 없음"
                )
            )
        )
        row.operator("prep.select_asset", text="", icon="FILE")
        row = col.row(align=True)
        row.label(
            text=(
                "모드: "
                + (
                    os.path.basename(os.path.normpath(scene.evbh_mod_path))
                    if scene.evbh_mod_path
                    else "선택 없음"
                )
            )
        )
        row.operator("prep.select_mod", text="", icon="FILE_FOLDER")
        layout.separator()


def register():
    bpy.utils.register_class(PREP_PANEL)


def unregister():
    bpy.utils.unregister_class(PREP_PANEL)
