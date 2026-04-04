import bpy
import os

TARGET_NAME = "엵툵 도우미"
BLEND_FILENAME = "EVBH.blend"


def _install_workspace_helper(target_name=TARGET_NAME, blend_filename=BLEND_FILENAME):
    addon_dir = os.path.dirname(__file__)
    blend_path = os.path.join(addon_dir, "../../", blend_filename)
    if not os.path.exists(blend_path):
        return False, f"{blend_filename} 파일을 찾을 수 없습니다."

    try:
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            available = getattr(data_from, "workspaces", [])
            if target_name not in available:
                return False, f"'{target_name}' 작업공간이 파일에 없습니다."
            if any(w.name == target_name for w in bpy.data.workspaces):
                return False, f"'{target_name}' 작업공간은 이미 존재합니다."
            data_to.workspaces = [target_name]

        ws = bpy.data.workspaces.get(target_name)
        if ws is not None:
            try:
                ws["_evbh_installed_by_addon"] = True
            except Exception:
                pass

        return True, f"'{target_name}' 작업공간이 추가되었습니다."
    except Exception as e:
        return False, str(e)


class WM_OT_install_workspace(bpy.types.Operator):
    bl_idname = "wm.install_workspace"
    bl_label = "작업공간 설치"
    bl_description = "'엵툵 도우미' 작업공간을 설치합니다"

    def execute(self, context):
        ok, msg = _install_workspace_helper()
        if ok:
            self.report({"INFO"}, msg)
            return {"FINISHED"}
        else:
            self.report({"ERROR"}, msg)
            return {"CANCELLED"}


classes = (WM_OT_install_workspace,)


def _auto_install_timer():
    ok, msg = _install_workspace_helper()
    if not ok:
        print(f"[EVBH] auto-install: {msg}")
    else:
        print(f"[EVBH] auto-install: {msg}")
    return None


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    try:
        bpy.app.timers.register(_auto_install_timer, first_interval=0.1)
    except Exception as e:
        print(f"[EVBH] auto-install failed: {e}")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
