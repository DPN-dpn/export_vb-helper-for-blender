from . import preferences, properties


def register():
    preferences.register()
    properties.register()


def unregister():
    properties.unregister()
    preferences.unregister()