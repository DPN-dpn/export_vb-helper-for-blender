import bpy
import json
from bpy.types import Operator
from bpy.props import StringProperty
from ...data import text_data_block


def _find_first_node_editor_space(context):
    # Find a NODE_EDITOR area in the current screen and return its space.
    screen = context.window.screen
    for area in screen.areas:
        if area.type != "NODE_EDITOR":
            continue
        for space in area.spaces:
            if space.type == "NODE_EDITOR":
                return space
    return None


def _create_asset_nodes(op, tree):
    asset_blocks = getattr(text_data_block, "_asset_text_blocks", set())
    x = 0
    y = 0
    y_step = -80
    y_socket_step = -20
    created_count = 0

    for text_name in list(asset_blocks):
        text = bpy.data.texts.get(text_name)
        if text is None:
            continue

        # 안전하게 텍스트 내용을 얻기
        try:
            content = "\n".join([ln.body for ln in text.lines])
        except Exception:
            content = text.as_string() if hasattr(text, "as_string") else ""

        try:
            data = json.loads(content)
        except Exception:
            continue

        for comp in data:
            name = comp.get("component_name", "Component")
            node = tree.nodes.new("AssetSlotNode")
            node.name = name
            try:
                node.label = name
            except Exception:
                pass
            socket_count = 0

            name_map = {
                "position_vb": "Position",
                "blend_vb": "Blend",
                "texcoord_vb": "Texcoord",
            }
            for key in ("position_vb", "blend_vb", "texcoord_vb"):
                display = name_map.get(key, key)
                socket_type = (
                    "INI_PositionSocket"
                    if key == "position_vb"
                    else (
                        "INI_BlendSocket" if key == "blend_vb" else "INI_TexcoordSocket"
                    )
                )
                sock = node.inputs.new(socket_type, display)
                socket_count += 1
                hint_val = comp.get(key, "")
                if hint_val is None:
                    hint_val = ""
                try:
                    sock["hint"] = str(hint_val)
                except Exception:
                    pass

            classifications = comp.get("object_classifications", [])
            for c in classifications:
                socket_name = f"IB_{c}"
                sock = node.inputs.new("INI_IBSocket", socket_name)
                socket_count += 1
                ib_hint = comp.get("ib", "")
                if ib_hint is None:
                    ib_hint = ""
                try:
                    sock["hint"] = str(ib_hint)
                except Exception:
                    pass

            node.location = (x, y)
            y += y_step + socket_count * y_socket_step
            created_count += 1

        op.report({"INFO"}, f"생성된 에셋 노드 수: {created_count}")


def _create_mod_nodes(op, tree):
    mod_blocks = getattr(text_data_block, "_mod_text_blocks", set())
    
    x = -350
    y = 0
    y_step = -80
    y_socket_step = -20
    created_count = 0
    
    # 
    
    return


class EVHB_OT_create_new_tree(Operator):
    bl_idname = "evhb.create_new_tree"
    bl_label = "슬롯 매칭 시작하기"
    bl_description = "불러온 에셋/모드 파일로 슬롯 매칭을 시작합니다."

    name: StringProperty(name="Name", default="EVBH Graph")

    def execute(self, context):
        tree = bpy.data.node_groups.new(self.name, "EVBHNodeTree")

        # 현재 화면의 첫 번째 NODE_EDITOR 공간을 찾아 새 노드트리를 엽니다.
        space = _find_first_node_editor_space(context)
        if space is not None:
            space.node_tree = tree
            # 일부 버전/스페이스에서 tree_type 속성을 사용하므로 시도해봄
            if hasattr(space, "tree_type"):
                space.tree_type = "EVBHNodeTree"

        # 현재 활성 영역이 NODE_EDITOR이면 컨텍스트의 space_data도 업데이트
        if context.area and context.area.type == "NODE_EDITOR":
            context.area.spaces.active.node_tree = tree
        self.report({"INFO"}, f"노드 트리 생성: {tree.name}")

        _create_asset_nodes(self, tree)
        _create_mod_nodes(self, tree)
        return {"FINISHED"}


classes = (EVHB_OT_create_new_tree,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
