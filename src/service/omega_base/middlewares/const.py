"""
@Author         : Ailitonia
@Date           : 2023/6/9 18:58
@FileName       : const
@Project        : nonebot2_miya
@Description    : middlewares const
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.database.internal.bot import BotType as SupportedPlatform
from src.database.internal.entity import EntityType as SupportedTarget

__all__ = [
    'SupportedPlatform',
    'SupportedTarget'
]
