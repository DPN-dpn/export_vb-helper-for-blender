import bpy
import os
from .tree import EVBHNodeTree

_original_node_header_draw = None


def _custom_node_header_draw(self, context):
    global _original_node_header_draw

    tree_type = getattr(context.space_data, "tree_type", None)

    if tree_type != EVBHNodeTree.bl_idname:
        if _original_node_header_draw:
            return _original_node_header_draw(self, context)
        return

    layout = self.layout
    layout.template_header()

    row = layout.row()
    row.alignment = "RIGHT"
    scene = context.scene

    layout.separator_spacer()

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
    row.operator("evhb.select_asset", text="", icon="FILE")
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
    row.operator("evhb.select_mod", text="", icon="FILE_FOLDER")

    layout.separator_spacer()


def register():
    global _original_node_header_draw

    if _original_node_header_draw is None:
        _original_node_header_draw = getattr(bpy.types, "NODE_HT_header").draw
    bpy.types.NODE_HT_header.draw = _custom_node_header_draw


def unregister():
    global _original_node_header_draw

    if _original_node_header_draw is not None:
        bpy.types.NODE_HT_header.draw = _original_node_header_draw
    _original_node_header_draw = None
