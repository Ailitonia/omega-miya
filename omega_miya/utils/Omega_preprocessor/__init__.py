"""
@Author         : Ailitonia
@Date           : 2021/07/09 19:49
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : preprocessor 统一处理冷却、权限等
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.message import run_preprocessor
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.event import Event, MessageEvent
from nonebot.adapters.cqhttp.bot import Bot
from .permission import preprocessor_permission
from .cooldown import preprocessor_cooldown


@run_preprocessor
async def handle_preprocessor(matcher: Matcher, bot: Bot, event: Event, state: T_State):
    # 处理权限
    if isinstance(event, MessageEvent):
        await preprocessor_permission(matcher=matcher, bot=bot, event=event, state=state)

    # 处理冷却
    if isinstance(event, MessageEvent):
        await preprocessor_cooldown(matcher=matcher, bot=bot, event=event, state=state)
