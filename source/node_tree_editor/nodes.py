import bpy
from bpy.types import Node


class ModFileNode(Node):
    bl_idname = "ModFileNode"
    bl_label = "Mod File"
    bl_icon = "MOD_ARMATURE"
    bl_width_default = 200

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.use_custom_color = True
        self.color = (0.20, 0.17, 0.17)


class ModTextureNode(Node):
    bl_idname = "ModTextureNode"
    bl_label = "Mod Texture"
    bl_icon = "TEXTURE"
    bl_width_default = 200

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.use_custom_color = True
        self.color = (0.17, 0.20, 0.17)


class AssetSlotNode(Node):
    bl_idname = "AssetSlotNode"
    bl_label = "Asset Slot"
    bl_icon = "CON_ARMATURE"
    bl_width_default = 180

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.outputs.new("ResultSocket", "Result")
        self.use_custom_color = True
        self.color = (0.17, 0.17, 0.20)

    def update(self):
        out = self.outputs[0] if self.outputs else None
        if not out:
            return
        links = out.links[:]
        if len(links) > 1:
            for link in links[1:]:
                try:
                    self.id_data.links.remove(link)
                except Exception:
                    pass


class ResultNode(Node):
    bl_idname = "ResultNode"
    bl_label = "Result"
    bl_icon = "POSE_HLT"
    bl_width_default = 160
    bl_height_default = 120

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.inputs.new("ResultSocket", "Result")
        self.use_custom_color = True
        self.color = (0.10, 0.10, 0.10)

    def update(self):
        for i in range(len(self.inputs) - 1, -1, -1):
            socket = self.inputs[i]
            if not socket.is_linked and len(self.inputs) > 1:
                if i != len(self.inputs) - 1:
                    self.inputs.remove(socket)

        if self.inputs[-1].is_linked:
            new_socket = self.inputs.new("ResultSocket", f"Data {len(self.inputs) + 1}")

        for i, socket in enumerate(self.inputs):
            socket.name = f"Data {i + 1}"

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)
        col.enabled = any(socket.is_linked for socket in self.inputs)
        col.operator("evhb.export_mod", text="내보내기", icon="EXPORT")


classes = (
    ModFileNode,
    ModTextureNode,
    AssetSlotNode,
    ResultNode,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
