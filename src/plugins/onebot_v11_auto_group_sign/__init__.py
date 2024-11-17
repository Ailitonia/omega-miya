"""
@Author         : Ailitonia
@Date           : 2023/7/15 20:00
@FileName       : onebot_v11_auto_group_sign
@Project        : nonebot2_miya
@Description    : 自动群打卡 (go-cqhttp v1.0.0-rc3 以上版本可用)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

from .config import auto_group_sign_config

__plugin_meta__ = PluginMetadata(
    name='自动群打卡',
    description='【QQ 自动群打卡插件】\n'
                '仅限 OneBot V11 使用\n'
                '让机器人参与抢群打卡每日第一',
    usage='由管理员配置, 无命令用法',
    config=auto_group_sign_config.__class__,
    supported_adapters={'OneBot V11'},
    extra={'author': 'Ailitonia'},
)

from . import scheduled_tasks as tasks

__all__ = []
