"""
@Author         : Ailitonia
@Date           : 2021/05/29 11:27
@FileName       : multi_bot_test.py
@Project        : nonebot2_miya
@Description    :
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import on_command
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.permission import Permission
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event, MessageEvent


permission_count = 0


@run_preprocessor
async def _permission_checker(matcher: Matcher, bot: Bot, event: MessageEvent, state: T_State):
    print('==>> _permission_checker progressing, permission.checkers now is: ', matcher.permission.checkers)


test = on_command('test', permission=SUPERUSER, priority=10, block=True)


@test.permission_updater
async def _permission_updater(bot: Bot, event: Event, state: T_State, permission: Permission):
    global permission_count
    print('==>> _permission_updater progressing, permission.checkers now is: ', permission.checkers)
    print('==>> permission_count is: ', permission_count)
    permission_count += 1

    async def _new_permission(_bot: Bot, _event: Event) -> bool:
        if permission_count > 3:
            return False and await permission(bot, event)
        else:
            return True and await permission(bot, event)
    return Permission(_new_permission)


@test.got('sub_command', prompt='sub_command?')
async def _handle(bot: Bot, event: MessageEvent, state: T_State):
    sub_command = state['sub_command']
    msg = f'Last msg: {sub_command}, sending anything to continue...'
    await test.reject(msg)
