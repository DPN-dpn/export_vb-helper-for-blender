from . import operator, panel


def register():
    operator.register()
    panel.register()


def unregister():
    panel.unregister()
    operator.unregister()
