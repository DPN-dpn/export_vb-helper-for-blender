import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
import os


class PREP_OT_select_asset(bpy.types.Operator, ImportHelper):
    bl_idname = "prep.select_asset"
    bl_label = "hash.json 선택"
    bl_description = "에셋 hash.json 파일을 선택하세요."

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        context.scene.evbh_asset_path = self.filepath
        return {"FINISHED"}


class PREP_OT_select_mod(bpy.types.Operator, ImportHelper):
    bl_idname = "prep.select_mod"
    bl_label = "모드 폴더 선택"
    bl_description = "모드 폴더를 선택하세요."

    filename_ext = ""
    filter_glob: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        chosen = os.path.expanduser(self.filepath)
        if os.path.isfile(chosen):
            base = os.path.dirname(chosen)
        else:
            base = chosen
        if not base or not os.path.isdir(base):
            self.report({"ERROR"}, f"Not a valid folder: {base}")
            return {"CANCELLED"}

        context.scene.evbh_mod_path = base
        return {"FINISHED"}


classes = (PREP_OT_select_asset, PREP_OT_select_mod)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
