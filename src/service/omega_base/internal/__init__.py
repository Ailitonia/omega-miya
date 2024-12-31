"""
@Author         : Ailitonia
@Date           : 2022/12/08 21:29
@FileName       : internal.py
@Project        : nonebot2_miya 
@Description    : Omega 基础服务, 数据库二次封装
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .entity import InternalEntity as OmegaEntity
from .subscription_source import InternalBilibiliDynamicSubscriptionSource as OmegaBiliDynamicSubSource
from .subscription_source import InternalBilibiliLiveSubscriptionSource as OmegaBiliLiveSubSource
from .subscription_source import InternalPixivUserSubscriptionSource as OmegaPixivUserSubSource
from .subscription_source import InternalPixivisionSubscriptionSource as OmegaPixivisionSubSource
from .subscription_source import InternalWeiboUserSubscriptionSource as OmegaWeiboUserSubSource

__all__ = [
    'OmegaEntity',
    'OmegaBiliDynamicSubSource',
    'OmegaBiliLiveSubSource',
    'OmegaPixivUserSubSource',
    'OmegaPixivisionSubSource',
    'OmegaWeiboUserSubSource'
]
