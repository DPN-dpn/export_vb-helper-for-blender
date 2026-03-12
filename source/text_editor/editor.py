import bpy
from ..node_tree_editor.tree import EVBHNodeTree

_original_node_header_draw = None


def workspace_has_evbhnodetree(context) -> bool:
    screen = context.screen or (context.window and context.window.screen)
    if not screen:
        return False
    for area in screen.areas:
        if area.type != "NODE_EDITOR":
            continue
        space = area.spaces.active

        # 1) 직접 연결된 node_tree 데이터블록이 있고 그 클래스의 bl_idname 체크
        node_tree = getattr(space, "node_tree", None)
        if node_tree is not None:
            bt = getattr(type(node_tree), "bl_idname", None)
            if bt == EVBHNodeTree.bl_idname:
                return True

        # 2) 일부 API/버전에서는 tree_type 또는 tree_id 같은 속성을 사용
        tree_type = getattr(space, "tree_type", None)
        if tree_type == EVBHNodeTree.bl_idname:
            return True

        # 3) 안전망: space 자체에 ui_type/other 식별자가 있을 수 있음
        ui_type = getattr(area, "ui_type", None)
        if ui_type == EVBHNodeTree.bl_idname:
            return True


def simplified_text_header_draw(self, context):
    layout = self.layout

    st = context.space_data
    text = st.text
    is_syntax_highlight_supported = st.is_syntax_highlight_supported()

    # 왼쪽: 뷰 메뉴
    row = layout.row(align=True)
    row.menu("TEXT_MT_view")

    layout.separator_spacer()

    # 가운데: 텍스트 데이터블록
    if text and text.is_modified:
        row = layout.row(align=True)
        row.alert = True
        row.operator("text.resolve_conflict", text="", icon="QUESTION")

    row = layout.row(align=True)
    row.template_ID(st, "text")

    if text:
        is_osl = text.name.endswith((".osl", ".osl"))
        if is_osl:
            row.operator("node.shader_script_update", text="", icon="FILE_REFRESH")
        else:
            row = layout.row()
            row.active = is_syntax_highlight_supported

    layout.separator_spacer()

    # 오른쪽: 라인 번호, 단어 줄바꿈, 구문 강조 토글
    row = layout.row(align=True)
    row.prop(st, "show_line_numbers", text="")
    row.prop(st, "show_word_wrap", text="")

    syntax = row.row(align=True)
    syntax.active = is_syntax_highlight_supported
    syntax.prop(st, "show_syntax_highlight", text="")


def patched_text_header_draw(self, context):
    if workspace_has_evbhnodetree(context):
        simplified_text_header_draw(self, context)
        return

    if _original_node_header_draw:
        _original_node_header_draw(self, context)


def register():
    global _original_node_header_draw

    if _original_node_header_draw is None:
        _original_node_header_draw = getattr(bpy.types.TEXT_HT_header, "draw", None)
        bpy.types.TEXT_HT_header.draw = patched_text_header_draw


def unregister():
    global _original_node_header_draw

    if _original_node_header_draw is not None:
        bpy.types.TEXT_HT_header.draw = _original_node_header_draw
        _original_node_header_draw = None
