"""
@Author         : Ailitonia
@Date           : 2024/3/26 22:52
@FileName       : consts
@Project        : nonebot2_miya
@Description    : Pixiv Plugin Consts
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.database.internal.subscription_source import SubscriptionSourceType

PIXIV_USER_SUB_TYPE: str = SubscriptionSourceType.pixiv_user.value
"""Pixiv 用户订阅类型"""


__all__ = [
    'PIXIV_USER_SUB_TYPE',
]
