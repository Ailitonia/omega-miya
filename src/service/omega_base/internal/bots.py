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
from typing import Literal

from nonebot import get_driver, logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.message import handle_event, run_preprocessor

from .event import BotConnectEvent, BotDisconnectEvent

__ORIGINAL_RESPOND_ID_KEY: Literal['_omega_original_respond_id'] = '_omega_original_respond_id'
"""事件处理过程常量, 最初响应的 Bot 发起的会话 id 存储 key"""
__ONLINE_BOTS: dict[tuple[str, str], BaseBot] = {}
"""当前在线的 Bot, 键为 (适配器名, Bot self_id), 支持同一账号跨适配器多实例同时在线"""
__BOT_LOCK = asyncio.Lock()
"""读写在线 Bot 字典时的锁 (仅保护 __ONLINE_BOTS, 严禁持锁期间进行事件分发)"""
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
    online_self_ids = {x.self_id for x in list(__ONLINE_BOTS.values()) if x.self_id != bot.self_id}
    if event_user_id in online_self_ids:
        logger.debug(
            f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}'
        )
        raise IgnoredException(
            f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}'
        )


@run_preprocessor
async def __first_responded_bot_limit(bot: BaseBot, event: BaseEvent, matcher: Matcher) -> None:
    """检查当前事件是否属于由最初响应的 Bot 发起的指定会话, 避免多 Bot 在同一会话中重复响应"""
    async with __BOT_LOCK:
        if (original_respond_id := matcher.state.get(__ORIGINAL_RESPOND_ID_KEY, None)) is None:
            matcher.state[__ORIGINAL_RESPOND_ID_KEY] = bot.self_id
            logger.debug(
                f'Bot {bot.self_id} first responded event {event.get_event_name()!r}'
            )
        elif original_respond_id != bot.self_id:
            logger.debug(
                f'Bot {bot.self_id} ignored non-original responding event {event.get_event_name()!r}'
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
