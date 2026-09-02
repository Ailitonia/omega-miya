"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:18
@FileName       : database.py
@Project        : nonebot2_miya
@Description    : omega database utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

导入链 __init__.py -> helpers.py(on_startup) -> connector.py(init_database_engine/session)
此处导入不可删除, 否则将影响启动时初始化
"""

from .helpers import database_session, database_session_depend
from .internal import (
    ArtworkCollectionDAL,
    BotSelfDAL,
    EntityDAL,
    GlobalCacheDAL,
    HistoryDAL,
    PluginDAL,
    SocialMediaContentDAL,
    StatisticDAL,
    SubscriptionSourceDAL,
    SystemSettingDAL,
)

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
    'database_session',
    'database_session_depend',
]
