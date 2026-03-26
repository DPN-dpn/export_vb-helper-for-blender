import bpy
from bpy.props import StringProperty, BoolProperty
from .properties import prop_update


def addon_module_name():
    # Use the top-level package/module name so bl_idname matches the addon module
    try:
        return __name__.split(".")[0]
    except Exception:
        return __name__


class EVBHPreferences(bpy.types.AddonPreferences):
    bl_idname = addon_module_name()

    evbh_export_vb: StringProperty(
        name="엵툵",
        default="",
        subtype="FILE_PATH",
        description="export_vb.py",
    )

    evbh_export_vb_use: BoolProperty(
        name="엵툵으로 내보내기",
        default=True,
        description="엵툵으로 내보내기",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "evbh_export_vb")
        if self.evbh_export_vb:
            layout.prop(self, "evbh_export_vb_use")


classes = (EVBHPreferences,)


def register():
    bpy.types.Scene.evbh_export_vb = StringProperty(
        name="Export VB 파일",
        default="",
        subtype="FILE_PATH",
        update=prop_update,
    )
    bpy.types.Scene.evbh_export_vb_use = BoolProperty(
        name="엵툵으로 내보내기",
        default=True,
        update=prop_update,
    )

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    del bpy.types.Scene.evbh_export_vb_use
    del bpy.types.Scene.evbh_export_vb

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
