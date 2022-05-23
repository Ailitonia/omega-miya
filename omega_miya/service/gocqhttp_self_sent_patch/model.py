"""
@Author         : Ailitonia
@Date           : 2022/05/23 19:51
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp message-sent model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional, Type, TypeVar

from nonebot.adapters.onebot.v11.adapter import Adapter
from nonebot.adapters.onebot.v11.event import Event, MessageEvent, Anonymous, Sender
from nonebot.adapters.onebot.v11.message import Message
from nonebot.log import logger
from nonebot.typing import overrides
from nonebot.utils import escape_tag
from typing_extensions import Literal


Event_T = TypeVar("Event_T", bound=Type[Event])


def register_event(event: Event_T) -> Event_T:
    Adapter.add_custom_model(event)
    logger.opt(colors=True).debug(
        f"Custom event <e>{event.__event__!r}</e> registered "
        f"from class <g>{event.__qualname__!r}</g>"
    )
    return event


@register_event
class MessageSentEvent(Event):
    """自身发送消息事件"""

    __event__ = "message_sent"
    post_type: Literal["message_sent"]
    message_seq: int
    sub_type: str
    user_id: int
    message_type: str
    message_id: int
    message: Message
    raw_message: str
    font: int
    sender: Sender
    group_id: Optional[int] = 0
    anonymous: Optional[Anonymous] = None
    to_me: bool = False

    @overrides(Event)
    def get_event_name(self) -> str:
        sub_type = getattr(self, "sub_type", None)
        return f"{self.post_type}.{self.message_type}" + (
            f".{sub_type}" if sub_type else ""
        )

    @overrides(Event)
    def get_message(self) -> Message:
        return self.message

    @overrides(Event)
    def get_plaintext(self) -> str:
        return self.message.extract_plain_text()

    @overrides(Event)
    def get_event_description(self) -> str:
        return (
            f'Message {self.message_id} from bot self {self.self_id}@{self.message_type} "'
            + "".join(
                map(
                    lambda x: escape_tag(str(x))
                    if x.is_text()
                    else f"<le>{escape_tag(str(x))}</le>",
                    self.message,
                )
            )
            + '"'
        )

    @overrides(Event)
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
