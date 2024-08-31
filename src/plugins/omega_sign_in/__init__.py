"""
@Author         : Ailitonia
@Date           : 2021/07/17 1:29
@FileName       : omega_sign_in
@Project        : nonebot2_miya
@Description    : 轻量化签到插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

from .config import sign_in_config

__plugin_meta__ = PluginMetadata(
    name='签到',
    description='【OmegaSignIn 签到插件】\n'
                "轻量化签到插件, 好感度系统基础",
    usage='/签到\n'
          '/老黄历|好感度|一言\n'
          '/补签\n\n'
          'QQ可使用双击头像戳一戳触发',
    config=sign_in_config.__class__,
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
