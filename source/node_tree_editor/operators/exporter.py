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
    context.scene.evbh_mod_path = base
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
                "asset_socket_name": getattr(asset_socket, "name", "") if asset_socket else "",
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
                        "mod_socket_name": getattr(mod_socket, "name", "") if mod_socket else "",
                        "mod_socket_hash": (mod_socket.get("hash", "") if mod_socket and hasattr(mod_socket, "get") else ""),
                        "asset_input_name": getattr(a_input, "name", ""),
                        "asset_input_hash": (a_input.get("hash", "") if hasattr(a_input, "get") else ""),
                    }
                    asset_entry["mods"].append(mod_info)

            entry["assets"].append(asset_entry)

        mappings.append(entry)

    return mappings


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
        mod_path = getattr(context.scene, "evbh_mod_path", "") or ""

        try:
            base = select_export_path(context, self.filepath)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        # 현재 노드트리 얻기
        tree = getattr(context.space_data, "node_tree", None)

        mappings = collect_result_mappings(tree)
        # import pprint
        # pprint.pprint(mappings)


        
        # 1. 선택한 내보내기 경로에 폴더 생성 (폴더명은 eomd_path의 폴더명과 일치)
        
        
        # 2. 생성된 폴더에 ini 파일 생성 (파일명은 폴더명과 일치)
        

        return {"FINISHED"}


classes = (EVHB_OT_export_mod,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
