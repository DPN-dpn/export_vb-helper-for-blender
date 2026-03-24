import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
import os
import shutil


def select_export_path(context, path: str) -> str:
    chosen = os.path.expanduser(path or "")
    if os.path.isfile(chosen):
        base = os.path.dirname(chosen)
    else:
        base = chosen
    if not base or not os.path.isdir(base):
        raise ValueError(f"유효하지 않은 폴더입니다: {base}")
    # 선택은 내보내기 대상 폴더를 지정하므로 evbh_export_path에 저장
    context.scene.evbh_export_path = base
    return base


def collect_result_mappings(node_tree):
    """
    수집된 매핑 정보:
    [{'assets': [{'asset_node_name': 'Body',
                'asset_node_type': 'AssetSlotNode',
                'asset_socket_name': 'Result',
                'mods': [{'asset_input_hash': 'f84d5a49',
                            'asset_input_name': 'Position',
                            'mod_node_name': 'AriaDevil.ini',
                            'mod_node_type': 'ModFileNode',
                            'mod_socket_hash': '56eaff1c',
                            'mod_socket_name': 'AriaDevilBodyPosition.buf',
                            'mod_socket_type': 'INI_PositionSocket'},
                        {'asset_input_hash': 'c6bb960b',
                            'asset_input_name': 'IB_A',
                            'mod_node_name': 'AriaDevil.ini',
                            'mod_node_type': 'ModFileNode',
                            'mod_socket_hash': 'c6bb960b',
                            'mod_socket_name': 'AriaDevilBodyA.ib',
                            'mod_socket_type': 'INI_IBSocket'},
                        {'asset_input_hash': 'a55f187e',
                            'asset_input_name': 'IB_A_Diffuse',
                            'mod_node_name': 'AriaDevil.ini',
                            'mod_node_type': 'ModFileNode',
                            'mod_socket_hash': 'c6bb960b',
                            'mod_socket_name': 'AriaDevilBodyADiffuse.dds',
                            'mod_socket_type': 'INI_TextureSocket'},
    'input_index': 0,
    'input_name': 'Data 1'},
    """
    if node_tree is None:
        return []

    # ResultNode 찾기
    result_node = next(
        (n for n in node_tree.nodes if getattr(n, "bl_idname", "") == "ResultNode"),
        None,
    )
    if result_node is None:
        return []

    mappings = []
    for idx, input_sock in enumerate(result_node.inputs):
        # 각 Result 입력마다 여러 링크(여러 Asset이 올 수 있음)를 허용
        input_links = list(getattr(input_sock, "links", []))
        if not input_links:
            continue

        entry = {
            "input_index": idx,
            "input_name": getattr(input_sock, "name", ""),
            "assets": [],
        }

        for link in input_links:
            asset_node = getattr(link, "from_node", None)
            asset_socket = getattr(link, "from_socket", None)
            if asset_node is None:
                continue

            asset_entry = {
                "asset_node_name": getattr(asset_node, "name", ""),
                "asset_node_type": getattr(asset_node, "bl_idname", ""),
                "asset_socket_name": (
                    getattr(asset_socket, "name", "") if asset_socket else ""
                ),
                "mods": [],
            }

            # AssetSlotNode의 각 입력 소켓(Asset이 받는 각 슬롯)에 연결된 링크들을 검사
            for a_input in getattr(asset_node, "inputs", []):
                for link2 in list(getattr(a_input, "links", [])):
                    mod_node = getattr(link2, "from_node", None)
                    mod_socket = getattr(link2, "from_socket", None)
                    if mod_node is None:
                        continue
                    mod_info = {
                        "mod_node_name": getattr(mod_node, "name", ""),
                        "mod_node_type": getattr(mod_node, "bl_idname", ""),
                        "mod_socket_name": (
                            getattr(mod_socket, "name", "") if mod_socket else ""
                        ),
                        "mod_socket_type": (
                            getattr(getattr(mod_socket, "__class__", None), "bl_idname", "") if mod_socket else ""
                        ),
                        "mod_socket_hash": (
                            mod_socket.get("hash", "")
                            if mod_socket and hasattr(mod_socket, "get")
                            else ""
                        ),
                        "asset_input_name": getattr(a_input, "name", ""),
                        "asset_input_hash": (
                            a_input.get("hash", "") if hasattr(a_input, "get") else ""
                        ),
                    }
                    asset_entry["mods"].append(mod_info)

            entry["assets"].append(asset_entry)

        mappings.append(entry)

    return mappings


def group_mods_needed(mappings):
    """mappings에서 mod_node_name -> set(mod_socket_name) 형태로 그룹화해서 반환"""
    mods_needed = {}
    for entry in mappings:
        for asset in entry.get("assets", []):
            for mod in asset.get("mods", []):
                name = mod.get("mod_node_name", "")
                sock = mod.get("mod_socket_name", "")
                if not name:
                    continue
                mods_needed.setdefault(name, set()).add(sock)
    return mods_needed


def _parse_sections(text):
    """텍스트 블록을 섹션 단위로 파싱: (order, {name: lines}) 반환"""
    lines = [l.body for l in text.lines]
    sections = {}
    order = []
    cur_name = None
    cur_lines = []
    for ln in lines:
        s = ln.rstrip("\n\r")
        if s.strip().startswith("[") and s.strip().endswith("]"):
            if cur_name is not None:
                sections[cur_name] = cur_lines
            cur_name = s.strip()[1:-1]
            order.append(cur_name)
            cur_lines = [s + "\n"]
        else:
            if cur_name is None:
                cur_lines.append(s + "\n")
            else:
                cur_lines.append(s + "\n")
    if cur_name is not None:
        sections[cur_name] = cur_lines
    return order, sections


def process_mods(op, export_parent, source_mod_path, mods_needed):
    """mods_needed를 처리: INI 생성, 파일 복사. report_fn(msg_type, msg) 호출 가능.
    반환: (written_inis, copied_files)
    """
    written_inis = []
    copied_files = []

    export_folder_name = (
        os.path.basename(os.path.normpath(source_mod_path)) or "exported_mod"
    )
    export_dir = os.path.join(export_parent, export_folder_name)
    os.makedirs(export_dir, exist_ok=True)

    for mod_name, sockets in mods_needed.items():
        text = bpy.data.texts.get(mod_name)
        if text is None:
            text = bpy.data.texts.get(mod_name.replace("\\", "/"))
        if text is None:
            op.report({"WARNING"}, f"텍스트 데이터 블록을 찾지 못함: {mod_name}")
            continue

        order, sections = _parse_sections(text)

        initial = set()
        for sec_name, sec_lines in sections.items():
            joined = "".join(sec_lines)
            for sname in sockets:
                if sname and sname in joined:
                    initial.add(sec_name)

        found = set(initial)
        changed = True
        while changed:
            changed = False
            for sec_name, sec_lines in sections.items():
                if sec_name in found:
                    continue
                joined = "".join(sec_lines)
                if any(ref in joined for ref in found):
                    found.add(sec_name)
                    changed = True

        if not found:
            op.report({"INFO"}, f"모드 {mod_name}에서 참조된 섹션을 찾지 못함")

        out_lines = []
        for nm in order:
            if nm in found:
                out_lines.extend(sections.get(nm, []))

        dest_ini_path = os.path.join(export_dir, mod_name)
        dest_ini_dir = os.path.dirname(dest_ini_path)
        if dest_ini_dir:
            os.makedirs(dest_ini_dir, exist_ok=True)
        try:
            with open(dest_ini_path, "w", encoding="utf-8") as f:
                f.writelines(out_lines)
            written_inis.append(dest_ini_path)
        except Exception as e:
            op.report({"WARNING"}, f"INI 파일 쓰기 실패: {dest_ini_path} ({e})")

        mod_full = os.path.normpath(os.path.join(source_mod_path, mod_name))
        mod_dir = os.path.dirname(mod_full)
        for sock in sockets:
            if not sock:
                continue
            src = os.path.normpath(os.path.join(mod_dir, sock))
            if not os.path.isfile(src):
                if os.path.isabs(sock) and os.path.isfile(sock):
                    src = sock
                else:
                    op.report({"WARNING"}, f"복사할 파일을 찾지 못함: {src}")
                    continue
            try:
                rel = os.path.relpath(src, source_mod_path)
            except Exception:
                rel = os.path.basename(src)
            dst = os.path.normpath(os.path.join(export_dir, rel))
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            try:
                shutil.copy2(src, dst)
                copied_files.append(dst)
            except Exception as e:
                op.report({"WARNING"}, f"파일 복사 실패: {src} -> {dst} ({e})")

    op.report(
        {"INFO"}, f"INI 생성: {len(written_inis)} 파일, 복사: {len(copied_files)} 파일"
    )
    return


def _perform_file_copies(op, export_dir, occurrences):
    """각 소켓별로 파일을 복사하고 INI 치환 목록을 생성하여 반환한다.
    반환: (copied_files, rename_map, ini_replacements, originals_to_delete)
    """
    rename_map = {}
    copied_files = []
    ini_replacements = {}
    originals_to_delete = set()

    for occ in occurrences:
        mod_name = occ.get("mod_name")
        orig = occ.get("orig")
        orig_base = occ.get("orig_base")
        desired_new = occ.get("new_base")

        expected_src = os.path.normpath(os.path.join(export_dir, os.path.dirname(mod_name), orig))
        if not os.path.exists(expected_src):
            found = None
            for root, dirs, files in os.walk(export_dir):
                if orig_base in files:
                    found = os.path.join(root, orig_base)
                    break
            if found:
                expected_src = found
            else:
                op.report({"WARNING"}, f"복사할 원본 파일을 찾지 못함: {orig} (mod: {mod_name})")
                continue

        dst_dir = os.path.dirname(expected_src)
        originals_to_delete.add(expected_src)
        dst = os.path.join(dst_dir, desired_new)
        if os.path.exists(dst):
            base, ext = os.path.splitext(desired_new)
            i = 1
            while True:
                candidate = f"{base}_{i}{ext}"
                dst = os.path.join(dst_dir, candidate)
                if not os.path.exists(dst):
                    desired_new = candidate
                    break
                i += 1

        try:
            shutil.copy2(expected_src, dst)
            copied_files.append(dst)
            rel_src = os.path.relpath(expected_src, export_dir).replace("\\", "/")
            rel_dst = os.path.relpath(dst, export_dir).replace("\\", "/")
            rename_map.setdefault(rel_src, []).append(rel_dst)
        except Exception as e:
            op.report({"WARNING"}, f"소켓별 파일 복사 실패: {expected_src} -> {dst} ({e})")
            continue

        ini_path = os.path.normpath(os.path.join(export_dir, mod_name))
        ini_replacements.setdefault(ini_path, []).append((orig_base, desired_new))

    return copied_files, rename_map, ini_replacements, originals_to_delete


def _perform_ini_replacements(op, ini_replacements):
    """INI 파일들에 대해 순차적 치환을 수행한다."""
    for ini_path, repls in ini_replacements.items():
        if not os.path.exists(ini_path):
            continue
        try:
            with open(ini_path, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception:
            continue

        for orig_base, new_base in repls:
            idx = data.find(orig_base)
            if idx == -1:
                continue
            data = data[:idx] + data[idx:].replace(orig_base, new_base, 1)

        try:
            with open(ini_path, "w", encoding="utf-8") as f:
                f.write(data)
        except Exception as e:
            op.report({"WARNING"}, f"INI 파일 쓰기 실패: {ini_path} ({e})")



def replace_strings(op, mappings):
    # 내보내기로 복사된 파일에서 매핑 정보를 바탕으로 문자열교체함
    # {evbh_asset_path의 폴더명}{asset_node_name}{asset_input_name(mod_socket_type이 INI_IBSocket일 경우 _로 분리한 뒷 문자(예: IB_A가 원문이면 A), INI_TextureSocket일 경우 _로 분리한 뒷 문자들 연결(예: IB_A_Diffuse가 원문이면 ADiffuse), 둘 다 아니면 그냥 asset_input_name)}
    # evbh_asset_path는 파일경로이므로 파일명이 아닌 폴더명으로 하는 것에 주의
    # 이후 문자열 교체 과정은 문자열의 의도치 않은 중복을 방지하기 위해 원문->임시토큰->최종문자열 순으로 교체
    
    
    # 1. 실제 파일의 문자열 교체하기
    # 기존 네이밍 규칙에 확장자 추가 {확장자(mod_socket_type이 INI_IBSocket일 경우 .ib, INI_PositionSocket/INI_BlendSocket/INI_TexcoordSocket일 경우 .buf, INI_TextureSocket일 경우 원래 확장자 그대로)}
    
    # 2. ini 내용의 문자열 교체하기
    # 1에서 변경한 문자열로 ini 내용에 있는 파일명 문자열 교체
    
    scene = bpy.context.scene
    export_parent = getattr(scene, "evbh_export_path", "") or ""
    source_mod_path = getattr(scene, "evbh_mod_path", "") or ""
    asset_path = getattr(scene, "evbh_asset_path", "") or ""

    if not export_parent or not source_mod_path:
        op.report({"WARNING"}, "내보내기 또는 소스 모드 경로가 설정되지 않음 - 문자열 교체 건너뜀")
        return

    export_dir = os.path.join(export_parent, os.path.basename(os.path.normpath(source_mod_path)))
    if not os.path.isdir(export_dir):
        op.report({"WARNING"}, f"내보내기 폴더를 찾을 수 없음: {export_dir}")
        return

    # 에셋 폴더명
    asset_folder = os.path.basename(os.path.dirname(asset_path)) if asset_path else ""

    # 수집된 매핑을 바탕으로 각 소켓별로 복사할 파일 목록(복사 대상, 복사될 새 이름, INI 파일)을 생성
    occurrences = []
    for entry in mappings:
        for asset in entry.get("assets", []):
            asset_node_name = asset.get("asset_node_name", "")
            for mod in asset.get("mods", []):
                orig = mod.get("mod_socket_name", "")
                if not orig:
                    continue
                mod_node_name = mod.get("mod_node_name", "")
                in_name = mod.get("asset_input_name", "")
                sock_type = mod.get("mod_socket_type", "")

                parts = (in_name or "").split("_") if in_name else []
                if sock_type == "INI_IBSocket":
                    tail = parts[-1] if parts else in_name
                elif sock_type == "INI_TextureSocket":
                    tail = "".join(parts[1:]) if len(parts) > 1 else in_name
                else:
                    tail = in_name

                orig_base = os.path.basename(orig)
                orig_ext = os.path.splitext(orig_base)[1]
                if sock_type == "INI_IBSocket":
                    ext = ".ib"
                elif sock_type in ("INI_PositionSocket", "INI_BlendSocket", "INI_TexcoordSocket"):
                    ext = ".buf"
                elif sock_type == "INI_TextureSocket":
                    ext = orig_ext or ""
                else:
                    ext = orig_ext or ""

                new_base = f"{asset_folder}{asset_node_name}{tail}{ext}"

                occurrences.append(
                    {
                        "mod_name": mod_node_name,
                        "orig": orig,
                        "orig_base": orig_base,
                        "new_base": new_base,
                    }
                )

    # 실제 파일 복사/이름 변경 수행
    copied_files, rename_map, ini_replacements, originals_to_delete = _perform_file_copies(op, export_dir, occurrences)

    # INI 파일들에 대해 치환 수행
    _perform_ini_replacements(op, ini_replacements)

    # 모든 복사 및 INI 치환이 끝난 뒤 원본 파일 삭제
    deleted_count = 0
    if 'originals_to_delete' in locals():
        for orig_path in list(originals_to_delete):
            try:
                if os.path.exists(orig_path):
                    os.remove(orig_path)
                    deleted_count += 1
                else:
                    # 파일이 이미 이동/삭제된 경우 무시
                    pass
            except Exception as e:
                op.report({"WARNING"}, f"원본 파일 삭제 실패: {orig_path} ({e})")

    op.report({"INFO"}, f"문자열 교체 완료: 생성된 복사본 {len(copied_files)}개")
    return


class EVHB_OT_export_mod(Operator, ImportHelper):
    bl_idname = "evhb.export_mod"
    bl_label = "내보내기"
    bl_description = "사전작업을 적용한 모드를 내보냅니다"

    filename_ext = ""
    filter_glob: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        # source mod 폴더와 내보내기 대상 폴더
        source_mod_path = getattr(context.scene, "evbh_mod_path", "") or ""

        try:
            export_parent = select_export_path(context, self.filepath)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        if not source_mod_path or not os.path.isdir(source_mod_path):
            self.report({"ERROR"}, "Source mod 폴더(evbh_mod_path)가 유효하지 않습니다")
            return {"CANCELLED"}

        # 현재 노드트리 얻기
        tree = getattr(context.space_data, "node_tree", None)
        mappings = collect_result_mappings(tree)

        import pprint
        self.report({"INFO"}, f"수집된 매핑 정보:\n{pprint.pformat(mappings)}")

        # 그룹화
        mods_needed = group_mods_needed(mappings)

        # 실제 처리
        process_mods(self, export_parent, source_mod_path, mods_needed)

        # 문자열 교체
        replace_strings(self, mappings)

        return {"FINISHED"}


classes = (EVHB_OT_export_mod,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
