"""
@Author         : Ailitonia
@Date           : 2025/8/12 22:31:26
@FileName       : internal.py
@Project        : omega-miya
@Description    : Omega 内部数据库相关子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.params import Depends

from src.database import DATABASE_SESSION, begin_db_session
from ..internal import OmegaEntity
from ..middlewares.interface import OmegaMatcherInterface as OmMI
from ..middlewares.models import EntityInitParams

if TYPE_CHECKING:
    from ...omega_base.middlewares.typing import EntityAcquireType


def extract_entity_params(bot: BaseBot, event: BaseEvent, acquire_type: 'EntityAcquireType') -> EntityInitParams:
    """提取 Entity 实例化参数"""
    return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).extract_entity_params(acquire_type)


def _extract_event_entity_params(bot: BaseBot, event: BaseEvent) -> EntityInitParams:
    """提取事件本身对应 Entity 实例化参数"""
    return extract_entity_params(bot=bot, event=event, acquire_type='event')


type EVENT_ENTITY_PARAMS = Annotated[EntityInitParams, Depends(_extract_event_entity_params, use_cache=True)]
"""子依赖: 事件本身对应 Entity 实例化参数"""


def _extract_user_entity_params(bot: BaseBot, event: BaseEvent) -> EntityInitParams:
    """提取触发事件用户 Entity 实例化参数"""
    return extract_entity_params(bot=bot, event=event, acquire_type='user')


type USER_ENTITY_PARAMS = Annotated[EntityInitParams, Depends(_extract_user_entity_params, use_cache=True)]
"""子依赖: 触发事件用户 Entity 实例化参数"""


async def _get_event_internal_entity_instance(
        event_entity_params: EVENT_ENTITY_PARAMS,
        session: DATABASE_SESSION,
) -> AsyncGenerator[OmegaEntity, None]:
    """获取事件对象的 InternalEntity 实例"""
    async with OmegaEntity(session=session, **event_entity_params.kwargs) as entity:
        yield entity


type EVENT_INTERNAL_ENTITY = Annotated[OmegaEntity, Depends(_get_event_internal_entity_instance)]
"""子依赖: 事件对象的 InternalEntity 实例"""


async def _get_user_internal_entity_instance(
        user_entity_params: USER_ENTITY_PARAMS,
        session: DATABASE_SESSION,
) -> AsyncGenerator[OmegaEntity, None]:
    """获取事件对象的 InternalEntity 实例"""
    async with OmegaEntity(session=session, **user_entity_params.kwargs) as entity:
        yield entity


type USER_INTERNAL_ENTITY = Annotated[OmegaEntity, Depends(_get_user_internal_entity_instance)]
"""子依赖: 用户对象的 InternalEntity 实例"""


@asynccontextmanager
async def get_entity_session(
        bot: BaseBot,
        event: BaseEvent,
        *,
        acquire_type: 'EntityAcquireType' = 'event',
) -> AsyncGenerator[OmegaEntity, None]:
    """获取 InternalEntity 实例并开始会话"""
    entity_params = OmMI.get_event_depend_type(event)(bot=bot, event=event).extract_entity_params(acquire_type)
    async with begin_db_session() as session:
        async with OmegaEntity(session=session, **entity_params.kwargs) as entity:
            yield entity


@asynccontextmanager
async def get_entity_session_from_index(index_id: int) -> AsyncGenerator[OmegaEntity, None]:
    """根据 Entity 数据库索引 ID 获取 InternalEntity 实例并开始会话"""
    async with begin_db_session() as session:
        async with OmegaEntity.init_from_entity_index_id(session=session, index_id=index_id) as entity:
            yield entity


__all__ = [
    'EVENT_ENTITY_PARAMS',
    'EVENT_INTERNAL_ENTITY',
    'USER_ENTITY_PARAMS',
    'USER_INTERNAL_ENTITY',
    'extract_entity_params',
    'get_entity_session',
    'get_entity_session_from_index',
]
