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
    node_tree: bpy.types.NodeTree
    반환 형식:
    [
      {
        "input_index": 0,
        "input_name": "Data 1",
        "assets": [
          {
            "asset_node_name": "AssetNode",
            "asset_node_type": "AssetSlotNode",
            "asset_socket_name": "Result",
            "mods": [
              {
                "mod_node_name": "mod.ini.txt",
                "mod_node_type": "ModFileNode",
                "mod_socket_name": "Texture",
                "mod_socket_hash": "abcd1234",
                "asset_input_name": "Position",
                "asset_input_hash": "hash-if-any"
              }, ...
            ]
          }, ...
        ]
      }, ...
    ]
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

        # 그룹화
        mods_needed = group_mods_needed(mappings)

        # 실제 처리
        process_mods(self, export_parent, source_mod_path, mods_needed)

        return {"FINISHED"}


classes = (EVHB_OT_export_mod,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
