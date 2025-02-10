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
from src.utils.bilibili_api.models.dynamic import DynamicType

# 订阅相关
BILI_DYNAMIC_SUB_TYPE: str = SubscriptionSourceType.bili_dynamic.value
"""b站动态订阅类型"""
NOTICE_AT_ALL: Literal['notice_at_all'] = 'notice_at_all'
"""允许通知时@所有人的权限节点"""
IGNORED_DYNAMIC_TYPES: list[DynamicType] = [
    DynamicType.live_rcmd,
    DynamicType.ad,
    DynamicType.applet,
]
"""在通知时忽略的动态类型"""


# 计划任务相关
MONITOR_JOB_ID: Literal['bili_dynamic_update_monitor'] = 'bili_dynamic_update_monitor'
"""动态检查的定时任务 ID"""
AVERAGE_CHECKING_PER_MINUTE: int = 12
"""每分钟检查动态的用户数(数值大小影响风控概率, 请谨慎调整)"""
CHECKING_DELAY_UNDER_RATE_LIMITING: int = 6
"""被风控时的延迟间隔"""

# 插件相关
MODULE_NAME = str(__name__).rsplit('.', maxsplit=1)[0]
PLUGIN_NAME = MODULE_NAME.rsplit('.', maxsplit=1)[-1]


__all__ = [
    'BILI_DYNAMIC_SUB_TYPE',
    'NOTICE_AT_ALL',
    'IGNORED_DYNAMIC_TYPES',
    'MONITOR_JOB_ID',
    'AVERAGE_CHECKING_PER_MINUTE',
    'CHECKING_DELAY_UNDER_RATE_LIMITING',
    'MODULE_NAME',
    'PLUGIN_NAME',
]
