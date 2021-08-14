from typing import Dict
from nonebot import on_message
from nonebot.typing import T_State
from nonebot.exception import FinishedException
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from omega_miya.utils.omega_plugin_utils import OmegaRules
from .data_source import REPLY_RULES


LAST_MSG: Dict[int, str] = {}
LAST_REPEAT_MSG: Dict[int, str] = {}
REPEAT_COUNT: Dict[int, int] = {}

repeater = on_message(rule=OmegaRules.has_group_command_permission(), permission=GROUP, priority=100, block=False)


@repeater.handle()
async def handle_ignore_msg(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = event.raw_message
    if msg.startswith('/'):
        raise FinishedException
    elif msg.startswith('!SU'):
        raise FinishedException


@repeater.handle()
async def handle_auto_reply(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 处理回复规则
    msg = event.raw_message
    group_id = event.group_id
    check_res, reply_msg = REPLY_RULES.check_rule(group_id=group_id, message=msg)
    if check_res:
        await repeater.finish(reply_msg)


@repeater.handle()
async def handle_repeater(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 处理复读姬
    global LAST_MSG, LAST_REPEAT_MSG, REPEAT_COUNT
    group_id = event.group_id
    try:
        LAST_MSG[group_id]
    except KeyError:
        LAST_MSG[group_id] = ''
    try:
        LAST_REPEAT_MSG[group_id]
    except KeyError:
        LAST_REPEAT_MSG[group_id] = ''

    message = event.get_message()
    raw_msg = event.raw_message

    # 如果当前消息与上一条消息不同, 或者与上一次复读的消息相同, 则重置复读计数, 并更新上一条消息LAST_MSG
    if raw_msg != LAST_MSG[group_id] or raw_msg == LAST_REPEAT_MSG[group_id]:
        LAST_MSG[group_id] = raw_msg
        REPEAT_COUNT[group_id] = 0
        return
    # 否则这条消息和上条消息一致, 开始复读计数
    else:
        REPEAT_COUNT[group_id] += 1
        LAST_REPEAT_MSG[group_id] = ''
        # 当复读计数等于2时说明已经有连续三条同样的消息了, 此时触发复读, 更新上次服务消息LAST_REPEAT_MSG, 并重置复读计数
        if REPEAT_COUNT[group_id] >= 2:
            REPEAT_COUNT[group_id] = 0
            LAST_MSG[group_id] = ''
            LAST_REPEAT_MSG[group_id] = raw_msg
            await repeater.send(message)
