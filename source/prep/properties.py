import bpy
from bpy.props import StringProperty, BoolProperty
from ..node_tree_editor.tree import EVBHNodeTree


def _prop_update(self, context):
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "NODE_EDITOR":
                area.tag_redraw()


def _toggle_texture_sockets(self, context):
    show = getattr(context.scene, "evbh_show_texture_sockets", True)
    apply_texture_sockets_toggle(show)


def apply_texture_sockets_toggle(show: bool):
    key = "_evbh_saved_texture_sockets"

    for ng in bpy.data.node_groups:
        if getattr(ng, "bl_idname", "") != EVBHNodeTree.bl_idname:
            continue
        for node in ng.nodes:
            if not show:
                saved = []
                for s in list(node.inputs):
                    if getattr(s.__class__, "bl_idname", "") == "INI_TextureSocket":
                        saved.append({"is_output": False, "name": s.name, "hash": s.get("hash", None)})
                        try:
                            node.inputs.remove(s)
                        except Exception:
                            pass
                for s in list(node.outputs):
                    if getattr(s.__class__, "bl_idname", "") == "INI_TextureSocket":
                        saved.append({"is_output": True, "name": s.name, "hash": s.get("hash", None)})
                        try:
                            node.outputs.remove(s)
                        except Exception:
                            pass
                if saved:
                    try:
                        node[key] = saved
                    except Exception:
                        pass
            else:
                if key in node:
                    saved = node[key]
                    for info in saved:
                        try:
                            if info.get("is_output"):
                                new_sock = node.outputs.new("INI_TextureSocket", info.get("name", "Texture"))
                            else:
                                new_sock = node.inputs.new("INI_TextureSocket", info.get("name", "Texture"))
                            if new_sock is not None and info.get("hash") is not None:
                                try:
                                    new_sock["hash"] = info.get("hash")
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    try:
                        del node[key]
                    except Exception:
                        pass

    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "NODE_EDITOR":
                area.tag_redraw()


def register():
    bpy.types.Scene.evbh_asset_path = StringProperty(
        name="에셋", default="", subtype="FILE_PATH", update=_prop_update
    )
    bpy.types.Scene.evbh_mod_path = StringProperty(
        name="모드", default="", subtype="DIR_PATH", update=_prop_update
    )
    bpy.types.Scene.evbh_export_path = StringProperty(
        name="내보내기 폴더", default="", subtype="DIR_PATH", update=_prop_update
    )
    bpy.types.Scene.evbh_show_texture_sockets = BoolProperty(
        name="텍스처 소켓 표시", default=False, update=_toggle_texture_sockets
    )


def unregister():
    del bpy.types.Scene.evbh_show_texture_sockets
    del bpy.types.Scene.evbh_export_path
    del bpy.types.Scene.evbh_mod_path
    del bpy.types.Scene.evbh_asset_path
