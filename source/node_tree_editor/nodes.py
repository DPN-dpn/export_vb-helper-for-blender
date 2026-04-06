import bpy
from bpy.types import Node


class EVBH_ModFileNode(Node):
    bl_idname = "EVBH_ModFileNode"
    bl_label = "Mod File"
    bl_icon = "MATCLOTH"
    bl_width_default = 200

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.use_custom_color = True
        self.color = (0.20, 0.17, 0.17)


class EVBH_AssetSlotNode(Node):
    bl_idname = "EVBH_AssetSlotNode"
    bl_label = "Asset Slot"
    bl_icon = "RNA"
    bl_width_default = 180

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.outputs.new("EVBH_ResultSocket", "Result")
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


class EVBH_ResultNode(Node):
    bl_idname = "EVBH_ResultNode"
    bl_label = "Result"
    bl_icon = "GROUP"
    bl_width_default = 160
    bl_height_default = 120

    @classmethod
    def poll(cls, ntree):
        return True

    def init(self, context):
        self.inputs.new("EVBH_ResultSocket", "Result")
        self.use_custom_color = True
        self.color = (0.10, 0.10, 0.10)

    def update(self):
        for i in range(len(self.inputs) - 1, -1, -1):
            socket = self.inputs[i]
            if not socket.is_linked and len(self.inputs) > 1:
                if i != len(self.inputs) - 1:
                    self.inputs.remove(socket)

        if self.inputs[-1].is_linked:
            new_socket = self.inputs.new("EVBH_ResultSocket", f"Data {len(self.inputs) + 1}")

        for i, socket in enumerate(self.inputs):
            socket.name = f"Data {i + 1}"

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)
        col.enabled = any(socket.is_linked for socket in self.inputs)
        col.operator("evbh.export_mod", text="내보내기", icon="EXPORT")


classes = (
    EVBH_ModFileNode,
    EVBH_AssetSlotNode,
    EVBH_ResultNode,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
