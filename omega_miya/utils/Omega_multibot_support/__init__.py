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
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.event import Event, MessageEvent, NoticeEvent, RequestEvent
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.cqhttp.bot import Bot
from omega_miya.utils.Omega_Base import DBBot
from .multi_bot_utils import MultiBotUtils

driver = get_driver()
ONLINE_BOTS: Dict[str, Bot] = {}


@driver.on_bot_connect
async def upgrade_connected_bot(bot: Bot):
    global ONLINE_BOTS
    ONLINE_BOTS.update({bot.self_id: bot})
    # bot_info = await bot.get_login_info()
    bot_info = await bot.get_version_info()
    info = '||'.join([f'{k}:{v}' for (k, v) in bot_info.items()])
    bot_result = await DBBot(self_qq=int(bot.self_id)).upgrade(status=1, info=info)
    if bot_result.success():
        logger.opt(colors=True).info(f'Bot: {bot.self_id} <lg>已连接</lg>, '
                                     f'<lg>Database upgrade Success</lg>: {bot_result.info}')
    else:
        logger.opt(colors=True).error(f'Bot: {bot.self_id} <ly>已连接</ly>, '
                                      f'<r>Database upgrade Failed</r>: {bot_result.info}')


@driver.on_bot_disconnect
async def upgrade_disconnected_bot(bot: Bot):
    global ONLINE_BOTS
    ONLINE_BOTS.pop(bot.self_id, None)
    bot_result = await DBBot(self_qq=int(bot.self_id)).upgrade(status=0)
    if bot_result.success():
        logger.opt(colors=True).warning(f'Bot: {bot.self_id} <ly>已离线</ly>, '
                                        f'<lg>Database upgrade Success</lg>: {bot_result.info}')
    else:
        logger.opt(colors=True).error(f'Bot: {bot.self_id} <lr>已离线</lr>, '
                                      f'<r>Database upgrade Failed</r>: {bot_result.info}')


@run_preprocessor
async def unique_bot_responding_limit(matcher: Matcher, bot: Bot, event: Event, state: T_State):
    # 对于多协议端同时接入, 需匹配event.self_id与bot.self_id, 以保证会话不会被跨bot, 跨群, 跨用户触发
    if bot.self_id != str(event.self_id):
        logger.debug(f'Bot {bot.self_id} ignored event which not match self_id with {event.self_id}.')
        raise IgnoredException(f'Bot {bot.self_id} ignored event which not match self_id with {event.self_id}.')

    # 对于多协议端同时接入, 各个bot之间不能相互响应, 避免形成死循环
    event_user_id = str(getattr(event, 'user_id', -1))
    if event_user_id in [x for x in ONLINE_BOTS.keys() if x != bot.self_id]:
        logger.debug(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}.')
        raise IgnoredException(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}.')

    # 对于多协议端同时接入, 需要使用permission_updater限制bot id避免响应混乱
    # 在matcher首次运行时在statue中写入首次执行matcher的bot id
    if isinstance(event, (MessageEvent, NoticeEvent, RequestEvent)) and not matcher.temp:
        try:
            state.update({
                '_first_response_bot': bot.self_id,
                '_original_session_id': event.get_session_id(),
                '_original_permission': matcher.permission,
            })
            matcher.permission_updater(MultiBotUtils.first_response_bot_permission_updater)
        except ValueError:
            logger.warning(f'Unique bot responding limit preprocessor running failed with ValueError. '
                           f'The high probability is event had no session_id. Unsupported event: {repr(event)}.')
        except Exception as e:
            logger.error(f'Unique bot responding limit preprocessor running failed with error: {repr(e)}.')
