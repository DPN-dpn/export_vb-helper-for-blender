import bpy
from bpy.types import Operator


class EVHB_OT_export_mod(Operator):
    bl_idname = "evhb.export_mod"
    bl_label = "내보내기"
    bl_description = "사전작업을 적용한 모드를 내보냅니다"

    def execute(self, context):
        return {"FINISHED"}


classes = (EVHB_OT_export_mod,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
