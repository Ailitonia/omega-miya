"""
@Author         : Ailitonia
@Date           : 2022/12/03 17:58
@FileName       : bot.py
@Project        : nonebot2_miya 
@Description    : Bot Action Event
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from nonebot.typing import overrides

from .base import Event as OmegaEvent


class BotActionEvent(OmegaEvent):
    """Bot 动作事件"""

    event_type: Literal['bot_action'] = 'bot_action'
    bot_id: str
    bot_type: str
    action: str

    @overrides(OmegaEvent)
    def get_user_id(self) -> str:
        return str(self.bot_id)

    @overrides(OmegaEvent)
    def get_session_id(self) -> str:
        return str(self.bot_id)

    @overrides(OmegaEvent)
    def get_event_description(self) -> str:
        return f'Bot<{self.bot_type}/{self.bot_id}> occurred the action: {self.action.upper()}'


class BotConnectEvent(BotActionEvent):
    """Bot 已连接"""
    action: Literal['bot_connect'] = 'bot_connect'

    @overrides(OmegaEvent)
    def is_tome(self) -> bool:
        return True


class BotDisconnectEvent(BotActionEvent):
    """Bot 已断开连接"""
    action: Literal['bot_disconnect'] = 'bot_disconnect'

    @overrides(OmegaEvent)
    def is_tome(self) -> bool:
        return True


__all__ = [
    'BotActionEvent',
    'BotConnectEvent',
    'BotDisconnectEvent'
]
