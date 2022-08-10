"""
@Author         : Ailitonia
@Date           : 2021/10/07 0:57
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 随机口球
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import random
from nonebot.log import logger
from nonebot.plugin import on_command, PluginMetadata
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import Depends, CommandArg, Arg

from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.onebot_api import GoCqhttpBot


__plugin_meta__ = PluginMetadata(
    name="随机口球",
    description="【随机口球插件】\n"
                "自取随机口球礼包",
    usage="/随机口球 [n倍]",
    extra={"author": "Ailitonia"},
)


# 注册事件响应器
self_mute = on_command(
    'SelfMute',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='self_mute', level=10),
    aliases={'随机口球', '口球', '禁言礼包'},
    permission=GROUP,
    priority=10,
    block=True
)


@Depends
async def role_checker(bot: Bot, event: GroupMessageEvent, matcher: Matcher):
    gocq_bot = GoCqhttpBot(bot=bot)
    bot_role = await run_async_catching_exception(gocq_bot.get_group_member_info)(group_id=event.group_id,
                                                                                  user_id=bot.self_id)
    if bot_role.role not in ['owner', 'admin']:
        await matcher.finish('Bot非群管理员, 无法执行禁言操作QAQ')

    user_role = await run_async_catching_exception(gocq_bot.get_group_member_info)(group_id=event.group_id,
                                                                                   user_id=event.user_id)
    if user_role.role in ['owner', 'admin']:
        await matcher.finish('你也是个管理, 别来凑热闹OwO')


@Depends
async def parse_multiple(message: Message | str = Arg('multiple')) -> int:
    if isinstance(message, Message):
        message = message.extract_plain_text().strip()
    if multiple_text := re.search(r'^(\d+)倍$', message):
        multiple = int(multiple_text.group(1))
    elif message.isdigit():
        multiple = int(message)
    else:
        multiple = 1
    return multiple


@self_mute.handle()
async def handle_parser_multiple(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    multiple = cmd_arg.extract_plain_text().strip()
    if multiple:
        state.update({'multiple': multiple})
    else:
        state.update({'multiple': '1'})


@self_mute.got('multiple', parameterless=[role_checker])
async def handle_self_mute(bot: Bot, event: GroupMessageEvent, multiple: int = parse_multiple):
    # 随机禁言时间
    random_time = 2 * int(random.gauss(128 * multiple, 640 * multiple // 10))
    act_time = 60 if random_time < 60 else (random_time if random_time < 2591940 else 2591940)
    msg = f'既然你那么想被口球的话, 那我就成全你吧!\n送你一份{act_time // 60}分{act_time % 60}秒的禁言套餐哦, 谢谢惠顾~'

    await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=act_time)
    logger.info(f'SelfMute | Group({event.group_id})/User({event.user_id}) 被自己禁言 {act_time} 秒')
    await self_mute.finish(msg, at_sender=True)
