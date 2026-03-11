import bpy
from bpy.types import NodeTree


class ExportVBPrepNodeTree(NodeTree):
    bl_idname = "ExportVBPrepNodeTree"
    bl_label = "엵툵 사전작업 노드 에디터"
    bl_icon = "NODETREE"

    @classmethod
    def poll(cls, context):
        return True


classes = (ExportVBPrepNodeTree,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
