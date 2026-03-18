import bpy
from bpy.types import NodeSocket


class GenericSocket(NodeSocket):
    socket_color = (0.6, 0.6, 0.6, 1.0)

    def draw(self, context, layout, node, text):
        slotLabel = text or self.name
        hash_val = self.get("hash", "")

        if self.is_output:
            row = layout.row(align=True)
            col_left = row.column(align=True)
            col_left.scale_x = 1.0
            col_left.label(text=str(hash_val) if hash_val else "")
            row.separator()
            row.label(text=slotLabel)
        else:
            row = layout.row(align=True)
            row.label(text=slotLabel)
            row.separator()
            col_left = row.column(align=True)
            col_left.scale_x = 1.0
            col_left.label(text=str(hash_val) if hash_val else "")

    def draw_color(self, context, node):
        return getattr(self, "socket_color", self.socket_color)


class INI_PositionSocket(GenericSocket):
    bl_idname = "INI_PositionSocket"
    bl_label = "Position"
    socket_color = (0.8, 0.6, 0.3, 1.0)


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
    socket_color = (0.1, 0.6, 0.9, 1.0)


class INI_TextureSocket(GenericSocket):
    bl_idname = "INI_TextureSocket"
    bl_label = "Texture"
    socket_color = (0.4, 0.5, 0.4, 1.0)


class ResultSocket(NodeSocket):
    bl_idname = "ResultSocket"
    bl_options = {"MULTI_INPUT"}

    def draw(self, context, layout, node, text):
        layout.label(text="Result")

    def draw_color(self, context, node):
        return (0.0, 0.0, 0.0, 1.0)


classes = (
    INI_PositionSocket,
    INI_BlendSocket,
    INI_TexcoordSocket,
    INI_IBSocket,
    INI_TextureSocket,
    ResultSocket,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
