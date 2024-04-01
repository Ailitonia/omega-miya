"""
@Author         : Ailitonia
@Date           : 2022/05/23 19:51
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp message-sent model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional, Type, TypeVar, Literal

from nonebot.adapters.onebot.utils import highlight_rich_message
from nonebot.adapters.onebot.v11.adapter import Adapter
from nonebot.adapters.onebot.v11.event import Event, MessageEvent, Anonymous
from nonebot.log import logger
from nonebot.typing import overrides


Event_T = TypeVar("Event_T", bound=Type[Event])


def register_event(event: Event_T) -> Event_T:
    Adapter.add_custom_model(event)
    logger.opt(colors=True).trace(
        f"Custom event <e>{event.__qualname__!r}</e> registered to adapter <e>{Adapter.get_name()!r}</e> "
        f"from module <g>{event.__module__!r}</g>"
    )
    return event


@register_event
class MessageSentEvent(MessageEvent):
    """自身发送消息事件"""

    post_type: Literal["message_sent"]
    message_seq: Optional[int] = None
    target_id: Optional[int] = None
    group_id: Optional[int] = 0
    anonymous: Optional[Anonymous] = None
    to_me: bool = False

    @overrides(Event)
    def get_type(self) -> str:
        return "message"

    @overrides(Event)
    def get_event_description(self) -> str:
        return (
            f"Message {self.message_id} from Bot {self.user_id}@[self-sent] "
            f"{''.join(highlight_rich_message(repr(self.original_message.to_rich_text())))}"
        )

    @overrides(MessageEvent)
    def get_user_id(self) -> str:
        return str(self.self_id)

    @overrides(MessageEvent)
    def get_session_id(self) -> str:
        return f"self_sent_{self.self_id}"

    @overrides(Event)
    def is_tome(self) -> bool:
        return False


__all__ = [
    'MessageSentEvent'
]
