"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:49
@FileName       : internal.py
@Project        : nonebot2_miya 
@Description    : Data access layer model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .auth_setting import AuthSettingDAL
from .bili_dynamic import BiliDynamicDAL
from .bot import BotSelfDAL
from .cooldown import CoolDownDAL
from .email_box import EmailBoxDAL
from .email_box_bind import EmailBoxBindDAL
from .entity import EntityDAL
from .friendship import FriendshipDAL
from .history import HistoryDAL
from .pixiv_artwork import PixivArtworkDAL
from .pixiv_artwork_page import PixivArtworkPageDAL
from .pixivision_article import PixivisionArticleDAL
from .plugin import PluginDAL
from .sign_in import SignInDAL
from .statistic import StatisticDAL
from .subscription import SubscriptionDAL
from .subscription_source import SubscriptionSourceDAL
from .system_setting import SystemSettingDAL
from .weibo_detail import WeiboDetailDAL
from .word_bank import WordBankDAL


__all__ = [
    'AuthSettingDAL',
    'BiliDynamicDAL',
    'BotSelfDAL',
    'CoolDownDAL',
    'EmailBoxDAL',
    'EmailBoxBindDAL',
    'EntityDAL',
    'FriendshipDAL',
    'HistoryDAL',
    'PixivArtworkDAL',
    'PixivArtworkPageDAL',
    'PixivisionArticleDAL',
    'PluginDAL',
    'SignInDAL',
    'StatisticDAL',
    'SubscriptionDAL',
    'SubscriptionSourceDAL',
    'SystemSettingDAL',
    'WeiboDetailDAL',
    'WordBankDAL'
]
