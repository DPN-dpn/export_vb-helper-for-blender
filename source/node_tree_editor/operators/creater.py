import bpy
from bpy.types import Operator
from bpy.props import StringProperty
import json
import re
from ...data import text_data_block
from ...core import properties as prep_properties
from .functions.ini_parser import parse_ini


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
            node = tree.nodes.new("EVBH_AssetSlotNode")
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
                    "EVBH_PositionSocket"
                    if key == "position_vb"
                    else (
                        "EVBH_BlendSocket"
                        if key == "blend_vb"
                        else "EVBH_TexcoordSocket"
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
                sock = node.inputs.new("EVBH_IBSocket", socket_name)
                socket_count += 1
                ib_hint = comp.get("ib", "")
                if ib_hint is None:
                    ib_hint = ""
                try:
                    sock["hash"] = str(ib_hint)
                except Exception:
                    pass

            socket_count += _create_asset_texture_sockets(node, comp)

            node.location = (x, y)
            y += y_step + socket_count * y_socket_step
            created_count += 1

    op.report({"INFO"}, f"생성된 에셋 노드 수: {created_count}")


def _create_asset_texture_sockets(node, comp):
    texture_count = 0

    classifications = comp.get("object_classifications", []) or []
    texture_hashes = comp.get("texture_hashes", []) or []

    try:
        show_tex = getattr(bpy.context.scene, "evbh_show_texture_sockets", True)
    except Exception:
        show_tex = True
    key = "_evbh_saved_texture_sockets"

    for idx, classification in enumerate(classifications):
        try:
            textures = texture_hashes[idx] or []
        except Exception:
            textures = []

        for tex in textures:
            if not tex:
                continue

            # 기대형태: [name, ext, hash] 또는 dict
            if isinstance(tex, (list, tuple)) and len(tex) >= 3:
                tex_name = str(tex[0])
                hv = tex[2]
            elif isinstance(tex, dict):
                tex_name = tex.get("name") or tex.get("type") or "Texture"
                hv = tex.get("hash")
            else:
                continue

            socket_label = f"IB_{classification}_{tex_name}"

            if not show_tex:
                try:
                    saved = list(node.get(key, []))
                except Exception:
                    saved = []
                saved.append(
                    {
                        "is_output": False,
                        "name": socket_label,
                        "hash": str(hv) if hv else None,
                    }
                )
                node[key] = saved
                continue

            in_sock = node.inputs.new("EVBH_TextureSocket", socket_label)
            texture_count += 1
            if hv:
                in_sock["hash"] = str(hv)

    return texture_count


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

        # 섹션 파싱: parse_ini 사용
        order, sections = parse_ini(content)

        # ini 파일 하나당 노드 하나 생성
        node = tree.nodes.new("EVBH_ModFileNode")
        node.name = text_name
        try:
            node.label = text_name
        except Exception:
            pass

        socket_count = 0

        def _find_hash_recursive(start_sec, visited=None):
            if visited is None:
                visited = set()
            if start_sec in visited:
                return None
            visited.add(start_sec)

            lines0 = sections.get(start_sec, []) or []
            # 직접 hash가 있는지 확인
            for ln_h in lines0:
                m2 = re.match(r"^\s*hash\s*=\s*(.+)$", ln_h, re.IGNORECASE)
                if m2:
                    hv = m2.group(1).strip()
                    hv = re.split(r";|#", hv)[0].strip().strip('"')
                    if hv:
                        return hv

            # CommandList 계열 섹션인 경우, 이 섹션을 run = <start_sec>로 호출하는 섹션을 찾아 재귀
            if start_sec.lower().startswith("commandlist"):
                for other_n, other_ls in sections.items():
                    if other_n == start_sec:
                        continue
                    for ln_r in other_ls:
                        mm = re.match(r"^(?P<k>[^=]+)=\s*(?P<v>.+)$", ln_r)
                        if not mm:
                            continue
                        k_r = mm.group("k").strip().lower()
                        v_r = mm.group("v").strip()
                        v_clean_r = re.split(r";|#", v_r)[0].strip().strip('"')
                        if k_r == "run" and v_clean_r == start_sec:
                            hv2 = _find_hash_recursive(other_n, visited)
                            if hv2:
                                return hv2
            return None

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
                        if k == "ib":
                            socket_type = "EVBH_IBSocket"
                        elif k == "vb2":
                            socket_type = "EVBH_BlendSocket"
                        elif k == "vb0":
                            socket_type = "EVBH_PositionSocket"
                        elif k == "vb1":
                            socket_type = "EVBH_TexcoordSocket"

                        if socket_type:
                            # 참조 섹션(other_name)에서 직접 hash를 찾고,
                            # 없고 CommandList 계열이면 run=... 참조로 거슬러 올라가서 찾음
                            hash_val = _find_hash_recursive(other_name)
                        break
                if socket_type:
                    break

            if socket_type is None:
                continue

            out_sock = node.outputs.new(socket_type, socket_label)
            socket_count += 1
            if hash_val:
                out_sock["hash"] = str(hash_val)

        # 모드 노드에 모드 텍스처 소켓 추가
        socket_count += _create_mod_texture_sockets(node, sections)

        if socket_count == 0:
            tree.nodes.remove(node)
            continue

        node.location = (x, y)
        y += y_step + socket_count * y_socket_step
        created_count += 1

    op.report({"INFO"}, f"생성된 모드 노드 수: {created_count}")


def _create_mod_texture_sockets(node, sections):
    texture_count = 0

    for sec_name, lines in sections.items():
        # Resource로 시작하는 섹션을 대상으로 함 (대소문자 무시)
        if not sec_name.lower().startswith("resource"):
            continue

        # type= 또는 format= 구문이 있으면 건너뜀
        has_type = any(re.match(r"^\s*type\s*=", ln, re.IGNORECASE) for ln in lines)
        has_format = any(re.match(r"^\s*format\s*=", ln, re.IGNORECASE) for ln in lines)
        if has_type or has_format:
            continue

        # 섹션 내부에서 filename, type 를 찾음
        filename = None
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

        # 텍스처 확장자 조건
        if not (filename and filename.lower().endswith((".dds", ".jpg", ".png"))):
            continue

        # 소켓 라벨은 filename 이나 섹션 이름
        socket_label = filename or sec_name

        # 다른 섹션의 key=value에서 현재 섹션명을 값으로 사용하는지 검사하여
        # 참조 섹션의 hash 값을 가져옴
        hash_val = None
        for other_name, other_lines in sections.items():
            if other_name == sec_name:
                continue
            for ln in other_lines:
                m = re.match(r"^(?P<k>[^=]+)=\s*(?:ref\s*)?(?P<v>.+)$", ln)
                if not m:
                    continue
                k = m.group("k").strip().lower()
                v = m.group("v").strip()
                v_clean = re.split(r";|#", v)[0].strip().strip('"')
                if v_clean == sec_name:
                    # 참조 섹션에서 hash 값 추출
                    for ln2 in other_lines:
                        m2 = re.match(r"^\s*hash\s*=\s*(.+)$", ln2, re.IGNORECASE)
                        if m2:
                            hv = m2.group(1).strip()
                            hv = re.split(r";|#", hv)[0].strip().strip('"')
                            hash_val = hv
                            break
                    break

        # 텍스처 소켓 토글 처리
        try:
            show_tex = getattr(bpy.context.scene, "evbh_show_texture_sockets", True)
        except Exception:
            show_tex = True
        key = "_evbh_saved_texture_sockets"
        if not show_tex:
            try:
                saved = list(node.get(key, []))
            except Exception:
                saved = []
            saved.append(
                {
                    "is_output": True,
                    "name": socket_label,
                    "hash": str(hash_val) if hash_val else None,
                }
            )
            node[key] = saved
            continue

        # 소켓 생성
        out_sock = node.outputs.new("EVBH_TextureSocket", socket_label)
        texture_count += 1
        if hash_val:
            out_sock["hash"] = str(hash_val)

    return texture_count


def _create_result_node(tree):
    node = tree.nodes.new("EVBH_ResultNode")
    node.name = "Result"
    try:
        node.label = "Result"
    except Exception:
        pass
    node.location = (330, 0)


class EVBH_OT_create_new_tree(Operator):
    bl_idname = "evbh.create_new_tree"
    bl_label = "슬롯 매칭 시작하기"
    bl_description = "불러온 에셋/모드 파일로 슬롯 매칭을 시작합니다"

    name: StringProperty(name="Name", default="EVBH Graph")

    def execute(self, context):
        # 먼저 현재 화면에서 열려있는 EVBH_NodeTree 인스턴스들을 언링크하고 데이터블록에서 제거합니다.
        opened_groups = set()
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type != "NODE_EDITOR":
                    continue
                for space in area.spaces:
                    if getattr(space, "type", None) != "NODE_EDITOR":
                        continue
                    ng = getattr(space, "node_tree", None)
                    if ng is None:
                        continue
                    opened_groups.add(ng)
                    space.node_tree = None

        # 또한 context.area가 NODE_EDITOR이면 active도 언링크
        if context.area and context.area.type == "NODE_EDITOR":
            context.area.spaces.active.node_tree = None

        # 수집된 그룹을 데이터블록에서 제거
        for ng in list(opened_groups):
            if ng.name in bpy.data.node_groups:
                bpy.data.node_groups.remove(ng)

        # 노드트리 생성
        tree = bpy.data.node_groups.new(self.name, "EVBH_NodeTree")

        scene = context.scene
        scene.evbh_current_asset_path = getattr(scene, "evbh_asset_path", "") or ""
        scene.evbh_current_mod_path = getattr(scene, "evbh_mod_path", "") or ""

        # 현재 화면의 첫 번째 NODE_EDITOR 공간을 찾아 새 노드트리를 엽니다.
        space = _find_first_node_editor_space(context)
        if space is not None:
            space.node_tree = tree

        # 현재 활성 영역이 NODE_EDITOR이면 컨텍스트의 space_data도 업데이트
        if context.area and context.area.type == "NODE_EDITOR":
            context.area.spaces.active.node_tree = tree
        self.report({"INFO"}, f"노드 트리 생성: {tree.name}")

        # 노드 생성
        _create_asset_nodes(self, tree)
        _create_mod_nodes(self, tree)
        _create_result_node(tree)

        # 텍스처 토글 상태에 따라 텍스처 소켓 생성/제거
        if not getattr(bpy.context.scene, "evbh_show_texture_sockets", True):
            prep_properties.apply_texture_sockets_toggle(False)

        return {"FINISHED"}


classes = (EVBH_OT_create_new_tree,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
