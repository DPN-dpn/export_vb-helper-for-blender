import bpy
from bpy.types import Operator


class EVBH_OT_auto_link(Operator):
    bl_idname = "evbh.auto_link"
    bl_label = "자동 연결"
    bl_description = "노드 트리를 자동으로 연결합니다"

    def execute(self, context):
        node_tree = (
            getattr(context.space_data, "node_tree", None)
            or getattr(context.area, "spaces", None)
            and getattr(context.area.spaces.active, "node_tree", None)
        )
        if node_tree is None:
            self.report({"WARNING"}, "No node tree open")
            return {"CANCELLED"}

        # 노드 분류
        asset_nodes = [
            n
            for n in node_tree.nodes
            if getattr(n.__class__, "bl_idname", "") == "AssetSlotNode"
        ]
        mod_nodes = [
            n
            for n in node_tree.nodes
            if getattr(n.__class__, "bl_idname", "") == "ModFileNode"
        ]
        result_node = next(
            (
                n
                for n in node_tree.nodes
                if getattr(n.__class__, "bl_idname", "") == "ResultNode"
            ),
            None,
        )

        links_created = 0
        assets_with_links = set()

        # 인덱스화된 모드 출력 소켓 풀 (node, socket)
        mod_out_sockets = []
        for m in mod_nodes:
            for out in m.outputs:
                mod_out_sockets.append(
                    (
                        m,
                        out,
                        getattr(out.__class__, "bl_idname", ""),
                        out.get("hash", None),
                    )
                )

        # 자산 노드의 입력 소켓을 모드 출력과 매칭하여 연결
        for a in asset_nodes:
            asset_had_link = False
            for inp in list(a.inputs):
                inp_type = getattr(inp.__class__, "bl_idname", "")
                inp_hash = inp.get("hash", None)
                if inp_hash is None:
                    continue
                if inp.is_linked:
                    continue
                for m_node, out_sock, out_type, out_hash in mod_out_sockets:
                    if out_hash is None:
                        continue
                    if inp_type != out_type:
                        continue
                    if str(inp_hash) != str(out_hash):
                        continue
                    # 이미 동일 소켓에 같은 링크가 있지 않은지 확인
                    already = any(
                        l.from_socket == out_sock and l.to_socket == inp
                        for l in node_tree.links
                    )
                    if already:
                        continue
                    try:
                        node_tree.links.new(out_sock, inp)
                        links_created += 1
                        asset_had_link = True
                    except Exception:
                        pass
                    # 한 입력에 대해 하나만 연결
                    break

            if asset_had_link:
                assets_with_links.add(a)

        # ResultNode에 연결 (각 자산에 대해 Result 출력 -> ResultNode의 비어있는 입력)
        if result_node:
            for a in assets_with_links:
                # 자산의 Result 출력 찾기
                out_sock = next(
                    (
                        s
                        for s in a.outputs
                        if getattr(s.__class__, "bl_idname", "") == "ResultSocket"
                    ),
                    None,
                )
                if out_sock is None:
                    continue
                # 빈 입력 찾기 또는 새로 생성
                target_in = next(
                    (s for s in result_node.inputs if not s.is_linked), None
                )
                if target_in is None:
                    try:
                        target_in = result_node.inputs.new(
                            "ResultSocket", f"Data {len(result_node.inputs) + 1}"
                        )
                    except Exception:
                        continue
                # 중복 링크 방지
                already = any(
                    l.from_socket == out_sock and l.to_socket == target_in
                    for l in node_tree.links
                )
                if already:
                    continue
                try:
                    node_tree.links.new(out_sock, target_in)
                except Exception:
                    pass

        self.report(
            {"INFO"},
            f"링크 생성: {links_created}, 결과 노드에 연결된 자산: {len(assets_with_links)}",
        )
        return {"FINISHED"}


class EVBH_OT_unlink(Operator):
    bl_idname = "evbh.unlink"
    bl_label = "링크 해제"
    bl_description = "노드 트리의 모든 링크를 해제합니다"

    def execute(self, context):
        node_tree = (
            getattr(context.space_data, "node_tree", None)
            or getattr(context.area, "spaces", None)
            and getattr(context.area.spaces.active, "node_tree", None)
        )
        if node_tree is None:
            self.report({"WARNING"}, "No node tree open")
            return {"CANCELLED"}

        links_removed = len(node_tree.links)
        node_tree.links.clear()

        self.report({"INFO"}, f"링크 해제: {links_removed}개 링크가 제거되었습니다")
        return {"FINISHED"}


classes = (EVBH_OT_auto_link, EVBH_OT_unlink)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
