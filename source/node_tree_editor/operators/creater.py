import bpy
from bpy.types import Operator
from bpy.props import StringProperty
import json
import re
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
                    sock["hash"] = str(hint_val)
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
                    sock["hash"] = str(ib_hint)
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

    # mod_blocks에서 각 ini 를 읽어서 노드로 생성
    # 섹션 단위로 분리( [section] )하고 Resource로 시작하는 섹션에서 소켓 생성
    for text_name in list(mod_blocks):
        text = bpy.data.texts.get(text_name)
        if text is None:
            continue

        try:
            content = "\n".join([ln.body for ln in text.lines])
        except Exception:
            content = text.as_string() if hasattr(text, "as_string") else ""

        # 섹션 파싱: 단순 라인 기반으로 [section] 구간을 분리
        sections = {}
        cur_name = None
        for raw in content.splitlines():
            line = raw.strip()
            if not line:
                continue
            m = re.match(r"^\[(.+?)\]$", line)
            if m:
                cur_name = m.group(1)
                sections.setdefault(cur_name, [])
                continue
            if cur_name is None:
                continue
            sections[cur_name].append(line)

        # ini 파일 하나당 노드 하나 생성
        node = tree.nodes.new("ModFileNode")
        node.name = text_name
        try:
            node.label = text_name
        except Exception:
            pass

        socket_count = 0

        for sec_name, lines in sections.items():
            # Resource로 시작하는 섹션을 대상으로 함 (대소문자 무시)
            if not sec_name.lower().startswith("resource"):
                continue

            # 섹션 내부에서 filename, type 를 찾음
            filename = None
            type_token = None
            for ln in lines:
                # key = value 형태를 느슨하게 매칭
                m = re.match(r"^(?P<k>[^=]+)=(?P<v>.+)$", ln)
                if not m:
                    continue
                k = m.group("k").strip().lower()
                v = m.group("v").strip()
                # 값에서 주석 제거
                v = re.split(r";|#", v)[0].strip()
                if k == "filename":
                    filename = v.strip('"')
                elif k == "type":
                    type_token = v

            # type = Buffer 조건
            if type_token != "Buffer":
                continue

            # 소켓 라벨은 filename 이나 섹션 이름
            socket_label = filename or sec_name

            # 다른 섹션의 key=value에서 현재 섹션명을 값으로 사용하는지 검사하여
            # 키에 따라 소켓 타입을 결정하고, 참조 섹션의 hash 값을 가져옴
            hash_val = None
            socket_type = None
            for other_name, other_lines in sections.items():
                if other_name == sec_name:
                    continue
                for ln in other_lines:
                    m = re.match(r"^(?P<k>[^=]+)=(?P<v>.+)$", ln)
                    if not m:
                        continue
                    k = m.group("k").strip().lower()
                    v = m.group("v").strip()
                    v_clean = re.split(r";|#", v)[0].strip().strip('"')
                    if v_clean == sec_name:
                        # 단순 매핑: 'ib'/'vb2'/'vb0'/'vb1'
                        if k == "ib":
                            socket_type = "INI_IBSocket"
                        elif k == "vb2":
                            socket_type = "INI_BlendSocket"
                        elif k == "vb0":
                            socket_type = "INI_PositionSocket"
                        elif k == "vb1":
                            socket_type = "INI_TexcoordSocket"

                        # 참조 섹션에서 hash 값 추출
                        for ln2 in other_lines:
                            m2 = re.match(r"^\s*hash\s*=\s*(.+)$", ln2, re.IGNORECASE)
                            if m2:
                                hv = m2.group(1).strip()
                                hv = re.split(r";|#", hv)[0].strip().strip('"')
                                hash_val = hv
                                break
                        break
                if socket_type:
                    break

            # 매핑되는 소켓 타입이 없으면 이 섹션 건너뜀
            if socket_type is None:
                continue

            try:
                out_sock = node.outputs.new(socket_type, socket_label)
                socket_count += 1
                if hash_val:
                    try:
                        out_sock["hash"] = str(hash_val)
                    except Exception:
                        pass
            except Exception:
                continue

        if socket_count == 0:
            tree.nodes.remove(node)
            continue

        node.location = (x, y)
        y += y_step + socket_count * y_socket_step
        created_count += 1

    op.report({"INFO"}, f"생성된 모드 노드 수: {created_count}")

    return


def _create_result_node(tree):
    node = tree.nodes.new("ResultNode")
    node.name = "Result"
    try:
        node.label = "Result"
    except Exception:
        pass
    node.location = (350, 0)


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
        _create_result_node(tree)
        return {"FINISHED"}


classes = (EVHB_OT_create_new_tree,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
