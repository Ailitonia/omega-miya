"""
@Author         : Ailitonia
@Date           : 2022/12/03 17:59
@FileName       : base.py
@Project        : nonebot2_miya 
@Description    : Base event Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import override

from nonebot.adapters import Event as BaseEvent
from nonebot.adapters import Message
from nonebot.utils import escape_tag


class Event(BaseEvent):
    """Omega 内部事件基类"""

    event_type: str

    @override
    def get_type(self) -> str:
        return self.event_type

    @override
    def get_event_name(self) -> str:
        return self.event_type

    @override
    def get_event_description(self) -> str:
        return escape_tag(str(self.model_dump()))

    @override
    def get_message(self) -> Message:
        raise NotImplementedError

    @override
    def get_user_id(self) -> str:
        raise NotImplementedError

    @override
    def get_session_id(self) -> str:
        raise NotImplementedError

    @override
    def is_tome(self) -> bool:
        raise NotImplementedError


__all__ = [
    'Event'
]
