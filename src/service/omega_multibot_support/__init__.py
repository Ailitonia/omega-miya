"""
@Author         : Ailitonia
@Date           : 2022/12/03 20:51
@FileName       : omega_multibot_support.py
@Project        : nonebot2_miya 
@Description    : Multi-Bot 多协议端接入支持
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio

from nonebot import get_driver, logger
from nonebot.adapters import Bot, Event
from nonebot.exception import IgnoredException
from nonebot.message import handle_event, run_preprocessor

from src.service.omega_base.event import BotConnectEvent, BotDisconnectEvent

from . import console as console
from . import onebot_v11 as onebot_v11
from . import qq as qq
from . import telegram as telegram


__ONLINE_BOTS: dict[str, Bot] = {}
"""当前在线的 Bot"""
lock = asyncio.Lock()
driver = get_driver()


@run_preprocessor
async def __unique_bot_responding_limit(bot: Bot, event: Event):
    # 对于多协议端同时接入, 各个bot之间不能相互响应, 避免形成死循环
    try:
        event_user_id = event.get_user_id()
    except (NotImplementedError, ValueError):
        logger.opt(colors=True).trace('Unique bot responding limit checker Ignored with no-user_id event')
        return

    if event_user_id in [x for x in __ONLINE_BOTS.keys() if x != bot.self_id]:
        logger.debug(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}')
        raise IgnoredException(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}')


@driver.on_bot_connect
async def __init_bot_connect(bot: Bot):
    """在 Bot 连接时执行初始化操作"""
    global __ONLINE_BOTS
    async with lock:
        __ONLINE_BOTS.update({str(bot.self_id): bot})
        await handle_event(bot=bot, event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.type))


@driver.on_bot_disconnect
async def __dispose_bot_disconnect(bot: Bot):
    """在 Bot 断开连接时执行后续处理"""
    global __ONLINE_BOTS
    async with lock:
        __ONLINE_BOTS.pop(str(bot.self_id), None)
        await handle_event(bot=bot, event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.type))


def get_online_bots() -> dict[str, dict[str, Bot]]:
    """获取当前在线的 bot (根据 Adapter 分类)"""
    online_bots = {}
    for self_id, bot in __ONLINE_BOTS.items():
        adapter_name = bot.adapter.get_name()
        if adapter_name not in online_bots.keys():
            online_bots[adapter_name] = {}
        online_bots[adapter_name].update({self_id: bot})
    return online_bots


__all__ = [
    'get_online_bots'
]
