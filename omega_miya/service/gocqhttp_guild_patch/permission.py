"""
@Author         : Ailitonia
@Date           : 2022/05/22 1:17
@FileName       : permission.py
@Project        : nonebot2_miya 
@Description    : Guild Permission
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.permission import Permission
from .models import GuildMessageEvent


async def _guild(event: GuildMessageEvent) -> bool:
    return True


GUILD = Permission(_guild)
"""
- **说明**: 匹配任意频道消息类型事件
"""


__all__ = [
    'GUILD'
]
