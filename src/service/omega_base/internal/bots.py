"""
@Author         : Ailitonia
@Date           : 2026/9/5 19:20
@FileName       : bots
@Project        : omega-miya
@Description    : Omega 多协议端接入支持, 通用多平台连接处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import time

from nonebot import get_driver, logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import IgnoredException
from nonebot.message import handle_event, run_preprocessor

from .event import BotConnectEvent, BotDisconnectEvent

__FIRST_RESPOND_TTL: float = 300.0
"""首响应 Bot 会话归属的有效期 (秒)"""
__FIRST_RESPOND_REGISTRY: dict[str, tuple[str, float]] = {}
"""首响应 Bot 会话归属注册表, 键为事件 session_id, 值为 (Bot self_id, 过期时间戳)"""
__ONLINE_BOTS: dict[tuple[str, str], BaseBot] = {}
"""当前在线的 Bot, 键为 (适配器名, Bot self_id), 支持同一账号跨适配器多实例同时在线"""
__BOT_LOCK = asyncio.Lock()
"""读写进程级 Bot 状态时的锁 (仅保护 __ONLINE_BOTS/__FIRST_RESPOND_REGISTRY, 严禁持锁期间进行事件分发)"""
_DRIVER = get_driver()
"""获取全局 Driver 用于注册钩子函数"""


@run_preprocessor
async def __unique_bot_responding_limit(bot: BaseBot, event: BaseEvent) -> None:
    """多 Bot 响应去重预处理"""
    try:
        # 只检查有用户交互的事件
        event_user_id = event.get_user_id()
    except (NotImplementedError, ValueError):
        logger.opt(colors=True).trace(
            'Unique bot responding limit checker Ignored with no-user_id event'
        )
        return

    # 对于多协议端同时接入, 各个bot之间不能相互响应, 避免形成死循环
    # 快照读取在线 Bot 列表, 避免与连接/断开钩子并发读写冲突
    # 注意: 按 self_id 跨适配器比对是有意设计 (同一账号经不同协议端接入时防死循环),
    # 代价是不同平台数值 ID 恰好碰撞的极端场景下会误忽略该用户的消息
    online_self_ids = {x.self_id for x in list(__ONLINE_BOTS.values()) if x.self_id != bot.self_id}
    if event_user_id in online_self_ids:
        logger.debug(
            f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}'
        )
        raise IgnoredException(
            f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}'
        )


@run_preprocessor
async def __first_responded_bot_limit(bot: BaseBot, event: BaseEvent) -> None:
    """检查当前事件所属会话是否已由最初响应的 Bot 接管, 避免多 Bot 在同一会话中重复响应

    会话归属以事件 session_id 粒度登记在进程级注册表中 (TTL 内有效, 同一 Bot 的后续事件刷新有效期);
    无法提取 session_id 的事件不参与检查
    """
    try:
        # 只检查可提取会话 id 的事件
        session_id = event.get_session_id()
    except (NotImplementedError, ValueError):
        logger.opt(colors=True).trace(
            'First responded bot limit checker Ignored with no-session_id event'
        )
        return

    now = time.monotonic()
    async with __BOT_LOCK:
        # 惰性清理过期会话归属
        expired_keys = [k for k, (_, expire_at) in __FIRST_RESPOND_REGISTRY.items() if expire_at <= now]
        for key in expired_keys:
            __FIRST_RESPOND_REGISTRY.pop(key, None)

        record = __FIRST_RESPOND_REGISTRY.get(session_id)
        if record is None:
            __FIRST_RESPOND_REGISTRY[session_id] = (bot.self_id, now + __FIRST_RESPOND_TTL)
            logger.debug(
                f'Bot {bot.self_id} first responded event {event.get_event_name()!r} in session {session_id!r}'
            )
        elif record[0] == bot.self_id:
            # 同一会话内同一 Bot 的后续事件, 刷新会话归属有效期
            __FIRST_RESPOND_REGISTRY[session_id] = (bot.self_id, now + __FIRST_RESPOND_TTL)
        else:
            logger.debug(
                f'Bot {bot.self_id} ignored non-original responding event {event.get_event_name()!r} '
                f'in session {session_id!r}'
            )
            raise IgnoredException(
                f'Bot {bot.self_id} ignored non-original responding event {event.get_event_name()!r}'
            )


@_DRIVER.on_bot_connect
async def __init_bot_connect(bot: BaseBot) -> None:
    """在 Bot 连接时执行初始化操作"""
    async with __BOT_LOCK:
        __ONLINE_BOTS[(bot.adapter.get_name(), str(bot.self_id))] = bot
    await handle_event(bot=bot, event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()))


@_DRIVER.on_bot_disconnect
async def __dispose_bot_disconnect(bot: BaseBot) -> None:
    """在 Bot 断开连接时执行后续处理"""
    async with __BOT_LOCK:
        __ONLINE_BOTS.pop((bot.adapter.get_name(), str(bot.self_id)), None)
    await handle_event(bot=bot, event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()))


def get_online_bots() -> dict[str, dict[str, BaseBot]]:
    """获取当前在线的 bot (根据 Adapter 分类)"""
    online_bots = {}
    for bot in list(__ONLINE_BOTS.values()):
        adapter_name = bot.adapter.get_name()
        if adapter_name not in online_bots.keys():
            online_bots[adapter_name] = {}
        online_bots[adapter_name].update({str(bot.self_id): bot})
    return online_bots


__all__ = [
    'get_online_bots',
]
