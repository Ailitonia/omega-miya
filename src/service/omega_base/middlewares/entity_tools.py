"""
@Author         : Ailitonia
@Date           : 2023/6/24 2:56
@FileName       : entity_tools
@Project        : nonebot2_miya
@Description    : 内部 Entity 对象适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Callable, Type

from nonebot.log import logger
from nonebot.internal.adapter.event import Event

from .types import EntityDepend


__ENTITY_DEPENDS_MAP: dict[Type[Event], Type[EntityDepend]] = {}


def register_entity_depend(event: Type[Event]) -> Callable[[Type[EntityDepend]], Type[EntityDepend]]:
    """注册不同事件的 Entity 对象依赖类"""

    def decorator(entity_depend: Type[EntityDepend]) -> Type[EntityDepend]:
        """注册不同事件的 Entity 对象依赖类"""
        global __ENTITY_DEPENDS_MAP

        __ENTITY_DEPENDS_MAP[event] = entity_depend
        logger.opt(colors=True).debug(f'EntityDepend <e>{entity_depend.__name__!r}</e> is registered')
        return entity_depend

    return decorator


def get_entity_depend(event: Event) -> Type[EntityDepend]:
    """从事件中提取 Entity 对象依赖类"""

    for event_type in event.__class__.mro():
        if event_type in __ENTITY_DEPENDS_MAP:
            if not issubclass(event_type, Event):
                break
            return __ENTITY_DEPENDS_MAP[event_type]
    raise RuntimeError(f'Event {event.__class__} not supported')


__all__ = [
    'register_entity_depend',
    'get_entity_depend'
]
