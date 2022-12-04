"""
@Author         : Ailitonia
@Date           : 2022/12/03 17:59
@FileName       : base.py
@Project        : nonebot2_miya 
@Description    : Base event Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.adapters import Event as BaseEvent
from nonebot.adapters import Message
from nonebot.typing import overrides
from nonebot.utils import escape_tag


class Event(BaseEvent):
    """Omega 内部事件基类"""

    event_type: str

    @overrides(BaseEvent)
    def get_type(self) -> str:
        return self.event_type

    @overrides(BaseEvent)
    def get_event_name(self) -> str:
        return self.event_type

    @overrides(BaseEvent)
    def get_event_description(self) -> str:
        return escape_tag(str(self.dict()))

    @overrides(BaseEvent)
    def get_message(self) -> Message:
        raise ValueError('Event has no message!')

    @overrides(BaseEvent)
    def get_user_id(self) -> str:
        raise ValueError('Event has no context!')

    @overrides(BaseEvent)
    def get_session_id(self) -> str:
        raise ValueError('Event has no context!')

    @overrides(BaseEvent)
    def is_tome(self) -> bool:
        return False


__all__ = [
    'Event'
]
