"""
@Author         : Ailitonia
@Date           : 2021/05/23 19:40
@FileName       : __init__.py
@Project        : nonebot2_miya 
@Description    : Multi-Bot 多协议端接入支持
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Dict
from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException

from omega_miya.onebot_api import GoCqhttpBot


driver = get_driver()
_ONLINE_BOTS: Dict[str, Bot] = {}


@driver.on_bot_connect
async def connected_bot_database_upgrade(bot: Bot):
    """在 Bot 连接时更新数据库中 Bot 信息"""
    global _ONLINE_BOTS
    gocq_bot = GoCqhttpBot(bot=bot)
    _ONLINE_BOTS.update({gocq_bot.self_id: bot})
    try:
        await gocq_bot.connecting_db_upgrade()
        logger.opt(colors=True).success(f'Bot: {bot.self_id} <lg>已连接</lg>, <lg>Database upgrade Success</lg>')
    except Exception as e:
        logger.opt(colors=True).error(f'Bot: {bot.self_id} <ly>已连接</ly>, <r>Database upgrade Failed</r>: {repr(e)}')


@driver.on_bot_disconnect
async def disconnected_bot_database_upgrade(bot: Bot):
    """在 Bot 断开连接时更新数据库中 Bot 信息"""
    global _ONLINE_BOTS
    _bot = GoCqhttpBot(bot=bot)
    _ONLINE_BOTS.pop(_bot.self_id, None)
    try:
        await _bot.disconnecting_db_upgrade()
        logger.opt(colors=True).warning(f'Bot: {bot.self_id} <ly>已离线</ly>, <lg>Database upgrade Success</lg>')
    except Exception as e:
        logger.opt(colors=True).error(f'Bot: {bot.self_id} <lr>已离线</lr>, <r>Database upgrade Failed</r>: {repr(e)}')


@run_preprocessor
async def unique_bot_responding_limit(bot: Bot, event: Event):
    # 对于多协议端同时接入, 需匹配event.self_id与bot.self_id, 以保证会话不会被跨bot, 跨群, 跨用户触发
    if bot.self_id != str(event.self_id):
        logger.debug(f'Bot {bot.self_id} ignored event which not match self_id with {event.self_id}.')
        raise IgnoredException(f'Bot {bot.self_id} ignored event which not match self_id with {event.self_id}.')

    # 对于多协议端同时接入, 各个bot之间不能相互响应, 避免形成死循环
    event_user_id = str(getattr(event, 'user_id', -1))
    if event_user_id in [x for x in _ONLINE_BOTS.keys() if x != bot.self_id]:
        logger.debug(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}.')
        raise IgnoredException(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}.')
