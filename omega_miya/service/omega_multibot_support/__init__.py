"""
@Author         : Ailitonia
@Date           : 2021/05/23 19:40
@FileName       : omega_multibot_support.py
@Project        : nonebot2_miya 
@Description    : Multi-Bot 多协议端接入支持
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import Permission
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, MessageEvent, NoticeEvent, RequestEvent
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException

from omega_miya.onebot_api import GoCqhttpBot


driver = get_driver()
_ONLINE_BOTS: dict[str, Bot] = {}
"""当前在线的 Bot"""


class OriginalResponding:
    """检查当前事件是否属于由最初响应的 Bot 发起的指定会话

    参数:
        sessions: 会话 ID 元组
        original: 最初响应的 Bot
        perm: 需同时满足的权限
    """

    __slots__ = ('sessions', 'original', 'perm')

    def __init__(self, sessions: tuple[str, ...], original: str | None = None, perm: Permission | None = None) -> None:
        self.sessions = sessions
        self.original = original
        self.perm = perm

    async def __call__(self, bot: Bot, event: Event) -> bool:
        return bool(
            event.get_session_id() in self.sessions
            and (self.original is None or bot.self_id == self.original)
            and (self.perm is None or await self.perm(bot, event))
        )


async def original_responding_permission_updater(bot: Bot, event: Event, matcher: Matcher) -> Permission:
    """匹配当前事件是否属于由最初响应的 Bot 发起的指定会话"""
    return Permission(OriginalResponding(sessions=(event.get_session_id(),),
                                         original=bot.self_id, perm=matcher.permission))


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
async def unique_bot_responding_limit(bot: Bot, event: Event, matcher: Matcher):
    # 对于多协议端同时接入, 需匹配event.self_id与bot.self_id, 以保证会话不会被跨bot, 跨群, 跨用户触发
    if bot.self_id != str(event.self_id):
        logger.debug(f'Bot {bot.self_id} ignored event which not match self_id with {event.self_id}.')
        raise IgnoredException(f'Bot {bot.self_id} ignored event which not match self_id with {event.self_id}.')

    # 对于多协议端同时接入, 各个bot之间不能相互响应, 避免形成死循环
    event_user_id = str(getattr(event, 'user_id', -1))
    if event_user_id in [x for x in _ONLINE_BOTS.keys() if x != bot.self_id]:
        logger.debug(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}.')
        raise IgnoredException(f'Bot {bot.self_id} ignored responding self-relation event with Bot {event_user_id}.')

    # 对于多协议端同时接入, 需要使用 permission_updater 限制 bot 的 self_id 避免响应混乱
    if isinstance(event, (MessageEvent, NoticeEvent, RequestEvent)) and not matcher.temp:
        if not matcher.__class__._default_permission_updater:
            matcher.permission_updater(original_responding_permission_updater)
