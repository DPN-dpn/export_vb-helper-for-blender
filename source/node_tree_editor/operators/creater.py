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
    y_socket_step = -22
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
            name = comp.get("component_name", "")
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
                    sock["classification"] = str(c)
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
            in_sock["classification"] = str(classification)

    return texture_count


def _create_mod_nodes(op, tree):
    mod_blocks = getattr(text_data_block, "_mod_text_blocks", set())

    x = -350
    y = 0
    y_step = -80
    y_socket_step = -22
    created_count = 0

    # 에셋(hash.json) 데이터를 미리 수집하여 해시값 보정에 사용
    asset_blocks = getattr(text_data_block, "_asset_text_blocks", set())
    all_components = []
    for t_name in list(asset_blocks):
        t = bpy.data.texts.get(t_name)
        if not t: continue
        try:
            content = "\n".join([ln.body for ln in t.lines])
        except Exception:
            content = t.as_string() if hasattr(t, "as_string") else ""
        try:
            data = json.loads(content)
            if isinstance(data, list):
                all_components.extend(data)
        except Exception:
            pass

    def _resolve_real_hash(found_hash, target_key, match_first_index=None):
        if not found_hash or not target_key:
            return found_hash, None
            
        search_keys = ["position_vb", "blend_vb", "texcoord_vb", "ib", "draw_vb"]
        for comp in all_components:
            for k in search_keys:
                if comp.get(k) == found_hash:
                    # 발견된 컴포넌트에서 우리가 원하는 종류의 해시값을 반환
                    res = comp.get(target_key)
                    res_hash = str(res) if res else found_hash
                    
                    classification = None
                    idx_pos = 0
                    if match_first_index is not None:
                        try:
                            mfi_val = int(match_first_index)
                            idxs = comp.get("object_indexes", [])
                            clsfs = comp.get("object_classifications", [])
                            if mfi_val in idxs:
                                idx_pos = idxs.index(mfi_val)
                                if idx_pos < len(clsfs):
                                    classification = clsfs[idx_pos]
                        except ValueError:
                            pass
                            
                    # target_key가 텍스처 타입인 경우 texture_hashes 참조
                    if target_key not in search_keys:
                        tex_hashes = comp.get("texture_hashes", [])
                        if idx_pos < len(tex_hashes):
                            textures = tex_hashes[idx_pos]
                            if textures:
                                for tex in textures:
                                    if isinstance(tex, (list, tuple)) and len(tex) >= 3:
                                        if str(tex[0]).lower() == target_key.lower():
                                            return str(tex[2]), classification
                                    elif isinstance(tex, dict):
                                        tex_name = tex.get("name") or tex.get("type")
                                        if tex_name and str(tex_name).lower() == target_key.lower():
                                            return str(tex.get("hash")), classification
                        # 텍스처를 못 찾은 경우 기본값
                        return found_hash, classification
                        
                    return res_hash, classification
        return found_hash, None

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

        def _find_all_hashes_recursive(start_sec, visited=None):
            if visited is None:
                visited = set()
            if start_sec in visited:
                return []
            visited.add(start_sec)
            
            results = []
            lines0 = sections.get(start_sec, []) or []
            
            for ln_h in lines0:
                m2 = re.match(r"^\s*hash\s*=\s*(.+)$", ln_h, re.IGNORECASE)
                if m2:
                    hv = m2.group(1).strip()
                    hv = re.split(r";|#", hv)[0].strip().strip('"')
                    if hv:
                        results.append(hv)
                        
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
                            res = _find_all_hashes_recursive(other_n, visited)
                            results.extend(res)
            return results

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
            target_key = None
            classification = None
            for other_name, other_lines in sections.items():
                if other_name == sec_name:
                    continue
                
                mfi = None
                for ln in other_lines:
                    m2 = re.match(r"^(?P<k>[^=]+)=(?P<v>.+)$", ln)
                    if m2 and m2.group("k").strip().lower() == "match_first_index":
                        mfi = m2.group("v").strip().split(";")[0].split("#")[0].strip()
                        break
                        
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
                            target_key = "ib"
                        elif k == "vb2":
                            socket_type = "EVBH_BlendSocket"
                            target_key = "blend_vb"
                        elif k == "vb0":
                            socket_type = "EVBH_PositionSocket"
                            target_key = "position_vb"
                        elif k == "vb1":
                            socket_type = "EVBH_TexcoordSocket"
                            target_key = "texcoord_vb"

                        if socket_type:
                            # 참조 섹션(other_name)에서 직접 hash를 찾고,
                            # 없고 CommandList 계열이면 run=... 참조로 거슬러 올라가서 찾음
                            section_hash = _find_hash_recursive(other_name)
                            if section_hash:
                                hash_val, classification = _resolve_real_hash(section_hash, target_key, mfi)
                            else:
                                hash_val = None
                        break
                if socket_type:
                    break

            if socket_type is None:
                continue

            out_sock = node.outputs.new(socket_type, socket_label)
            socket_count += 1
            if hash_val:
                out_sock["hash"] = str(hash_val)
            if classification:
                out_sock["classification"] = str(classification)

        # 모드 노드에 모드 텍스처 소켓 추가
        socket_count += _create_mod_texture_sockets(node, sections, _resolve_real_hash, _find_hash_recursive, _find_all_hashes_recursive)

        if socket_count == 0:
            tree.nodes.remove(node)
            continue

        node.location = (x, y)
        y += y_step + socket_count * y_socket_step
        created_count += 1

    op.report({"INFO"}, f"생성된 모드 노드 수: {created_count}")


def _create_mod_texture_sockets(node, sections, _resolve_real_hash, _find_hash_recursive, _find_all_hashes_recursive):
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
        classification = None
        classifications = set()
        all_hashes = set()
        
        # 이름이나 파일명에서 텍스처 타입 힌트 유추
        fallback_tex_type = None
        name_lower = sec_name.lower()
        if "diffuse" in name_lower: fallback_tex_type = "Diffuse"
        elif "normal" in name_lower: fallback_tex_type = "NormalMap"
        elif "light" in name_lower: fallback_tex_type = "LightMap"
        elif "material" in name_lower: fallback_tex_type = "MaterialMap"
        elif filename:
            fn_lower = filename.lower()
            if "diffuse" in fn_lower: fallback_tex_type = "Diffuse"
            elif "normal" in fn_lower: fallback_tex_type = "NormalMap"
            elif "light" in fn_lower: fallback_tex_type = "LightMap"
            elif "material" in fn_lower: fallback_tex_type = "MaterialMap"

        for other_name, other_lines in sections.items():
            if other_name == sec_name:
                continue
                
            # match_first_index 추출
            mfi = None
            for ln in other_lines:
                m2 = re.match(r"^(?P<k>[^=]+)=(?P<v>.+)$", ln)
                if m2 and m2.group("k").strip().lower() == "match_first_index":
                    mfi = m2.group("v").strip().split(";")[0].split("#")[0].strip()
                    break
                    
            for ln in other_lines:
                m = re.match(r"^(?P<k>[^=]+)=\s*(?:ref\s*)?(?P<v>.+)$", ln)
                if not m:
                    continue
                k = m.group("k").strip()
                v = m.group("v").strip()
                v_clean = re.split(r";|#", v)[0].strip().strip('"')
                
                if v_clean == sec_name:
                    k_lower = k.lower()
                    found_hash = None
                    found_cls = None
                    
                    # 1. this = ResourceA
                    if k_lower == "this":
                        for ln2 in other_lines:
                            m2 = re.match(r"^\s*hash\s*=\s*(.+)$", ln2, re.IGNORECASE)
                            if m2:
                                hv = m2.group(1).strip()
                                hv = re.split(r";|#", hv)[0].strip().strip('"')
                                found_hash = hv
                                _, found_cls = _resolve_real_hash(found_hash, "ib", mfi)
                                break
                        
                    # 2. Resource\...\Diffuse = ref ResourceA
                    elif k_lower.startswith("resource\\"):
                        parts = k.split("\\")
                        tex_type = parts[-1]  
                        
                        section_hashes = _find_all_hashes_recursive(other_name)
                        for section_hash in section_hashes:
                            h, cls = _resolve_real_hash(section_hash, tex_type, mfi)
                            if h:
                                if hash_val is None:
                                    hash_val = h
                                all_hashes.add(h)
                            if cls:
                                classifications.add(cls)
                        
                    # 3. ps-t3 = ResourceA
                    elif re.match(r"^ps-t\d+$", k_lower):
                        section_hashes = _find_all_hashes_recursive(other_name)
                        for section_hash in section_hashes:
                            h, cls = None, None
                            if fallback_tex_type:
                                h, cls = _resolve_real_hash(section_hash, fallback_tex_type, mfi)
                            else:
                                _, cls = _resolve_real_hash(section_hash, "ib", mfi)
                                h = section_hash
                            
                            if h:
                                if hash_val is None:
                                    hash_val = h
                                all_hashes.add(h)
                            if cls:
                                classifications.add(cls)
                                
                    if found_hash:
                        if hash_val is None:
                            hash_val = found_hash
                        all_hashes.add(found_hash)
                    if found_cls:
                        classifications.add(found_cls)
                    break
                    
        classification = None
        if len(classifications) == 1:
            classification = classifications.pop()

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
                    "all_hashes": ",".join(all_hashes) if all_hashes else None,
                }
            )
            node[key] = saved
            continue

        # 소켓 생성 (중복 방지)
        if socket_label in node.outputs:
            out_sock = node.outputs[socket_label]
        else:
            out_sock = node.outputs.new("EVBH_TextureSocket", socket_label)
            texture_count += 1
            
        if hash_val:
            out_sock["hash"] = str(hash_val)
        if all_hashes:
            out_sock["all_hashes"] = ",".join(all_hashes)
        if classification:
            out_sock["classification"] = str(classification)
        else:
            # If multiple classifications, we explicitly remove it so it links to all
            if "classification" in out_sock:
                del out_sock["classification"]

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
