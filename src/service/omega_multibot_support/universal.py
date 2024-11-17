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

from nonebot import get_driver, logger
from nonebot.adapters import Bot, Event
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.message import handle_event, run_preprocessor
from nonebot.permission import Permission

from src.service.omega_base.event import BotConnectEvent, BotDisconnectEvent

__ONLINE_BOTS: dict[str, Bot] = {}
"""当前在线的 Bot"""
lock = asyncio.Lock()
driver = get_driver()


class __OriginalResponding:
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


async def __original_responding_permission_updater(bot: Bot, event: Event, matcher: Matcher) -> Permission:
    """匹配当前事件是否属于由最初响应的 Bot 发起的指定会话"""
    return Permission(
        __OriginalResponding(
            sessions=(event.get_session_id(),),
            original=bot.self_id,
            perm=matcher.permission
        )
    )


# 对于多协议端同时接入, 需要使用 permission_updater 限制 bot 的 self_id 避免响应混乱
Matcher.permission_updater(__original_responding_permission_updater)


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
    async with lock:
        __ONLINE_BOTS.update({str(bot.self_id): bot})
        await handle_event(bot=bot, event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.type))


@driver.on_bot_disconnect
async def __dispose_bot_disconnect(bot: Bot):
    """在 Bot 断开连接时执行后续处理"""
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
