"""
@Author         : Ailitonia
@Date           : 2022/12/03 17:56
@FileName       : service.py
@Project        : nonebot2_miya
@Description    : Omega 服务模块, 包括权限、冷却、多 Bot 适配等组件都在这里
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .apscheduler import reschedule_job, scheduler
from .omega_api import OmegaAPI
from .omega_base import (
    OmegaEntity,
    OmegaEntityInterface,
    OmegaMatcherInterface,
    OmegaMessage,
    OmegaMessageSegment,
    OmegaMessageTransfer,
)
from .omega_global_cache import OmegaGlobalCache
from .omega_multibot_support import get_online_bots
from .omega_processor import enable_processor_state
from .omega_subscription_service import OmegaSubscriptionHandlerManager

__all__ = [
    'OmegaAPI',
    'OmegaEntity',
    'OmegaEntityInterface',
    'OmegaGlobalCache',
    'OmegaMatcherInterface',
    'OmegaMessage',
    'OmegaMessageSegment',
    'OmegaMessageTransfer',
    'OmegaSubscriptionHandlerManager',
    'enable_processor_state',
    'get_online_bots',
    'reschedule_job',
    'scheduler',
]
