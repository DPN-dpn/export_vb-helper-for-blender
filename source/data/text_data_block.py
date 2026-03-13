import bpy

_asset_text_blocks = set()
_mod_text_blocks = set()


def create_or_replace_text_block(name: str, content: str, type: str):
    name = name.replace("\\", "/")
    text = bpy.data.texts.get(name)
    if text is None:
        text = bpy.data.texts.new(name)
    else:
        text.clear()
    text.write(content)

    # Try to attach to an open Text Editor so the text has a real user
    attached = False
    for area in bpy.context.screen.areas:
        if area.type == "TEXT_EDITOR":
            space = area.spaces.active
            space.text = text
            text.use_fake_user = False

            # Try to scroll view to top if supported by this Blender version
            if hasattr(space, "top"):
                space.top = 0

            attached = True
            break

    # If no editor was available, keep fake user to avoid automatic removal
    if not attached:
        text.use_fake_user = True

    if type == "ASSET":
        _asset_text_blocks.add(text.name)
    elif type == "MOD":
        _mod_text_blocks.add(text.name)
    return text


def clear_text_blocks(type: str = None):
    global _asset_text_blocks
    global _mod_text_blocks

    _target_blocks = set()
    if type == "ASSET":
        _target_blocks = _asset_text_blocks
    elif type == "MOD":
        _target_blocks = _mod_text_blocks
    else:
        _target_blocks = _asset_text_blocks | _mod_text_blocks

    removed = []
    for name in list(_target_blocks):
        text = bpy.data.texts.get(name)
        if text is not None:
            bpy.data.texts.remove(text)
            removed.append(name)
        _target_blocks.discard(name)
    return removed


def register():
    pass


def unregister():
    pass
