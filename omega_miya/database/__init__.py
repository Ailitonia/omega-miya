"""
@Author         : Ailitonia
@Date           : 2022/02/21 10:11
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : omega database driver
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .schemas import (DatabaseErrorInfo, AuthSetting, BiliDynamic, EmailBox, History, PixivisionArticle,
                      Plugin, Statistic, SystemSetting, WordBank)
from .internal import (InternalBotGroup, InternalBotUser, InternalBotGuild,
                       InternalGuildChannel, InternalGroupUser, InternalGuildUser,
                       InternalOneBotV11Bot,
                       InternalSubscriptionSource, InternalPixiv)
from .exception import DatabaseBaseException, DatabaseQueryError, DatabaseUpgradeError, DatabaseDeleteError


__all__ = [
    'DatabaseErrorInfo',
    'DatabaseBaseException',
    'DatabaseQueryError',
    'DatabaseUpgradeError',
    'DatabaseDeleteError',
    'AuthSetting',
    'BiliDynamic',
    'EmailBox',
    'History',
    'PixivisionArticle',
    'Plugin',
    'Statistic',
    'SystemSetting',
    'WordBank',
    'InternalBotGroup',
    'InternalBotUser',
    'InternalBotGuild',
    'InternalGuildChannel',
    'InternalGroupUser',
    'InternalGuildUser',
    'InternalOneBotV11Bot',
    'InternalSubscriptionSource',
    'InternalPixiv'
]
