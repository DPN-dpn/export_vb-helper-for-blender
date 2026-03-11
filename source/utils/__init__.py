from . import json_parser, ini_parser


def register():
    json_parser.register()
    ini_parser.register()


def unregister():
    ini_parser.unregister()
    json_parser.unregister()
