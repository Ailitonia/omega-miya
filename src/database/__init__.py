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

from typing import Annotated

from nonebot.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

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

type DATABASE_SESSION = Annotated[AsyncSession, Depends(database_session_depend)]
"""子依赖: 获取数据库 session 并开始事务"""


__all__ = [
    'DATABASE_SESSION',
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
