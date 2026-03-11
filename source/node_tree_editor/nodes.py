import bpy
from bpy.types import Node


class ModFileNode(Node):
    bl_idname = "ModFileNode"
    bl_label = "Mod File"
    bl_icon = "PLAY"

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.width = 180


class AssetSlotNode(Node):
    bl_idname = "AssetSlotNode"
    bl_label = "Asset Slot"
    bl_icon = "FILE_TEXT"

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.outputs.new("ResultSocket", "Result")
        self.width = 180


class ResultNode(Node):
    bl_idname = "ResultNode"
    bl_label = "Result"
    bl_icon = "OUTPUT"

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.width = 220
        self.inputs.new("ResultSocket", "Result")


classes = (
    ModFileNode,
    AssetSlotNode,
    ResultNode,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
