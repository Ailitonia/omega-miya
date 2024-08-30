"""
@Author         : Ailitonia
@Date           : 2021/10/07 0:57
@FileName       : command.py
@Project        : nonebot2_miya 
@Description    : 随机口球
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import functools
import random
import re
from typing import Annotated

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
    Message as OneBotV11Message,
    GroupMessageEvent as OneBotV11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Depends
from nonebot.plugin import on_command
from nonebot.typing import T_State

from src.service import enable_processor_state


@Depends
async def role_checker(bot: OneBotV11Bot, event: OneBotV11GroupMessageEvent, matcher: Matcher):
    bot_role = await bot.get_group_member_info(group_id=event.group_id, user_id=int(bot.self_id))
    if bot_role.get('role') not in ['owner', 'admin']:
        await matcher.finish('Bot非群管理员, 无法执行禁言操作QAQ')

    user_role = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    if user_role.get('role') in ['owner', 'admin']:
        await matcher.finish('你也是个管理, 别来凑热闹OwO')


async def handle_parse_multiple(state: T_State, cmd_arg: Annotated[OneBotV11Message, CommandArg()]):
    if cmd_arg:
        cmd_text = cmd_arg.extract_plain_text().strip()

        if multiple_text := re.search(r'^(\d+)倍$', cmd_text):
            multiple = int(multiple_text.group(1))
        elif cmd_text.isdigit():
            multiple = int(cmd_text)
        else:
            multiple = functools.reduce(lambda x, y: x * y, (int(x) for x in str(len(cmd_text)) if x.isdigit())) + 1
    else:
        multiple = 1

    state.update({'multiple': multiple})


# 注册事件响应器
@on_command(
    'self_mute',
    aliases={'随机口球', '口球'},
    permission=GROUP,
    handlers=[handle_parse_multiple],
    priority=10,
    block=True,
    state=enable_processor_state(name='OneBotV11SelfMute', level=10)
).handle(parameterless=[role_checker])
async def handle_self_mute(bot: OneBotV11Bot, event: OneBotV11GroupMessageEvent, matcher: Matcher, state: T_State):
    multiple = int(state.get('multiple', 1))

    # 随机禁言时间
    random_time = 2 * int(random.gauss(128 * multiple, 640 * multiple // 10))
    act_time = 60 if random_time < 60 else (random_time if random_time < 2591940 else 2591940)
    msg = f'既然你那么想被口球的话, 那我就成全你吧!\n送你一份{act_time // 60}分{act_time % 60}秒的禁言套餐哦, 谢谢惠顾~'

    await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=act_time)
    logger.info(f'SelfMute | Group({event.group_id})/User({event.user_id}) 被自己禁言 {act_time} 秒, 倍率 {multiple}')
    await matcher.finish(msg, at_sender=True)


__all__ = []
