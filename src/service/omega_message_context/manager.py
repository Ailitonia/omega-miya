"""
@Author         : Ailitonia
@Date           : 2025/7/31 16:29:56
@FileName       : manager.py
@Project        : omega-miya
@Description    : 插件消息上下文管理器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Any

from nonebot.adapters import Bot as BaseBot
from pydantic import BaseModel

from .utils import OPTIONAL_REPLY_MESSAGE_ID, query_context_value, set_context_value

if TYPE_CHECKING:
    from src.service.omega_base.middlewares.models import SentMessageResponse


class MessageContextManager[Data_T: BaseModel]:
    """消息上下文管理器"""

    def __init__(self, data_type: type[Data_T]):
        self._data_type = data_type

    def format_response_data_key(self, response: 'SentMessageResponse') -> str:
        """解析并格式化发送消息返回值为缓存键值"""
        return f'{self._data_type.__name__}:{response.bot_self_id}:{response.sent_message_id}'

    def format_interface_event_data_key(self, message_id: int | str, bot_self_id: str) -> str:
        """解析并格式化当前会话事件消息为缓存键值"""
        return f'{self._data_type.__name__}:{bot_self_id}:{message_id}'

    async def set_message_context(
            self,
            response: 'SentMessageResponse',
            data: Data_T | None = None,
            *,
            ttl_delta: int = 0,
            **context_data: Any,
    ) -> str:
        cache_key = self.format_response_data_key(response=response)
        if data is not None and isinstance(data, self._data_type):
            value = data.model_dump_json()
        else:
            value = self._data_type.model_validate(context_data).model_dump_json()

        await set_context_value(key=cache_key, value=value, ttl_delta=ttl_delta)
        return cache_key

    async def get_message_context(self, message_id: int | str, bot_self_id: str) -> Data_T | None:
        cache_key = self.format_interface_event_data_key(message_id=message_id, bot_self_id=bot_self_id)
        data = await query_context_value(key=cache_key)
        return None if not data else self._data_type.model_validate_json(data)

    """插件上下文使用的子依赖"""

    async def get_reply_context(
            self,
            bot: BaseBot,
            reply_message_id: OPTIONAL_REPLY_MESSAGE_ID,
    ) -> Data_T | None:
        """子依赖, 获取回复消息的上下文数据"""
        if reply_message_id is None:
            return None

        return await self.get_message_context(
            message_id=reply_message_id,
            bot_self_id=bot.self_id,
        )


__all__ = [
    'MessageContextManager',
]
