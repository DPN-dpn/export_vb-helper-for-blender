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
    scene = context.scene

    # 에디터 타입
    layout.template_header()

    row = layout.row(align=True)
    row.separator()

    # 에셋 선택
    box_asset = row.box()
    row_box_asset = box_asset.row(align=True)
    row_box_asset.operator("evhb.select_asset", text="에셋", icon="FILE")
    row_box_asset.separator()
    if scene.evbh_asset_path:
        row_box_asset.label(
            text=os.path.basename(os.path.dirname(scene.evbh_asset_path)),
        )
    else:
        row_box_asset.label(text="선택 없음")
    row_box_asset.separator()
    if scene.evbh_asset_path:
        row_box_asset.operator("evhb.unlink_asset", text="", icon="X")

    row.separator()

    # 모드 선택
    box_mod = row.box()
    row_box_mod = box_mod.row(align=True)
    row_box_mod.operator("evhb.select_mod", text="모드", icon="FILE_FOLDER")
    if scene.evbh_mod_path:
        row_box_asset.separator()
        row_box_mod.label(
            text=os.path.basename(os.path.normpath(scene.evbh_mod_path)),
        )
        row_box_asset.separator()
    else:
        row_box_mod.label(text="선택 없음")
    if scene.evbh_mod_path:
        row_box_mod.operator("evhb.unlink_mod", text="", icon="X")


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
