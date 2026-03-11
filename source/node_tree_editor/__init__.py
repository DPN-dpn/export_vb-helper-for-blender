from . import nodes, sockets, tree


def register():
    sockets.register()
    nodes.register()
    tree.register()


def unregister():
    tree.unregister()
    nodes.unregister()
    sockets.unregister()
