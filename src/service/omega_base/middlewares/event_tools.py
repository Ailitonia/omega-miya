"""
@Author         : Ailitonia
@Date           : 2023/7/5 0:19
@FileName       : event_tools
@Project        : nonebot2_miya
@Description    : 平台事件处理适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Callable, Type

from nonebot.log import logger
from nonebot.internal.adapter.event import Event

from .types import EventHandler


__EVENT_HANDLER_MAP: dict[Type[Event], Type[EventHandler]] = {}


def register_event_handler(event: Type[Event]) -> Callable[[Type[EventHandler]], Type[EventHandler]]:
    """注册不同事件的 EventHandler"""

    def decorator(event_handler: Type[EventHandler]) -> Type[EventHandler]:
        """注册不同事件的 EventHandler"""
        global __EVENT_HANDLER_MAP

        __EVENT_HANDLER_MAP[event] = event_handler
        logger.opt(colors=True).debug(f'EventHandler <e>{event_handler.__name__!r}</e> is registered')
        return event_handler

    return decorator


def get_event_handler(event: Event) -> Type[EventHandler]:
    """从事件中提取 EventHandler"""

    for event_type in event.__class__.mro():
        if event_type in __EVENT_HANDLER_MAP:
            if not issubclass(event_type, Event):
                break
            return __EVENT_HANDLER_MAP[event_type]
    raise RuntimeError(f'Event {event.__class__} not supported')


__all__ = [
    'register_event_handler',
    'get_event_handler'
]
