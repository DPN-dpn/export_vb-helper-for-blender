import bpy
from bpy.types import NodeSocket


class GenericSocket(NodeSocket):
    socket_color = (0.6, 0.6, 0.6, 1.0)

    def draw(self, context, layout, node, text):
        slotLabel = text or self.name
        hash = self.get("hash", "")
        split = layout.split(factor=0.6)
        c = split.column()
        c.alignment = "RIGHT"
        if self.is_output:
            if hash:
                split.column().label(text=str(hash))
            else:
                split.column().label(text=str.empty)
            c.label(text=text or self.name)
        else:
            split.column().label(text=slotLabel)
            if hash:
                c.label(text=str(hash))

    def draw_color(self, context, node):
        return getattr(self, "socket_color", self.socket_color)


class INI_PositionSocket(GenericSocket):
    bl_idname = "INI_PositionSocket"
    bl_label = "Position"
    socket_color = (0.2, 0.4, 0.8, 1.0)


class INI_BlendSocket(GenericSocket):
    bl_idname = "INI_BlendSocket"
    bl_label = "Blend"
    socket_color = (0.7, 0.3, 0.8, 1.0)


class INI_TexcoordSocket(GenericSocket):
    bl_idname = "INI_TexcoordSocket"
    bl_label = "Texcoord"
    socket_color = (0.2, 0.7, 0.2, 1.0)


class INI_IBSocket(GenericSocket):
    bl_idname = "INI_IBSocket"
    bl_label = "IB"
    socket_color = (0.9, 0.6, 0.2, 1.0)


class ResultSocket(NodeSocket):
    bl_idname = "ResultSocket"
    bl_label = "Result"

    def draw(self, context, layout, node, text):
        layout.label(text=text or self.name)

    def draw_color(self, context, node):
        return (0.1, 0.6, 0.9, 1.0)


classes = (
    INI_PositionSocket,
    INI_BlendSocket,
    INI_TexcoordSocket,
    INI_IBSocket,
    ResultSocket,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
