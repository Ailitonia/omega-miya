"""
@Author         : Ailitonia
@Date           : 2022/12/03 20:51
@FileName       : omega_multibot_support.py
@Project        : nonebot2_miya 
@Description    : Multi-Bot 多协议端接入支持
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from nonebot.adapters import Bot, Event
from nonebot.exception import IgnoredException
from nonebot.message import handle_event, run_preprocessor

from src.service.omega_event import BotConnectEvent, BotDisconnectEvent

from .gocqhttp import *


__ONLINE_BOTS: dict[str, Bot] = {}
"""当前在线的 Bot"""
driver = get_driver()


@run_preprocessor
async def __unique_bot_responding_limit(bot: Bot, event: Event):
    # 对于多协议端同时接入, 需匹配event.self_id与bot.self_id, 以保证会话不会被跨bot, 跨群, 跨用户触发
    if bot.self_id != str(getattr(event, 'self_id', -1)):
        logger.debug(f'Bot {bot.self_id} ignored event which not match self_id {getattr(event, "self_id")}')
        raise IgnoredException(f'Bot {bot.self_id} ignored event which not match self_id {getattr(event, "self_id")}')

    # 对于多协议端同时接入, 各个bot之间不能相互响应, 避免形成死循环
    event_user_id = str(getattr(event, 'user_id', -1))
    if event_user_id in [x for x in __ONLINE_BOTS.keys() if x != bot.self_id]:
        logger.debug(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}')
        raise IgnoredException(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}')


@driver.on_bot_connect
async def __init_bot_connect(bot: Bot):
    """在 Bot 连接时执行初始化操作"""
    global __ONLINE_BOTS
    __ONLINE_BOTS.update({str(bot.self_id): bot})

    await handle_event(bot=bot, event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.type))


@driver.on_bot_disconnect
async def __dispose_bot_disconnect(bot: Bot):
    """在 Bot 断开连接时执行后续处理"""
    global __ONLINE_BOTS
    __ONLINE_BOTS.pop(str(bot.self_id), None)

    await handle_event(bot=bot, event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.type))


__all__ = []
