"""
@Author         : Ailitonia
@Date           : 2026/9/5 19:04
@FileName       : event
@Project        : omega-miya
@Description    : Omega 内部事件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Literal, override

from nonebot.adapters import Event as BaseEvent
from nonebot.utils import escape_tag

if TYPE_CHECKING:
    from nonebot.adapters import Message as BaseMessage


class OmegaBaseEvent(BaseEvent):
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
    def get_message(self) -> 'BaseMessage':
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


class BotActionEvent(OmegaBaseEvent):
    """Bot 动作事件"""

    event_type: Literal['bot_action'] = 'bot_action'
    bot_id: str
    bot_type: str
    action: str

    @override
    def get_message(self) -> 'BaseMessage':
        raise ValueError('Event has no message!')

    @override
    def get_user_id(self) -> str:
        return str(self.bot_id)

    @override
    def get_session_id(self) -> str:
        return str(self.bot_id)

    @override
    def get_event_description(self) -> str:
        return f'Bot({self.bot_type}/{self.bot_id}) occurred the action: {self.action.upper()}'

    @override
    def is_tome(self) -> bool:
        return True


class BotConnectEvent(BotActionEvent):
    """Bot 已连接"""
    action: Literal['bot_connect'] = 'bot_connect'


class BotDisconnectEvent(BotActionEvent):
    """Bot 已断开连接"""
    action: Literal['bot_disconnect'] = 'bot_disconnect'


__all__ = [
    'BotActionEvent',
    'BotConnectEvent',
    'BotDisconnectEvent',
    'OmegaBaseEvent',
]
