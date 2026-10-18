"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:00
@FileName       : omega_artwork_collection_updater
@Project        : nonebot2_miya
@Description    : 图库统计与更新工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='图库统计与更新工具',
    description='【图库统计信息查询与自动更新工具】',
    usage='仅限超级管理员使用:\n/图库统计 [-o <origin>] [-k <keywords...>]',
    extra={'author': 'Ailitonia'},
)

from . import scheduled_tasks as scheduled_tasks
from . import statistics_command as statistics_command

__all__ = []
