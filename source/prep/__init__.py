from . import properties, operators, panel


def register():
    properties.register()
    operators.register()
    panel.register()


def unregister():
    properties.unregister()
    panel.unregister()
    operators.unregister()
