import bpy
from bpy.props import StringProperty


def _prop_update(self, context):
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


def unregister():
    del bpy.types.Scene.evbh_asset_path
    del bpy.types.Scene.evbh_mod_path
