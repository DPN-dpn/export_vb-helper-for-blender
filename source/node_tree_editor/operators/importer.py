import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
from ...data import text_data_block
import os


def read_file_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"# 파일을 읽는 데 실패했습니다: {path}\n# 오류: {e}\n"


class EVHB_OT_select_asset(Operator, ImportHelper):
    bl_idname = "evhb.select_asset"
    bl_label = "hash.json 선택"
    bl_description = "에셋 hash.json 파일을 선택하세요."

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        text_data_block.clear_text_blocks("ASSET")
        context.scene.evbh_asset_path = self.filepath

        content = read_file_text(self.filepath)
        text_name = os.path.basename(self.filepath).replace("\\", "/")
        text = text_data_block.create_or_replace_text_block(text_name, content, "ASSET")

        self.report({"INFO"}, f"텍스트 블록 생성됨: {text_name}")

        return {"FINISHED"}


class EVHB_OT_select_mod(Operator, ImportHelper):
    bl_idname = "evhb.select_mod"
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
            self.report({"ERROR"}, f"유효하지 않은 폴더입니다: {base}")
            return {"CANCELLED"}

        text_data_block.clear_text_blocks("MOD")
        context.scene.evbh_mod_path = base

        # ini 파일 검색
        ini_paths = []
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if fname.lower().endswith(".ini"):
                    ini_paths.append(os.path.join(root, fname))

        if not ini_paths:
            self.report({"INFO"}, "선택한 폴더 아래에 .ini 파일이 없습니다.")
            return {"FINISHED"}

        created_texts = []
        for p in ini_paths:
            try:
                rel = os.path.relpath(p, base)
                text_name = rel.replace("\\", "/")
            except Exception:
                text_name = os.path.basename(p).replace("\\", "/")
            content = read_file_text(p)
            text = text_data_block.create_or_replace_text_block(
                text_name, content, "MOD"
            )
            created_texts.append(text)

        if created_texts:
            self.report(
                {"INFO"}, f"{len(created_texts)}개의 텍스트 블록이 생성되었습니다."
            )

        return {"FINISHED"}


class EVHB_OT_unlink_asset(Operator):
    bl_idname = "evhb.unlink_asset"
    bl_label = "언링크 에셋"
    bl_description = "불러온 에셋 텍스트 블록을 삭제하고 경로를 지웁니다."

    def execute(self, context):
        text_data_block.clear_text_blocks("ASSET")
        context.scene.evbh_asset_path = ""
        self.report({"INFO"}, "에셋 언링크 완료")
        return {"FINISHED"}


class EVHB_OT_unlink_mod(Operator):
    bl_idname = "evhb.unlink_mod"
    bl_label = "언링크 모드"
    bl_description = "불러온 모드 텍스트 블록들을 삭제하고 경로를 지웁니다."

    def execute(self, context):
        text_data_block.clear_text_blocks("MOD")
        context.scene.evbh_mod_path = ""
        self.report({"INFO"}, "모드 언링크 완료")
        return {"FINISHED"}


classes = (
    EVHB_OT_select_asset,
    EVHB_OT_select_mod,
    EVHB_OT_unlink_asset,
    EVHB_OT_unlink_mod,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    text_data_block.clear_all_created_text_blocks()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
