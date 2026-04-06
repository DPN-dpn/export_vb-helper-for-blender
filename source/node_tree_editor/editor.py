import bpy
import os
from .tree import EVBH_NodeTree

_original_node_header_draw = None


def _custom_node_header_draw(self, context):
    global _original_node_header_draw

    tree_type = getattr(context.space_data, "tree_type", None)

    if tree_type != EVBH_NodeTree.bl_idname:
        if _original_node_header_draw:
            return _original_node_header_draw(self, context)
        return

    layout = self.layout
    scene = context.scene

    # 에디터 타입
    layout.template_header()

    row = layout.row(align=True)
    row.separator()

    # 모드 선택
    box_mod = row.box()
    row_box_mod = box_mod.row(align=True)
    row_box_mod.operator("evbh.select_mod", text="모드", icon="FILE_FOLDER")
    row_box_mod.separator()
    if scene.evbh_mod_path:
        row_box_mod.label(
            text=os.path.basename(os.path.normpath(scene.evbh_mod_path)),
        )
    else:
        row_box_mod.label(text="선택 없음")
    row_box_mod.separator()
    if scene.evbh_mod_path:
        row_box_mod.operator("evbh.unlink_mod", text="", icon="X")

    row.separator()

    # 에셋 선택
    box_asset = row.box()
    row_box_asset = box_asset.row(align=True)
    row_box_asset.operator("evbh.select_asset", text="에셋", icon="FILE")
    row_box_asset.separator()
    if scene.evbh_asset_path:
        row_box_asset.label(
            text=os.path.basename(os.path.dirname(scene.evbh_asset_path)),
        )
    else:
        row_box_asset.label(text="선택 없음")
    row_box_asset.separator()
    if scene.evbh_asset_path:
        row_box_asset.operator("evbh.unlink_asset", text="", icon="X")

    row.separator()

    # 노드 트리 생성
    col = row.column(align=True)
    col.enabled = bool(scene.evbh_asset_path) and bool(scene.evbh_mod_path)
    col.operator("evbh.create_new_tree", text="", icon="PLAY")

    # 자동 연결/내보내기
    row2 = row.row(align=True)
    nt = getattr(context.space_data, "node_tree", None)
    row2.enabled = bool(nt)
    row2.operator("evbh.auto_link", text="", icon="GP_ONLY_SELECTED")
    row3 = row.row(align=True)
    row3.enabled = bool(nt and len(getattr(nt, "links", ())) > 0)
    row3.operator("evbh.unlink", text="", icon="GP_SELECT_POINTS")
    row4 = row.row(align=True)
    row4.enabled = bool(nt)
    row4.operator("evbh.export_mod", text="", icon="EXPORT")

    row.separator()

    # 텍스처 소켓 활성화
    row.prop(scene, "evbh_show_texture_sockets", text="", toggle=True, icon="TEXTURE")


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
