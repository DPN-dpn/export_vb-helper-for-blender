from . import nodes, sockets, tree, editor, operators


def register():
    operators.register()
    sockets.register()
    nodes.register()
    tree.register()
    editor.register()


def unregister():
    editor.unregister()
    tree.unregister()
    nodes.unregister()
    sockets.unregister()
    operators.unregister()
