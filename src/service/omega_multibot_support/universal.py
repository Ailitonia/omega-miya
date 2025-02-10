"""
@Author         : Ailitonia
@Date           : 2024/6/21 下午11:40
@FileName       : universal
@Project        : nonebot2_miya
@Description    : 通用多平台连接处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
from typing import Literal

from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.internal.adapter import Bot as BaseBot
from nonebot.internal.adapter import Event as BaseEvent
from nonebot.matcher import Matcher
from nonebot.message import handle_event, run_preprocessor

from src.service.omega_base.event import BotConnectEvent, BotDisconnectEvent

__ORIGINAL_RESPOND_ID_KEY: Literal['_omega_original_respond_id'] = '_omega_original_respond_id'
"""事件处理过程常量, 最初响应的 Bot 发起的会话 id 存储 key"""
__ONLINE_BOTS: dict[str, BaseBot] = {}
"""当前在线的 Bot"""
lock = asyncio.Lock()
driver = get_driver()


@run_preprocessor
async def __unique_bot_responding_limit(bot: BaseBot, event: BaseEvent):
    """多 Bot 响应去重预处理"""
    try:
        # 只检查有用户交互的事件
        event_user_id = event.get_user_id()
    except (NotImplementedError, ValueError):
        logger.opt(colors=True).trace('Unique bot responding limit checker Ignored with no-user_id event')
        return

    # 对于多协议端同时接入, 各个bot之间不能相互响应, 避免形成死循环
    if event_user_id in [x for x in __ONLINE_BOTS.keys() if x != bot.self_id]:
        logger.debug(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}')
        raise IgnoredException(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}')


@run_preprocessor
async def __first_responded_bot_limit(bot: BaseBot, event: BaseEvent, matcher: Matcher):
    """检查当前事件是否属于由最初响应的 Bot 发起的指定会话, 避免多 Bot 在同一会话中重复响应"""
    if (original_respond_id := matcher.state.get(__ORIGINAL_RESPOND_ID_KEY, None)) is None:
        logger.debug(f'Bot {bot.self_id} first responded event {event.get_event_name()!r}')
        matcher.state[__ORIGINAL_RESPOND_ID_KEY] = bot.self_id
    elif original_respond_id != bot.self_id:
        logger.debug(f'Bot {bot.self_id} ignored non-original responding event {event.get_event_name()!r}')
        raise IgnoredException(f'Bot {bot.self_id} ignored non-original responding event {event.get_event_name()!r}')


@driver.on_bot_connect
async def __init_bot_connect(bot: BaseBot):
    """在 Bot 连接时执行初始化操作"""
    async with lock:
        __ONLINE_BOTS.update({str(bot.self_id): bot})
        await handle_event(bot=bot, event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.type))


@driver.on_bot_disconnect
async def __dispose_bot_disconnect(bot: BaseBot):
    """在 Bot 断开连接时执行后续处理"""
    async with lock:
        __ONLINE_BOTS.pop(str(bot.self_id), None)
        await handle_event(bot=bot, event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.type))


def get_online_bots() -> dict[str, dict[str, BaseBot]]:
    """获取当前在线的 bot (根据 Adapter 分类)"""
    online_bots = {}
    for self_id, bot in __ONLINE_BOTS.items():
        adapter_name = bot.adapter.get_name()
        if adapter_name not in online_bots.keys():
            online_bots[adapter_name] = {}
        online_bots[adapter_name].update({self_id: bot})
    return online_bots


__all__ = [
    'get_online_bots',
]
