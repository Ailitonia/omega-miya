"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:49
@FileName       : internal.py
@Project        : nonebot2_miya
@Description    : Data access layer model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .artwork_collection import ArtworkCollectionDAL
from .bot import BotSelfDAL
from .entity import EntityDAL
from .global_cache import GlobalCacheDAL
from .history import HistoryDAL
from .plugin import PluginDAL
from .social_media_content import SocialMediaContentDAL
from .statistic import StatisticDAL
from .subscription_source import SubscriptionSourceDAL
from .system_setting import SystemSettingDAL

__all__ = [
    'ArtworkCollectionDAL',
    'BotSelfDAL',
    'EntityDAL',
    'GlobalCacheDAL',
    'HistoryDAL',
    'PluginDAL',
    'SocialMediaContentDAL',
    'StatisticDAL',
    'SubscriptionSourceDAL',
    'SystemSettingDAL',
]
