from nonebot.plugin import Export
from .rules import *
from .encrypt import AESEncryptStr
from .cooldown import *


def init_export(plugin_export: Export, custom_name: str, usage: str, auth_node: list = None, **kwargs: str) -> Export:
    setattr(plugin_export, 'custom_name', custom_name)
    setattr(plugin_export, 'usage', usage)
    setattr(plugin_export, 'auth_node', auth_node)
    for key, value in kwargs.items():
        setattr(plugin_export, key, value)
    return plugin_export
