# Blender 애드온 정보
bl_info = {
    "name": "엵툵 도우미",
    "author": "DPN",
    "version": (0, 3, 0),
    "blender": (3, 6, 23),
    "location": "상단 작업공간 메뉴 > 작업공간을 추가 > 엵툵",
    "description": "export_vb.py를 보조하는 블렌더용 애드온입니다.",
    "category": "Import-Export",
}

# 라이브러리 임포트
from .source import node_tree_editor, core, text_editor, updator, addon


# 애드온 등록 함수
def register():
    core.register()
    addon.register()
    updator.register()
    node_tree_editor.register()
    text_editor.register()


# 애드온 해제 함수
def unregister():
    text_editor.unregister()
    node_tree_editor.unregister()
    updator.unregister()
    addon.unregister()
    core.unregister()


# 스크립트 직접 실행 시 등록
if __name__ == "__main__":
    register()
