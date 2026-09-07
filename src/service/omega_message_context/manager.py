"""
@Author         : Ailitonia
@Date           : 2025/7/31 16:29:56
@FileName       : manager.py
@Project        : omega-miya
@Description    : 插件消息上下文管理器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from nonebot import get_driver, logger
from nonebot.adapters import Bot as BaseBot, Event as BaseEvent
from nonebot_plugin_alconna.uniseg import Receipt, reply_fetch
from pydantic import BaseModel

from ..apscheduler import scheduler
from ..omega_global_cache import OmegaGlobalCache

_MESSAGE_CONTEXT_CACHE_TTL: int = 86400 * 7
"""消息上下文数据缓存时间"""

_MESSAGE_CONTEXT_CACHE = OmegaGlobalCache(
    cache_name='omega_message_context',
    default_ttl=_MESSAGE_CONTEXT_CACHE_TTL,
)
"""消息上下文数据全局缓存"""


async def set_context_value(key: str, value: str, *, ttl_delta: int = 0) -> None:
    """设置消息上下文缓存"""
    if not key.strip():
        raise ValueError('Invalid key')

    await _MESSAGE_CONTEXT_CACHE.save(key=key, value=value, ttl_delta=ttl_delta)


async def query_context_value(key: str) -> str | None:
    """读取消息上下文缓存"""
    data = await _MESSAGE_CONTEXT_CACHE.load(key=key)
    return data or None  # 确保返回的不是空字符串


@scheduler.scheduled_job(
    'cron',
    hour='4',
    minute='6',
    second='8',
    id='omega_message_context_sync_message_context_cache',
    coalesce=True,
)
@get_driver().on_startup
async def _sync_message_context_cache() -> None:
    """同步消息上下文数据缓存"""
    try:
        await _MESSAGE_CONTEXT_CACHE.sync_internal()
        logger.opt(colors=True).success('<lc>OmegaMessageContext</lc> | <lg>消息上下文缓存同步成功</lg>')
    except Exception as e:
        logger.opt(colors=True).error(f'<lc>OmegaMessageContext</lc> | <r>消息上下文缓存同步失败</r>, {e}')


class MessageContextManager[Data_T: BaseModel]:
    """消息上下文管理器"""

    def __init__(self, data_type: type[Data_T]):
        self._data_type = data_type

    def format_response_data_key(self, receipt: 'Receipt') -> str:
        """解析并格式化发送消息返回值为缓存键值"""
        return f'{self._data_type.__name__}:{receipt.bot.self_id}:{receipt.msg_ids[0]}'

    def format_interface_event_data_key(self, bot_self_id: str, message_id: str) -> str:
        """格式化消息 ID 为缓存键值"""
        return f'{self._data_type.__name__}:{bot_self_id}:{message_id}'

    async def set_message_context(
            self,
            receipt: 'Receipt',
            data: Data_T | None = None,
            *,
            ttl_delta: int = 0,
            **context_data: Any,
    ) -> str:
        """保存消息上下文数据"""
        cache_key = self.format_response_data_key(receipt=receipt)

        if data is not None and isinstance(data, self._data_type):
            value = data.model_dump_json()
        else:
            value = self._data_type.model_validate(context_data).model_dump_json()

        await set_context_value(key=cache_key, value=value, ttl_delta=ttl_delta)
        return cache_key

    async def get_message_context(self, bot_self_id: str, message_id: str) -> Data_T | None:
        """提取消息上下文数据"""
        cache_key = self.format_interface_event_data_key(bot_self_id=bot_self_id, message_id=message_id)
        data = await query_context_value(key=cache_key)
        return None if not data else self._data_type.model_validate_json(data)

    async def get_reply_context(self, bot: BaseBot, event: BaseEvent) -> Data_T | None:
        """插件上下文使用的子依赖, 获取回复消息的上下文数据"""
        reply = await reply_fetch(bot=bot, event=event)
        if not reply:
            return None
        return await self.get_message_context(bot_self_id=bot.self_id, message_id=reply.id)


__all__ = [
    'MessageContextManager',
]
