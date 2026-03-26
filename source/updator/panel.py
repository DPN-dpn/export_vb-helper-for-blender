# 라이브러리 임포트
import bpy
from bpy.types import Panel


# 업데이터 패널 UI
class PT_Updater(Panel):
    bl_label = "업데이트"
    bl_idname = "PREP_PT_updater"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "엵툵 사전작업"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        latest_version = scene.get("latest_version", "")
        current_version = scene.get("current_version", "")
        update_available = scene.get("update_available", False)
        show_restart = scene.get("show_restart", False)

        # 버튼 라벨 조건 분기
        if not latest_version:
            update_label = "업데이트 체크 필요"
        elif not update_available:
            update_label = "현재 최신 버전입니다"
        else:
            update_label = f"업데이트: {current_version} → {latest_version}"

        layout.operator(
            "updater.check_update", text="업데이트 체크", icon="FILE_REFRESH"
        )
        row = layout.row()
        if show_restart:
            row.operator(
                "wm.quit_blender", text="블렌더 종료(애드온 재실행)", icon="CANCEL"
            )
        else:
            row.enabled = bool(update_available)
            row.operator("updater.do_update", text=update_label, icon="IMPORT")
        layout.operator("updater.open_github", text="GitHub", icon="URL")


def register():
    bpy.utils.register_class(PT_Updater)


def unregister():
    bpy.utils.unregister_class(PT_Updater)
