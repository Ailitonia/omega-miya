"""
@Author         : Ailitonia
@Date           : 2026/10/7 18:14
@FileName       : dal
@Project        : omega-miya
@Description    : 数据库 DAL 对象子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.params import Depends

from src.database import (
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

type ARTWORK_COLLECTION_DAL = Annotated[ArtworkCollectionDAL, Depends(ArtworkCollectionDAL.dal_dependence)]
"""子依赖: 获取 ArtworkCollectionDAL"""
type BOT_SELF_DAL = Annotated[BotSelfDAL, Depends(BotSelfDAL.dal_dependence)]
"""子依赖: 获取 BotSelfDAL"""
type ENTITY_DAL = Annotated[EntityDAL, Depends(EntityDAL.dal_dependence)]
"""子依赖: 获取 EntityDAL"""
type GLOBAL_CACHE_DAL = Annotated[GlobalCacheDAL, Depends(GlobalCacheDAL.dal_dependence)]
"""子依赖: 获取 GlobalCacheDAL"""
type HISTORY_DAL = Annotated[HistoryDAL, Depends(HistoryDAL.dal_dependence)]
"""子依赖: 获取 HistoryDAL"""
type PLUGIN_DAL = Annotated[PluginDAL, Depends(PluginDAL.dal_dependence)]
"""子依赖: 获取 PluginDAL"""
type SOCIAL_MEDIA_CONTENT_DAL = Annotated[SocialMediaContentDAL, Depends(SocialMediaContentDAL.dal_dependence)]
"""子依赖: 获取 SocialMediaContentDAL"""
type STATISTIC_DAL = Annotated[StatisticDAL, Depends(StatisticDAL.dal_dependence)]
"""子依赖: 获取 StatisticDAL"""
type SUBSCRIPTION_SOURCE_DAL = Annotated[SubscriptionSourceDAL, Depends(SubscriptionSourceDAL.dal_dependence)]
"""子依赖: 获取 SubscriptionSourceDAL"""
type SYSTEM_SETTING_DAL = Annotated[SystemSettingDAL, Depends(SystemSettingDAL.dal_dependence)]
"""子依赖: 获取 SystemSettingDAL"""

__all__ = [
    'ARTWORK_COLLECTION_DAL',
    'BOT_SELF_DAL',
    'ENTITY_DAL',
    'GLOBAL_CACHE_DAL',
    'HISTORY_DAL',
    'PLUGIN_DAL',
    'SOCIAL_MEDIA_CONTENT_DAL',
    'STATISTIC_DAL',
    'SUBSCRIPTION_SOURCE_DAL',
    'SYSTEM_SETTING_DAL',
]
