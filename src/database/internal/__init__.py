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
from .auth_setting import AuthSettingDAL
from .bot import BotSelfDAL
from .cooldown import CoolDownDAL
from .entity import EntityDAL
from .friendship import FriendshipDAL
from .global_cache import GlobalCacheDAL
from .history import HistoryDAL
from .plugin import PluginDAL
from .sign_in import SignInDAL
from .social_media_content import SocialMediaContentDAL
from .statistic import StatisticDAL
from .subscription import SubscriptionDAL
from .subscription_source import SubscriptionSourceDAL
from .system_setting import SystemSettingDAL
from .word_bank import WordBankDAL

__all__ = [
    'ArtworkCollectionDAL',
    'AuthSettingDAL',
    'BotSelfDAL',
    'CoolDownDAL',
    'EntityDAL',
    'FriendshipDAL',
    'GlobalCacheDAL',
    'HistoryDAL',
    'PluginDAL',
    'SignInDAL',
    'SocialMediaContentDAL',
    'StatisticDAL',
    'SubscriptionDAL',
    'SubscriptionSourceDAL',
    'SystemSettingDAL',
    'WordBankDAL',
]
