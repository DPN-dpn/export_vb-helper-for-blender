import bpy
from bpy.types import NodeSocket


class EVBH_GenericSocket(NodeSocket):
    socket_color = (0.6, 0.6, 0.6, 1.0)

    def draw(self, context, layout, node, text):
        # 토글이 꺼져있으면 EVBH_TextureSocket은 그리지 않음
        show_tex = getattr(context.scene, "evbh_show_texture_sockets", True)
        if getattr(self.__class__, "bl_idname", "") == "EVBH_TextureSocket" and not show_tex:
            return
        
        slotLabel = text or self.name
        hash_val = self.get("hash", "")

        row = layout.row(align=True)
        row.label(text=slotLabel)
        row.separator()
        col_right = row.column(align=True)
        col_right.alignment = 'RIGHT'
        col_right.scale_x = 1.0
        col_right.label(text=str(hash_val) if hash_val else "")

    def draw_color(self, context, node):
        return getattr(self, "socket_color", self.socket_color)


class EVBH_PositionSocket(EVBH_GenericSocket):
    bl_idname = "EVBH_PositionSocket"
    bl_label = "Position"
    socket_color = (0.8, 0.6, 0.3, 1.0)


class EVBH_BlendSocket(EVBH_GenericSocket):
    bl_idname = "EVBH_BlendSocket"
    bl_label = "Blend"
    socket_color = (0.7, 0.3, 0.8, 1.0)


class EVBH_TexcoordSocket(EVBH_GenericSocket):
    bl_idname = "EVBH_TexcoordSocket"
    bl_label = "Texcoord"
    socket_color = (0.2, 0.7, 0.2, 1.0)


class EVBH_IBSocket(EVBH_GenericSocket):
    bl_idname = "EVBH_IBSocket"
    bl_label = "IB"
    socket_color = (0.1, 0.6, 0.9, 1.0)


class EVBH_TextureSocket(EVBH_GenericSocket):
    bl_idname = "EVBH_TextureSocket"
    bl_label = "Texture"
    socket_color = (0.4, 0.5, 0.4, 1.0)


class EVBH_ResultSocket(NodeSocket):
    bl_idname = "EVBH_ResultSocket"
    bl_options = {"MULTI_INPUT"}

    def draw(self, context, layout, node, text):
        layout.label(text="Result")

    def draw_color(self, context, node):
        return (0.0, 0.0, 0.0, 1.0)


classes = (
    EVBH_PositionSocket,
    EVBH_BlendSocket,
    EVBH_TexcoordSocket,
    EVBH_IBSocket,
    EVBH_TextureSocket,
    EVBH_ResultSocket,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
