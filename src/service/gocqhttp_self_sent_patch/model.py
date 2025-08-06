"""
@Author         : Ailitonia
@Date           : 2022/05/23 19:51
@FileName       : model.py
@Project        : nonebot2_miya
@Description    : go-cqhttp message-sent model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal, override

from nonebot.adapters.onebot.utils import highlight_rich_message
from nonebot.adapters.onebot.v11.adapter import Adapter
from nonebot.adapters.onebot.v11.event import Anonymous, Event, MessageEvent
from nonebot.log import logger


def register_event[Event_T: type[Event]](event: Event_T) -> Event_T:
    Adapter.add_custom_model(event)
    logger.opt(colors=True).trace(
        f'Custom event <e>{event.__qualname__!r}</e> registered to adapter <e>{Adapter.get_name()!r}</e> '
        f'from module <g>{event.__module__!r}</g>'
    )
    return event


@register_event
class MessageSentEvent(MessageEvent):
    """自身发送消息事件"""

    post_type: Literal['message_sent']
    message_seq: int | None = None
    target_id: int | None = None
    group_id: int | None = 0
    anonymous: Anonymous | None = None
    to_me: bool = False

    @override
    def get_type(self) -> str:
        return 'message'

    @override
    def get_event_description(self) -> str:
        return (
            f"Message {self.message_id} from Bot {self.user_id}@[self-sent] "
            f"{''.join(highlight_rich_message(repr(self.original_message.to_rich_text())))}"
        )

    @override
    def get_user_id(self) -> str:
        return str(self.self_id)

    @override
    def get_session_id(self) -> str:
        return f'self_sent_{self.self_id}'

    @override
    def is_tome(self) -> bool:
        return False


__all__ = [
    'MessageSentEvent',
]
