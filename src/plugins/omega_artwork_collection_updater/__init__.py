"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:00
@FileName       : omega_artwork_collection_updater
@Project        : nonebot2_miya
@Description    : 图库自动更新工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='图库更新工具',
    description='【图库作品自动更新/手动导入工具】',
    usage='仅限超级管理员使用:\n'
          '/导入图库\n'
          '/图库统计 [origin] [keywords]',
    extra={'author': 'Ailitonia'},
)

from . import manual_update_tools as manual_update_tools
from . import scheduler as scheduler

__all__ = []
