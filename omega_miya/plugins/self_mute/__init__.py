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
from nonebot import on_command, logger
from nonebot.plugin.export import export
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.omega_plugin_utils import init_export, init_processor_state, RoleChecker


# Custom plugin usage text
__plugin_custom_name__ = '随机口球'
__plugin_usage__ = r'''【随机口球】
自取随机口球礼包

**Permission**
Friend Private
Command & Lv.10
or AuthNode

**AuthNode**
basic

**Usage**
/随机口球 [n倍]'''


# Init plugin export
init_export(export(), __plugin_custom_name__, __plugin_usage__)


# 注册事件响应器
self_mute = on_command(
    'SelfMute',
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(
        name='self_mute',
        command=True,
        level=10),
    aliases={'随机口球', '口球', '禁言礼包'},
    permission=GROUP,
    priority=10,
    block=True)


@self_mute.handle()
async def handle_self_mute(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip()
    # 检查是否有倍数参数
    if multiple_text := re.search(r'^(\d+)倍$', args):
        multiple = int(multiple_text.groups()[0])
    else:
        multiple = 1

    # 检查bot和用户身份
    if not (await RoleChecker(group_id=event.group_id, user_id=event.self_id, bot=bot).is_group_admin()):
        await self_mute.finish('Bot非群管理员, 无法执行禁言操作QAQ')
    if await RoleChecker(group_id=event.group_id, user_id=event.user_id, bot=bot).is_group_admin():
        await self_mute.finish('你也是个管理, 别来凑热闹OvO', at_sender=True)

    # 随机禁言时间
    random_time = 2 * int(random.gauss(128 * multiple, 640 * multiple // 10))
    act_time = 60 if random_time < 60 else (random_time if random_time < 2591940 else 2591940)
    msg = f'既然你那么想被口球的话, 那我就成全你吧!\n送你一份{act_time // 60}分{act_time % 60}秒禁言套餐哦, 谢谢惠顾~'

    await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=act_time)
    await self_mute.finish(msg, at_sender=True)
    logger.info(f'Group: {event.group_id}, User: {event.user_id} 抽取了 {act_time} 秒的禁言套餐')
