"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午1:07
@FileName       : consts
@Project        : nonebot2_miya
@Description    : Bilibili 用户动态订阅插件常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

from src.database.internal.subscription_source import SubscriptionSourceType

BILI_DYNAMIC_SUB_TYPE: str = SubscriptionSourceType.bili_dynamic.value
"""b站动态订阅类型"""
NOTICE_AT_ALL: Literal['notice_at_all'] = 'notice_at_all'
"""允许通知时@所有人的权限节点"""
MONITOR_USER_CHECK_DELAY: int = 30
"""检查用户动态时的延迟, 用于规避流控和风控"""

MODULE_NAME = str(__name__).rsplit('.', maxsplit=1)[0]
PLUGIN_NAME = MODULE_NAME.rsplit('.', maxsplit=1)[-1]


__all__ = [
    'BILI_DYNAMIC_SUB_TYPE',
    'NOTICE_AT_ALL',
    'MONITOR_USER_CHECK_DELAY',
    'MODULE_NAME',
    'PLUGIN_NAME',
]
