"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:30
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : omega database tables metadata
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base import BaseDatabaseResult, BaseDataAccessLayerModel
from .table_meta import *


__all__ = [
    'BaseDatabaseResult',
    'BaseDataAccessLayerModel',
    'Base',
    'SystemSettingOrm',
    'PluginOrm',
    'StatisticOrm',
    'HistoryOrm',
    'BotSelfOrm',
    'EntityOrm',
    'FriendshipOrm',
    'SignInOrm',
    'AuthSettingOrm',
    'CoolDownOrm',
    'EmailBoxOrm',
    'EmailBoxBindOrm',
    'SubscriptionSourceOrm',
    'SubscriptionOrm',
    'BiliDynamicOrm',
    'PixivArtworkOrm',
    'PixivArtworkPageOrm',
    'PixivisionArticleOrm',
    'WordBankOrm'
]
