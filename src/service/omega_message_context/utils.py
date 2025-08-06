"""
@Author         : Ailitonia
@Date           : 2025/8/5 13:55:07
@FileName       : utils.py
@Project        : omega-miya
@Description    : 插件消息上下文缓存及处理工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated, TypeAlias

from nonebot import get_driver, logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.params import Depends

from src.service import OmegaMatcherInterface as OmMI
from ..apscheduler import scheduler
from ..omega_global_cache import OmegaGlobalCache

_MESSAGE_CONTEXT_CACHE_TTL: int = 86400 * 7
"""消息上下文数据缓存时间"""
_MESSAGE_CONTEXT_CACHE = OmegaGlobalCache(
    cache_name='omega_message_context',
    default_ttl=_MESSAGE_CONTEXT_CACHE_TTL,
)
"""消息上下文数据全局缓存"""


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


async def query_context_value(key: str) -> str | None:
    """读取消息上下文缓存"""
    data = await _MESSAGE_CONTEXT_CACHE.load(key=key)
    return None if not data else data  # 确保返回的不是空字符串


async def set_context_value(key: str, value: str, *, ttl_delta: int = 0) -> None:
    """设置消息上下文缓存"""
    return await _MESSAGE_CONTEXT_CACHE.save(key=key, value=value, ttl_delta=ttl_delta)


def _get_reply_message_id(bot: BaseBot, event: BaseEvent) -> str | None:
    """子依赖, 获取事件回复或引用消息 ID"""
    try:
        return OmMI.get_event_depend_type(target_event=event)(bot=bot, event=event).get_reply_msg_id()
    except Exception as e:
        logger.warning(f'current event {event.get_event_name()!r} not support reply message, {e}')
        return None


OPTIONAL_REPLY_MESSAGE_ID: TypeAlias = Annotated[
    str | None, Depends(_get_reply_message_id, use_cache=True)
]
"""获取事件回复或引用消息 ID"""


__all__ = [
    'OPTIONAL_REPLY_MESSAGE_ID',
    'query_context_value',
    'set_context_value',
]
