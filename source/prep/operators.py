import bpy
from bpy.types import Operator


class EXPORTVB_OT_dummy(Operator):
    bl_idname = "exportvb.dummy"
    bl_label = "실행"

    def execute(self, context):
        self.report({"INFO"}, "엵툵 작업 실행")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(EXPORTVB_OT_dummy)


def unregister():
    bpy.utils.unregister_class(EXPORTVB_OT_dummy)
